import React, { useState, useEffect, useRef } from 'react';
import api from '../../../services/api';
import { Button, Input, Select, Card, Alert, TotalDisplay } from '../../../components/ui';
import useRequestTypes from '../../../hooks/useRequestTypes';
import useMotivos from '../../../hooks/useMotivos';
import SalePreviewModal from '../../../components/SalePreview';

const SERVICE_TYPES = [
  { value: 'internet', label: 'INTERNET' },
  { value: 'tv', label: 'TV ANALOGA' },
  { value: 'tv_digital', label: 'TV DIGITAL' },
  { value: 'combo_analog', label: 'INTERNET + TV ANALOGA' },
  { value: 'combo_digital', label: 'INTERNET + TV DIGITAL' },
];

const SERVICE_TYPE_LABELS = Object.fromEntries(
  SERVICE_TYPES.map((t) => [t.value, t.label]));

// Tipo de servicio -> familia de plan que ese servicio puede contratar.
// El catalogo de planes distingue tres familias, no cinco servicios: por eso
// TV analoga y TV digital comparten 'tv', y los combos comparten 'combo'.
const SERVICE_TYPE_TO_PLAN_TYPE = {
  internet: 'internet',
  tv: 'tv',
  tv_digital: 'tv',
  combo_analog: 'combo',
  combo_digital: 'combo',
};

// Servicio anterior que se presume por defecto segun la familia del plan
// elegido. El operador puede corregirlo si el cliente tiene otra variante.
const FAMILY_DEFAULT_SERVICE = {
  internet: 'internet',
  tv: 'tv',
  combo: 'combo_analog',
};

const FAMILY_LABELS = { internet: 'INTERNET', tv: 'TV', combo: 'COMBO' };

