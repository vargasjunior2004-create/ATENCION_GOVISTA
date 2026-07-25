import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { Button, Input, Select, Card, Alert, TotalDisplay } from './ui';

export default function SaleForm() {
  const today = new Date().toISOString().split('T')[0];
  const [plans, setPlans] = useState([]);
  const [form, setForm] = useState({
    date: today, clientCode: '', clientName: '', serviceType: 'internet', planId: '',
  });
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getActivePlans().then(setPlans).catch(() => {});
  }, []);

  const filteredPlans = plans.filter((p) => p.type === form.serviceType);

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
    setForm((prev) => {
      const next = { ...prev, [name]: value };
      if (name === 'serviceType') next.planId = '';
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
        planId: Number(form.planId),
      });
      setSuccess('Venta registrada correctamente');
      setForm({ date: today, clientCode: '', clientName: '', serviceType: 'internet', planId: '' });
      setSelectedPlan(null);
    } catch (err) {
      setError(err.error || 'Error al registrar venta');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-slate-900">Nueva Venta</h1>

      <Card className="p-5">
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <Alert type="error">{error}</Alert>}
          {success && <Alert type="success">{success}</Alert>}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input label="Fecha" type="date" name="date" value={form.date} onChange={handleChange} required />
            <Input label="Codigo Cliente" name="clientCode" value={form.clientCode} onChange={handleChange} required placeholder="Ej: CLI-001" />
          </div>

          <Input label="Nombre Completo" name="clientName" value={form.clientName} onChange={handleChange} required placeholder="Nombre del cliente" />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Select label="Tipo de Servicio" name="serviceType" value={form.serviceType} onChange={handleChange}>
              <option value="internet">Solo Internet</option>
              <option value="tv">Solo TV Cable</option>
              <option value="combo">Combo Internet + TV</option>
            </Select>
            <Select label="Plan" name="planId" value={form.planId} onChange={handleChange} required>
              <option value="">Seleccionar plan...</option>
              {filteredPlans.map((p) => (
                <option key={p.id} value={p.id}>{p.label}{p.speed ? ` (${p.speed} Mbps)` : ''}</option>
              ))}
            </Select>
          </div>

          {selectedPlan && (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4 space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Mensualidad</span>
                <span className="font-medium text-slate-700">{parseFloat(selectedPlan.monthly).toFixed(2)} Bs</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Instalacion</span>
                <span className="font-medium text-slate-700">{parseFloat(selectedPlan.installation).toFixed(2)} Bs</span>
              </div>
              <div className="border-t border-green-200 pt-2 mt-2">
                <TotalDisplay value={selectedPlan.total} label="Total a cobrar" />
              </div>
            </div>
          )}

          <Button type="submit" size="lg" className="w-full" disabled={loading || !form.planId}>
            {loading ? 'Registrando...' : 'Registrar Venta'}
          </Button>
        </form>
      </Card>
    </div>
  );
}
