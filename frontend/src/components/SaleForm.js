import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';
import { Button, Input, Select, Card, Alert, TotalDisplay } from './ui';

const REQUEST_TYPES = [
  { value: 'nuevo_contrato', label: 'NUEVO CONTRATO' },
  { value: 'cambio_plan', label: 'CAMBIO DE PLAN' },
  { value: 'recontratacion', label: 'RECONTRATACION' },
  { value: 'retiro', label: 'RETIRO' },
  { value: 'adicion', label: 'ADICION' },
  { value: 'baja_temporal', label: 'BAJA TEMPORAL' },
  { value: 'otro', label: 'OTRO' },
];

const SERVICE_TYPES = [
  { value: 'internet', label: 'INTERNET' },
  { value: 'tv', label: 'TV ANALOGA' },
  { value: 'tv_digital', label: 'TV DIGITAL' },
  { value: 'combo_analog', label: 'INTERNET + TV ANALOGA' },
  { value: 'combo_digital', label: 'INTERNET + TV DIGITAL' },
];

const CHANGE_REASONS = [
  'ECONOMICOS', 'AUMENTO DE DISPOSITIVOS', 'VIAJE', 'POCO USO',
  'NO UTILIZA EL SERVICIO', 'MEJOR CALIDAD', 'OTROS',
];

const RETIRO_REASONS = [
  'ECONOMICOS', 'CAMBIO A OTRA EMPRESA', 'MAL SERVICIO', 'TRASLADO',
  'NO UTILIZA EL SERVICIO', 'FUERA DE AREA', 'VIAJE', 'OTROS',
];

