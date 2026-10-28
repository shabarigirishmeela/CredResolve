import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { BorrowerDrawer } from './components/BorrowerDrawer';

// Pages
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { WorkQueue } from './pages/WorkQueue';
import { Borrowers } from './pages/Borrowers';
import { Accounts } from './pages/Accounts';
import { Payments } from './pages/Payments';
import { PromisesToPay } from './pages/PromisesToPay';
import { AgentPerformance } from './pages/AgentPerformance';
import { CampaignAnalytics } from './pages/CampaignAnalytics';
import { CommunicationAnalytics } from './pages/CommunicationAnalytics';
import { FieldVisits } from './pages/FieldVisits';
import { ComplaintsCompliance } from './pages/ComplaintsCompliance';
import { DataQuality } from './pages/DataQuality';
import { ReportsSettings } from './pages/ReportsSettings';

const MainApp: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [selectedBorrowerId, setSelectedBorrowerId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#070b13] flex items-center justify-center text-slate-400">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-400 flex items-center justify-center text-white font-bold animate-pulse">
            CR
          </div>
          <span className="text-xs">Authenticating CredResolve Intelligence session...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  const handleOpenBorrower = (borrowerId: string) => {
    setSelectedBorrowerId(borrowerId);
    setDrawerOpen(true);
  };

  const getPageTitle = () => {
    switch (currentTab) {
      case 'dashboard': return 'Executive Recovery Dashboard';
      case 'work-queue': return 'Intelligent Collection Work Queue';
      case 'borrowers': return 'Borrower Directory & 360° Profiles';
      case 'accounts': return 'Account Management & Delinquency Registry';
      case 'payments': return 'Payment Transactions & Reconciliation';
      case 'ptp': return 'Promise-to-Pay (PTP) Registry';
      case 'agents': return 'Agent Performance & Leaderboards';
      case 'campaigns': return 'Campaign Analytics & Strategy Versioning';
      case 'communications': return 'Omnichannel Communication Analytics';
      case 'field-visits': return 'Field Visit Operations & Verification';
      case 'complaints': return 'Complaints, Disputes & Compliance Surveillance';
      case 'data-quality': return 'Data Quality, Pipeline Health & Auditing';
      case 'reports': return 'Reports, CSV Exports & Methodologies';
      case 'settings': return 'Platform & Engine Configuration';
      default: return 'CredResolve Intelligence';
    }
  };

  const getPageSubtitle = () => {
    switch (currentTab) {
      case 'dashboard': return 'High-level portfolio performance, cash recovery KPIs, and risk distribution';
      case 'work-queue': return 'Rule-based prioritization engine with explainable factor breakdown and compliance pauses';
      case 'borrowers': return 'PII-protected borrower profiles with consolidated accounts and contact telemetry';
      case 'accounts': return '30,000 accounts with lifecycle status history and loan product distribution';
      case 'payments': return 'Idempotent transaction tracking, success rates, and duplicate reference detection';
      case 'ptp': return 'Commitment conversion funnel, broken PTP recovery, and channel attribution';
      case 'agents': return 'Productivity scorecards for 1,000 agents with contact rates and conversion metrics';
      case 'campaigns': return 'Omnichannel strategy comparisons across 120 targeting campaigns';
      case 'communications': return 'Calls, WhatsApp, and SMS delivery telemetry and borrower response funnels';
      case 'field-visits': return '25,000 on-ground field visits with GPS coordinates and visit outcomes';
      case 'complaints': return 'Fair Practices Code enforcement, dispute review, and grievance resolution';
      case 'data-quality': return 'Audit telemetry across 17 datasets with duplicate purging and timestamp reconciliation';
      case 'reports': return 'Streamed CSV downloads and documented financial recovery metric formulas';
      case 'settings': return 'Configurable prioritization engine weights and contact window parameters';
      default: return '';
    }
  };

  return (
    <div className="flex h-screen bg-[#070b13] overflow-hidden">
      
      {/* Sidebar Navigation */}
      <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden">
        
        {/* Header */}
        <Header title={getPageTitle()} subtitle={getPageSubtitle()} />

        {/* Scrollable Page Body */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <div className="max-w-7xl mx-auto">
            {currentTab === 'dashboard' && <Dashboard onNavigate={setCurrentTab} />}
            {currentTab === 'work-queue' && <WorkQueue onOpenBorrower={handleOpenBorrower} />}
            {currentTab === 'borrowers' && <Borrowers onOpenBorrower={handleOpenBorrower} />}
            {currentTab === 'accounts' && <Accounts onOpenBorrower={handleOpenBorrower} />}
            {currentTab === 'payments' && <Payments />}
            {currentTab === 'ptp' && <PromisesToPay />}
            {currentTab === 'agents' && <AgentPerformance />}
            {currentTab === 'campaigns' && <CampaignAnalytics />}
            {currentTab === 'communications' && <CommunicationAnalytics />}
            {currentTab === 'field-visits' && <FieldVisits />}
            {currentTab === 'complaints' && <ComplaintsCompliance />}
            {currentTab === 'data-quality' && <DataQuality />}
            {currentTab === 'reports' && <ReportsSettings />}
            {currentTab === 'settings' && <ReportsSettings />}
          </div>
        </main>

      </div>

      {/* Global 360° Borrower Drawer */}
      <BorrowerDrawer
        borrowerId={selectedBorrowerId}
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />

    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
};

export default App;
