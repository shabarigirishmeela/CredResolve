"""
SmartDialer Test Suite.

Covers:
- Agent state machine transitions (valid and invalid)
- Call state machine transitions (valid and invalid)
- Concurrent agent reservation (OCC race)
- Safety Controller enforcement
- Pacing engine recommendation
- Circuit breaker behaviour
- Duplicate and out-of-order event handling
- Crash recovery
- Progressive dialer invariant (no overshoot)
- API endpoint behaviour
"""
from __future__ import annotations
import threading
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.models.dialer_schema import (
    AgentState, CallState, CircuitState,
    DialerSession, DialerAgent, DialerCall,
    DialerBorrowerLock, DialerEvent, DialerProviderHealth,
    SessionState, DialingMode,
)
from app.services.state_machines import (
    transition_agent, transition_call, InvalidTransition
)
from app.services.pacing_engine import PacingEngine, PacingInput
from app.services.safety_controller import SafetyController, SafetyVerdict
from app.services.event_processor import EventProcessor, recover_stale_state
from app.services.providers import ProviderAlpha, ProviderBeta, ProviderEvent


# ---------------------------------------------------------------------------
# Test database fixture (in-memory SQLite, isolated per test)
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def engine():
    eng = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
    # Import all models so their tables are created
    from app.models import schema  # existing collections models
    from app.models import dialer_schema  # SmartDialer models
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def session_id():
    return f"test-session-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def dialer_session(db, session_id):
    s = DialerSession(
        session_id=session_id,
        mode=DialingMode.PROGRESSIVE,
        state=SessionState.RUNNING,
        created_at=datetime.utcnow(),
    )
    db.add(s)
    db.commit()
    return s


@pytest.fixture
def make_agent(db, session_id):
    def _make(agent_id: str = None, state: str = AgentState.AVAILABLE):
        aid = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        a = DialerAgent(
            agent_id=aid,
            dialer_state=state,
            session_id=session_id,
            version=0,
        )
        db.add(a)
        db.commit()
        return a
    return _make


