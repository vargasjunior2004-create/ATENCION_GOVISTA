const API_URL = '';

let onAuthExpired = null;
export function setOnAuthExpired(cb) { onAuthExpired = cb; }

async function request(path, options = {}) {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    if (onAuthExpired) onAuthExpired();
    throw new Error('Sesión expirada');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Error del servidor' }));
    throw err;
  }
  // Endpoints que devuelven archivos binarios (PDF, XLSX)
  const ct = res.headers.get('content-type');
  if (ct && (ct.includes('application/pdf') || ct.includes('spreadsheetml') || ct.includes('octet-stream') || ct.includes('image/png') || ct.includes('image/'))) {
    return res.blob();
  }
  return res.json();
}

const api = {
  login: (name, password) =>
    request('/api/auth/login', { method: 'POST', body: JSON.stringify({ name, password }) }),

  me: () => request('/api/auth/me'),

  // Dashboard
  getDashboardStats: () => request('/api/dashboard/stats'),

  // Planes
  getPlans: () => request('/api/plans'),
  getActivePlans: () => request('/api/plans/active'),
  createPlan: (data) => request('/api/plans', { method: 'POST', body: JSON.stringify(data) }),
  updatePlan: (id, data) => request(`/api/plans/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deletePlan: (id) => request(`/api/plans/${id}`, { method: 'DELETE' }),

  // Ventas
  getSales: (from, to, requestType, page = 1, pageSize = 25, serviceType = '') => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    if (requestType) params.set('requestType', requestType);
    if (serviceType) params.set('serviceType', serviceType);
    params.set('page', page);
    params.set('page_size', pageSize);
    return request(`/api/sales?${params.toString()}`);
  },
  createSale: (data) => request('/api/sales', { method: 'POST', body: JSON.stringify(data) }),
  updateSale: (id, data) => request(`/api/sales/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSale: (id) => request(`/api/sales/${id}`, { method: 'DELETE' }),

  // Usuarios
  getUsers: () => request('/api/users'),
  createUser: (data) => request('/api/users', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id, data) => request(`/api/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteUser: (id) => request(`/api/users/${id}`, { method: 'DELETE' }),

  // Clientes
  searchCustomers: (q) => {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    return request(`/api/customers?${params.toString()}`);
  },

  // Reportes
  getPDF: (from, to, requestType, serviceType = '') => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    if (requestType) params.set('requestType', requestType);
    if (serviceType) params.set('serviceType', serviceType);
    return request(`/api/reports/pdf?${params.toString()}`);
  },
  getXLSX: (from, to) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    return request(`/api/reports/xlsx?${params.toString()}`);
  },
  getPNG: (from, to) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    return request(`/api/reports/png?${params.toString()}`);
  },

  // Backups
  getBackups: () => request('/api/backups'),
  createBackup: () => request('/api/backups', { method: 'POST' }),
  downloadBackup: (id) => {
    const token = localStorage.getItem('token');
    return fetch(`${API_URL}/api/backups/${id}/download`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(res => {
      if (!res.ok) throw new Error('Error al descargar');
      return res.blob();
    });
  },
  deleteBackup: (id) => request(`/api/backups/${id}`, { method: 'DELETE' }),
};

export default api;
