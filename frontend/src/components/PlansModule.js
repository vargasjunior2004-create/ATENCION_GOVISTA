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

  const loadPlans = useCallback(async () => {
    try { setPlans(await api.getPlans()); } catch (err) { console.error(err); } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadPlans(); }, [loadPlans]);

  const handleChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

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
    try { await api.updatePlan(plan.id, { active: !plan.active }); loadPlans(); } catch (err) { alert(err.error || 'Error'); }
  };

  if (loading) return <p className="text-center text-slate-400 py-20">Cargando...</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-900">Planes</h1>
        <Button onClick={openNew}>Agregar Plan</Button>
      </div>

      {/* Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setShowForm(false)}>
          <Card className="w-full max-w-lg p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-slate-900">{editingId ? 'Editar Plan' : 'Nuevo Plan'}</h3>
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
            <tr className="border-b border-slate-200">
              {['Codigo', 'Nombre', 'Tipo', 'Velocidad', 'Mensual', 'Instalacion', 'Total', 'Estado', ''].map((h) => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {plans.map((p) => (
              <tr key={p.id} className={`hover:bg-slate-50 transition-colors ${!p.active ? 'opacity-50' : ''}`}>
                <td className="px-4 py-3 font-mono text-xs text-slate-600">{p.code}</td>
                <td className="px-4 py-3 font-medium text-slate-900">{p.label}</td>
                <td className="px-4 py-3"><Badge color={typeColor[p.type]}>{p.type}</Badge></td>
                <td className="px-4 py-3 text-slate-600">{p.speed ? `${p.speed} Mbps` : '-'}</td>
                <td className="px-4 py-3 text-slate-600 tabular-nums">{parseFloat(p.monthly).toFixed(2)}</td>
                <td className="px-4 py-3 text-slate-600 tabular-nums">{parseFloat(p.installation).toFixed(2)}</td>
                <td className="px-4 py-3 font-bold text-green-700 tabular-nums">{parseFloat(p.total).toFixed(2)}</td>
                <td className="px-4 py-3">
                  <Badge color={p.active ? 'green' : 'red'}>{p.active ? 'Activo' : 'Inactivo'}</Badge>
                </td>
                <td className="px-4 py-3 space-x-1">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(p)}>Editar</Button>
                  <Button variant={p.active ? 'danger' : 'success'} size="sm" onClick={() => toggleActive(p)}>
                    {p.active ? 'Inhabilitar' : 'Habilitar'}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Mobile cards */}
      <div className="md:hidden space-y-3">
        {plans.map((p) => (
          <Card key={p.id} className={`p-4 space-y-2 ${!p.active ? 'opacity-50' : ''}`}>
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-slate-900">{p.label}</p>
                <p className="text-xs text-slate-400 font-mono">{p.code}</p>
              </div>
              <div className="flex gap-1.5">
                <Badge color={typeColor[p.type]}>{p.type}</Badge>
                <Badge color={p.active ? 'green' : 'red'}>{p.active ? 'Activo' : 'Inactivo'}</Badge>
              </div>
            </div>
            <div className="text-sm text-slate-500">{p.speed ? `${p.speed} Mbps` : 'Sin velocidad'}</div>
            <div className="flex items-center justify-between pt-1 border-t border-slate-100">
              <span className="text-xs text-slate-400">Mensual: {parseFloat(p.monthly).toFixed(2)} | Inst: {parseFloat(p.installation).toFixed(2)}</span>
              <span className="font-bold text-green-700 tabular-nums">{parseFloat(p.total).toFixed(2)} Bs</span>
            </div>
            <div className="flex gap-2 pt-1">
              <Button variant="ghost" size="sm" onClick={() => openEdit(p)} className="flex-1">Editar</Button>
              <Button variant={p.active ? 'danger' : 'success'} size="sm" onClick={() => toggleActive(p)} className="flex-1">
                {p.active ? 'Inhabilitar' : 'Habilitar'}
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
