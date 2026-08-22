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
    <Card className="p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold text-slate-900">{sale.clientName}</p>
          <p className="text-sm text-slate-400">{sale.clientCode} &middot; {sale.date}</p>
        </div>
        <Badge color={REQUEST_COLOR[sale.requestType] || 'slate'}>{REQUEST_LABEL[sale.requestType] || sale.requestType}</Badge>
      </div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-500">{sale.Plan?.label || '-'}</span>
        <span className="font-bold text-brand-700 tabular-nums">{parseFloat(sale.total).toFixed(2)} Bs</span>
      </div>
      <div className="flex items-center justify-between pt-2 border-t border-slate-100">
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
    const UPPERCASE_FIELDS = ['clientCode', 'clientName'];
    const finalValue = UPPERCASE_FIELDS.includes(name) ? value.toUpperCase() : value;
    setEditForm((prev) => {
      const next = { ...prev, [name]: finalValue };
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

  const filteredPlans = plans.filter((p) => {
    const typeMap = {
      'internet': 'internet',
      'tv': 'tv',
      'tv_digital': 'tv',
      'combo_analog': 'combo',
      'combo_digital': 'combo',
    };
    return p.type === typeMap[editForm.serviceType];
  });
  const currentPlans = filteredPlans.filter((p) => !p.legacy);
  const legacyPlans = filteredPlans.filter((p) => p.legacy);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Ventas</h1>
        <p className="text-sm text-slate-400 mt-1">Historial de movimientos</p>
      </div>

      {/* Filters */}
      <Card className="p-5">
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
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setEditingSale(null)}>
          <Card className="w-full max-w-lg p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-black text-slate-900">Editar Venta #{editingSale.id}</h3>
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
        <div className="flex items-center justify-center py-20">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-brand-500/20 border-t-brand-500 rounded-full animate-spin" />
            <p className="text-sm text-slate-400 font-medium">Cargando...</p>
          </div>
        </div>
      ) : sales.length === 0 ? (
        <Card className="p-16 text-center">
          <svg className="w-12 h-12 text-slate-200 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <p className="text-slate-400 text-sm">No hay ventas en este periodo</p>
        </Card>
      ) : (
        <>
          {/* Desktop table */}
          <Card className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  {['Fecha', 'Cod.', 'Nombre', 'Movimiento', 'Plan', 'Total', 'Por', ''].map((h) => (
                    <th key={h} className="text-left px-5 py-3.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {sales.map((s) => (
                  <tr key={s.id} className="hover:bg-brand-50/30 transition-colors">
                    <td className="px-5 py-3.5 text-slate-500">{s.date}</td>
                    <td className="px-5 py-3.5 text-slate-500 font-mono text-xs">{s.clientCode}</td>
                    <td className="px-5 py-3.5 font-medium text-slate-900">{s.clientName}</td>
                    <td className="px-5 py-3.5"><Badge color={REQUEST_COLOR[s.requestType] || 'slate'}>{REQUEST_LABEL[s.requestType] || s.requestType}</Badge></td>
                    <td className="px-5 py-3.5 text-slate-500">{s.Plan?.label || '-'}</td>
                    <td className="px-5 py-3.5 text-right font-bold text-brand-700 tabular-nums">{parseFloat(s.total).toFixed(2)} Bs</td>
                    <td className="px-5 py-3.5 text-slate-500 text-xs">{s.creator?.name || '-'}</td>
                    {isAdmin && (
                      <td className="px-5 py-3.5">
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
