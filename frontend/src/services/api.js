const API_URL = '';

async function request(path, options = {}) {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Error del servidor' }));
    throw err;
  }
  // Endpoints que devuelven archivos binarios (PDF, XLSX)
  const ct = res.headers.get('content-type');
  if (ct && (ct.includes('application/pdf') || ct.includes('spreadsheetml') || ct.includes('octet-stream'))) {
    return res.blob();
  }
  return res.json();
}

const api = {
  login: (password) =>
    request('/api/auth/login', { method: 'POST', body: JSON.stringify({ password }) }),

  me: () => request('/api/auth/me'),

  // Planes
  getPlans: () => request('/api/plans'),
  getActivePlans: () => request('/api/plans/active'),
  createPlan: (data) => request('/api/plans', { method: 'POST', body: JSON.stringify(data) }),
  updatePlan: (id, data) => request(`/api/plans/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Ventas
  getSales: (from, to) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    const qs = params.toString();
    return request(`/api/sales${qs ? '?' + qs : ''}`);
  },
  createSale: (data) => request('/api/sales', { method: 'POST', body: JSON.stringify(data) }),
  updateSale: (id, data) => request(`/api/sales/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Usuarios
  getUsers: () => request('/api/users'),
  createUser: (data) => request('/api/users', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id, data) => request(`/api/users/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Reportes
  getPDF: (from, to) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    return request(`/api/reports/pdf?${params.toString()}`);
  },
  getXLSX: (from, to) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    return request(`/api/reports/xlsx?${params.toString()}`);
  },
  getPDFLink: (from, to) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    return request(`/api/reports/pdf-link?${params.toString()}`);
  },
  getXLSXLink: (from, to) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    return request(`/api/reports/xlsx-link?${params.toString()}`);
  },

  // Arqueo de caja
  getCashCount: (date) => {
    const params = date ? `?date=${date}` : '';
    return request(`/api/cash-count${params}`);
  },
  saveCashCount: (data) =>
    request('/api/cash-count', { method: 'POST', body: JSON.stringify(data) }),
  addOutflow: (data) =>
    request('/api/cash-count/outflows', { method: 'POST', body: JSON.stringify(data) }),
  deleteOutflow: (id) =>
    request(`/api/cash-count/outflows/${id}`, { method: 'DELETE' }),
  getCashPDF: (date) => {
    const params = date ? `?date=${date}` : '';
    return request(`/api/cash-count/pdf${params}`);
  },
  getCashPDFLink: (date) => {
    const params = date ? `?date=${date}` : '';
    return request(`/api/cash-count/pdf-link${params}`);
  },
};

export default api;
