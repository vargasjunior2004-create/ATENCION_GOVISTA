import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button, Input, Select, Card, Alert, Badge } from './ui';

const typeColor = { internet: 'blue', tv: 'amber', combo: 'violet' };

const REQUEST_TYPES = [
  { value: '', label: 'Todos los movimientos' },
  { value: 'nuevo_contrato', label: 'Nuevo Contrato' },
  { value: 'cambio_plan', label: 'Cambio de Plan' },
  { value: 'recontratacion', label: 'Recontratacion' },
  { value: 'retiro', label: 'Retiro' },
  { value: 'adicion', label: 'Adicion' },
  { value: 'baja_temporal', label: 'Baja Temporal' },
  { value: 'otro', label: 'Otro' },
];

const REQUEST_LABEL = Object.fromEntries(
  REQUEST_TYPES.filter((t) => t.value).map((t) => [t.value, t.label])
);

const REQUEST_COLOR = {
  nuevo_contrato: 'green', cambio_plan: 'amber', recontratacion: 'violet',
  retiro: 'red', adicion: 'blue', baja_temporal: 'slate', otro: 'slate',
};

function SaleCard({ sale, isAdmin, onEdit }) {
  return (
    <Card className="p-4 space-y-2">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold text-slate-900">{sale.clientName}</p>
          <p className="text-sm text-slate-500">{sale.clientCode} &middot; {sale.date}</p>
        </div>
        <Badge color={REQUEST_COLOR[sale.requestType] || 'slate'}>{REQUEST_LABEL[sale.requestType] || sale.requestType}</Badge>
      </div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-500">{sale.Plan?.label || '-'}</span>
        <span className="font-bold text-green-700 tabular-nums">{parseFloat(sale.total).toFixed(2)} Bs</span>
      </div>
      <div className="flex items-center justify-between pt-1 border-t border-slate-100">
        <span className="text-xs text-slate-400">por {sale.creator?.name || '-'}</span>
        {isAdmin && (
          <Button variant="ghost" size="sm" onClick={() => onEdit(sale)}>Editar</Button>
        )}
      </div>
    </Card>
  );
}

