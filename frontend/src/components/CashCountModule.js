import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import { Card, Button, Input, Alert } from './ui';
import api from '../services/api';

const DENOMINATIONS = [
  { key: 'coin_050', value: 0.50, label: '0.50 Bs', type: 'coin' },
  { key: 'coin_1', value: 1, label: '1 Bs', type: 'coin' },
  { key: 'coin_2', value: 2, label: '2 Bs', type: 'coin' },
  { key: 'coin_5', value: 5, label: '5 Bs', type: 'coin' },
  { key: 'bill_10', value: 10, label: '10 Bs', type: 'bill' },
  { key: 'bill_20', value: 20, label: '20 Bs', type: 'bill' },
  { key: 'bill_50', value: 50, label: '50 Bs', type: 'bill' },
  { key: 'bill_100', value: 100, label: '100 Bs', type: 'bill' },
  { key: 'bill_200', value: 200, label: '200 Bs', type: 'bill' },
];

function formatNum(n) {
  return parseFloat(n || 0).toFixed(2);
}

function zeroCounts() {
  const obj = {};
  DENOMINATIONS.forEach(d => { obj[d.key] = '0'; });
  return obj;
}

function parseCount(val) {
  return Number(val) || 0;
}

function computeTotal(countsObj) {
  return DENOMINATIONS.reduce((sum, d) => {
    return sum + (Number(countsObj[d.key]) || 0) * d.value;
  }, 0);
}

