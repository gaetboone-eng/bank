import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Banks
export const getBanks = () => axios.get(`${API}/banks`);
export const createBank = (data) => axios.post(`${API}/banks`, data);
export const updateBank = (id, data) => axios.put(`${API}/banks/${id}`, data);
export const deleteBank = (id) => axios.delete(`${API}/banks/${id}`);

// Tenants
export const getTenants = () => axios.get(`${API}/tenants`);
export const getTenant = (id) => axios.get(`${API}/tenants/${id}`);
export const createTenant = (data) => axios.post(`${API}/tenants`, data);
export const updateTenant = (id, data) => axios.put(`${API}/tenants/${id}`, data);
export const deleteTenant = (id) => axios.delete(`${API}/tenants/${id}`);
export const syncTenantsFromNotion = () => axios.post(`${API}/tenants/sync-notion`);

// Transactions
export const getTransactions = (bankId) => 
  axios.get(`${API}/transactions`, { params: bankId ? { bank_id: bankId } : {} });
export const createTransaction = (data) => axios.post(`${API}/transactions`, data);
export const matchTransaction = (txId, tenantId) => 
  axios.post(`${API}/transactions/${txId}/match/${tenantId}`);

// Payments
export const getPayments = (tenantId) => 
  axios.get(`${API}/payments`, { params: tenantId ? { tenant_id: tenantId } : {} });
export const createPayment = (data) => axios.post(`${API}/payments`, data);

// Dashboard
export const getDashboardStats = () => axios.get(`${API}/dashboard/stats`);

// Notifications
export const sendWhatsAppNotification = (tenantId, message) => 
  axios.post(`${API}/notifications/whatsapp`, { tenant_id: tenantId, message });

// Settings
export const getSettings = () => axios.get(`${API}/settings`);
export const updateSettings = (data) => axios.put(`${API}/settings`, data);