export default function SalesList() {
  const { isAdmin } = useAuth();
  const today = new Date().toISOString().split('T')[0];
  const [from, setFrom] = useState(today);
  const [to, setTo] = useState(today);
  const [requestType, setRequestType] = useState('');
  const [sales, setSales] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingSale, setEditingSale] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [editError, setEditError] = useState('');

  const loadSales = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getSales(from, to, requestType);
      setSales(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [from, to, requestType]);

  useEffect(() => { loadSales(); }, [loadSales]);
  useEffect(() => {
    if (isAdmin) api.getPlans().then(setPlans).catch(() => {});
  }, [isAdmin]);

  const startEdit = (sale) => {
    setEditingSale(sale);
    setEditForm({ date: sale.date, clientCode: sale.clientCode, clientName: sale.clientName, serviceType: sale.serviceType, requestType: sale.requestType, planId: sale.planId });
    setEditError('');
  };

  const handleEditChange = (e) => {
    const { name, value } = e.target;
    setEditForm((prev) => {
      const next = { ...prev, [name]: value };
      if (name === 'serviceType') next.planId = '';
      return next;
    });
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    setEditError('');
    try {
      await api.updateSale(editingSale.id, { date: editForm.date, clientCode: editForm.clientCode, clientName: editForm.clientName, serviceType: editForm.serviceType, requestType: editForm.requestType, planId: Number(editForm.planId) });
      setEditingSale(null);
      loadSales();
    } catch (err) {
      setEditError(err.error || 'Error al editar');
    }
  };

  const filteredPlans = plans.filter((p) => p.type === editForm.serviceType);
  const currentPlans = filteredPlans.filter((p) => !p.legacy);
  const legacyPlans = filteredPlans.filter((p) => p.legacy);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-slate-900">Ventas</h1>

      {/* Filters */}
      <Card className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-4 items-end gap-3">
          <div>
            <Input label="Desde" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </div>
          <div>
            <Input label="Hasta" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </div>
          <div>
            <Select label="Movimiento" value={requestType} onChange={(e) => setRequestType(e.target.value)}>
              {REQUEST_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </Select>
          </div>
          <Button variant="secondary" onClick={loadSales}>Buscar</Button>
        </div>
      </Card>

      {/* Edit modal */}
      {editingSale && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={() => setEditingSale(null)}>
          <Card className="w-full max-w-lg p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-slate-900">Editar Venta #{editingSale.id}</h3>
            {editError && <Alert type="error">{editError}</Alert>}
            <form onSubmit={handleUpdate} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input label="Fecha" type="date" name="date" value={editForm.date} onChange={handleEditChange} required />
                <Input label="Codigo Cliente" name="clientCode" value={editForm.clientCode} onChange={handleEditChange} required />
              </div>
              <Input label="Nombre" name="clientName" value={editForm.clientName} onChange={handleEditChange} required />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Select label="Movimiento" name="requestType" value={editForm.requestType} onChange={handleEditChange}>
                  {REQUEST_TYPES.filter((t) => t.value).map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </Select>
                <Select label="Tipo" name="serviceType" value={editForm.serviceType} onChange={handleEditChange}>
                  <option value="internet">Internet</option>
                  <option value="tv">TV Cable</option>
                  <option value="combo">Combo</option>
                </Select>
              </div>
              <Select label="Plan" name="planId" value={editForm.planId} onChange={handleEditChange} required>
                <option value="">Seleccionar...</option>
                <optgroup label="Planes vigentes">
                  {currentPlans.map((p) => (
                    <option key={p.id} value={p.id}>{p.label}</option>
                  ))}
                </optgroup>
                {legacyPlans.length > 0 && (
                  <optgroup label="Planes anteriores">
                    {legacyPlans.map((p) => (
                      <option key={p.id} value={p.id}>{p.label}</option>
                    ))}
                  </optgroup>
                )}
              </Select>
              <div className="flex gap-3 pt-2">
                <Button type="submit">Guardar</Button>
                <Button variant="secondary" type="button" onClick={() => setEditingSale(null)}>Cancelar</Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Sales */}
      {loading ? (
        <p className="text-center text-slate-400 py-12">Cargando...</p>
      ) : sales.length === 0 ? (
        <Card className="p-12 text-center">
          <p className="text-slate-400 text-sm">No hay ventas en este periodo</p>
        </Card>
      ) : (
        <>
          {/* Desktop table */}
          <Card className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Fecha</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Cod.</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Nombre</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Movimiento</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Plan</th>
                  <th className="text-right px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Total</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Por</th>
                  {isAdmin && <th className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400"></th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sales.map((s) => (
                  <tr key={s.id} className="hover:bg-green-50 transition-colors">
                    <td className="px-4 py-3 text-slate-600">{s.date}</td>
                    <td className="px-4 py-3 text-slate-600 font-mono text-xs">{s.clientCode}</td>
                    <td className="px-4 py-3 font-medium text-slate-900">{s.clientName}</td>
                    <td className="px-4 py-3"><Badge color={REQUEST_COLOR[s.requestType] || 'slate'}>{REQUEST_LABEL[s.requestType] || s.requestType}</Badge></td>
                    <td className="px-4 py-3 text-slate-600">{s.Plan?.label || '-'}</td>
                    <td className="px-4 py-3 text-right font-bold text-green-700 tabular-nums">{parseFloat(s.total).toFixed(2)} Bs</td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{s.creator?.name || '-'}</td>
                    {isAdmin && (
                      <td className="px-4 py-3">
                        <Button variant="ghost" size="sm" onClick={() => startEdit(s)}>Editar</Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {sales.map((s) => (
              <SaleCard key={s.id} sale={s} isAdmin={isAdmin} onEdit={startEdit} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