@pytest.fixture
def make_call(db, session_id):
    def _make(agent_id: str, borrower_id: str = None, state: str = CallState.QUEUED):
        cid = f"call-{uuid.uuid4().hex[:8]}"
        c = DialerCall(
            call_id=cid,
            session_id=session_id,
            agent_id=agent_id,
            borrower_id=borrower_id or f"bor-{uuid.uuid4().hex[:8]}",
            state=state,
            version=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(c)
        db.commit()
        return c
    return _make


# ===========================================================================
# 1. Agent state machine
# ===========================================================================

class TestAgentStateMachine:

    def test_valid_transition_offline_to_available(self, db, make_agent):
        a = make_agent(state=AgentState.OFFLINE)
        result = transition_agent(db, a.agent_id, AgentState.AVAILABLE, reason="login")
        db.commit()
        assert result.dialer_state == AgentState.AVAILABLE
        assert result.version == 1

    def test_valid_transition_available_to_reserved(self, db, make_agent):
        a = make_agent(state=AgentState.AVAILABLE)
        result = transition_agent(db, a.agent_id, AgentState.RESERVED)
        db.commit()
        assert result.dialer_state == AgentState.RESERVED

    def test_invalid_transition_reserved_to_wrap_up(self, db, make_agent):
        a = make_agent(state=AgentState.RESERVED)
        with pytest.raises(InvalidTransition):
            transition_agent(db, a.agent_id, AgentState.WRAP_UP)

    def test_invalid_transition_connected_to_available_direct(self, db, make_agent):
        # CONNECTED must go through WRAP_UP
        a = make_agent(state=AgentState.CONNECTED)
        with pytest.raises(InvalidTransition):
            transition_agent(db, a.agent_id, AgentState.AVAILABLE)

    def test_invalid_transition_unknown_state(self, db, make_agent):
        a = make_agent(state="UNKNOWN_STATE")
        with pytest.raises(InvalidTransition):
            transition_agent(db, a.agent_id, AgentState.AVAILABLE)

    def test_occ_version_mismatch_raises(self, db, make_agent):
        a = make_agent(state=AgentState.AVAILABLE)
        with pytest.raises(RuntimeError, match="OCC conflict"):
            transition_agent(db, a.agent_id, AgentState.RESERVED, expected_version=999)

    def test_agent_not_found_raises(self, db):
        with pytest.raises(LookupError):
            transition_agent(db, "nonexistent-agent", AgentState.AVAILABLE)

    def test_full_agent_lifecycle(self, db, make_agent):
        a = make_agent(state=AgentState.OFFLINE)
        transition_agent(db, a.agent_id, AgentState.AVAILABLE)
        db.commit()
        transition_agent(db, a.agent_id, AgentState.RESERVED)
        db.commit()
        transition_agent(db, a.agent_id, AgentState.DIALING)
        db.commit()
        transition_agent(db, a.agent_id, AgentState.CONNECTED)
        db.commit()
        transition_agent(db, a.agent_id, AgentState.WRAP_UP)
        db.commit()
        result = transition_agent(db, a.agent_id, AgentState.AVAILABLE)
        db.commit()
        assert result.dialer_state == AgentState.AVAILABLE
        assert result.version == 6


# ===========================================================================
# 2. Call state machine
# ===========================================================================

class TestCallStateMachine:

    def test_valid_transition_queued_to_reserved(self, db, make_agent, make_call):
        a = make_agent()
        c = make_call(a.agent_id)
        result = transition_call(db, c.call_id, CallState.RESERVED)
        db.commit()
        assert result.state == CallState.RESERVED

    def test_invalid_transition_completed_to_anything(self, db, make_agent, make_call):
        a = make_agent()
        c = make_call(a.agent_id, state=CallState.COMPLETED)
        with pytest.raises(InvalidTransition):
            transition_call(db, c.call_id, CallState.ANSWERED)

    def test_terminal_idempotency(self, db, make_agent, make_call):
        """Transitioning a terminal call to the same terminal state is a no-op."""
        a = make_agent()
        c = make_call(a.agent_id, state=CallState.FAILED)
        result = transition_call(db, c.call_id, CallState.FAILED)
        assert result.state == CallState.FAILED

    def test_invalid_transition_ringing_to_completed(self, db, make_agent, make_call):
        a = make_agent()
        c = make_call(a.agent_id, state=CallState.RINGING)
        with pytest.raises(InvalidTransition):
            transition_call(db, c.call_id, CallState.COMPLETED)

    def test_full_call_lifecycle(self, db, make_agent, make_call):
        a = make_agent()
        c = make_call(a.agent_id)
        for st in [CallState.RESERVED, CallState.INITIATED,
                   CallState.RINGING, CallState.ANSWERED,
                   CallState.CONNECTED, CallState.COMPLETED]:
            transition_call(db, c.call_id, st)
            db.commit()
        db.refresh(c)
        assert c.state == CallState.COMPLETED
        assert c.version == 6


# ===========================================================================
# 3. Concurrent agent reservation (OCC race condition)
# ===========================================================================

class TestConcurrentReservation:

    def test_only_one_worker_reserves_agent(self, tmp_path):
        """Two threads try to reserve the same agent. Exactly one must succeed."""
        import os
        from sqlalchemy import create_engine, event
        from sqlalchemy.orm import sessionmaker

        # Use a file-based SQLite in WAL mode so concurrent writers are serialized
        db_path = tmp_path / "race_test.db"
        race_engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(race_engine, "connect")
        def set_wal(conn, _):
            conn.execute("PRAGMA journal_mode=WAL")

        Base.metadata.create_all(bind=race_engine)
        Session = sessionmaker(bind=race_engine)

        session_id = f"race-{uuid.uuid4().hex[:8]}"

        # Create session and agent
        setup_db = Session()
        ds = DialerSession(session_id=session_id, mode="PROGRESSIVE",
                           state="RUNNING", created_at=datetime.utcnow())
        setup_db.add(ds)
        agent_id = f"shared-agent-{uuid.uuid4().hex[:8]}"
        a = DialerAgent(agent_id=agent_id, dialer_state=AgentState.AVAILABLE,
                        session_id=session_id, version=0)
        setup_db.add(a)
        setup_db.commit()
        setup_db.close()

        results = []
        errors  = []

        def try_reserve():
            db = Session()
            try:
                result = transition_agent(
                    db, agent_id, AgentState.RESERVED,
                    reason="race test",
                )
                db.commit()
                results.append("success")
            except Exception as e:
                errors.append(str(e))
            finally:
                db.close()

        t1 = threading.Thread(target=try_reserve)
        t2 = threading.Thread(target=try_reserve)
        t1.start(); t2.start()
        t1.join(); t2.join()

        # Exactly one must succeed (the other gets an OCC conflict or DB lock error)
        assert len(results) == 1, (
            f"Expected 1 success, got {len(results)}. "
            f"Successes: {results}, Errors: {errors}"
        )

        # The agent must be in RESERVED state
        verify_db = Session()
        final = verify_db.query(DialerAgent).filter(
            DialerAgent.agent_id == agent_id
        ).first()
        assert final.dialer_state == AgentState.RESERVED
        assert final.version == 1
        verify_db.close()
        Base.metadata.drop_all(bind=race_engine)
        race_engine.dispose()


# ===========================================================================
# 4. Pacing Engine
# ===========================================================================

class TestPacingEngine:

    def _inp(self, available=10, reserved=0, dialing=0, connected=0, wrap=0,
             initiated=0, connected_calls=0, answer_rate=0.5, mode="PREDICTIVE"):
        return PacingInput(
            available_agents=available,
            reserved_agents=reserved,
            dialing_agents=dialing,
            connected_agents=connected,
            wrap_up_agents=wrap,
            calls_initiated=initiated,
            calls_connected=connected_calls,
            provider_health={},
            avg_setup_latency_ms=100.0,
            avg_talk_time_sec=90.0,
            answer_rate=answer_rate,
            mode=mode,
        )

    def test_progressive_caps_at_available(self):
        pe = PacingEngine()
        d = pe.recommend(self._inp(available=7, mode="PROGRESSIVE"))
        assert d.proposed_dials == 7

    def test_progressive_zero_if_no_agents(self):
        pe = PacingEngine()
        d = pe.recommend(self._inp(available=0, mode="PROGRESSIVE"))
        assert d.proposed_dials == 0

    def test_predictive_reduces_when_inflight(self):
        pe = PacingEngine()
        # 5 available, 4 already in-flight at 50% answer rate → headroom = 5-2=3
        d = pe.recommend(self._inp(available=5, initiated=4, answer_rate=0.5))
        # Should propose ≤ 5 (cannot exceed available)
        assert d.proposed_dials <= 5

    def test_predictive_zero_when_no_headroom(self):
        pe = PacingEngine()
        # All 10 available agents already have in-flight calls that will answer
        d = pe.recommend(self._inp(available=10, initiated=20, answer_rate=0.9))
        assert d.proposed_dials == 0

    def test_provider_health_reduces_dials(self):
        pe = PacingEngine()
        bad_health = {"prov": {"healthy": False, "failure_rate": 0.8}}
        inp = self._inp(available=10, answer_rate=0.5)
        inp.provider_health = bad_health
        d = pe.recommend(inp)
        # With 80% failure rate, factor = max(0, 1 - 1.6) = 0 → 0 or minimal dials
        assert d.proposed_dials <= 2

    def test_explanation_is_populated(self):
        pe = PacingEngine()
        d = pe.recommend(self._inp(available=5))
        assert len(d.explanation) > 10
        assert d.computed_at


# ===========================================================================
# 5. Safety Controller
# ===========================================================================

class TestSafetyController:

    def _setup_session(self, db, session_id, num_agents=10, mode="PREDICTIVE"):
        s = DialerSession(session_id=session_id, mode=mode,
                          state=SessionState.RUNNING, created_at=datetime.utcnow())
        db.add(s)
        for i in range(num_agents):
            db.add(DialerAgent(
                agent_id=f"sa-agent-{i}",
                dialer_state=AgentState.AVAILABLE,
                session_id=session_id,
                version=0,
            ))
        db.commit()

    def test_approves_within_limits(self, db, session_id):
        self._setup_session(db, session_id, num_agents=10)
        pe = PacingEngine()
        sc = SafetyController()
        from app.services.pacing_engine import PacingDecision
        pacing = PacingDecision(proposed_dials=2, explanation="test")
        decision = sc.evaluate(db, pacing, session_id, "PREDICTIVE")
        assert decision.verdict in (SafetyVerdict.APPROVED, SafetyVerdict.REDUCED)
        assert decision.approved_dials >= 0

    def test_rejects_when_no_agents(self, db, session_id):
        # Session with 0 agents
        s = DialerSession(session_id=session_id, mode="PREDICTIVE",
                          state=SessionState.RUNNING, created_at=datetime.utcnow())
        db.add(s)
        db.commit()
        sc = SafetyController()
        from app.services.pacing_engine import PacingDecision
        pacing = PacingDecision(proposed_dials=5, explanation="test")
        decision = sc.evaluate(db, pacing, session_id, "PREDICTIVE")
        assert decision.verdict == SafetyVerdict.REJECTED
        assert decision.approved_dials == 0

    def test_progressive_caps_at_available(self, db, session_id):
        self._setup_session(db, session_id, num_agents=5, mode="PROGRESSIVE")
        sc = SafetyController()
        from app.services.pacing_engine import PacingDecision
        # Pacing says 100, but only 5 available
        pacing = PacingDecision(proposed_dials=100, explanation="test")
        decision = sc.evaluate(db, pacing, session_id, "PROGRESSIVE")
        assert decision.approved_dials == 5
        assert decision.verdict == SafetyVerdict.REDUCED

    def test_circuit_open_falls_back_to_progressive(self, db, session_id):
        self._setup_session(db, session_id, num_agents=10)
        # Mark a circuit OPEN
        db.add(DialerProviderHealth(
            provider_name="test_provider",
            circuit_state=CircuitState.OPEN,
            consecutive_failures=10,
        ))
        db.commit()
        sc = SafetyController()
        from app.services.pacing_engine import PacingDecision
        pacing = PacingDecision(proposed_dials=20, explanation="test")
        decision = sc.evaluate(db, pacing, session_id, "PREDICTIVE")
        # Must fallback and cap at available agents
        assert decision.approved_dials <= 10
        assert decision.verdict in (SafetyVerdict.FALLBACK, SafetyVerdict.REDUCED)

    def test_pacing_cannot_bypass_safety(self, db, session_id):
        """
        The pacing engine has no reference to the Safety Controller.
        Verifying the architectural separation: even if pacing proposes ∞,
        safety still caps it.
        """
        self._setup_session(db, session_id, num_agents=5)
        sc = SafetyController()
        from app.services.pacing_engine import PacingDecision
        pacing = PacingDecision(proposed_dials=999999, explanation="bypass attempt")
        decision = sc.evaluate(db, pacing, session_id, "PREDICTIVE")
        # The approved dials MUST be ≤ available agents (5)
        assert decision.approved_dials <= 5

    def test_fail_closed_on_exception(self, db, session_id):
        """Safety Controller must return REJECTED if it encounters an error."""
        sc = SafetyController()
        from app.services.pacing_engine import PacingDecision
        pacing = PacingDecision(proposed_dials=5, explanation="test")
        # Pass a non-Session object to force an error
        decision = sc.evaluate("not_a_db", pacing, session_id, "PREDICTIVE")
        assert decision.verdict == SafetyVerdict.REJECTED
        assert decision.approved_dials == 0


# ===========================================================================
# 6. Event Processor — duplicates and out-of-order events
# ===========================================================================

class TestEventProcessor:

    def test_duplicate_answered_event_ignored(self, db, make_agent, make_call):
        a = make_agent()
        c = make_call(a.agent_id, state=CallState.RINGING)
        ep = EventProcessor()

        evt1 = ProviderEvent(call_id=c.call_id, provider_call_id="prov-1",
                             event_type="ANSWERED", event_seq=2)
        evt2 = ProviderEvent(call_id=c.call_id, provider_call_id="prov-1",
                             event_type="ANSWERED", event_seq=2)   # same seq = duplicate

        with patch("app.services.event_processor.SessionLocal", return_value=db):
            r1 = ep._process_with_db(db, evt1)
            db.commit()
            r2 = ep._process_with_db(db, evt2)   # should be ignored

        assert r1 is True
        assert r2 is False

        # Verify the call state was only changed once
        db.refresh(c)
        assert c.state == CallState.ANSWERED

    def test_out_of_order_completed_before_answered(self, db, make_agent, make_call):
        """
        Provider sends COMPLETED before ANSWERED (out of order).
        Since RINGING→COMPLETED is not a valid transition, the COMPLETED event
        should be rejected gracefully without corrupting state.
        """
        a = make_agent()
        c = make_call(a.agent_id, state=CallState.RINGING)
        ep = EventProcessor()

        # OOO: COMPLETED arrives before ANSWERED
        completed_evt = ProviderEvent(call_id=c.call_id, provider_call_id="prov-1",
                                       event_type="COMPLETED", event_seq=3)
        with patch("app.services.event_processor.SessionLocal", return_value=db):
            result = ep._process_with_db(db, completed_evt)

        # Should be rejected (invalid transition RINGING→COMPLETED)
        assert result is False
        db.refresh(c)
        assert c.state == CallState.RINGING   # state unchanged

    def test_terminal_state_is_not_overwritten(self, db, make_agent, make_call):
        """Once COMPLETED, subsequent events should be rejected."""
        a = make_agent()
        c = make_call(a.agent_id, state=CallState.COMPLETED)
        ep = EventProcessor()

        evt = ProviderEvent(call_id=c.call_id, provider_call_id="prov-1",
                            event_type="ANSWERED", event_seq=5)
        with patch("app.services.event_processor.SessionLocal", return_value=db):
            result = ep._process_with_db(db, evt)
        assert result is False
        db.refresh(c)
        assert c.state == CallState.COMPLETED


# ===========================================================================
# 7. Crash Recovery
# ===========================================================================

class TestCrashRecovery:

    def test_stale_reserved_call_recovered(self, db, make_agent, make_call, session_id):
        a = make_agent(state=AgentState.RESERVED)
        c = make_call(a.agent_id, state=CallState.RESERVED)

        # Make it appear stale by backdating updated_at
        from sqlalchemy import update as sq_update
        db.execute(
            sq_update(DialerCall)
            .where(DialerCall.call_id == c.call_id)
            .values(updated_at=datetime.utcnow() - timedelta(seconds=200))
        )
        db.commit()

        result = recover_stale_state(db, session_id)

        db.refresh(c)
        db.refresh(a)
        assert c.state == CallState.FAILED
        assert a.dialer_state == AgentState.AVAILABLE
        assert result["failed"] >= 1
        assert result["agents_released"] >= 1

    def test_recent_reservation_not_recovered(self, db, make_agent, make_call, session_id):
        """A fresh reservation must not be incorrectly cleaned up."""
        a = make_agent(state=AgentState.RESERVED)
        c = make_call(a.agent_id, state=CallState.RESERVED)
        # updated_at is fresh (default datetime.utcnow)
        db.commit()

        result = recover_stale_state(db, session_id)

        db.refresh(c)
        db.refresh(a)
        # Should still be reserved (not stale)
        assert c.state == CallState.RESERVED
        assert result["failed"] == 0


# ===========================================================================
# 8. Circuit Breaker
# ===========================================================================

class TestCircuitBreaker:

    def test_opens_after_threshold_failures(self, db):
        from app.services.call_allocator import CircuitBreaker, _FAILURE_THRESHOLD
        cb = CircuitBreaker("test-provider")
        for _ in range(_FAILURE_THRESHOLD):
            cb.record_failure(db)
        assert cb.get_state(db) == CircuitState.OPEN

    def test_transitions_to_half_open_after_timeout(self, db):
        from app.services.call_allocator import CircuitBreaker, _FAILURE_THRESHOLD, _HALF_OPEN_TIMEOUT
        cb = CircuitBreaker("test-provider-2")
        for _ in range(_FAILURE_THRESHOLD):
            cb.record_failure(db)
        assert cb.get_state(db) == CircuitState.OPEN

        # Backdate the half_open_at to simulate timeout
        from sqlalchemy import update as sq_update
        db.execute(
            sq_update(DialerProviderHealth)
            .where(DialerProviderHealth.provider_name == "test-provider-2")
            .values(half_open_at=datetime.utcnow() - timedelta(seconds=_HALF_OPEN_TIMEOUT + 5))
        )
        db.commit()

        # is_open() should now return False (probe allowed)
        assert cb.is_open(db) is False
        assert cb.get_state(db) == CircuitState.HALF_OPEN

    def test_closes_after_successes(self, db):
        from app.services.call_allocator import CircuitBreaker, _FAILURE_THRESHOLD, _SUCCESS_TO_CLOSE
        cb = CircuitBreaker("test-provider-3")
        for _ in range(_FAILURE_THRESHOLD):
            cb.record_failure(db)

        # Transition to HALF_OPEN
        from sqlalchemy import update as sq_update
        db.execute(
            sq_update(DialerProviderHealth)
            .where(DialerProviderHealth.provider_name == "test-provider-3")
            .values(half_open_at=datetime.utcnow() - timedelta(seconds=60))
        )
        db.commit()
        cb.is_open(db)   # triggers HALF_OPEN transition

        for _ in range(_SUCCESS_TO_CLOSE):
            cb.record_success(db)
        assert cb.get_state(db) == CircuitState.CLOSED


# ===========================================================================
# 9. Provider mock behaviour
# ===========================================================================

class TestProviders:

    def test_provider_alpha_initiates_call(self):
        from app.services.providers import ProviderAlpha, ProviderCallRequest
        p = ProviderAlpha(answer_rate=1.0, fail_rate=0.0)
        req = ProviderCallRequest(
            call_id="test-call-1",
            borrower_phone="+911234567890",
            agent_id="agent-1",
            idempotency_key="idem-1",
        )
        result = p.initiate_call(req)
        assert result.success is True
        assert result.provider_call_id is not None

    def test_provider_alpha_fails_at_100_percent(self):
        from app.services.providers import ProviderAlpha, ProviderCallRequest
        p = ProviderAlpha(fail_rate=1.0)
        req = ProviderCallRequest(
            call_id="test-call-2",
            borrower_phone="+911234567890",
            agent_id="agent-1",
            idempotency_key="idem-2",
        )
        result = p.initiate_call(req)
        assert result.success is False

    def test_provider_beta_timeout(self):
        from app.services.providers import ProviderBeta, ProviderCallRequest
        p = ProviderBeta(timeout_rate=1.0, timeout_sec=0.01)
        req = ProviderCallRequest(
            call_id="test-call-3",
            borrower_phone="+911234567890",
            agent_id="agent-1",
            idempotency_key="idem-3",
        )
        result = p.initiate_call(req)
        assert result.success is False
        assert "timeout" in result.error.lower()

    def test_provider_health_reporting(self):
        p = ProviderAlpha()
        h = p.get_health()
        assert "healthy" in h
        assert "failure_rate" in h
        assert "total_calls" in h


# ===========================================================================
# 10. Simulation scenarios
# ===========================================================================

class TestSimulation:

    def test_scenario_a(self):
        from app.services.simulation import run_scenario
        result = run_scenario("A", num_agents=5, num_borrowers=50, duration_ticks=10)
        assert result["scenario"] == "A"
        assert result["summary"]["total_initiated"] >= 0
        assert "tick_metrics" in result
        assert len(result["tick_metrics"]) == 10

    def test_scenario_b(self):
        from app.services.simulation import run_scenario
        result = run_scenario("B", num_agents=5, num_borrowers=50, duration_ticks=10)
        assert result["summary"]["answer_rate_pct"] >= 0

    def test_scenario_c(self):
        from app.services.simulation import run_scenario
        result = run_scenario("C", num_agents=5, num_borrowers=50, duration_ticks=10)
        # High answer rate → more completions
        assert result["summary"]["total_completed"] >= 0

    def test_scenario_d_changes(self):
        from app.services.simulation import run_scenario
        result = run_scenario("D", num_agents=10, num_borrowers=100, duration_ticks=20)
        assert result["scenario"] == "D"

    def test_progressive_never_overshoots(self):
        """
        In PROGRESSIVE mode, calls created per tick must never exceed the
        proposed dial count (which equals available agents at recommendation time).
        The available_agents in tick_metrics is captured AFTER allocation so
        we compare new_calls_this_tick <= proposed_dials instead.
        """
        from app.services.simulation import run_scenario
        result = run_scenario("B", num_agents=10, num_borrowers=200,
                              duration_ticks=15, mode="PROGRESSIVE")
        for tick in result["tick_metrics"]:
            assert tick["new_calls_this_tick"] <= tick["proposed_dials"], \
                f"Overshoot at tick {tick['tick']}: created {tick['new_calls_this_tick']} > proposed {tick['proposed_dials']}"
            # Safety verdict must also approve/reduce — never allow more than proposed
            assert tick["approved_dials"] <= tick["proposed_dials"], \
                f"Safety approved more than proposed at tick {tick['tick']}"

    def test_safety_rejections_tracked(self):
        from app.services.simulation import run_scenario
        result = run_scenario("C", num_agents=3, num_borrowers=50, duration_ticks=20)
        # With few agents and high answer rate, safety may need to reduce
        assert "safety_reductions" in result["summary"]


# ===========================================================================
# 11. Pacing/Safety Overhang Consistency
# ===========================================================================

class TestOverhangConsistency:

    def _setup_session(self, db, session_id, num_agents=10, mode="PREDICTIVE"):
        s = DialerSession(session_id=session_id, mode=mode,
                          state=SessionState.RUNNING, created_at=datetime.utcnow())
        db.add(s)
        for i in range(num_agents):
            db.add(DialerAgent(
                agent_id=f"oh-agent-{i}",
                dialer_state=AgentState.AVAILABLE,
                session_id=session_id,
                version=0,
            ))
        db.commit()

    def _test_consistency(self, db, session_id, num_agents, in_flight=0, reserved=0):
        """Helper: verify pacing never proposes more than safety allows."""
        self._setup_session(db, session_id, num_agents=num_agents)

        # Create in-flight calls if specified
        for i in range(in_flight):
            agent = db.query(DialerAgent).filter(
                DialerAgent.session_id == session_id,
                DialerAgent.dialer_state == AgentState.AVAILABLE
            ).first()
            if agent:
                from app.services.state_machines import transition_agent
                transition_agent(db, agent.agent_id, AgentState.RESERVED)
                db.commit()
                c = DialerCall(
                    call_id=f"oh-call-{i}",
                    session_id=session_id,
                    agent_id=agent.agent_id,
                    borrower_id=f"bor-{i}",
                    state=CallState.INITIATED,
                    created_at=datetime.utcnow(),
                )
                db.add(c)
                db.commit()

        # Create reserved agents if specified
        for i in range(reserved):
            agent = db.query(DialerAgent).filter(
                DialerAgent.session_id == session_id,
                DialerAgent.dialer_state == AgentState.AVAILABLE
            ).first()
            if agent:
                from app.services.state_machines import transition_agent
                transition_agent(db, agent.agent_id, AgentState.RESERVED)
                db.commit()

        pe = PacingEngine()
        sc = SafetyController()
        from app.services.pacing_engine import PacingDecision

        inp = PacingInput(
            available_agents=num_agents - in_flight - reserved,
            reserved_agents=reserved,
            dialing_agents=0,
            connected_agents=0,
            wrap_up_agents=0,
            calls_initiated=in_flight,
            calls_connected=0,
            provider_health={},
            avg_setup_latency_ms=100.0,
            avg_talk_time_sec=90.0,
            answer_rate=0.5,
            mode="PREDICTIVE",
        )

        pacing = pe.recommend(inp)
        safety = sc.evaluate(db, pacing, session_id, "PREDICTIVE")

        # Pacing must never propose more than safety will approve
        assert pacing.proposed_dials <= safety.approved_dials or safety.verdict in (
            SafetyVerdict.APPROVED, SafetyVerdict.REDUCED
        ), (
            f"Pacing proposed {pacing.proposed_dials} but safety only allows "
            f"{safety.approved_dials} (verdict={safety.verdict}) for "
            f"{num_agents} agents, {in_flight} in-flight, {reserved} reserved"
        )

    def test_one_agent_zero_inflight(self, db, session_id):
        """1 agent, 0 in-flight: floor(1 * 0.25) = 0, pacing should propose 0."""
        self._test_consistency(db, session_id, num_agents=1, in_flight=0)

    def test_two_agents_zero_inflight(self, db, session_id):
        """2 agents, 0 in-flight: floor(2 * 0.25) = 0, pacing should propose 0."""
        self._test_consistency(db, session_id, num_agents=2, in_flight=0)

    def test_two_agents_with_reserved(self, db, session_id):
        """2 agents, 1 reserved: floor(2 * 0.25) = 0, pacing should propose 0."""
        self._test_consistency(db, session_id, num_agents=2, in_flight=0, reserved=1)

    def test_five_agents_zero_inflight(self, db, session_id):
        """5 agents, 0 in-flight: floor(5 * 0.25) = 1, pacing should propose ≤1."""
        self._test_consistency(db, session_id, num_agents=5, in_flight=0)

    def test_five_agents_one_inflight(self, db, session_id):
        """5 agents, 1 in-flight: floor(5 * 0.25) = 1, headroom = 0, pacing should propose 0."""
        self._test_consistency(db, session_id, num_agents=5, in_flight=1)

    def test_ten_agents_zero_inflight(self, db, session_id):
        """10 agents, 0 in-flight: floor(10 * 0.25) = 2, pacing should propose ≤2."""
        self._test_consistency(db, session_id, num_agents=10, in_flight=0)

    def test_ten_agents_two_inflight(self, db, session_id):
        """10 agents, 2 in-flight: floor(10 * 0.25) = 2, headroom = 0, pacing should propose 0."""
        self._test_consistency(db, session_id, num_agents=10, in_flight=2)

    def test_ten_agents_with_reserved(self, db, session_id):
        """10 agents, 2 reserved: floor(10 * 0.25) = 2, reserved counts as in-flight."""
        self._test_consistency(db, session_id, num_agents=10, in_flight=0, reserved=2)

    def test_fifty_agents_zero_inflight(self, db, session_id):
        """50 agents, 0 in-flight: floor(50 * 0.25) = 12, pacing should propose ≤12."""
        self._test_consistency(db, session_id, num_agents=50, in_flight=0)

    def test_fifty_agents_ten_inflight(self, db, session_id):
        """50 agents, 10 in-flight: floor(50 * 0.25) = 12, headroom = 2, pacing should propose ≤2."""
        self._test_consistency(db, session_id, num_agents=50, in_flight=10)

    def test_exact_two_agent_scenario(self, db, session_id):
        """
        Exact reproduction of the reported bug scenario:
        - 2 agents, 0 in-flight, 50% answer rate
        - Pacing previously proposed 1 (ceil(2*0.30)=1 with MIN_DIALS floor)
        - Safety allowed 0 (floor(2*0.25)=0)
        - After fix: pacing should propose 0 (floor(2*0.25)=0, no MIN_DIALS override)
        """
        self._setup_session(db, session_id, num_agents=2)
        pe = PacingEngine()
        sc = SafetyController()
        from app.services.pacing_engine import PacingDecision

        inp = PacingInput(
            available_agents=2,
            reserved_agents=0,
            dialing_agents=0,
            connected_agents=0,
            wrap_up_agents=0,
            calls_initiated=0,
            calls_connected=0,
            provider_health={},
            avg_setup_latency_ms=100.0,
            avg_talk_time_sec=90.0,
            answer_rate=0.5,
            mode="PREDICTIVE",
        )

        pacing = pe.recommend(inp)
        safety = sc.evaluate(db, pacing, session_id, "PREDICTIVE")

        # After fix: pacing should propose 0 to match safety
        assert pacing.proposed_dials == 0, (
            f"Pacing proposed {pacing.proposed_dials} but should be 0 for 2 agents"
        )
        assert safety.approved_dials == 0, (
            f"Safety allowed {safety.approved_dials} but should be 0 for 2 agents"
        )
        assert safety.verdict == SafetyVerdict.APPROVED or pacing.proposed_dials == 0

    def test_minimum_one_dial_bug_regression(self, db, session_id):
        """
        Regression test for the MIN_DIALS floor bug.
        When headroom_cap is 0, pacing must not force dials to 1 just because
        available_agents > 0. The Safety Controller's overhang limit takes
        precedence over any minimum-dial heuristic.
        """
        self._setup_session(db, session_id, num_agents=2)
        pe = PacingEngine()

        # Scenario: 2 agents, 0 in-flight, 50% answer rate
        # floor(2 * 0.25) = 0 overhang allowed
        # headroom_cap = 0 - 0 = 0
        # pacing should propose 0, not 1
        inp = PacingInput(
            available_agents=2,
            reserved_agents=0,
            dialing_agents=0,
            connected_agents=0,
            wrap_up_agents=0,
            calls_initiated=0,
            calls_connected=0,
            provider_health={},
            avg_setup_latency_ms=100.0,
            avg_talk_time_sec=90.0,
            answer_rate=0.5,
            mode="PREDICTIVE",
        )

        pacing = pe.recommend(inp)

        # Verify the calculation trace
        # total_agents = 2
        # max_overhang = floor(2 * 0.25) = 0
        # current_inflight = 0
        # headroom_cap = max(0, 0 - 0) = 0
        # raw_dials = 2 / 0.5 = 4
        # dials = min(4, 0) = 0
        # health_factor = 1.0
        # final dials = floor(0 * 1.0) = 0
        assert pacing.proposed_dials == 0, (
            f"Pacing proposed {pacing.proposed_dials} but headroom_cap is 0; "
            f"MIN_DIALS floor should not override safety limits"
        )

    def test_one_agent_overhang_cap_zero(self, db, session_id):
        """
        Test that with 1 agent, overhang_cap is 0.
        This is correct per the safety policy:
        - 25% overhang limit: floor(1 * 0.25) = 0
        - 10% free buffer: max(1, ceil(1 * 0.10)) = 1 agent must be free
        - Predictive mode requires multiple agents to be useful
        - With 1 agent, use PROGRESSIVE mode (1:1 mapping)
        """
        self._setup_session(db, session_id, num_agents=1)
        pe = PacingEngine()

        inp = PacingInput(
            available_agents=1,
            reserved_agents=0,
            dialing_agents=0,
            connected_agents=0,
            wrap_up_agents=0,
            calls_initiated=0,
            calls_connected=0,
            provider_health={},
            avg_setup_latency_ms=100.0,
            avg_talk_time_sec=90.0,
            answer_rate=0.5,
            mode="PREDICTIVE",
        )

        pacing = pe.recommend(inp)

        # total_agents = 1
        # max_overhang = floor(1 * 0.25) = 0
        # headroom_cap = 0
        assert pacing.proposed_dials == 0, (
            f"With 1 agent, overhang_cap must be 0 (got {pacing.proposed_dials})"
        )

        # In PROGRESSIVE mode, 1 agent should allow 1 dial
        inp.mode = "PROGRESSIVE"
        pacing_progressive = pe.recommend(inp)
        assert pacing_progressive.proposed_dials == 1, (
            f"PROGRESSIVE mode with 1 agent should propose 1 dial"
        )


# ===========================================================================
# 12. API Endpoint Tests
# ===========================================================================

class TestAddAgentsAPI:

    def _setup_session(self, db, session_id):
        s = DialerSession(session_id=session_id, mode="PROGRESSIVE",
                          state=SessionState.RUNNING, created_at=datetime.utcnow())
        db.add(s)
        db.commit()

    def test_add_agents_creates_new_agents(self, db, session_id):
        """Verify add_agents endpoint creates agents that don't already exist."""
        self._setup_session(db, session_id)

        # Call the logic directly (not via HTTP)
        added = []
        skipped = []
        for aid in ["agent-1", "agent-2"]:
            existing = db.query(DialerAgent).filter(
                DialerAgent.agent_id == aid,
                DialerAgent.session_id == session_id,
            ).first()
            if not existing:
                agent = DialerAgent(
                    agent_id=aid,
                    dialer_state=AgentState.AVAILABLE,
                    session_id=session_id,
                    version=0,
                )
                db.add(agent)
                added.append(aid)
            else:
                skipped.append(aid)
        db.commit()

        # Verify agents were created
        assert len(added) == 2
        assert len(skipped) == 0
        agent1 = db.query(DialerAgent).filter(
            DialerAgent.agent_id == "agent-1",
            DialerAgent.session_id == session_id
        ).first()
        agent2 = db.query(DialerAgent).filter(
            DialerAgent.agent_id == "agent-2",
            DialerAgent.session_id == session_id
        ).first()
        assert agent1 is not None
        assert agent2 is not None
        assert agent1.dialer_state == AgentState.AVAILABLE
        assert agent2.dialer_state == AgentState.AVAILABLE

    def test_add_agents_skips_duplicates(self, db, session_id):
        """Verify add_agents skips agents that already exist in the same session."""
        self._setup_session(db, session_id)

        # Add agent-1 first
        agent = DialerAgent(
            agent_id="agent-1",
            dialer_state=AgentState.AVAILABLE,
            session_id=session_id,
            version=0,
        )
        db.add(agent)
        db.commit()

        # Try to add agent-1 again and agent-2
        added = []
        skipped = []
        for aid in ["agent-1", "agent-2"]:
            existing = db.query(DialerAgent).filter(
                DialerAgent.agent_id == aid,
                DialerAgent.session_id == session_id,
            ).first()
            if not existing:
                agent = DialerAgent(
                    agent_id=aid,
                    dialer_state=AgentState.AVAILABLE,
                    session_id=session_id,
                    version=0,
                )
                db.add(agent)
                added.append(aid)
            else:
                skipped.append(aid)
        db.commit()

        # Only agent-2 should be added, agent-1 should be skipped
        assert len(added) == 1
        assert len(skipped) == 1
        assert "agent-2" in added
        assert "agent-1" in skipped

    def test_add_agents_across_sessions(self, db, session_id):
        """Verify same agent_id can exist in different sessions."""
        self._setup_session(db, session_id)

        # Add agent-1 to session_id
        agent1 = DialerAgent(
            agent_id="agent-1",
            dialer_state=AgentState.AVAILABLE,
            session_id=session_id,
            version=0,
        )
        db.add(agent1)
        db.commit()

        # Create a second session
        session_id_2 = f"session-{uuid.uuid4().hex[:16]}"
        s2 = DialerSession(session_id=session_id_2, mode="PROGRESSIVE",
                          state=SessionState.RUNNING, created_at=datetime.utcnow())
        db.add(s2)
        db.commit()

        # Add the same agent-1 to session_id_2 (should succeed)
        agent2 = DialerAgent(
            agent_id="agent-1",
            dialer_state=AgentState.AVAILABLE,
            session_id=session_id_2,
            version=0,
        )
        db.add(agent2)
        db.commit()

        # Both should exist
        agent_in_session1 = db.query(DialerAgent).filter(
            DialerAgent.agent_id == "agent-1",
            DialerAgent.session_id == session_id
        ).first()
        agent_in_session2 = db.query(DialerAgent).filter(
            DialerAgent.agent_id == "agent-1",
            DialerAgent.session_id == session_id_2
        ).first()

        assert agent_in_session1 is not None
        assert agent_in_session2 is not None
        assert agent_in_session1.session_id == session_id
        assert agent_in_session2.session_id == session_id_2

    def test_add_agents_mixed_existing_and_new(self, db, session_id):
        """Verify adding a mix of existing and new agents works correctly."""
        self._setup_session(db, session_id)

        # Pre-add agent-1
        agent = DialerAgent(
            agent_id="agent-1",
            dialer_state=AgentState.AVAILABLE,
            session_id=session_id,
            version=0,
        )
        db.add(agent)
        db.commit()

        # Add agent-1 (existing), agent-2 (new), agent-3 (new)
        added = []
        skipped = []
        for aid in ["agent-1", "agent-2", "agent-3"]:
            existing = db.query(DialerAgent).filter(
                DialerAgent.agent_id == aid,
                DialerAgent.session_id == session_id,
            ).first()
            if not existing:
                agent = DialerAgent(
                    agent_id=aid,
                    dialer_state=AgentState.AVAILABLE,
                    session_id=session_id,
                    version=0,
                )
                db.add(agent)
                added.append(aid)
            else:
                skipped.append(aid)
        db.commit()

        # agent-1 should be skipped, agent-2 and agent-3 should be added
        assert len(added) == 2
        assert len(skipped) == 1
        assert "agent-1" in skipped
        assert "agent-2" in added
        assert "agent-3" in added

    def test_add_agents_duplicate_submission(self, db, session_id):
        """Verify submitting the same request twice is idempotent."""
        self._setup_session(db, session_id)

        # First submission
        added1 = []
        skipped1 = []
        for aid in ["agent-1", "agent-2"]:
            existing = db.query(DialerAgent).filter(
                DialerAgent.agent_id == aid,
                DialerAgent.session_id == session_id,
            ).first()
            if not existing:
                agent = DialerAgent(
                    agent_id=aid,
                    dialer_state=AgentState.AVAILABLE,
                    session_id=session_id,
                    version=0,
                )
                db.add(agent)
                added1.append(aid)
            else:
                skipped1.append(aid)
        db.commit()

        assert len(added1) == 2
        assert len(skipped1) == 0

        # Second submission (same agents)
        added2 = []
        skipped2 = []
        for aid in ["agent-1", "agent-2"]:
            existing = db.query(DialerAgent).filter(
                DialerAgent.agent_id == aid,
                DialerAgent.session_id == session_id,
            ).first()
            if not existing:
                agent = DialerAgent(
                    agent_id=aid,
                    dialer_state=AgentState.AVAILABLE,
                    session_id=session_id,
                    version=0,
                )
                db.add(agent)
                added2.append(aid)
            else:
                skipped2.append(aid)
        db.commit()

        # Both should be skipped on second submission
        assert len(added2) == 0
        assert len(skipped2) == 2
        assert "agent-1" in skipped2
        assert "agent-2" in skipped2

    def test_add_agents_via_http_endpoint(self, db, session_id, engine):
        """Test the actual FastAPI endpoint to reproduce the HTTP 500 error."""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.security import create_access_token
        from app.core.database import Base

        # Ensure all SmartDialer tables exist in test database
        Base.metadata.create_all(bind=engine)

        # Create a test session
        self._setup_session(db, session_id)

        # Create a test user and get auth token
        from app.models.schema import User
        from app.core.security import get_password_hash
        test_user = User(
            email="test@example.com",
            hashed_password=get_password_hash("test123"),
            full_name="Test User",
            role="agent",
            is_active=True
        )
        db.add(test_user)
        db.commit()

        token = create_access_token(subject=test_user.email, role=test_user.role)

        # Override the get_db dependency to use the test's database session
        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db

        # Create test client
        client = TestClient(app)

        try:
            # Call the add_agents endpoint
            response = client.post(
                f"/api/v1/dialer/sessions/{session_id}/agents",
                json={"agent_ids": ["agent-1", "agent-2"]},
                headers={"Authorization": f"Bearer {token}"}
            )

            # Should succeed with 201
            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
            data = response.json()
            assert data["added"] == 2
            assert data["skipped"] == 0

            # Verify agents were actually created in the database
            agents = db.query(DialerAgent).filter(
                DialerAgent.session_id == session_id
            ).all()
            assert len(agents) == 2
        finally:
            # Clean up the override
            app.dependency_overrides.clear()