export default function CashCountModule() {
  const { user } = useAuth();
  const d = new Date();
  const today = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

  const [date, setDate] = useState(today);
  const [counts, setCounts] = useState(zeroCounts);
  const [outflows, setOutflows] = useState([]);
  const [totalOutflows, setTotalOutflows] = useState(0);
  const [cashCountId, setCashCountId] = useState(null);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  const [newPerson, setNewPerson] = useState('');
  const [newAmount, setNewAmount] = useState('');
  const [newConcept, setNewConcept] = useState('');
  const [addingOutflow, setAddingOutflow] = useState(false);

  const totalCounted = useMemo(() => computeTotal(counts), [counts]);
  const totalCash = useMemo(() => {
    const counted = Number(totalCounted) || 0;
    const outflows = Number(totalOutflows) || 0;
    return counted + outflows;
  }, [totalCounted, totalOutflows]);

  useEffect(() => {
    loadCashCount();
  }, [date]);

  async function loadCashCount() {
    setLoading(true);
    try {
      const data = await api.getCashCount(date);
      if (data.cashCount) {
        const c = data.cashCount;
        setCounts({
          coin_050: String(Number(c.coin_050) || 0),
          coin_1: String(Number(c.coin_1) || 0),
          coin_2: String(Number(c.coin_2) || 0),
          coin_5: String(Number(c.coin_5) || 0),
          bill_10: String(Number(c.bill_10) || 0),
          bill_20: String(Number(c.bill_20) || 0),
          bill_50: String(Number(c.bill_50) || 0),
          bill_100: String(Number(c.bill_100) || 0),
          bill_200: String(Number(c.bill_200) || 0),
        });
        setCashCountId(c.id);
        setSaved(false);
      } else {
        setCounts(zeroCounts());
        setCashCountId(null);
        setSaved(false);
      }
      setOutflows(data.outflows || []);
      setTotalOutflows(data.totalOutflows || 0);
    } catch {
      setMsg({ type: 'error', text: 'Error al cargar arqueo' });
    }
    setLoading(false);
  }

  function handleCountChange(key, val) {
    setCounts(prev => ({ ...prev, [key]: val }));
    setSaved(false);
  }

  function getSavePayload() {
    const payload = { date };
    DENOMINATIONS.forEach(d => {
      payload[d.key] = Number(counts[d.key]) || 0;
    });
    return payload;
  }

  async function handleSaveCount() {
    setSaving(true);
    setMsg(null);
    try {
      await api.saveCashCount(getSavePayload());
      await loadCashCount();
      setMsg({ type: 'success', text: 'Arqueo guardado' });
      setSaved(true);
    } catch (e) {
      setMsg({ type: 'error', text: e.error || 'Error al guardar' });
    }
    setSaving(false);
  }

  function handleReset() {
    if (!window.confirm('¿Limpiar el conteo y las salidas en pantalla? (No afecta lo guardado en la base de datos)')) return;
    setCounts(zeroCounts());
    setOutflows([]);
    setTotalOutflows(0);
    setCashCountId(null);
    setSaved(false);
    setMsg({ type: 'success', text: 'Arqueo limpiado en pantalla' });
  }

  async function handleAddOutflow() {
    if (!newPerson || !newAmount) return;
    setAddingOutflow(true);
    setMsg(null);
    try {
      const data = await api.addOutflow({
        date,
        personName: newPerson,
        amount: parseFloat(newAmount),
        concept: newConcept,
      });
      setOutflows(prev => [...prev, data.outflow]);
      setTotalOutflows(data.totalOutflows);
      setSaved(false);
      setNewPerson('');
      setNewAmount('');
      setNewConcept('');
    } catch (e) {
      setMsg({ type: 'error', text: e.error || 'Error al agregar salida' });
    }
    setAddingOutflow(false);
  }

  async function handleDeleteOutflow(id) {
    try {
      const data = await api.deleteOutflow(id);
      setOutflows(prev => prev.filter(o => o.id !== id));
      setTotalOutflows(data.totalOutflows);
      setSaved(false);
    } catch (e) {
      setMsg({ type: 'error', text: e.error || 'Error al eliminar' });
    }
  }

  async function handleDownloadPDF() {
    try {
      const blob = await api.getCashPDF(date);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `arqueo-${date}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setMsg({ type: 'error', text: 'Error al descargar PDF' });
    }
  }

  const coins = DENOMINATIONS.filter(d => d.type === 'coin');
  const bills = DENOMINATIONS.filter(d => d.type === 'bill');

  function renderDenominationInput(d) {
    const qty = Number(counts[d.key]) || 0;
    const subtotal = qty * d.value;
    return (
      <div key={d.key} className="bg-green-50 rounded-lg p-3">
        <label className="block text-xs font-medium text-slate-600 mb-1">{d.label}</label>
        <input
          type="number"
          min="0"
          inputMode="numeric"
          value={counts[d.key]}
          onChange={e => handleCountChange(d.key, e.target.value)}
          className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
          placeholder="0"
        />
        <p className="text-xs text-slate-500 mt-1 text-right">
          = {formatNum(subtotal)} Bs
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Arqueo de Caja</h1>
        <p className="text-sm text-slate-400 mt-1">Control diario de efectivo</p>
      </div>

      {msg && <Alert type={msg.type}>{msg.text}</Alert>}

      <Card className="p-6">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <Input
            label="Fecha"
            type="date"
            value={date}
            onChange={e => setDate(e.target.value)}
          />
          <Input
            label="Usuario"
            value={user?.name || ''}
            readOnly
            className="bg-slate-50"
          />
          <div className="flex items-end gap-2">
            <Button
              variant="primary"
              onClick={handleSaveCount}
              disabled={saving}
              className="flex-1"
            >
              {saving ? 'Guardando...' : 'Guardar Arqueo'}
            </Button>
            <Button
              variant="danger"
              onClick={handleReset}
              className="flex-1"
            >
              Resetear
            </Button>
          </div>
        </div>

        <h2 className="text-lg font-bold text-slate-800 mb-3">Conteo de Efectivo</h2>

        {loading ? (
          <p className="text-slate-500 text-sm">Cargando...</p>
        ) : (
          <>
            <div className="mb-4">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Monedas</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {coins.map(d => renderDenominationInput(d))}
              </div>
            </div>

            <div className="mb-6">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Billetes</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {bills.map(d => renderDenominationInput(d))}
              </div>
            </div>

            <div className="bg-brand-50 border border-brand-100 rounded-xl p-4 flex items-center justify-between">
              <span className="text-sm font-bold text-brand-800">Total Contado</span>
              <span className="text-2xl font-extrabold text-brand-700 tabular-nums">{formatNum(totalCounted)} Bs</span>
            </div>
          </>
        )}
      </Card>

      <Card className="p-6">
        <h2 className="text-lg font-bold text-slate-800 mb-3">Salidas de Efectivo</h2>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 mb-4">
          <Input
            label="A quién se le dio"
            value={newPerson}
            onChange={e => setNewPerson(e.target.value.toUpperCase())}
            placeholder="Nombre"
          />
          <Input
            label="Monto (Bs)"
            type="number"
            min="0"
            step="0.01"
            value={newAmount}
            onChange={e => setNewAmount(e.target.value)}
            placeholder="0.00"
          />
          <Input
            label="Concepto (opcional)"
            value={newConcept}
            onChange={e => setNewConcept(e.target.value.toUpperCase())}
            placeholder="Ej: deposito"
          />
          <div className="flex items-end">
            <Button
              variant="danger"
              onClick={handleAddOutflow}
              disabled={addingOutflow || !newPerson || !newAmount}
              className="w-full"
            >
              {addingOutflow ? 'Agregando...' : 'Agregar Salida'}
            </Button>
          </div>
        </div>

        {outflows.length === 0 ? (
          <p className="text-sm text-slate-400 mb-4">Sin salidas registradas</p>
        ) : (
          <div className="overflow-x-auto mb-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left py-2.5 px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400">Hora</th>
                  <th className="text-left py-2.5 px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400">Persona</th>
                  <th className="text-right py-2.5 px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400">Monto</th>
                  <th className="text-left py-2.5 px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400">Concepto</th>
                  <th className="py-2 px-3 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {outflows.map(o => (
                  <tr key={o.id} className="border-b border-slate-100">
                    <td className="py-2 px-3 text-slate-500 text-xs">
                      {o.created_at ? new Date(o.created_at).toLocaleTimeString('es-BO', { hour: '2-digit', minute: '2-digit' }) : '—'}
                    </td>
                    <td className="py-2 px-3 text-slate-800">{o.personName}</td>
                    <td className="py-2 px-3 text-right font-medium text-red-600 tabular-nums">{formatNum(o.amount)} Bs</td>
                    <td className="py-2 px-3 text-slate-500">{o.concept || '—'}</td>
                    <td className="py-2 px-3 text-center">
                      <button
                        onClick={() => handleDeleteOutflow(o.id)}
                        className="text-red-400 hover:text-red-600 text-xs"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="bg-red-50 border border-red-100 rounded-xl p-4 flex items-center justify-between">
          <span className="text-sm font-bold text-red-800">Total Salidas</span>
          <span className="text-2xl font-extrabold text-red-600 tabular-nums">{formatNum(totalOutflows)} Bs</span>
        </div>
      </Card>

      <Card className="p-6">
        <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4 flex items-center justify-between mb-4">
          <span className="text-sm font-bold text-emerald-800">Efectivo Total</span>
          <span className="text-2xl font-extrabold text-emerald-700 tabular-nums">{formatNum(totalCash)} Bs</span>
        </div>
        <p className="text-xs text-slate-500 mb-4 text-right">Total contado en efectivo</p>
        <div className="flex flex-col sm:flex-row gap-3">
          <Button
            variant="secondary"
            onClick={handleDownloadPDF}
            className="flex-1"
            disabled={!saved}
          >
            {saved ? 'Descargar PDF' : 'Guarda el arqueo para descargar'}
          </Button>
        </div>
      </Card>
    </div>
  );
}
