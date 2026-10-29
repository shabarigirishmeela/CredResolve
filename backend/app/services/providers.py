"""
Mock Telecom Provider interface and two concrete implementations.

Provider A – fast, reliable, low failure rate.
Provider B – slower, configurable timeouts, duplicate events, out-of-order events.

The dialer knows only the abstract TelecomProvider interface.
"""
from __future__ import annotations
import asyncio
import random
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# Shared event / result types
# ---------------------------------------------------------------------------

@dataclass
class ProviderCallRequest:
    call_id: str
    borrower_phone: str
    agent_id: str
    idempotency_key: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ProviderCallResult:
    """Synchronous response from initiate_call."""
    success: bool
    provider_call_id: Optional[str] = None
    error: Optional[str] = None
    latency_ms: float = 0.0


@dataclass
class ProviderEvent:
    """Asynchronous webhook event emitted by the provider."""
    call_id: str
    provider_call_id: str
    event_type: str          # RINGING / ANSWERED / CONNECTED / COMPLETED / FAILED
    event_seq: int = 0       # monotonically increasing per call (0 = unknown order)
    occurred_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class TelecomProvider(ABC):
    """
    Interface that all provider implementations must satisfy.
    The Call Allocator depends only on this interface.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def initiate_call(self, req: ProviderCallRequest) -> ProviderCallResult:
        """
        Synchronously attempt to initiate an outbound call.
        Returns within the configured timeout; never raises (returns error result).
        """

    @abstractmethod
    def get_health(self) -> dict:
        """Return current health metrics for circuit-breaker evaluation."""

    def cancel_call(self, provider_call_id: str) -> bool:
        """Cancel an in-progress call. Default: no-op, returns False."""
        return False

    def set_event_callback(self, cb: Callable[[ProviderEvent], None]) -> None:
        """Register callback for async event delivery (webhook simulation)."""
        self._event_callback = cb

    def _emit(self, event: ProviderEvent) -> None:
        cb = getattr(self, "_event_callback", None)
        if cb:
            try:
                cb(event)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Provider A – fast, reliable
# ---------------------------------------------------------------------------

class ProviderAlpha(TelecomProvider):
    """
    Fast, reliable provider.
    - Answer rate: ~80%
    - Setup latency: 50–150 ms
    - Failure rate: < 2%
    - Events arrive in order, no duplicates
    """

    def __init__(
        self,
        answer_rate: float = 0.80,
        setup_ms_min: int = 50,
        setup_ms_max: int = 150,
        fail_rate: float = 0.02,
    ):
        self._answer_rate = answer_rate
        self._setup_ms_min = setup_ms_min
        self._setup_ms_max = setup_ms_max
        self._fail_rate = fail_rate
        self._calls: dict[str, dict] = {}
        self._total = 0
        self._failures = 0

    @property
    def name(self) -> str:
        return "provider_alpha"

    def initiate_call(self, req: ProviderCallRequest) -> ProviderCallResult:
        latency = random.randint(self._setup_ms_min, self._setup_ms_max) / 1000
        time.sleep(latency)
        self._total += 1

        if random.random() < self._fail_rate:
            self._failures += 1
            return ProviderCallResult(
                success=False,
                error="provider_alpha: transient error",
                latency_ms=latency * 1000,
            )

        provider_call_id = f"PA-{uuid.uuid4().hex[:12]}"
        self._calls[provider_call_id] = {
            "call_id": req.call_id,
            "answer_rate": self._answer_rate,
        }
        # Schedule async events in background thread
        asyncio.get_event_loop().call_later(
            0.1, self._simulate_events, req.call_id, provider_call_id
        ) if self._has_loop() else self._schedule_thread(
            req.call_id, provider_call_id
        )
        return ProviderCallResult(
            success=True,
            provider_call_id=provider_call_id,
            latency_ms=latency * 1000,
        )

    def _has_loop(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            return loop.is_running()
        except RuntimeError:
            return False

    def _schedule_thread(self, call_id: str, pcid: str) -> None:
        import threading
        t = threading.Thread(
            target=self._simulate_events,
            args=(call_id, pcid),
            daemon=True,
        )
        t.start()

    def _simulate_events(self, call_id: str, pcid: str) -> None:
        time.sleep(random.uniform(0.05, 0.2))   # ringing delay
        self._emit(ProviderEvent(call_id=call_id, provider_call_id=pcid,
                                  event_type="RINGING", event_seq=1))

        if random.random() < self._answer_rate:
            time.sleep(random.uniform(0.05, 0.15))
            self._emit(ProviderEvent(call_id=call_id, provider_call_id=pcid,
                                      event_type="ANSWERED", event_seq=2))
            talk_time = random.uniform(30, 300)
            time.sleep(min(talk_time, 0.5))      # compressed for simulation
            self._emit(ProviderEvent(call_id=call_id, provider_call_id=pcid,
                                      event_type="COMPLETED", event_seq=3))
        else:
            time.sleep(random.uniform(0.1, 0.3))
            self._emit(ProviderEvent(call_id=call_id, provider_call_id=pcid,
                                      event_type="FAILED",
                                      event_seq=2,
                                      extra={"reason": "no_answer"}))

    def get_health(self) -> dict:
        fail_rate = self._failures / max(1, self._total)
        return {
            "provider": self.name,
            "total_calls": self._total,
            "failure_rate": round(fail_rate, 4),
            "healthy": fail_rate < 0.10,
        }

    def cancel_call(self, provider_call_id: str) -> bool:
        return provider_call_id in self._calls


# ---------------------------------------------------------------------------
# Provider B – slow, unreliable, OOO events, duplicates
# ---------------------------------------------------------------------------

class ProviderBeta(TelecomProvider):
    """
    Slow, unreliable provider used to test resilience.
    - Answer rate: configurable (default 40%)
    - Setup latency: 200–1200 ms (with occasional timeouts)
    - Failure rate: ~10%
    - Emits duplicate ANSWERED events with probability dup_prob
    - Emits out-of-order events with probability ooo_prob
    - Configurable timeout rate
    """

    def __init__(
        self,
        answer_rate: float = 0.40,
        setup_ms_min: int = 200,
        setup_ms_max: int = 1200,
        fail_rate: float = 0.10,
        timeout_rate: float = 0.05,
        timeout_sec: float = 3.0,
        dup_prob: float = 0.08,
        ooo_prob: float = 0.06,
    ):
        self._answer_rate = answer_rate
        self._setup_ms_min = setup_ms_min
        self._setup_ms_max = setup_ms_max
        self._fail_rate = fail_rate
        self._timeout_rate = timeout_rate
        self._timeout_sec = timeout_sec
        self._dup_prob = dup_prob
        self._ooo_prob = ooo_prob
        self._calls: dict[str, dict] = {}
        self._total = 0
        self._failures = 0
        self._timeouts = 0

    @property
    def name(self) -> str:
        return "provider_beta"

    def initiate_call(self, req: ProviderCallRequest) -> ProviderCallResult:
        self._total += 1

        # Simulate timeout
        if random.random() < self._timeout_rate:
            self._timeouts += 1
            time.sleep(self._timeout_sec)
            return ProviderCallResult(
                success=False,
                error="provider_beta: timeout",
                latency_ms=self._timeout_sec * 1000,
            )

        latency = random.randint(self._setup_ms_min, self._setup_ms_max) / 1000
        time.sleep(latency)

        if random.random() < self._fail_rate:
            self._failures += 1
            return ProviderCallResult(
                success=False,
                error="provider_beta: network error",
                latency_ms=latency * 1000,
            )

        provider_call_id = f"PB-{uuid.uuid4().hex[:12]}"
        self._calls[provider_call_id] = {"call_id": req.call_id}
        self._schedule_thread(req.call_id, provider_call_id)
        return ProviderCallResult(
            success=True,
            provider_call_id=provider_call_id,
            latency_ms=latency * 1000,
        )

    def _schedule_thread(self, call_id: str, pcid: str) -> None:
        import threading
        t = threading.Thread(
            target=self._simulate_events,
            args=(call_id, pcid),
            daemon=True,
        )
        t.start()

    def _simulate_events(self, call_id: str, pcid: str) -> None:
        # Build event sequence
        events = []
        seq = 1

        ringing = ProviderEvent(call_id=call_id, provider_call_id=pcid,
                                 event_type="RINGING", event_seq=seq)
        seq += 1
        events.append((random.uniform(0.1, 0.5), ringing))

        answered = random.random() < self._answer_rate
        if answered:
            ans_evt = ProviderEvent(call_id=call_id, provider_call_id=pcid,
                                    event_type="ANSWERED", event_seq=seq)
            seq += 1
            events.append((random.uniform(0.3, 0.8), ans_evt))

            # Duplicate ANSWERED
            if random.random() < self._dup_prob:
                dup = ProviderEvent(call_id=call_id, provider_call_id=pcid,
                                    event_type="ANSWERED", event_seq=seq - 1)  # same seq
                events.append((random.uniform(0.35, 0.9), dup))

            comp_evt = ProviderEvent(call_id=call_id, provider_call_id=pcid,
                                     event_type="COMPLETED", event_seq=seq)
            seq += 1
            events.append((random.uniform(0.8, 2.0), comp_evt))
        else:
            fail_evt = ProviderEvent(call_id=call_id, provider_call_id=pcid,
                                     event_type="FAILED", event_seq=seq,
                                     extra={"reason": "no_answer"})
            events.append((random.uniform(0.5, 1.5), fail_evt))

        # Out-of-order: shuffle delivery order
        if random.random() < self._ooo_prob:
            random.shuffle(events)

        for delay, evt in events:
            time.sleep(delay)
            self._emit(evt)

    def get_health(self) -> dict:
        total = max(1, self._total)
        fail_rate = (self._failures + self._timeouts) / total
        return {
            "provider": self.name,
            "total_calls": self._total,
            "failure_rate": round(fail_rate, 4),
            "timeout_rate": round(self._timeouts / total, 4),
            "healthy": fail_rate < 0.20,
        }

    def set_answer_rate(self, rate: float) -> None:
        """Allow simulator to dynamically adjust answer rate (scenario D)."""
        self._answer_rate = max(0.0, min(1.0, rate))

    def set_failure_rate(self, rate: float) -> None:
        self._fail_rate = max(0.0, min(1.0, rate))
