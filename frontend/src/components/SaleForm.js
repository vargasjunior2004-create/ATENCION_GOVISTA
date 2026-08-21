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
  const today = new Date().toISOString().split('T')[0];
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

  // Autocompletar cliente por kardex/nombre
  const [query, setQuery] = useState('');
  const [customers, setCustomers] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const dropdownRef = useRef(null);

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
    // Map service types to plan types
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
    } else {
      setSelectedPlan(null);
    }
  }, [form.planId, plans]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    // Convertir a mayusculas los campos de texto
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
      await api.createSale({
        date: form.date,
        clientCode: form.clientCode,
        clientName: form.clientName,
        serviceType: form.serviceType,
        requestType: form.requestType,
        changeReason: isCambio ? form.changeReason : (isRetiro ? form.retiroReason : ''),
        notes: form.notes,
        planId: Number(form.planId),
      });
      setSuccess('Registro guardado correctamente');
      setForm({ date: today, clientCode: '', clientName: '', serviceType: 'internet', requestType: 'nuevo_contrato', changeReason: '', retiroReason: '', notes: '', planId: '' });
      setSelectedPlan(null); setSelectedCustomer(null); setQuery(''); setCustomers([]);
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
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-slate-900">Registrar Movimiento</h1>

      <Card className="p-5">
        <form onSubmit={(e) => { e.preventDefault(); setShowPreview(true); }} className="space-y-4">
          {error && <Alert type="error">{error}</Alert>}
          {success && <Alert type="success">{success}</Alert>}

          {/* Fila 1: Fecha + Kardex */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input label="Fecha *" type="date" name="date" value={form.date} onChange={handleChange} required />
            <Input label="Kardex *" name="clientCode" value={form.clientCode} onChange={handleChange} required placeholder="N° kardex" />
          </div>

          {/* Fila 2: Nombre Cliente */}
          <div ref={dropdownRef} className="relative">
            <Input
              label="Nombre del Cliente *"
              value={query}
              onChange={(e) => { setSelectedCustomer(null); searchCustomers(e.target.value); }}
              placeholder="Escriba nombre o kardex del cliente..."
              autoComplete="off"
              required
            />
            {showDropdown && customers.length > 0 && (
              <ul className="absolute z-20 mt-1 w-full bg-white border border-slate-200 rounded-xl shadow-lg max-h-56 overflow-auto">
                {customers.map((c) => (
                  <li key={c.id}>
                    <button type="button" onClick={() => pickCustomer(c)}
                      className="w-full text-left px-4 py-2 hover:bg-green-50 flex items-center justify-between gap-2">
                      <span className="text-sm text-slate-700">{c.name}</span>
                      <span className="text-xs font-mono text-slate-400">{c.code}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {!query && !selectedCustomer && (
              <p className="text-xs text-slate-400 mt-1">Ingrese nombre o kardex; si no existe, se creara automaticamente.</p>
            )}
          </div>

          {/* Fila 3: Tipo Solicitud + Tipo Servicio */}
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

          {/* Fila 4: Plan */}
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

          {/* Motivo Cambio */}
          {isCambio && (
            <Select label="Motivo del Cambio *" name="changeReason" value={form.changeReason} onChange={handleChange} required>
              <option value="">Seleccionar motivo...</option>
              {CHANGE_REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
            </Select>
          )}

          {/* Motivo Retiro */}
          {isRetiro && (
            <Select label="Motivo del Retiro *" name="retiroReason" value={form.retiroReason} onChange={handleChange} required>
              <option value="">Seleccionar motivo...</option>
              {RETIRO_REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
            </Select>
          )}

          {/* Comentarios */}
          <Input label="Comentarios (opcional)" name="notes" value={form.notes} onChange={handleChange} placeholder="Notas internas" />

          {/* Vista Previa */}
          {selectedPlan && (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
              <h3 className="text-sm font-semibold text-slate-700 border-b pb-2">VISTA PREVIA</h3>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-slate-500">Fecha:</span></div>
                <div className="font-medium">{formatDate(form.date)}</div>

                <div><span className="text-slate-500">Kardex:</span></div>
                <div className="font-medium">{form.clientCode || '—'}</div>

                <div><span className="text-slate-500">Cliente:</span></div>
                <div className="font-medium">{form.clientName || '—'}</div>

                <div><span className="text-slate-500">Solicitud:</span></div>
                <div className="font-medium">{getRequestLabel(form.requestType)}</div>

                <div><span className="text-slate-500">Servicio:</span></div>
                <div className="font-medium">{getServiceLabel(form.serviceType)}</div>

                <div><span className="text-slate-500">Plan:</span></div>
                <div className="font-medium">{selectedPlan.label}</div>

                <div><span className="text-slate-500">Monto:</span></div>
                <div className="font-bold text-green-700">Bs. {parseFloat(selectedPlan.monthly).toFixed(2)}</div>

                {getMotivoLabel() && (
                  <>
                    <div><span className="text-slate-500">Motivo:</span></div>
                    <div className="font-medium">{getMotivoLabel()}</div>
                  </>
                )}

                {form.notes && (
                  <>
                    <div><span className="text-slate-500">Comentarios:</span></div>
                    <div className="font-medium">{form.notes}</div>
                  </>
                )}
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <Button type="submit" size="lg" className="flex-1" disabled={!form.planId}>
              Revisar Registro
            </Button>
          </div>
        </form>
      </Card>

      {/* Modal de Confirmacion */}
      {showPreview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900 text-center">Confirmar Registro</h2>
            
            {selectedPlan && (
              <div className="bg-slate-50 rounded-xl p-4 space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-slate-500">Fecha:</span><span className="font-medium">{formatDate(form.date)}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Kardex:</span><span className="font-medium">{form.clientCode}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Cliente:</span><span className="font-medium">{form.clientName}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Solicitud:</span><span className="font-medium">{getRequestLabel(form.requestType)}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Servicio:</span><span className="font-medium">{getServiceLabel(form.serviceType)}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Plan:</span><span className="font-medium">{selectedPlan.label}</span></div>
                <div className="flex justify-between border-t pt-2"><span className="text-slate-500">Total:</span><span className="font-bold text-green-700 text-lg">Bs. {parseFloat(selectedPlan.monthly).toFixed(2)}</span></div>
                {getMotivoLabel() && (
                  <div className="flex justify-between"><span className="text-slate-500">Motivo:</span><span className="font-medium">{getMotivoLabel()}</span></div>
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
