import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Button, Input, Select, Card, Alert, Badge } from './ui';

const emptyForm = {
  name: '', plan: '', apply_installation: false, apply_monthly: false,
  installation_price: '', monthly_price: '', start_date: '', end_date: '', active: true,
};

export default function PromotionsModule() {
  const [promotions, setPromotions] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');
  const [deletingPromo, setDeletingPromo] = useState(null);
  const [filterPlan, setFilterPlan] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  const load = useCallback(async () => {
    try {
      const [promos, planList] = await Promise.all([
        api.getPromotions(filterPlan || undefined),
        api.getPlans(),
      ]);
      setPromotions(promos);
      setPlans(planList);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }, [filterPlan]);

  useEffect(() => { load(); }, [load]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((p) => ({ ...p, [name]: type === 'checkbox' ? checked : value }));
  };

  const openNew = () => { setForm({ ...emptyForm }); setEditingId(null); setShowForm(true); setError(''); };
  const openEdit = (promo) => {
    setForm({
      name: promo.name,
      plan: promo.plan,
      apply_installation: promo.apply_installation,
      apply_monthly: promo.apply_monthly,
      installation_price: promo.installation_price ?? '',
      monthly_price: promo.monthly_price ?? '',
      start_date: promo.start_date,
      end_date: promo.end_date,
      active: promo.active,
    });
    setEditingId(promo.id);
    setShowForm(true);
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const payload = {
        name: form.name,
        plan: Number(form.plan),
        apply_installation: form.apply_installation,
        apply_monthly: form.apply_monthly,
        installation_price: form.apply_installation ? Number(form.installation_price) : null,
        monthly_price: form.apply_monthly ? Number(form.monthly_price) : null,
        start_date: form.start_date,
        end_date: form.end_date,
        active: form.active,
      };
      if (editingId) {
        await api.updatePromotion(editingId, payload);
      } else {
        await api.createPromotion(payload);
      }
      setShowForm(false);
      load();
    } catch (err) { setError(err.error || 'Error al guardar promocion'); }
  };

  const handleDelete = async () => {
    if (!deletingPromo) return;
    try {
      await api.deletePromotion(deletingPromo.id);
      setDeletingPromo(null);
      load();
    } catch (err) {
      alert(err.error || 'Error al eliminar');
      setDeletingPromo(null);
    }
  };

  const toggleActive = async (promo) => {
    try {
      await api.updatePromotion(promo.id, { active: !promo.active });
      load();
    } catch (err) { alert(err.error || 'Error'); }
  };

  if (loading) return <p className="text-center text-slate-400 py-20">Cargando...</p>;

  const planMap = Object.fromEntries(plans.map((p) => [p.id, p]));

  const today = new Date().toISOString().slice(0, 10);
  const filtered = promotions.filter((p) => {
    if (filterStatus === 'active') return p.active && p.start_date <= today && p.end_date >= today;
    if (filterStatus === 'inactive') return !p.active;
    if (filterStatus === 'expired') return p.end_date < today;
    return true;
  });

  const formatDate = (d) => {
    if (!d) return '';
    const [y, m, day] = d.split('-');
    return `${day}/${m}/${y}`;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Promociones</h1>
          <p className="text-sm text-slate-400 mt-1">Descuentos temporales asociados a planes</p>
        </div>
        <Button onClick={openNew}>+ Nueva Promocion</Button>
      </div>

      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <Select label="Filtrar por plan" value={filterPlan} onChange={(e) => setFilterPlan(e.target.value)}>
              <option value="">Todos los planes</option>
              {plans.map((p) => (
                <option key={p.id} value={p.id}>{p.code} - {p.label}</option>
              ))}
            </Select>
          </div>
          <div className="flex-1">
            <Select label="Estado" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="">Todos</option>
              <option value="active">Vigentes</option>
              <option value="expired">Vencidas</option>
              <option value="inactive">Desactivadas</option>
            </Select>
          </div>
        </div>
      </Card>

      {error && <Alert type="error">{error}</Alert>}

      {/* Delete confirmation */}
      {deletingPromo && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setDeletingPromo(null)}>
          <Card className="w-full max-w-sm p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Eliminar promocion</h3>
                <p className="text-sm text-slate-500">Esta accion no se puede deshacer</p>
              </div>
            </div>
            <p className="text-sm text-slate-600">
              Seguro que deseas eliminar la promocion <strong>{deletingPromo.name}</strong>?
            </p>
            <div className="flex gap-3 pt-2">
              <Button variant="danger" onClick={handleDelete}>Si, eliminar</Button>
              <Button variant="secondary" onClick={() => setDeletingPromo(null)}>Cancelar</Button>
            </div>
          </Card>
        </div>
      )}

      {/* Create/Edit modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowForm(false)}>
          <Card className="w-full max-w-lg p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-black text-slate-900">{editingId ? 'Editar Promocion' : 'Nueva Promocion'}</h3>
            {error && <Alert type="error">{error}</Alert>}
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input label="Nombre" name="name" value={form.name} onChange={handleChange} required placeholder="Ej: Feria septiembre" />
              <Select label="Plan" name="plan" value={form.plan} onChange={handleChange} required>
                <option value="">Seleccionar...</option>
                {plans.filter((p) => p.active && !p.legacy).map((p) => (
                  <option key={p.id} value={p.id}>{p.code} - {p.label}</option>
                ))}
              </Select>

              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide">Aplica a</label>
                <div className="flex gap-6">
                  <label className="flex items-center gap-2 text-sm text-slate-700">
                    <input type="checkbox" name="apply_installation" checked={form.apply_installation} onChange={handleChange} className="rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
                    Instalacion
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-700">
                    <input type="checkbox" name="apply_monthly" checked={form.apply_monthly} onChange={handleChange} className="rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
                    Mensualidad
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {form.apply_installation && (
                  <Input label="Precio Instalacion (Bs)" name="installation_price" type="number" step="0.01" min="0" value={form.installation_price} onChange={handleChange} required />
                )}
                {form.apply_monthly && (
                  <Input label="Precio Mensualidad (Bs)" name="monthly_price" type="number" step="0.01" min="0" value={form.monthly_price} onChange={handleChange} required />
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input label="Fecha inicio" name="start_date" type="date" value={form.start_date} onChange={handleChange} required />
                <Input label="Fecha fin" name="end_date" type="date" value={form.end_date} onChange={handleChange} required />
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" name="active" checked={form.active} onChange={handleChange} className="rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
                Activa
              </label>

              <div className="flex gap-3 pt-2">
                <Button type="submit">Guardar</Button>
                <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Cancelar</Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Desktop table */}
      <Card className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              {['Nombre', 'Plan', 'Concepto', 'Precio', 'Vigencia', 'Estado', ''].map((h) => (
                <th key={h} className="text-left px-4 py-3.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {filtered.map((p) => {
              const plan = planMap[p.plan];
              const concepts = [];
              if (p.apply_installation) concepts.push(`Inst: ${parseFloat(p.installation_price).toFixed(2)} Bs`);
              if (p.apply_monthly) concepts.push(`Mensual: ${parseFloat(p.monthly_price).toFixed(2)} Bs`);
              const isExpired = p.end_date < today;
              return (
                <tr key={p.id} className={`hover:bg-brand-50/30 transition-colors ${!p.active ? 'opacity-50' : ''}`}>
                  <td className="px-4 py-3 font-medium text-slate-900">{p.name}</td>
                  <td className="px-4 py-3 text-slate-500">{plan ? `${plan.code} - ${plan.label}` : '-'}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{concepts.join(' | ')}</td>
                  <td className="px-4 py-3 text-slate-500">
                    {p.apply_installation && <div>Inst: {parseFloat(p.installation_price).toFixed(2)}</div>}
                    {p.apply_monthly && <div>Mensual: {parseFloat(p.monthly_price).toFixed(2)}</div>}
                  </td>
                  <td className="px-4 py-3 text-slate-500 text-xs">
                    {formatDate(p.start_date)} - {formatDate(p.end_date)}
                  </td>
                  <td className="px-4 py-3">
                    <Badge color={!p.active ? 'slate' : isExpired ? 'amber' : 'green'}>
                      {!p.active ? 'Desactivada' : isExpired ? 'Vencida' : 'Activa'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 space-x-1">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(p)}>Editar</Button>
                    <Button variant={p.active ? 'secondary' : 'success'} size="sm" onClick={() => toggleActive(p)}>
                      {p.active ? 'Desactivar' : 'Activar'}
                    </Button>
                    <Button variant="danger" size="sm" onClick={() => setDeletingPromo(p)}>Eliminar</Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      {/* Mobile cards */}
      <div className="md:hidden space-y-3">
        {filtered.map((p) => {
          const plan = planMap[p.plan];
          const isExpired = p.end_date < today;
          return (
            <Card key={p.id} className={`p-4 space-y-2 ${!p.active ? 'opacity-50' : ''}`}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-slate-900">{p.name}</p>
                  <p className="text-xs text-slate-400">{plan ? `${plan.code} - ${plan.label}` : '-'}</p>
                </div>
                <Badge color={!p.active ? 'slate' : isExpired ? 'amber' : 'green'}>
                  {!p.active ? 'Desactivada' : isExpired ? 'Vencida' : 'Activa'}
                </Badge>
              </div>
              <div className="text-sm text-slate-500">
                {p.apply_installation && <div>Instalacion: {parseFloat(p.installation_price).toFixed(2)} Bs</div>}
                {p.apply_monthly && <div>Mensualidad: {parseFloat(p.monthly_price).toFixed(2)} Bs</div>}
              </div>
              <div className="text-xs text-slate-400">Vigencia: {formatDate(p.start_date)} - {formatDate(p.end_date)}</div>
              <div className="flex gap-2 pt-1">
                <Button variant="ghost" size="sm" onClick={() => openEdit(p)} className="flex-1">Editar</Button>
                <Button variant={p.active ? 'secondary' : 'success'} size="sm" onClick={() => toggleActive(p)} className="flex-1">
                  {p.active ? 'Desactivar' : 'Activar'}
                </Button>
                <Button variant="danger" size="sm" onClick={() => setDeletingPromo(p)} className="flex-1">Eliminar</Button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
