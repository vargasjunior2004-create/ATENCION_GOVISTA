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
  if (res.status === 204) return null;
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

  changePassword: (current_password, new_password) =>
    request('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    }),

  // Dashboard
  getDashboardStats: () => request('/api/dashboard/stats'),

  // Planes
  getPlans: () => request('/api/plans'),
  getActivePlans: () => request('/api/plans/active'),
  createPlan: (data) => request('/api/plans', { method: 'POST', body: JSON.stringify(data) }),
  updatePlan: (id, data) => request(`/api/plans/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deletePlan: (id) => request(`/api/plans/${id}`, { method: 'DELETE' }),

  // Promociones
  getPromotions: (planId) => {
    const params = new URLSearchParams();
    if (planId) params.set('plan_id', planId);
    return request(`/api/promotions?${params.toString()}`);
  },
  getActivePromotions: (planId) => {
    const params = new URLSearchParams();
    if (planId) params.set('plan_id', planId);
    return request(`/api/promotions/active?${params.toString()}`);
  },
  createPromotion: (data) => request('/api/promotions', { method: 'POST', body: JSON.stringify(data) }),
  updatePromotion: (id, data) => request(`/api/promotions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deletePromotion: (id) => request(`/api/promotions/${id}`, { method: 'DELETE' }),

  // Ventas
  getSales: (from, to, requestType, page = 1, pageSize = 25, serviceType = '') => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    if (requestType && requestType !== 'all') params.set('requestType', requestType);
    if (serviceType && serviceType !== 'all') params.set('serviceType', serviceType);
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
    if (requestType && requestType !== 'all') params.set('requestType', requestType);
    if (serviceType && serviceType !== 'all') params.set('serviceType', serviceType);
    return request(`/api/reports/pdf?${params.toString()}`);
  },
  getXLSX: (from, to, requestType = '', serviceType = '') => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    if (requestType && requestType !== 'all') params.set('requestType', requestType);
    if (serviceType && serviceType !== 'all') params.set('serviceType', serviceType);
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
  // Genera el respaldo y devuelve el archivo .dump directamente.
  // El servidor lo borra tras la transmision: no queda almacenado en Render.
  createBackup: () => {
    const token = localStorage.getItem('token');
    return fetch(`${API_URL}/api/backups`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    }).then(async (res) => {
      if (!res.ok) {
        let msg = 'No se pudo generar el respaldo.';
        try {
          const data = await res.json();
          if (data && data.error) msg = data.error;
        } catch (e) { /* respuesta sin cuerpo JSON */ }
        throw new Error(msg);
      }
      const disposition = res.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : 'govista_backup.dump';
      return { blob: await res.blob(), filename };
    });
  },
  deleteBackup: (id) => request(`/api/backups/${id}`, { method: 'DELETE' }),
};

export default api;
