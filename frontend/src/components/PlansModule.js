import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Button, Input, Select, Card, Alert, Badge, TotalDisplay } from './ui';

const emptyPlan = { code: '', label: '', type: 'internet', speed: '', monthly: '', installation: '' };
const typeColor = { internet: 'blue', tv: 'amber', combo: 'violet' };

export default function PlansModule() {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...emptyPlan });
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');
  const [deletingPlan, setDeletingPlan] = useState(null);
  const [search, setSearch] = useState('');

  const loadPlans = useCallback(async () => {
    try { setPlans(await api.getPlans()); } catch (err) { console.error(err); } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadPlans(); }, [loadPlans]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    const UPPERCASE_FIELDS = ['code', 'label'];
    const finalValue = UPPERCASE_FIELDS.includes(name) ? value.toUpperCase() : value;
    setForm((p) => ({ ...p, [name]: finalValue }));
  };

  const openNew = () => { setForm({ ...emptyPlan }); setEditingId(null); setShowForm(true); setError(''); };
  const openEdit = (plan) => {
    setForm({ code: plan.code, label: plan.label, type: plan.type, speed: plan.speed || '', monthly: String(plan.monthly ?? ''), installation: String(plan.installation ?? '') });
    setEditingId(plan.id); setShowForm(true); setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault(); setError('');
    try {
      const payload = { code: form.code, label: form.label, type: form.type, speed: form.speed ? Number(form.speed) : null, monthly: Number(form.monthly), installation: Number(form.installation) };
      editingId ? await api.updatePlan(editingId, payload) : await api.createPlan(payload);
      setShowForm(false); loadPlans();
    } catch (err) { setError(err.error || 'Error al guardar plan'); }
  };

  const toggleActive = async (plan) => {
    try { await api.updatePlan(plan.id, { legacy: !plan.legacy }); loadPlans(); } catch (err) { alert(err.error || 'Error'); }
  };

  const handleDeletePlan = async () => {
    if (!deletingPlan) return;
    try {
      await api.deletePlan(deletingPlan.id);
      setDeletingPlan(null);
      loadPlans();
    } catch (err) {
      alert(err.error || 'Error al eliminar plan');
      setDeletingPlan(null);
    }
  };

  if (loading) return <p className="text-center text-slate-400 py-20">Cargando...</p>;

  const q = search.toLowerCase();
  const filtered = plans.filter((p) =>
    !q || p.code.toLowerCase().includes(q) || p.label.toLowerCase().includes(q) || p.type.toLowerCase().includes(q)
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Planes</h1>
          <p className="text-sm text-slate-400 mt-1">Gestion de paquetes de servicio</p>
        </div>
        <Button onClick={openNew}>+ Agregar Plan</Button>
      </div>

      <Card className="p-4">
        <Input placeholder="Buscar por codigo, nombre o tipo..." value={search} onChange={(e) => setSearch(e.target.value)} />
      </Card>

      {/* Delete confirmation modal */}
      {deletingPlan && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setDeletingPlan(null)}>
          <Card className="w-full max-w-sm p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Eliminar plan</h3>
                <p className="text-sm text-slate-500">Esta accion no se puede deshacer</p>
              </div>
            </div>
            <p className="text-sm text-slate-600">
              Seguro que deseas eliminar el plan <strong>{deletingPlan.label}</strong> ({deletingPlan.code})?
            </p>
            <div className="flex gap-3 pt-2">
              <Button variant="danger" onClick={handleDeletePlan}>Si, eliminar</Button>
              <Button variant="secondary" onClick={() => setDeletingPlan(null)}>Cancelar</Button>
            </div>
          </Card>
        </div>
      )}

      {/* Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowForm(false)}>
          <Card className="w-full max-w-lg p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-black text-slate-900">{editingId ? 'Editar Plan' : 'Nuevo Plan'}</h3>
            {error && <Alert type="error">{error}</Alert>}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input label="Codigo" name="code" value={form.code} onChange={handleChange} required placeholder="Ej: GO-BASIC" />
                <Input label="Nombre" name="label" value={form.label} onChange={handleChange} required />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Select label="Tipo" name="type" value={form.type} onChange={handleChange}>
                  <option value="internet">Internet</option>
                  <option value="tv">TV Cable</option>
                  <option value="combo">Combo</option>
                </Select>
                <Input label="Velocidad (Mbps)" name="speed" type="number" value={form.speed} onChange={handleChange} placeholder="Opcional" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input label="Mensualidad (Bs)" name="monthly" type="number" step="0.01" value={form.monthly} onChange={handleChange} required />
                <Input label="Instalacion (Bs)" name="installation" type="number" step="0.01" value={form.installation} onChange={handleChange} required />
              </div>
              <div className="bg-green-50 border border-green-200 rounded-xl p-4">
                <TotalDisplay value={Number(form.monthly || 0) + Number(form.installation || 0)} label="Total" />
              </div>
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
              {['Codigo', 'Nombre', 'Tipo', 'Velocidad', 'Mensual', 'Instalacion', 'Total', 'Estado', ''].map((h) => (
                <th key={h} className="text-left px-4 py-3.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {filtered.map((p) => (
              <tr key={p.id} className={`hover:bg-brand-50/30 transition-colors ${p.legacy ? 'opacity-50' : ''}`}>
                <td className="px-4 py-3 font-mono text-xs text-slate-500">{p.code}</td>
                <td className="px-4 py-3 font-medium text-slate-900">{p.label}</td>
                <td className="px-4 py-3"><Badge color={typeColor[p.type]}>{p.type}</Badge></td>
                <td className="px-4 py-3 text-slate-500">{p.speed ? `${p.speed} Mbps` : '-'}</td>
                <td className="px-4 py-3 text-slate-500 tabular-nums">{parseFloat(p.monthly).toFixed(2)}</td>
                <td className="px-4 py-3 text-slate-500 tabular-nums">{parseFloat(p.installation).toFixed(2)}</td>
                <td className="px-4 py-3 font-bold text-brand-700 tabular-nums">{parseFloat(p.total).toFixed(2)}</td>
                <td className="px-4 py-3">
                  <Badge color={p.legacy ? 'slate' : 'green'}>{p.legacy ? 'Anterior' : 'Actual'}</Badge>
                </td>
                <td className="px-4 py-3 space-x-1">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(p)}>Editar</Button>
                  <Button variant="danger" size="sm" onClick={() => setDeletingPlan(p)}>Eliminar</Button>
                  <Button variant={p.legacy ? 'success' : 'secondary'} size="sm" onClick={() => toggleActive(p)}>
                    {p.legacy ? 'Marcar como actual' : 'Inhabilitar como actual'}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Mobile cards */}
      <div className="md:hidden space-y-3">
        {filtered.map((p) => (
          <Card key={p.id} className={`p-4 space-y-2 ${p.legacy ? 'opacity-50' : ''}`}>
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-slate-900">{p.label}</p>
                <p className="text-xs text-slate-400 font-mono">{p.code}</p>
              </div>
              <div className="flex gap-1.5">
                <Badge color={typeColor[p.type]}>{p.type}</Badge>
                <Badge color={p.legacy ? 'slate' : 'green'}>{p.legacy ? 'Anterior' : 'Actual'}</Badge>
              </div>
            </div>
            <div className="text-sm text-slate-500">{p.speed ? `${p.speed} Mbps` : 'Sin velocidad'}</div>
            <div className="flex items-center justify-between pt-1 border-t border-slate-100">
              <span className="text-xs text-slate-400">Mensual: {parseFloat(p.monthly).toFixed(2)} | Inst: {parseFloat(p.installation).toFixed(2)}</span>
              <span className="font-bold text-brand-700 tabular-nums">{parseFloat(p.total).toFixed(2)} Bs</span>
            </div>
            <div className="flex gap-2 pt-1">
              <Button variant="ghost" size="sm" onClick={() => openEdit(p)} className="flex-1">Editar</Button>
              <Button variant="danger" size="sm" onClick={() => setDeletingPlan(p)} className="flex-1">Eliminar</Button>
              <Button variant={p.legacy ? 'success' : 'secondary'} size="sm" onClick={() => toggleActive(p)} className="flex-1">
                {p.legacy ? 'Marcar como actual' : 'Inhabilitar como actual'}
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
