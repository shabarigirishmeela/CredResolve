import axios from 'axios';
import { 
  User, DemoUser, DashboardData, PaginatedResult, 
  AccountItem, BorrowerItem, PaymentItem, PTPItem, 
  AgentItem, CampaignItem, CallItem, FieldVisitItem, 
  ComplaintItem, DataQualityReport, ExplainabilityReport 
} from '../types';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('credresolve_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !window.location.pathname.includes('/login')) {
      localStorage.removeItem('credresolve_token');
      localStorage.removeItem('credresolve_user');
      // Window redirect if not in login
    }
    return Promise.reject(error);
  }
);

export const apiClient = {
  // Auth
  login: async (creds: { email: string; password: string }) => {
    const res = await api.post('/auth/login', creds);
    return res.data;
  },
  getMe: async (): Promise<User> => {
    const res = await api.get('/auth/me');
    return res.data;
  },
  getDemoUsers: async (): Promise<DemoUser[]> => {
    const res = await api.get('/auth/demo-users');
    return res.data;
  },

  // Dashboard
  getDashboardSummary: async (params?: Record<string, any>): Promise<DashboardData> => {
    const res = await api.get('/dashboard/summary', { params });
    return res.data;
  },

  // Borrowers
  getBorrowers: async (params?: Record<string, any>): Promise<PaginatedResult<BorrowerItem>> => {
    const res = await api.get('/borrowers', { params });
    return res.data;
  },
  getBorrowerDetail: async (borrowerId: string) => {
    const res = await api.get(`/borrowers/${borrowerId}`);
    return res.data;
  },

  // Accounts
  getAccounts: async (params?: Record<string, any>): Promise<PaginatedResult<AccountItem>> => {
    const res = await api.get('/accounts', { params });
    return res.data;
  },
  getAccountDetail: async (accountId: string) => {
    const res = await api.get(`/accounts/${accountId}`);
    return res.data;
  },

  // Queue
  getWorkQueue: async (params?: Record<string, any>): Promise<PaginatedResult<AccountItem>> => {
    const res = await api.get('/queue', { params });
    return res.data;
  },
  explainPriority: async (accountId: string): Promise<ExplainabilityReport> => {
    const res = await api.get(`/queue/${accountId}/explain`);
    return res.data;
  },
  logQueueAction: async (accountId: string, data: { action_type: string; notes?: string; outcome?: string }) => {
    const res = await api.post(`/queue/${accountId}/action`, data);
    return res.data;
  },

  // Payments
  getPayments: async (params?: Record<string, any>): Promise<PaginatedResult<PaymentItem>> => {
    const res = await api.get('/payments', { params });
    return res.data;
  },
  getPaymentSummary: async () => {
    const res = await api.get('/payments/summary');
    return res.data;
  },

  // Promises to Pay
  getPTPs: async (params?: Record<string, any>): Promise<PaginatedResult<PTPItem>> => {
    const res = await api.get('/ptp', { params });
    return res.data;
  },
  getPTPSummary: async () => {
    const res = await api.get('/ptp/summary');
    return res.data;
  },

  // Agents
  getAgents: async (params?: Record<string, any>): Promise<PaginatedResult<AgentItem>> => {
    const res = await api.get('/agents', { params });
    return res.data;
  },
  getAgentDetail: async (agentId: string) => {
    const res = await api.get(`/agents/${agentId}`);
    return res.data;
  },

  // Campaigns
  getCampaigns: async (params?: Record<string, any>): Promise<PaginatedResult<CampaignItem>> => {
    const res = await api.get('/campaigns', { params });
    return res.data;
  },
  getCampaignSummary: async () => {
    const res = await api.get('/campaigns/summary');
    return res.data;
  },

  // Communications
  getCommunicationsSummary: async () => {
    const res = await api.get('/communications/summary');
    return res.data;
  },
  getCalls: async (params?: Record<string, any>): Promise<PaginatedResult<CallItem>> => {
    const res = await api.get('/communications/calls', { params });
    return res.data;
  },
  getSms: async (params?: Record<string, any>): Promise<PaginatedResult<any>> => {
    const res = await api.get('/communications/sms', { params });
    return res.data;
  },
  getWhatsapp: async (params?: Record<string, any>): Promise<PaginatedResult<any>> => {
    const res = await api.get('/communications/whatsapp', { params });
    return res.data;
  },

  // Field Visits
  getFieldVisits: async (params?: Record<string, any>): Promise<PaginatedResult<FieldVisitItem>> => {
    const res = await api.get('/field-visits', { params });
    return res.data;
  },
  getFieldVisitSummary: async () => {
    const res = await api.get('/field-visits/summary');
    return res.data;
  },

  // Complaints
  getComplaints: async (params?: Record<string, any>): Promise<PaginatedResult<ComplaintItem>> => {
    const res = await api.get('/complaints', { params });
    return res.data;
  },
  getComplaintsSummary: async () => {
    const res = await api.get('/complaints/summary');
    return res.data;
  },
  resolveComplaint: async (complaintId: string, notes?: string) => {
    const res = await api.post(`/complaints/${complaintId}/resolve`, { resolution_notes: notes });
    return res.data;
  },

  // Data Quality
  getDataQualityReport: async (): Promise<DataQualityReport> => {
    const res = await api.get('/data-quality/report');
    return res.data;
  },
  triggerCleaning: async () => {
    const res = await api.post('/data-quality/trigger-cleaning');
    return res.data;
  },
  uploadCsv: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post('/data-quality/upload-csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },

  // Reports
  getDefinitions: async () => {
    const res = await api.get('/reports/definitions');
    return res.data;
  },
  getSettings: async () => {
    const res = await api.get('/reports/settings');
    return res.data;
  },
  getExportUrl: (type: string) => `/api/v1/reports/export-csv?report_type=${type}`
};

export default api;
