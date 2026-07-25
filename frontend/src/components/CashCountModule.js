import React, { useState, useEffect } from 'react';
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

export default function CashCountModule() {
  const { user } = useAuth();
  const today = new Date().toISOString().slice(0, 10);

  const [date, setDate] = useState(today);
  const [counts, setCounts] = useState(() => {
    const obj = {};
    DENOMINATIONS.forEach(d => obj[d.key] = 0);
    return obj;
  });
  const [outflows, setOutflows] = useState([]);
  const [totalOutflows, setTotalOutflows] = useState(0);
  const [cashCountId, setCashCountId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  const [newPerson, setNewPerson] = useState('');
  const [newAmount, setNewAmount] = useState('');
  const [newConcept, setNewConcept] = useState('');
  const [addingOutflow, setAddingOutflow] = useState(false);

  const totalCounted = DENOMINATIONS.reduce((sum, d) => sum + (counts[d.key] || 0) * d.value, 0);
  const netCash = totalCounted - totalOutflows;

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
          coin_050: c.coin_050,
          coin_1: c.coin_1,
          coin_2: c.coin_2,
          coin_5: c.coin_5,
          bill_10: c.bill_10,
          bill_20: c.bill_20,
          bill_50: c.bill_50,
          bill_100: c.bill_100,
          bill_200: c.bill_200,
        });
        setCashCountId(c.id);
      } else {
        const obj = {};
        DENOMINATIONS.forEach(d => obj[d.key] = 0);
        setCounts(obj);
        setCashCountId(null);
      }
      setOutflows(data.outflows || []);
      setTotalOutflows(data.totalOutflows || 0);
    } catch {
      setMsg({ type: 'error', text: 'Error al cargar arqueo' });
    }
    setLoading(false);
  }

  function handleCountChange(key, val) {
    const n = parseInt(val) || 0;
    setCounts(prev => ({ ...prev, [key]: n }));
  }

  async function handleSaveCount() {
    setSaving(true);
    setMsg(null);
    try {
      await api.saveCashCount({ date, ...counts });
      setMsg({ type: 'success', text: 'Arqueo guardado' });
      loadCashCount();
    } catch (e) {
      setMsg({ type: 'error', text: e.error || 'Error al guardar' });
    }
    setSaving(false);
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

  async function handleWhatsApp() {
    try {
      const data = await api.getCashPDFLink(date);
      const text = encodeURIComponent(`Arqueo de Caja ${date}\n${data.url}`);
      window.open(`https://wa.me/?text=${text}`, '_blank');
    } catch {
      setMsg({ type: 'error', text: 'Error al generar link para WhatsApp' });
    }
  }

  const coins = DENOMINATIONS.filter(d => d.type === 'coin');
  const bills = DENOMINATIONS.filter(d => d.type === 'bill');

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-800">Arqueo de Caja</h1>

      {msg && <Alert type={msg.type}>{msg.text}</Alert>}

      <Card className="p-4 sm:p-6">
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
          <div className="flex items-end">
            <Button
              variant="primary"
              onClick={handleSaveCount}
              disabled={saving}
              className="w-full"
            >
              {saving ? 'Guardando...' : 'Guardar Arqueo'}
            </Button>
          </div>
        </div>

        <h2 className="text-lg font-semibold text-slate-700 mb-3">Conteo de Efectivo</h2>

        {loading ? (
          <p className="text-slate-500 text-sm">Cargando...</p>
        ) : (
          <>
            <div className="mb-4">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">Monedas</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {coins.map(d => (
                  <div key={d.key} className="bg-slate-50 rounded-lg p-3">
                    <label className="block text-xs font-medium text-slate-600 mb-1">{d.label}</label>
                    <input
                      type="number"
                      min="0"
                      value={counts[d.key] || ''}
                      onChange={e => handleCountChange(d.key, e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                      placeholder="0"
                    />
                    <p className="text-xs text-slate-500 mt-1 text-right">
                      = {formatNum((counts[d.key] || 0) * d.value)} Bs
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="mb-6">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">Billetes</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {bills.map(d => (
                  <div key={d.key} className="bg-slate-50 rounded-lg p-3">
                    <label className="block text-xs font-medium text-slate-600 mb-1">{d.label}</label>
                    <input
                      type="number"
                      min="0"
                      value={counts[d.key] || ''}
                      onChange={e => handleCountChange(d.key, e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                      placeholder="0"
                    />
                    <p className="text-xs text-slate-500 mt-1 text-right">
                      = {formatNum((counts[d.key] || 0) * d.value)} Bs
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-brand-50 border border-brand-200 rounded-lg p-4 flex items-center justify-between">
              <span className="text-base font-semibold text-brand-800">Total Contado</span>
              <span className="text-2xl font-bold text-brand-700 tabular-nums">{formatNum(totalCounted)} Bs</span>
            </div>
          </>
        )}
      </Card>

      <Card className="p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-slate-700 mb-3">Salidas de Efectivo</h2>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 mb-4">
          <Input
            label="A quién se le dio"
            value={newPerson}
            onChange={e => setNewPerson(e.target.value)}
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
            onChange={e => setNewConcept(e.target.value)}
            placeholder="Ej: depósito"
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
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-3 font-semibold text-slate-600">Persona</th>
                  <th className="text-right py-2 px-3 font-semibold text-slate-600">Monto</th>
                  <th className="text-left py-2 px-3 font-semibold text-slate-600">Concepto</th>
                  <th className="py-2 px-3 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {outflows.map(o => (
                  <tr key={o.id} className="border-b border-slate-100">
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

        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center justify-between">
          <span className="text-base font-semibold text-red-800">Total Salidas</span>
          <span className="text-2xl font-bold text-red-600 tabular-nums">{formatNum(totalOutflows)} Bs</span>
        </div>
      </Card>

      <Card className="p-4 sm:p-6">
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center justify-between mb-4">
          <span className="text-base font-semibold text-green-800">Efectivo Neto</span>
          <span className="text-2xl font-bold text-green-700 tabular-nums">{formatNum(netCash)} Bs</span>
        </div>
        <p className="text-xs text-slate-500 mb-4 text-right">Total Contado − Total Salidas</p>
        <div className="flex flex-col sm:flex-row gap-3">
          <Button variant="secondary" onClick={handleDownloadPDF} className="flex-1">
            Descargar PDF
          </Button>
          <Button variant="success" onClick={handleWhatsApp} className="flex-1">
            Enviar por WhatsApp
          </Button>
        </div>
      </Card>
    </div>
  );
}