export default function SaleForm() {
  const getToday = () => {
    const now = new Date();
    const bolivia = new Date(now.toLocaleString('en-US', { timeZone: 'America/La_Paz' }));
    const y = bolivia.getFullYear();
    const m = String(bolivia.getMonth() + 1).padStart(2, '0');
    const d = String(bolivia.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  };
  const today = getToday();
  const [plans, setPlans] = useState([]);
  const [form, setForm] = useState({
    date: today, clientCode: '', clientName: '', serviceType: 'internet',
    requestType: 'nuevo_contrato', changeReason: '', retiroReason: '',
    notes: '', planId: '',
  });
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  const [query, setQuery] = useState('');
  const [customers, setCustomers] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const dropdownRef = useRef(null);

  // Promotion state
  const [promotions, setPromotions] = useState([]);
  const [selectedPromotion, setSelectedPromotion] = useState(null);
  const [priceMode, setPriceMode] = useState('normal');

  useEffect(() => {
    api.getActivePlans().then(setPlans).catch(() => {});
  }, []);

  const searchCustomers = async (q) => {
    setQuery(q.toUpperCase());
    if (!q.trim()) { setCustomers([]); return; }
    try {
      const res = await api.searchCustomers(q);
      setCustomers(res);
      setShowDropdown(true);
    } catch (err) { setCustomers([]); }
  };

  const pickCustomer = (c) => {
    setSelectedCustomer(c);
    setForm((prev) => ({ ...prev, clientCode: c.code, clientName: c.name }));
    setQuery(c.name);
    setCustomers([]);
    setShowDropdown(false);
  };

  useEffect(() => {
    const onClick = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) setShowDropdown(false);
    };
    document.addEventListener('click', onClick);
    return () => document.removeEventListener('click', onClick);
  }, []);

  const filteredPlans = plans.filter((p) => {
    const typeMap = {
      'internet': 'internet',
      'tv': 'tv',
      'tv_digital': 'tv',
      'combo_analog': 'combo',
      'combo_digital': 'combo',
    };
    return p.type === typeMap[form.serviceType];
  });
  const currentPlans = filteredPlans.filter((p) => !p.legacy);
  const legacyPlans = filteredPlans.filter((p) => p.legacy);
  const isRetiro = form.requestType === 'retiro';
  const isCambio = form.requestType === 'cambio_plan';

  useEffect(() => {
    if (form.planId) {
      const p = plans.find((pl) => String(pl.id) === String(form.planId));
      setSelectedPlan(p || null);
      // Fetch active promotions for this plan
      api.getActivePromotions(form.planId)
        .then(setPromotions)
        .catch(() => setPromotions([]));
      setPriceMode('normal');
      setSelectedPromotion(null);
    } else {
      setSelectedPlan(null);
      setPromotions([]);
      setSelectedPromotion(null);
      setPriceMode('normal');
    }
  }, [form.planId, plans]);

  const handlePriceModeChange = (mode, promo) => {
    setPriceMode(mode);
    setSelectedPromotion(mode === 'promo' ? promo : null);
  };

  const getEffectivePrices = () => {
    if (!selectedPlan) return { installation: 0, monthly: 0, total: 0 };
    const installation = selectedPlan.installation;
    const monthly = selectedPlan.monthly;
    if (priceMode === 'promo' && selectedPromotion) {
      const promoInst = selectedPromotion.apply_installation
        ? parseFloat(selectedPromotion.installation_price)
        : installation;
      const promoMonthly = selectedPromotion.apply_monthly
        ? parseFloat(selectedPromotion.monthly_price)
        : monthly;
      return {
        installation: promoInst,
        monthly: promoMonthly,
        total: isRetiro ? promoMonthly : promoMonthly + promoInst,
      };
    }
    return {
      installation,
      monthly,
      total: isRetiro ? monthly : parseFloat(selectedPlan.total),
    };
  };

  const effectivePrices = getEffectivePrices();

  const handleChange = (e) => {
    const { name, value } = e.target;
    const UPPERCASE_FIELDS = ['clientCode', 'clientName', 'notes'];
    const finalValue = UPPERCASE_FIELDS.includes(name) ? value.toUpperCase() : value;
    setForm((prev) => {
      const next = { ...prev, [name]: finalValue };
      if (name === 'serviceType' || name === 'requestType') next.planId = '';
      return next;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      const payload = {
        date: form.date,
        clientCode: form.clientCode,
        clientName: form.clientName,
        serviceType: form.serviceType,
        requestType: form.requestType,
        changeReason: isCambio ? form.changeReason : (isRetiro ? form.retiroReason : ''),
        notes: form.notes,
        planId: Number(form.planId),
      };
      if (selectedPromotion) {
        payload.promotionId = selectedPromotion.id;
      }
      await api.createSale(payload);
      setSuccess('Registro guardado correctamente');
      setForm({ date: today, clientCode: '', clientName: '', serviceType: 'internet', requestType: 'nuevo_contrato', changeReason: '', retiroReason: '', notes: '', planId: '' });
      setSelectedPlan(null); setSelectedCustomer(null); setQuery(''); setCustomers([]);
      setPromotions([]); setSelectedPromotion(null); setPriceMode('normal');
      setShowPreview(false);
    } catch (err) {
      setError(err.error || 'Error al registrar');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    const [y, m, d] = dateStr.split('-');
    return `${d}/${m}/${y}`;
  };

  const getRequestLabel = (val) => {
    const found = REQUEST_TYPES.find(t => t.value === val);
    return found ? found.label : val;
  };

  const getServiceLabel = (val) => {
    const found = SERVICE_TYPES.find(t => t.value === val);
    return found ? found.label : val;
  };

  const getMotivoLabel = () => {
    if (isCambio) return form.changeReason;
    if (isRetiro) return form.retiroReason;
    return '';
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Registrar Movimiento</h1>
        <p className="text-sm text-slate-400 mt-1">Nuevo registro de movimiento de cliente</p>
      </div>

      <Card className="p-6">
        <form onSubmit={(e) => { e.preventDefault(); setShowPreview(true); }} className="space-y-5">
          {error && <Alert type="error">{error}</Alert>}
          {success && <Alert type="success">{success}</Alert>}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Fecha</label>
              <div className="w-full px-4 py-3 rounded-xl bg-brand-50 border border-brand-200 text-brand-800 font-bold text-sm">
                {formatDate(today)}
              </div>
            </div>
            <Input label="Kardex *" name="clientCode" value={form.clientCode} onChange={handleChange} required placeholder="N° kardex" />
          </div>

          <div ref={dropdownRef} className="relative">
            <Input
              label="Nombre del Cliente *"
              value={query}
              onChange={(e) => { setSelectedCustomer(null); setForm(prev => ({ ...prev, clientName: e.target.value.toUpperCase() })); searchCustomers(e.target.value); }}
              placeholder="Escriba nombre o kardex del cliente..."
              autoComplete="off"
              required
            />
            {showDropdown && customers.length > 0 && (
              <ul className="absolute z-20 mt-1 w-full bg-white border-0 rounded-xl shadow-xl max-h-56 overflow-auto">
                {customers.map((c) => (
                  <li key={c.id}>
                    <button type="button" onClick={() => pickCustomer(c)}
                      className="w-full text-left px-4 py-3 hover:bg-brand-50 flex items-center justify-between gap-2 transition-colors">
                      <span className="text-sm text-slate-700 font-medium">{c.name}</span>
                      <span className="text-xs font-mono text-slate-400 bg-slate-100 px-2 py-0.5 rounded">{c.code}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {!query && !selectedCustomer && (
              <p className="text-xs text-slate-400 mt-1">Ingrese nombre o kardex; si no existe, se creara automaticamente.</p>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select label="Tipo de Solicitud *" name="requestType" value={form.requestType} onChange={handleChange} required>
              {REQUEST_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </Select>
            <Select label="Tipo de Servicio *" name="serviceType" value={form.serviceType} onChange={handleChange}>
              {SERVICE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </Select>
          </div>

          <Select label="Paquete / Plan *" name="planId" value={form.planId} onChange={handleChange} required>
            <option value="">Seleccionar plan...</option>
            <optgroup label="Planes vigentes">
              {currentPlans.map((p) => (
                <option key={p.id} value={p.id}>{p.label} - {parseFloat(p.monthly).toFixed(0)} Bs</option>
              ))}
            </optgroup>
            {isRetiro && legacyPlans.length > 0 && (
              <optgroup label="Planes anteriores">
                {legacyPlans.map((p) => (
                  <option key={p.id} value={p.id}>{p.label} - {parseFloat(p.monthly).toFixed(0)} Bs</option>
                ))}
              </optgroup>
            )}
          </Select>

          {isCambio && (
            <Select label="Motivo del Cambio *" name="changeReason" value={form.changeReason} onChange={handleChange} required>
              <option value="">Seleccionar motivo...</option>
              {CHANGE_REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
            </Select>
          )}

          {isRetiro && (
            <Select label="Motivo del Retiro *" name="retiroReason" value={form.retiroReason} onChange={handleChange} required>
              <option value="">Seleccionar motivo...</option>
              {RETIRO_REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
            </Select>
          )}

          <Input label="Comentarios (opcional)" name="notes" value={form.notes} onChange={handleChange} placeholder="Notas internas" />

          {/* Price mode selection */}
          {selectedPlan && promotions.length > 0 && (
            <div className="bg-slate-50 rounded-2xl p-5 space-y-3 border border-slate-100">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Modalidad de precio</h3>
              <div className="space-y-2">
                <label className="flex items-start gap-3 p-3 rounded-xl border-2 cursor-pointer transition-all hover:bg-white"
                  style={{ borderColor: priceMode === 'normal' ? 'rgb(99 102 241)' : 'rgb(226 232 240)' }}>
                  <input type="radio" name="priceMode" value="normal"
                    checked={priceMode === 'normal'}
                    onChange={() => handlePriceModeChange('normal', null)}
                    className="mt-0.5 text-brand-600 focus:ring-brand-500" />
                  <div className="flex-1">
                    <div className="font-semibold text-sm text-slate-900">Precio normal</div>
                    <div className="text-xs text-slate-500 mt-1">
                      Instalacion: {parseFloat(selectedPlan.installation).toFixed(2)} Bs
                      {' | '}
                      Mensualidad: {parseFloat(selectedPlan.monthly).toFixed(2)} Bs
                    </div>
                  </div>
                  <div className="font-bold text-sm text-slate-700">
                    {parseFloat(isRetiro ? selectedPlan.monthly : selectedPlan.total).toFixed(2)} Bs
                  </div>
                </label>
                {promotions.map((promo) => {
                  const promoInst = promo.apply_installation
                    ? parseFloat(promo.installation_price)
                    : parseFloat(selectedPlan.installation);
                  const promoMonthly = promo.apply_monthly
                    ? parseFloat(promo.monthly_price)
                    : parseFloat(selectedPlan.monthly);
                  const promoTotal = isRetiro ? promoMonthly : promoMonthly + promoInst;
                  const concepts = [];
                  if (promo.apply_installation) concepts.push(`Inst: ${parseFloat(promo.installation_price).toFixed(2)} Bs`);
                  if (promo.apply_monthly) concepts.push(`Mensual: ${parseFloat(promo.monthly_price).toFixed(2)} Bs`);
                  return (
                    <label key={promo.id}
                      className="flex items-start gap-3 p-3 rounded-xl border-2 cursor-pointer transition-all hover:bg-white"
                      style={{ borderColor: priceMode === 'promo' && selectedPromotion?.id === promo.id ? 'rgb(99 102 241)' : 'rgb(226 232 240)' }}>
                      <input type="radio" name="priceMode" value={`promo-${promo.id}`}
                        checked={priceMode === 'promo' && selectedPromotion?.id === promo.id}
                        onChange={() => handlePriceModeChange('promo', promo)}
                        className="mt-0.5 text-brand-600 focus:ring-brand-500" />
                      <div className="flex-1">
                        <div className="font-semibold text-sm text-slate-900">Promocion {promo.name}</div>
                        <div className="text-xs text-emerald-600 font-medium mt-0.5">
                          {concepts.join(' | ')}
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          Instalacion: {promoInst.toFixed(2)} Bs
                          {' | '}
                          Mensualidad: {promoMonthly.toFixed(2)} Bs
                        </div>
                      </div>
                      <div className="font-bold text-sm text-emerald-700">
                        {promoTotal.toFixed(2)} Bs
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          {/* Preview */}
          {selectedPlan && (
            <div className="bg-slate-50 rounded-2xl p-5 space-y-3 border border-slate-100">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Vista Previa</h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-slate-400">Fecha:</span></div>
                <div className="font-medium">{formatDate(form.date)}</div>
                <div><span className="text-slate-400">Kardex:</span></div>
                <div className="font-medium">{form.clientCode || '—'}</div>
                <div><span className="text-slate-400">Cliente:</span></div>
                <div className="font-medium">{form.clientName || '—'}</div>
                <div><span className="text-slate-400">Solicitud:</span></div>
                <div className="font-medium">{getRequestLabel(form.requestType)}</div>
                <div><span className="text-slate-400">Servicio:</span></div>
                <div className="font-medium">{getServiceLabel(form.serviceType)}</div>
                <div><span className="text-slate-400">Plan:</span></div>
                <div className="font-medium">{selectedPlan.label}</div>
                {selectedPromotion && (
                  <>
                    <div><span className="text-slate-400">Promocion:</span></div>
                    <div className="font-medium text-emerald-600">{selectedPromotion.name}</div>
                  </>
                )}
                <div><span className="text-slate-400">Instalacion:</span></div>
                <div className="font-medium">{effectivePrices.installation.toFixed(2)} Bs</div>
                <div><span className="text-slate-400">Mensualidad:</span></div>
                <div className="font-medium">{effectivePrices.monthly.toFixed(2)} Bs</div>
                <div><span className="text-slate-400">Monto:</span></div>
                <div className="font-bold text-brand-700">Bs. {effectivePrices.total.toFixed(2)}</div>
                {getMotivoLabel() && (
                  <>
                    <div><span className="text-slate-400">Motivo:</span></div>
                    <div className="font-medium">{getMotivoLabel()}</div>
                  </>
                )}
                {form.notes && (
                  <>
                    <div><span className="text-slate-400">Comentarios:</span></div>
                    <div className="font-medium">{form.notes}</div>
                  </>
                )}
              </div>
            </div>
          )}

          <Button type="submit" size="lg" className="w-full" disabled={!form.planId}>
            Revisar Registro
          </Button>
        </form>
      </Card>

      {showPreview && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-6 space-y-4">
            <div className="text-center">
              <h2 className="text-xl font-black text-slate-900">Confirmar Registro</h2>
              <p className="text-xs text-slate-400 mt-1">Revise los datos antes de guardar</p>
            </div>
            {selectedPlan && (
              <div className="bg-slate-50 rounded-2xl p-4 space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-slate-400">Fecha:</span><span className="font-medium">{formatDate(form.date)}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Kardex:</span><span className="font-medium">{form.clientCode}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Cliente:</span><span className="font-medium">{form.clientName}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Solicitud:</span><span className="font-medium">{getRequestLabel(form.requestType)}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Servicio:</span><span className="font-medium">{getServiceLabel(form.serviceType)}</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Plan:</span><span className="font-medium">{selectedPlan.label}</span></div>
                {selectedPromotion && (
                  <div className="flex justify-between"><span className="text-slate-400">Promocion:</span><span className="font-medium text-emerald-600">{selectedPromotion.name}</span></div>
                )}
                <div className="flex justify-between"><span className="text-slate-400">Instalacion:</span><span className="font-medium">{effectivePrices.installation.toFixed(2)} Bs</span></div>
                <div className="flex justify-between"><span className="text-slate-400">Mensualidad:</span><span className="font-medium">{effectivePrices.monthly.toFixed(2)} Bs</span></div>
                <div className="flex justify-between border-t border-slate-200 pt-2"><span className="text-slate-400">Monto:</span><span className="font-bold text-brand-700 text-lg">Bs. {effectivePrices.total.toFixed(2)}</span></div>
                {getMotivoLabel() && (
                  <div className="flex justify-between"><span className="text-slate-400">Motivo:</span><span className="font-medium">{getMotivoLabel()}</span></div>
                )}
              </div>
            )}
            <div className="flex gap-3">
              <Button type="button" variant="secondary" size="lg" className="flex-1" onClick={() => setShowPreview(false)}>
                Cancelar
              </Button>
              <Button type="button" size="lg" className="flex-1" onClick={handleSubmit} disabled={loading}>
                {loading ? 'Guardando...' : 'Confirmar'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
