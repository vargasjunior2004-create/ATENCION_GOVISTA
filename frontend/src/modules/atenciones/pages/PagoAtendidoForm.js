import React, { useState } from 'react';
import api from '../../../services/api';
import { Alert, Button, Card, Input } from '../../../components/ui';

export default function PagoAtendidoForm() {
  const [form, setForm] = useState({
    customer_code: '', customer_name: '', amount: '', paid_on: new Date().toISOString().slice(0, 10),
    payment_channel: '', reference: '', notes: '',
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value });
  const save = async (event) => {
    event.preventDefault(); setError(''); setMessage('');
    try {
      await api.createPagoAtendido({ ...form, amount: Number(form.amount) });
      setMessage('Pago registrado correctamente.');
      setForm({ ...form, amount: '', reference: '', notes: '' });
    } catch (err) { setError(err.error || 'No fue posible registrar el pago.'); }
  };
  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <header><p className="text-xs font-black uppercase tracking-[0.18em] text-brand-600">Call Center</p><h2 className="mt-1 text-3xl font-black text-slate-900">Registrar pago atendido</h2></header>
      {message && <Alert type="success">{message}</Alert>}{error && <Alert type="error">{error}</Alert>}
      <Card className="p-5"><form onSubmit={save} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Kardex / código" value={form.customer_code} onChange={update('customer_code')} required />
          <Input label="Nombre del cliente" value={form.customer_name} onChange={update('customer_name')} required />
          <Input label="Monto" type="number" min="0.01" step="0.01" value={form.amount} onChange={update('amount')} required />
          <Input label="Fecha del pago" type="date" value={form.paid_on} onChange={update('paid_on')} required />
          <Input label="Canal de pago" value={form.payment_channel} onChange={update('payment_channel')} />
          <Input label="Referencia" value={form.reference} onChange={update('reference')} />
        </div>
        <label className="block text-sm font-bold text-slate-700">Observaciones<textarea className="mt-1 min-h-24 w-full rounded-xl border border-slate-200 p-3 font-normal" value={form.notes} onChange={update('notes')} /></label>
        <Button type="submit" className="w-full py-3">Registrar pago</Button>
      </form></Card>
    </div>
  );
}
