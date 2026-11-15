import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../../services/api';
import { useAuth } from '../../../context/AuthContext';
import { SERVICE_TYPES, SERVICE_TYPE_TO_PLAN_TYPE } from '../../comercial/serviceTypes';
import { Alert, Button, Card, Input, Select } from '../../../components/ui';

const EMPTY_FORM = {
  customer_code: '',
  customer_name: '',
  attention_type: '',
  classification: '',
  channel: '',
  service_type: '',
  plan: '',
  notes: '',
  actions: [],
};

function getErrorMessage(error, fallback) {
  if (typeof error?.error === 'string') return error.error;
  if (error && typeof error === 'object') {
    const firstField = Object.values(error).find((value) => Array.isArray(value));
    if (firstField?.[0]) return String(firstField[0]);
  }
  return fallback;
}

export default function AtencionForm() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [catalogs, setCatalogs] = useState([]);
  const [plans, setPlans] = useState([]);
  const [openAttention, setOpenAttention] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    Promise.all([api.getAtencionCatalogs(), api.getActivePlans(), api.getOpenAtencion()])
      .then(([catalogData, planData, openData]) => {
        if (!active) return;
        setCatalogs(Array.isArray(catalogData) ? catalogData : []);
        setPlans(Array.isArray(planData) ? planData : []);
        setOpenAttention(openData);
      })
      .catch((err) => {
        if (active) setError(getErrorMessage(err, 'No fue posible cargar el formulario.'));
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const options = (type) => catalogs.filter((item) => item.catalog_type === type);
  const channels = useMemo(
    () => options('channel').filter((item) => (
      user?.role !== 'call-center' || ['mensaje', 'llamada'].includes(item.code)
    )),
    [catalogs, user?.role],
  );
  const availablePlans = useMemo(() => (
    form.service_type
      ? plans.filter((plan) => plan.type === SERVICE_TYPE_TO_PLAN_TYPE[form.service_type])
      : plans
  ), [form.service_type, plans]);

  const update = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const toggleAction = (actionId) => {
    setForm((current) => ({
      ...current,
      actions: current.actions.includes(actionId)
        ? current.actions.filter((id) => id !== actionId)
        : [...current.actions, actionId],
    }));
  };

  const start = async (event) => {
    event.preventDefault();
    setError('');
    setMessage('');
    setSaving(true);
    try {
      const { actions, ...payload } = form;
      const attention = await api.startAtencion(
        { ...payload, plan: payload.plan ? Number(payload.plan) : null },
        crypto.randomUUID(),
      );
      await Promise.all(actions.map((action) => api.addAtencionAction(attention.id, { action })));
      setMessage('Atención iniciada correctamente.');
      setOpenAttention(attention);
      setForm(EMPTY_FORM);
      navigate('/atenciones/listado');
    } catch (err) {
      setError(getErrorMessage(err, 'No fue posible iniciar la atención.'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="text-sm text-slate-500">Cargando formulario...</p>;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header>
        <p className="text-xs font-black uppercase tracking-[0.18em] text-brand-600">Call Center</p>
        <h2 className="mt-1 text-3xl font-black text-slate-900">Iniciar atención</h2>
        <p className="mt-1 text-sm text-slate-500">El ticket y el tiempo se crean en el servidor al iniciar.</p>
      </header>
      {message && <Alert type="success">{message}</Alert>}
      {error && <Alert type="error">{error}</Alert>}
      {openAttention && (
        <Alert type="info">
          Ya tienes una atención abierta. Puedes continuarla desde <Link className="font-bold underline" to="/atenciones/listado">Atenciones</Link>.
        </Alert>
      )}
      <Card className="p-5">
        <form className="space-y-5" onSubmit={start}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Kardex / código" value={form.customer_code} onChange={update('customer_code')} required />
            <Input label="Nombre del cliente" value={form.customer_name} onChange={update('customer_name')} required />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Select label="Tipo de atención" value={form.attention_type} onChange={update('attention_type')} required>
              <option value="">Seleccionar</option>
              {options('attention_type').map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </Select>
            <Select label="Clasificación" value={form.classification} onChange={update('classification')} required>
              <option value="">Seleccionar</option>
              {options('classification').map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </Select>
            <Select label="Canal de origen" value={form.channel} onChange={update('channel')} required>
              <option value="">Seleccionar</option>
              {channels.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </Select>
            <Select label="Tipo de servicio" value={form.service_type} onChange={update('service_type')}>
              <option value="">No especificado</option>
              {SERVICE_TYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </Select>
            <Select label="Tipo de plan" value={form.plan} onChange={update('plan')}>
              <option value="">No especificado</option>
              {availablePlans.map((plan) => <option key={plan.id} value={plan.id}>{plan.label}</option>)}
            </Select>
          </div>
          <fieldset>
            <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Acciones de soporte</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {options('support_action').map((action) => (
                <label key={action.id} className="flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm text-slate-700">
                  <input type="checkbox" checked={form.actions.includes(action.id)} onChange={() => toggleAction(action.id)} />
                  {action.name}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="block text-sm font-bold text-slate-700">
            Observaciones
            <textarea className="mt-1 min-h-24 w-full rounded-xl border border-slate-200 p-3 font-normal" value={form.notes} onChange={update('notes')} />
          </label>
          <Button type="submit" className="w-full py-3" disabled={saving || Boolean(openAttention)}>
            {saving ? 'Iniciando...' : 'Iniciar atención'}
          </Button>
        </form>
      </Card>
    </div>
  );
}
