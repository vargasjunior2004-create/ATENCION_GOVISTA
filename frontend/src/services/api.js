const API_URL = '';

let onAuthExpired = null;
export function setOnAuthExpired(cb) { onAuthExpired = cb; }

async function request(path, options = {}) {
  const token = localStorage.getItem('token');
  const isLoginRequest = path === '/api/auth/login';
  const isFormData = options.body instanceof FormData;
  const headers = { ...(isFormData ? {} : { 'Content-Type': 'application/json' }), ...options.headers };
  if (token && !isLoginRequest) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    const err = await res.json().catch(() => ({ error: 'Sesión inválida' }));
    if (!isLoginRequest) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (onAuthExpired) onAuthExpired();
    }
    throw err;
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

  logout: () => request('/api/auth/logout', { method: 'POST' }),

  me: () => request('/api/auth/me'),

  changePassword: (current_password, new_password, new_password_confirm) =>
    request('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password, new_password_confirm }),
    }),

  // Dashboard
  getDashboardStats: (from = '', to = '', movementType = 'all') => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    if (movementType && movementType !== 'all') {
      params.set('movement_type', movementType);
    }
    const query = params.toString();
    return request(`/api/dashboard/stats${query ? `?${query}` : ''}`);
  },
  getCommercialProductivity: (from = '', to = '', movementType = 'all', page = 1, pageSize = 25, userId = '') => {
    const params = new URLSearchParams({ from, to, movement_type: movementType, page: String(page), page_size: String(pageSize) });
    if (userId) params.set('user_id', String(userId));
    return request(`/api/dashboard/productivity?${params.toString()}`);
  },
  getDashboardDrilldown: ({
    indicator, category, from, to, movementType = 'all',
    zoneName = '', planName = '', catalogLabel = '', planType = '',
    channelKey = '',
    motiveId = '',
    search = '', page = 1, pageSize = 25,
  }) => {
    const params = new URLSearchParams({
      indicator,
      from,
      to,
      movement_type: movementType,
      search,
      page: String(page),
      page_size: String(pageSize),
    });
    if (category) params.set('category', category);
    if (zoneName) params.set('zone_name', zoneName);
    if (indicator === 'plan') {
      params.set('plan_name', planName);
      params.set('catalog_label', catalogLabel);
      params.set('plan_type', planType);
    }
    if (indicator === 'channel') params.set('channel_key', channelKey);
    if (indicator === 'motive') params.set('motive_id', String(motiveId));
    return request(`/api/dashboard/drilldown?${params.toString()}`);
  },

  // Planes
  getPlans: () => request('/api/plans'),
  getActivePlans: () => request('/api/plans/active'),
  createPlan: (data) => request('/api/plans', { method: 'POST', body: JSON.stringify(data) }),
  updatePlan: (id, data) => request(`/api/plans/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deletePlan: (id) => request(`/api/plans/${id}`, { method: 'DELETE' }),

  // Tipos de solicitud (solo lectura para el formulario)
  getActiveRequestTypes: () => request('/api/request-types/active'),

  // Zonas de cobertura
  getActiveCoverageZones: () => request('/api/coverage/zones/?active=true'),
  getCoverageZones: () => request('/api/coverage/zones/'),
  getManagedCoverageZones: () => request('/api/coverage/zones/manage/'),

  // Ubicación de clientes
  searchLocationCustomers: (q = '') => request(`/api/ubicaciones/clientes${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  createCustomerLocation: (data) => request('/api/ubicaciones', { method: 'POST', body: data }),
  updateCustomerLocation: (id, data) => request(`/api/ubicaciones/${id}`, { method: 'PATCH', body: data }),
  getCustomerLocation: (id) => request(`/api/ubicaciones/${id}`),
  getCustomerLocationHistory: (id) => request(`/api/ubicaciones/${id}/historial`),
  createCoverageZone: (data) => request('/api/coverage/zones/manage/', {
    method: 'POST', body: JSON.stringify(data),
  }),
  updateCoverageZone: (id, data) => request(`/api/coverage/zones/${id}/`, {
    method: 'PATCH', body: JSON.stringify(data),
  }),

  // Motivos
  getMotivos: (categoria = '') => {
    const params = new URLSearchParams();
    if (categoria) params.set('categoria', categoria);
    const qs = params.toString();
    return request(`/api/motivos${qs ? `?${qs}` : ''}`);
  },
  getActiveMotivos: (categoria = '') => {
    const params = new URLSearchParams();
    if (categoria) params.set('categoria', categoria);
    const qs = params.toString();
    return request(`/api/motivos/active${qs ? `?${qs}` : ''}`);
  },
  createMotivo: (data) => request('/api/motivos', { method: 'POST', body: JSON.stringify(data) }),
  updateMotivo: (id, data) => request(`/api/motivos/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteMotivo: (id) => request(`/api/motivos/${id}`, { method: 'DELETE' }),

  // Canales de captación
  getCanalesCaptacion: () => request('/api/canales-captacion'),
  getActiveCanalesCaptacion: () => request('/api/canales-captacion/active'),
  createCanalCaptacion: (data) => request('/api/canales-captacion', {
    method: 'POST', body: JSON.stringify(data),
  }),
  updateCanalCaptacion: (id, data) => request(`/api/canales-captacion/${id}`, {
    method: 'PATCH', body: JSON.stringify(data),
  }),
  deleteCanalCaptacion: (id) => request(`/api/canales-captacion/${id}`, {
    method: 'DELETE',
  }),

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
  getTransferTariffs: () => request('/api/transfer-tariffs'),
  getActiveTransferTariffs: () => request('/api/transfer-tariffs/active'),
  createTransferTariff: (data) => request('/api/transfer-tariffs', { method: 'POST', body: JSON.stringify(data) }),
  updateTransferTariff: (id, data) => request(`/api/transfer-tariffs/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  getTransferTariffHistory: (id) => request(`/api/transfer-tariffs/${id}/history`),
  createPromotion: (data) => request('/api/promotions', { method: 'POST', body: JSON.stringify(data) }),
  updatePromotion: (id, data) => request(`/api/promotions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deletePromotion: (id) => request(`/api/promotions/${id}`, { method: 'DELETE' }),

  // Ventas
  getSales: (from, to, requestType, page = 1, pageSize = 25, serviceType = '', archived = false) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    if (requestType && requestType !== 'all') params.set('requestType', requestType);
    if (serviceType && serviceType !== 'all') params.set('serviceType', serviceType);
    if (archived) params.set('archived', 'true');
    params.set('page', page);
    params.set('page_size', pageSize);
    return request(`/api/sales?${params.toString()}`);
  },
  createSale: (data) => request('/api/sales', { method: 'POST', body: JSON.stringify(data) }),
  scanSaleDocument: (file) => {
    const body = new FormData();
    body.append('file', file);
    return request('/api/sales/escanear/', { method: 'POST', body });
  },
  extractRetirementDocument: (file) => {
    const body = new FormData();
    body.append('file', file);
    return request('/api/document-reader/extract-retirement/', {
      method: 'POST', body,
    });
  },
  updateSale: (id, data) => request(`/api/sales/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSale: (id) => request(`/api/sales/${id}`, { method: 'DELETE' }),
  restoreSale: (id) => request(`/api/sales/${id}/restore`, { method: 'POST' }),

  // Clientes y contratos
  searchCustomers: (q = '') => request(`/api/customers?q=${encodeURIComponent(q)}`),
  getCustomer: (id) => request(`/api/customers/${id}`),
  updateCustomer: (id, data) => request(`/api/customers/${id}`, {
    method: 'PUT', body: JSON.stringify(data),
  }),
  reviewContractMeter: (id, data) => request(`/api/contracts/${id}/meter-review`, {
    method: 'PATCH', body: JSON.stringify(data),
  }),
  getContract: (id) => request(`/api/contracts/${id}`),
  updateContractMeter: (id, meter_number) => request(`/api/contracts/${id}/meter`, {
    method: 'PATCH', body: JSON.stringify({ meter_number }),
  }),

  // Usuarios
  getUsers: () => request('/api/admin/usuarios').then((data) => data.results || data),
  getActiveExternalSellers: () => request('/api/external-sellers/active'),
  createUser: (data) => request('/api/admin/usuarios', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id, data) => request(`/api/admin/usuarios/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  getRoles: () => request('/api/admin/roles'),
  getPermissions: () => request('/api/admin/permisos'),
  getAdminAudit: () => request('/api/admin/auditoria'),
  createRole: (data) => request('/api/admin/roles', { method: 'POST', body: JSON.stringify(data) }),
  updateRole: (id, data) => request(`/api/admin/roles/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  getUserRoles: (id) => request(`/api/admin/usuarios/${id}/roles`),
  assignUserRole: (id, role) => request(`/api/admin/usuarios/${id}/roles`, { method: 'POST', body: JSON.stringify({ role }) }),
  revokeUserRole: (id) => request(`/api/admin/usuarios/roles/${id}`, { method: 'DELETE' }),
  getTemporaryFunctions: () => request('/api/temporary-functions'),
  getTemporaryAssignments: () => request('/api/temporary-assignments'),
  createTemporaryAssignment: (data) => request('/api/temporary-assignments', { method: 'POST', body: JSON.stringify(data) }),
  finishTemporaryAssignment: (id, status) => request(`/api/temporary-assignments/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),

  // Clientes
  searchCustomers: (q) => {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    return request(`/api/customers?${params.toString()}`);
  },

  // Inventario (fase 1: solo lectura)
  getEquipmentBySerial: (serie) =>
    request(`/api/inventario/equipos/serie/${encodeURIComponent(serie.trim())}`),
  getPendingInventoryMovements: () => request('/api/inventario/movimientos/pendientes'),
  confirmInventoryReception: (id) => request(`/api/inventario/movimientos/${id}/confirmar`, { method: 'POST' }),

  // Reportes
  getPDF: (from, to, requestType, serviceType = '', showMotivos = false) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    if (requestType && requestType !== 'all') params.set('requestType', requestType);
    if (serviceType && serviceType !== 'all') params.set('serviceType', serviceType);
    if (showMotivos) params.set('showMotivos', 'si');
    return request(`/api/reports/pdf?${params.toString()}`);
  },
  getXLSX: (from, to, requestType = '', serviceType = '', showMotivos = false) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    if (requestType && requestType !== 'all') params.set('requestType', requestType);
    if (serviceType && serviceType !== 'all') params.set('serviceType', serviceType);
    if (showMotivos) params.set('showMotivos', 'si');
    return request(`/api/reports/xlsx?${params.toString()}`);
  },
  getPNG: (from, to, showMotivos = false) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    if (showMotivos) params.set('showMotivos', 'si');
    return request(`/api/reports/png?${params.toString()}`);
  },
  getDashboardPDF: (requestType = 'all') => {
    const query = requestType && requestType !== 'all'
      ? `?requestType=${encodeURIComponent(requestType)}` : '';
    return request(`/api/reports/dashboard/pdf${query}`);
  },
  getDashboardXLSX: (requestType = 'all') => {
    const query = requestType && requestType !== 'all'
      ? `?requestType=${encodeURIComponent(requestType)}` : '';
    return request(`/api/reports/dashboard/xlsx${query}`);
  },
  getDashboardPNG: (requestType = 'all') => {
    const query = requestType && requestType !== 'all'
      ? `?requestType=${encodeURIComponent(requestType)}` : '';
    return request(`/api/reports/dashboard/png${query}`);
  },

  // Backups
  getBackups: () => request('/api/admin/respaldos'),
  // Genera el respaldo y devuelve el archivo .dump directamente.
  // El servidor lo borra tras la transmision: no queda almacenado en Render.
  createBackup: () => {
    const token = localStorage.getItem('token');
    return fetch(`${API_URL}/api/admin/respaldos`, {
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
  deleteBackup: (id) => request(`/api/admin/respaldos/${id}`, { method: 'DELETE' }),
};

export default api;