const ADDITION_TYPES = [
  { value: 'adicion_internet', label: 'ADICION INTERNET' },
  { value: 'adicion_tv', label: 'ADICION TV' },
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
    requestType: 'nuevo_contrato', additionType: '', planFromId: '',
    serviceTypeFrom: '', motivoId: '', notes: '',
    planId: '',
    equipmentRetained: null, requiresTechnicalVisit: null,
    debtApplies: false, debtAmount: '',
    transferCurrentAddress: '', transferNewAddress: '', transferZone: '',
    transferReferences: '', transferHasSketch: null,
  });
  const { tipos: requestTypes, modoOf, nombreOf } = useRequestTypes();
  const { porCategoria, nombreOf: motivoNombreOf } = useMotivos();
  const modo = modoOf(form.requestType);
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
  const [transferTariffs, setTransferTariffs] = useState([]);

  useEffect(() => {
    api.getActivePlans().then(setPlans).catch(() => {});
    api.getActiveTransferTariffs().then(setTransferTariffs).catch(() => {});
  }, []);

  // El tipo por defecto viene sembrado, pero si un administrador lo
  // desactiva el formulario no puede quedar con un valor que ya no existe.
  useEffect(() => {
    if (!requestTypes.length) return;
    if (requestTypes.some((t) => t.code === form.requestType)) return;
    setForm((f) => ({ ...f, requestType: requestTypes[0].code }));
  }, [requestTypes, form.requestType]);

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

  const isRetiro = modo === 'retiro';
  const isCambio = modo === 'cambio_plan';
  const isAdicion = modo === 'adicion';
  const isRecontratacion = form.requestType === 'recontratacion';
  const isTransfer = form.requestType === 'traslado_externo';

  // Motivos del catalogo segun el formulario que corresponde.
  const motivosCambio = porCategoria('cambio');
  const motivosRetiro = porCategoria('retiro');

  // El plan nuevo se filtra por el servicio NUEVO. El plan anterior se
  // filtra por su propia familia, no por el servicio nuevo: por eso ahora
  // es posible cambiar de Combo a Internet o de TV a Combo, que antes era
  // imposible porque ambos selectores compartian un unico tipo de servicio.
  const newPlanOptions = plans.filter((p) => {
    if (modo === 'adicion') return p.type === 'combo';
    return p.type === SERVICE_TYPE_TO_PLAN_TYPE[form.serviceType];
  });

  // El plan anterior se ofrece completo y agrupado por familia, sin atarse
  // al servicio nuevo. Se omite el plan ya elegido como nuevo para no
  // proponer un cambio que no cambia nada.
  const previousPlanOptions = isCambio
    ? plans.filter((p) => String(p.id) !== String(form.planId))
    : [];

  const currentPlans = newPlanOptions.filter((p) => !p.legacy);
  const legacyPlans = isRetiro ? newPlanOptions.filter((p) => p.legacy) : [];

  const selectedPreviousPlan = plans.find(
    (p) => String(p.id) === String(form.planFromId)) || null;

  const previousFamily = selectedPreviousPlan ? selectedPreviousPlan.type : null;
  const currentFamily = SERVICE_TYPE_TO_PLAN_TYPE[form.serviceType];
  const isServiceChange = isCambio && previousFamily && currentFamily
    && previousFamily !== currentFamily;

  // El backend vuelve a validar todo esto; aqui solo se evita que el
  // operador vea un formulario que el servidor va a rechazar.
  const samePlanSelected = isCambio && form.planFromId
    && String(form.planId) === String(form.planFromId)
    && (!form.serviceTypeFrom || form.serviceTypeFrom === form.serviceType);

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
    if (isTransfer) {
      const family = SERVICE_TYPE_TO_PLAN_TYPE[form.serviceType];
      const tariff = transferTariffs.find((item) => item.service_type === family);
      return { installation: 0, monthly: 0, total: Number(tariff?.amount || 0) };
    }
    if (!selectedPlan) return { installation: 0, monthly: 0, total: 0 };
    const installation = parseFloat(selectedPlan.installation) || 0;
    const monthly = parseFloat(selectedPlan.monthly) || 0;
    if (priceMode === 'promo' && selectedPromotion) {
      const promoInst = selectedPromotion.apply_installation
        ? parseFloat(selectedPromotion.installation_price)
        : installation;
      const promoMonthly = selectedPromotion.apply_monthly
        ? parseFloat(selectedPromotion.monthly_price)
        : monthly;
      return {
        installation: (isAdicion || isCambio) ? 0 : promoInst,
        monthly: promoMonthly,
        total: isRetiro || isAdicion || isCambio ? promoMonthly : promoMonthly + promoInst,
      };
    }
    return {
      installation: (isAdicion || isCambio) ? 0 : installation,
      monthly,
      total: isRetiro || isAdicion || isCambio ? monthly : installation + monthly,
    };
  };

  const effectivePrices = getEffectivePrices();
  const debtValue = isRecontratacion && form.debtApplies
    ? Number(form.debtAmount || 0) : 0;
  const totalWithDebt = effectivePrices.total + debtValue;

  const handleChange = (e) => {
    const { name, value } = e.target;
    const UPPERCASE_FIELDS = ['clientCode', 'clientName', 'notes'];
    const finalValue = UPPERCASE_FIELDS.includes(name) ? value.toUpperCase() : value;
    setForm((prev) => {
      const next = { ...prev, [name]: finalValue };
      // Cambiar el servicio nuevo invalida el plan nuevo, y con el el tipo
      // de servicio anterior derivado: dejarlos puestos dejaria un plan
      // incompatible seleccionado que el backend rechazaria.
      if (name === 'serviceType') {
        next.planId = '';
        next.serviceTypeFrom = '';
      }
      if (name === 'requestType') {
        next.planId = '';
        next.motivoId = '';
        const nuevoModo = modoOf(value);
        if (nuevoModo !== 'adicion') next.additionType = '';
        if (nuevoModo !== 'cambio_plan') {
          next.planFromId = '';
          next.serviceTypeFrom = '';
        }
        if (value !== 'recontratacion') {
          next.equipmentRetained = null;
          next.requiresTechnicalVisit = null;
          next.debtApplies = false;
          next.debtAmount = '';
        }
        if (value !== 'traslado_externo') {
          next.transferCurrentAddress = '';
          next.transferNewAddress = '';
          next.transferZone = '';
          next.transferReferences = '';
          next.transferHasSketch = null;
        }
      }
      return next;
    });
  };

  const handlePreviousPlanChange = (e) => {
    const value = e.target.value;
    const picked = plans.find((p) => String(p.id) === String(value));
    setForm((prev) => ({
      ...prev,
      planFromId: value,
      // El servicio anterior se deduce del plan anterior. El operador solo
      // tiene que corregirlo cuando el cliente tiene otra variante (analogica
      // o digital) de la misma familia.
      serviceTypeFrom: picked ? (FAMILY_DEFAULT_SERVICE[picked.type] || '') : '',
    }));
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
        additionType: isAdicion ? form.additionType : '',
        planFromId: isCambio && form.planFromId ? Number(form.planFromId) : null,
        serviceTypeFrom: isCambio && form.serviceTypeFrom ? form.serviceTypeFrom : null,
        motivoId: (isCambio || isRetiro) && form.motivoId ? Number(form.motivoId) : null,
        notes: form.notes,
        planId: Number(form.planId),
      };
      if (isRecontratacion) {
        payload.equipmentRetained = form.equipmentRetained;
        payload.requiresTechnicalVisit = form.requiresTechnicalVisit;
        payload.debtApplies = form.debtApplies;
        payload.debtAmount = form.debtApplies ? Number(form.debtAmount) : 0;
      }
      if (isTransfer) {
        const family = SERVICE_TYPE_TO_PLAN_TYPE[form.serviceType];
        const tariff = transferTariffs.find((item) => item.service_type === family);
        payload.transferTariffId = tariff?.id;
        payload.transferCurrentAddress = form.transferCurrentAddress;
        payload.transferNewAddress = form.transferNewAddress;
        payload.transferZone = form.transferZone;
        payload.transferReferences = form.transferReferences;
        payload.transferHasSketch = form.transferHasSketch;
      }
      if (selectedPromotion) {
        payload.promotionId = selectedPromotion.id;
      }
      await api.createSale(payload);
      setSuccess('Registro guardado correctamente');
       setForm({ date: today, clientCode: '', clientName: '', serviceType: 'internet', requestType: 'nuevo_contrato', additionType: '', planFromId: '', serviceTypeFrom: '', motivoId: '', notes: '', planId: '', equipmentRetained: null, requiresTechnicalVisit: null, debtApplies: false, debtAmount: '', transferCurrentAddress: '', transferNewAddress: '', transferZone: '', transferReferences: '', transferHasSketch: null });
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
    if (modoOf(val) === 'adicion' && form.additionType) {
      return form.additionType === 'adicion_internet' ? 'ADICION INTERNET' : 'ADICION TV';
    }
    return nombreOf(val);
  };

  const getServiceLabel = (val) => {
    const found = SERVICE_TYPES.find(t => t.value === val);
    return found ? found.label : val;
  };

  const getMotivoLabel = () => motivoNombreOf(form.motivoId);

  const previewSale = {
    date: formatDate(form.date),
    requestType: form.requestType,
    clientCode: form.clientCode,
    clientName: form.clientName,
    requestLabel: getRequestLabel(form.requestType),
    serviceLabel: getServiceLabel(form.serviceType),
    previousServiceLabel: SERVICE_TYPE_LABELS[form.serviceTypeFrom] || FAMILY_LABELS[previousFamily],
    previousPlanLabel: selectedPreviousPlan?.label,
    planLabel: selectedPlan?.label,
    promotionName: selectedPromotion?.name,
    installation: effectivePrices.installation.toFixed(2),
    monthly: effectivePrices.monthly.toFixed(2),
    total: totalWithDebt.toFixed(2),
    debtAmount: isRecontratacion ? Number(form.debtAmount || 0).toFixed(2) : null,
    totalToCollect: isRecontratacion
      ? totalWithDebt.toFixed(2)
      : null,
    equipmentRetained: isRecontratacion ? form.equipmentRetained : null,
    requiresTechnicalVisit: isRecontratacion ? form.requiresTechnicalVisit : null,
    transferCurrentAddress: isTransfer ? form.transferCurrentAddress : null,
    transferNewAddress: isTransfer ? form.transferNewAddress : null,
    transferZone: isTransfer ? form.transferZone : null,
    transferReferences: isTransfer ? form.transferReferences : null,
    transferHasSketch: isTransfer ? form.transferHasSketch : null,
    motivo: getMotivoLabel(),
    notes: form.notes,
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Registrar Solicitud</h1>
        <p className="text-sm text-slate-400 mt-1">Nuevo registro de solicitud de cliente</p>
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
              {requestTypes.map((t) => (
                <option key={t.code} value={t.code}>{t.nombre}</option>
              ))}
            </Select>
             <Select
               label={isCambio ? 'Tipo de Servicio Nuevo *' : 'Tipo de Servicio *'}
               name="serviceType"
               value={form.serviceType}
               onChange={handleChange}
             >
               {SERVICE_TYPES.map((t) => (
                 <option key={t.value} value={t.value}>{t.label}</option>
               ))}
             </Select>
          </div>

          {isAdicion && (
            <Select label="Tipo de Adicion *" name="additionType" value={form.additionType} onChange={handleChange} required>
              <option value="">--Seleccione--</option>
              {ADDITION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </Select>
          )}

          {isTransfer && (
            <div className="rounded-2xl border-2 border-dashed border-sky-200 bg-sky-50/40 p-4 space-y-4">
              <p className="text-xs font-bold uppercase tracking-wider text-sky-700">Datos del traslado externo</p>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input label="Domicilio actual" name="transferCurrentAddress" value={form.transferCurrentAddress} onChange={handleChange} placeholder="Si está disponible" />
                <Input label="Nuevo domicilio *" name="transferNewAddress" value={form.transferNewAddress} onChange={handleChange} required placeholder="Calle y número" />
                <Input label="Barrio / zona" name="transferZone" value={form.transferZone} onChange={handleChange} placeholder="Zona del nuevo domicilio" />
                <Input label="Referencias" name="transferReferences" value={form.transferReferences} onChange={handleChange} placeholder="Puntos de referencia" />
              </div>
              <Select label="¿El cliente trajo croquis físico? *" name="transferHasSketch" value={form.transferHasSketch === null ? '' : String(form.transferHasSketch)} onChange={(event) => setForm((prev) => ({ ...prev, transferHasSketch: event.target.value === '' ? null : event.target.value === 'true' }))} required>
                <option value="">--Seleccione--</option>
                <option value="true">Sí, trajo croquis físico</option>
                <option value="false">No, queda pendiente de ubicación</option>
              </Select>
              <p className="text-xs text-slate-500">La validación de cobertura, la ubicación por QR y la asignación de técnicos corresponden a Operaciones.</p>
            </div>
          )}

          {isCambio && (
            <div className="rounded-2xl border-2 border-dashed border-amber-200 bg-amber-50/40 p-4 space-y-4">
              <p className="text-xs font-bold text-amber-700 uppercase tracking-wider">
                Servicio que tiene el cliente
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Select
                  label="Plan Anterior *"
                  name="planFromId"
                  value={form.planFromId}
                  onChange={handlePreviousPlanChange}
                  required
                >
                  <option value="">--Seleccione plan anterior--</option>
                  {['internet', 'tv', 'combo'].map((family) => {
                    const group = previousPlanOptions.filter((p) => p.type === family);
                    if (!group.length) return null;
                    return (
                      <optgroup key={family} label={FAMILY_LABELS[family]}>
                        {group.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.code} - {p.label}{p.legacy ? ' (Anterior)' : ''}
                          </option>
                        ))}
                      </optgroup>
                    );
                  })}
                </Select>
                <Select
                  label="Tipo de Servicio Anterior *"
                  name="serviceTypeFrom"
                  value={form.serviceTypeFrom}
                  onChange={handleChange}
                  required
                  disabled={!form.planFromId}
                >
                  <option value="">--Seleccione--</option>
                  {SERVICE_TYPES
                    .filter((t) => !previousFamily
                      || SERVICE_TYPE_TO_PLAN_TYPE[t.value] === previousFamily)
                    .map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                </Select>
              </div>
              <p className="text-xs text-slate-500">
                Se deduce del plan anterior. Corrijalo solo si el cliente tiene
                otra variante de la misma familia.
              </p>
            </div>
          )}

          <div className={isCambio ? 'rounded-2xl border-2 border-dashed border-brand-200 bg-brand-50/40 p-4 space-y-4' : ''}>
            {isCambio && (
              <p className="text-xs font-bold text-brand-700 uppercase tracking-wider">
                Servicio nuevo
              </p>
            )}
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
          </div>

          {isServiceChange && (
            <div className="flex items-center gap-2 rounded-xl bg-violet-50 border border-violet-200 px-4 py-3">
              <span className="text-xs font-bold text-violet-700 uppercase tracking-wider">
                Conversion de servicio
              </span>
              <span className="text-sm font-semibold text-violet-900">
                {FAMILY_LABELS[previousFamily]} → {FAMILY_LABELS[currentFamily]}
              </span>
              <span className="text-xs text-violet-600">
                (se registra como CAMBIO DE PLAN)
              </span>
            </div>
          )}

          {samePlanSelected && (
            <Alert type="error">
              El plan anterior y el nuevo son el mismo. Elija otro plan, o
              registre la solicitud con otro tipo.
            </Alert>
          )}

          {isCambio && (
            <Select label="Motivo del Cambio *" name="motivoId" value={form.motivoId} onChange={handleChange} required>
              <option value="">Seleccionar motivo...</option>
              {motivosCambio.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
            </Select>
          )}

          {isRetiro && (
            <Select label="Motivo del Retiro *" name="motivoId" value={form.motivoId} onChange={handleChange} required>
              <option value="">Seleccionar motivo...</option>
              {motivosRetiro.map((m) => <option key={m.id} value={m.id}>{m.nombre}</option>)}
            </Select>
          )}

          {isRecontratacion && (
            <div className="rounded-2xl border-2 border-dashed border-violet-200 bg-violet-50/40 p-4 space-y-4">
              <p className="text-xs font-bold text-violet-700 uppercase tracking-wider">
                Datos de la recontratación
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Select label="¿Conserva el router/ONU? *" name="equipmentRetained" value={form.equipmentRetained === null ? '' : String(form.equipmentRetained)} onChange={(e) => setForm((prev) => ({ ...prev, equipmentRetained: e.target.value === '' ? null : e.target.value === 'true' }))} required>
                  <option value="">--Seleccione--</option>
                  <option value="true">Sí</option>
                  <option value="false">No</option>
                </Select>
                <Select label="¿Requiere visita técnica? *" name="requiresTechnicalVisit" value={form.requiresTechnicalVisit === null ? '' : String(form.requiresTechnicalVisit)} onChange={(e) => setForm((prev) => ({ ...prev, requiresTechnicalVisit: e.target.value === '' ? null : e.target.value === 'true' }))} required>
                  <option value="">--Seleccione--</option>
                  <option value="true">Sí</option>
                  <option value="false">No</option>
                </Select>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Select label="¿Tiene adeudo pendiente? *" name="debtApplies" value={String(form.debtApplies)} onChange={(e) => setForm((prev) => ({ ...prev, debtApplies: e.target.value === 'true', debtAmount: e.target.value === 'true' ? prev.debtAmount : '' }))} required>
                  <option value="false">No</option>
                  <option value="true">Sí</option>
                </Select>
                {form.debtApplies && (
                  <Input label="Adeudo pendiente (Bs) *" name="debtAmount" type="number" min="0.01" step="0.01" value={form.debtAmount} onChange={handleChange} required />
                )}
              </div>
            </div>
          )}

          <Input label="Comentarios (opcional)" name="notes" value={form.notes} onChange={handleChange} placeholder="Notas internas" />

          {/* Price mode selection */}
          {selectedPlan && promotions.length > 0 && !isTransfer && (
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
                      Instalacion: {(isAdicion || isCambio) ? '0.00' : parseFloat(selectedPlan.installation).toFixed(2)} Bs
                      {' | '}
                      Mensualidad: {parseFloat(selectedPlan.monthly).toFixed(2)} Bs
                    </div>
                  </div>
                  <div className="font-bold text-sm text-slate-700">
                    {parseFloat(isRetiro || isAdicion || isCambio ? selectedPlan.monthly : selectedPlan.total).toFixed(2)} Bs
                  </div>
                </label>
                {promotions.map((promo) => {
                  const promoInst = promo.apply_installation
                    ? parseFloat(promo.installation_price)
                    : parseFloat(selectedPlan.installation);
                  const promoMonthly = promo.apply_monthly
                    ? parseFloat(promo.monthly_price)
                    : parseFloat(selectedPlan.monthly);
                  const promoTotal = isRetiro || isAdicion || isCambio ? promoMonthly : promoMonthly + promoInst;
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
                          Instalacion: {(isAdicion || isCambio) ? '0.00' : promoInst.toFixed(2)} Bs
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
                {isCambio && selectedPreviousPlan ? (
                  <>
                    <div><span className="text-slate-400">Servicio anterior:</span></div>
                    <div className="font-medium">{SERVICE_TYPE_LABELS[form.serviceTypeFrom] || FAMILY_LABELS[previousFamily]}</div>
                    <div><span className="text-slate-400">Plan anterior:</span></div>
                    <div className="font-medium">{selectedPreviousPlan.label}</div>
                  </>
                ) : (
                  <>
                    <div><span className="text-slate-400">Servicio:</span></div>
                    <div className="font-medium">{getServiceLabel(form.serviceType)}</div>
                  </>
                )}
                {isCambio && (
                  <>
                    <div><span className="text-slate-400">Servicio nuevo:</span></div>
                    <div className="font-medium">{getServiceLabel(form.serviceType)}</div>
                  </>
                )}
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
                 <div><span className="text-slate-400">Monto total:</span></div>
                 <div className="font-bold text-brand-700">Bs. {totalWithDebt.toFixed(2)}</div>
                {isRecontratacion && (
                  <>
                    <div><span className="text-slate-400">Adeudo:</span></div>
                    <div className="font-medium">{form.debtApplies ? `${Number(form.debtAmount || 0).toFixed(2)} Bs` : '0.00 Bs'}</div>
                  </>
                )}
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

           <Button type="submit" size="lg" className="w-full" disabled={!form.planId || samePlanSelected || ((isCambio || isRetiro) && !form.motivoId) || (isRecontratacion && (form.equipmentRetained === null || form.requiresTechnicalVisit === null || (form.debtApplies && (!form.debtAmount || Number(form.debtAmount) <= 0)))) || (isTransfer && (!form.transferNewAddress.trim() || form.transferHasSketch === null || !transferTariffs.some((item) => item.service_type === SERVICE_TYPE_TO_PLAN_TYPE[form.serviceType])))}>
            Revisar Registro
          </Button>
        </form>
      </Card>

      {showPreview && (
        <SalePreviewModal
          sale={previewSale}
          title="Confirmar Registro"
          subtitle="Revise los datos antes de guardar"
          onClose={() => setShowPreview(false)}
          onConfirm={handleSubmit}
          confirmLabel="Confirmar"
          loading={loading}
        />
      )}
    </div>
  );
}
