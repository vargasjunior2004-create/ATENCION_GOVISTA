import React, { useEffect, useState } from 'react';
import api from '../../../services/api';
import { Alert, Button, Card, Input } from '../../../components/ui';

export default function AtencionForm() {
  const [catalogs, setCatalogs] = useState([]);
  const [form, setForm] = useState({ customer_code: '', customer_name: '', attention_type: '', classification: '', channel: '', notes: '' });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    api.getAtencionCatalogs().then(setCatalogs).catch(() => setError('No fue posible cargar los catálogos.'));
  }, []);

  const options = (type) => catalogs.filter((item) => item.catalog_type === type);
  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value });
  const save = async (event) => {
    event.preventDefault();
    setError(''); setMessage('');
    try {
      await api.createAtencion({ ...form, attention_type: Number(form.attention_type), classification: Number(form.classification), channel: Number(form.channel) });
      setForm({ customer_code: '', customer_name: '', attention_type: '', classification: '', channel: '', notes: '' });
      setMessage('Atención registrada. Ahora puedes iniciarla desde el listado.');
    } catch (err) { setError(err.error || 'No fue posible registrar la atención.'); }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <header><p className="text-xs font-black uppercase tracking-[0.18em] text-brand-600">Call Center</p><h2 className="mt-1 text-3xl font-black text-slate-900">Registrar atención</h2></header>
      {message && <Alert type="success">{message}</Alert>}
      {error && <Alert type="error">{error}</Alert>}
      <Card className="p-5">
        <form className="space-y-4" onSubmit={save}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Input label="Kardex / código" value={form.customer_code} onChange={update('customer_code')} required />
            <Input label="Nombre del cliente" value={form.customer_name} onChange={update('customer_name')} required />
          </div>
          {[
            ['attention_type', 'Tipo de atención', 'attention_type'],
            ['classification', 'Clasificación', 'classification'],
            ['channel', 'Canal de origen', 'channel'],
          ].map(([field, label, type]) => (
            <label key={field} className="block text-sm font-bold text-slate-700">{label}
              <select className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5" value={form[field]} onChange={update(field)} required>
                <option value="">Seleccionar</option>
                {options(type).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </label>
          ))}
          <label className="block text-sm font-bold text-slate-700">Observaciones<textarea className="mt-1 min-h-24 w-full rounded-xl border border-slate-200 p-3 font-normal" value={form.notes} onChange={update('notes')} /></label>
          <Button type="submit" className="w-full py-3">Registrar atención</Button>
        </form>
      </Card>
    </div>
  );
}
