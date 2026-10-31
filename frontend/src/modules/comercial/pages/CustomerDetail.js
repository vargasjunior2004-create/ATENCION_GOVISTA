import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, ClipboardList, FileText, Gauge, Pencil, Save, UserRound } from 'lucide-react';
import api from '../../../services/api';
import { useAuth } from '../../../context/AuthContext';
import { Alert, Button, Card, Input, Select } from '../../../components/ui';

const dateLabel = (value) => value ? new Date(`${value}T12:00:00`).toLocaleDateString('es-BO') : '—';
const dateTimeLabel = (value) => value ? new Date(value).toLocaleString('es-BO', { dateStyle: 'short', timeStyle: 'short' }) : '—';

function Stat({ icon: Icon, value, label }) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-4"><Icon className="h-5 w-5 text-brand-600" /><p className="mt-3 text-2xl font-black text-slate-900">{value}</p><p className="text-xs font-bold uppercase tracking-wide text-slate-400">{label}</p></div>;
}

export default function CustomerDetail() {
  const { id } = useParams();
  const { isAdmin } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});
  const [message, setMessage] = useState('');

  const load = async () => {
    setLoading(true); setError('');
    try {
      const result = await api.getCustomer(id);
      setData(result); setForm(result.customer);
    } catch (err) { setError(err?.error || 'No fue posible cargar la ficha del cliente.'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [id]);

  const saveCustomer = async (event) => {
    event.preventDefault(); setMessage('');
    try { const customer = await api.updateCustomer(id, form); setData((current) => ({ ...current, customer })); setForm(customer); setEditing(false); setMessage('Información actualizada correctamente.'); }
    catch (err) { setMessage(err?.error || 'No fue posible actualizar la información.'); }
  };

  const reviewMeter = async (contract, status, notes) => {
    try { await api.reviewContractMeter(contract.id, { meter_review_status: status, meter_review_notes: notes }); setMessage('Revisión del medidor registrada.'); load(); }
    catch (err) { setMessage(err?.error || 'No fue posible registrar la revisión.'); }
  };

  if (loading) return <div className="py-20 text-center text-sm text-slate-400">Cargando ficha del cliente...</div>;
  if (error) return <div className="space-y-4"><Link to="/comercial/clientes" className="inline-flex items-center gap-2 text-sm font-bold text-brand-700"><ArrowLeft className="h-4 w-4" /> Volver a clientes</Link><Alert type="error">{error}</Alert></div>;

  const customer = data.customer;
  return (
    <div className="space-y-6">
      <Link to="/comercial/clientes" className="inline-flex items-center gap-2 text-sm font-bold text-brand-700 hover:text-brand-900"><ArrowLeft className="h-4 w-4" /> Volver a clientes</Link>
      <header className="rounded-3xl bg-gradient-to-br from-slate-950 via-slate-900 to-brand-950 p-6 text-white shadow-xl sm:p-8">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start"><div><p className="text-xs font-black uppercase tracking-[0.2em] text-emerald-300">Ficha del cliente</p><h1 className="mt-2 text-3xl font-black tracking-tight">{customer.name}</h1><p className="mt-2 text-sm text-slate-300">CI: {customer.ci || 'No registrado'} · Kardex: {customer.code}</p></div><span className="rounded-full bg-white/10 px-3 py-1.5 text-xs font-bold capitalize text-emerald-200">{customer.status}</span></div>
        <div className="mt-6 grid gap-3 text-sm text-slate-300 sm:grid-cols-3"><div><span className="block text-xs uppercase tracking-wide text-slate-500">Teléfono</span>{customer.phone || 'No registrado'}</div><div><span className="block text-xs uppercase tracking-wide text-slate-500">Cliente creado</span>{dateTimeLabel(customer.created_at)}</div><div className="flex items-end sm:justify-end">{isAdmin && <Button variant="secondary" onClick={() => setEditing((value) => !value)}><Pencil className="h-4 w-4" /> Editar información</Button>}</div></div>
      </header>

      {message && <Alert type={message.includes('No fue') ? 'error' : 'success'}>{message}</Alert>}
      {editing && isAdmin && <Card className="p-5"><form onSubmit={saveCustomer} className="space-y-4"><div className="grid gap-4 sm:grid-cols-2"><Input label="Nombre completo" value={form.name || ''} onChange={(e) => setForm({ ...form, name: e.target.value.toUpperCase() })} required /><Input label="CI" value={form.ci || ''} onChange={(e) => setForm({ ...form, ci: e.target.value.trim() })} /><Input label="Teléfono" value={form.phone || ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} /><Select label="Estado" value={form.status || 'activo'} onChange={(e) => setForm({ ...form, status: e.target.value })}><option value="activo">Activo</option><option value="inactivo">Inactivo</option><option value="observado">Observado</option></Select></div><Button type="submit"><Save className="h-4 w-4" /> Guardar cambios</Button></form></Card>}

      <section className="grid gap-4 sm:grid-cols-3"><Stat icon={FileText} value={data.summary.contracts} label="Contratos" /><Stat icon={Gauge} value={data.summary.meters} label="Medidores" /><Stat icon={ClipboardList} value={data.summary.movements} label="Movimientos" /></section>

      <section className="space-y-4"><div><h2 className="text-xl font-black text-slate-900">Contratos y servicios</h2><p className="text-sm text-slate-500">La relación del medidor pertenece al contrato y conserva su historial.</p></div>{data.contracts.length === 0 ? <Card className="p-8 text-center text-sm text-slate-500">Este cliente todavía no tiene contratos registrados.</Card> : <div className="grid gap-4 lg:grid-cols-2">{data.contracts.map((contract) => <ContractCard key={contract.id} contract={contract} isAdmin={isAdmin} onReview={reviewMeter} />)}</div>}</section>

      <section className="space-y-4"><div><h2 className="text-xl font-black text-slate-900">Línea de tiempo comercial</h2><p className="text-sm text-slate-500">Movimientos registrados en GO VISTA, del más reciente al más antiguo.</p></div>{data.timeline.length === 0 ? <Card className="p-8 text-center text-sm text-slate-500">No hay movimientos históricos asociados.</Card> : <Card className="divide-y divide-slate-100 p-0">{data.timeline.map((sale) => <div key={sale.id} className="flex gap-4 p-5"><div className="mt-1 h-3 w-3 shrink-0 rounded-full bg-brand-600 ring-4 ring-brand-50" /><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-bold text-slate-800">{sale.requestType} · {sale.Plan?.label || 'Sin plan'}</p><span className="text-xs font-semibold text-slate-400">{dateLabel(sale.date)}</span></div><p className="mt-1 text-sm text-slate-500">{sale.changeReason || sale.notes || 'Operación comercial registrada'} · por {sale.creator?.name || '—'}</p></div></div>)}</Card>}</section>
    </div>
  );
}

function ContractCard({ contract, isAdmin, onReview }) {
  const [notes, setNotes] = useState(contract.meter_review_notes || '');
  return <Card className="p-5"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-black uppercase tracking-wide text-brand-600">Contrato {contract.number}</p><h3 className="mt-1 text-lg font-black text-slate-900">{contract.planLabel}</h3><p className="text-sm text-slate-500">Servicio: {contract.service_type} · Desde: {dateLabel(contract.contracted_on)}</p></div><span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold capitalize text-slate-600">{contract.status}</span></div><div className="mt-4 grid gap-3 text-sm sm:grid-cols-2"><div><span className="block text-xs font-bold uppercase text-slate-400">Medidor de luz</span><span className="font-semibold text-slate-800">{contract.meter_number || 'No registrado'}</span></div><div><span className="block text-xs font-bold uppercase text-slate-400">Origen</span><span className="font-semibold text-slate-800">{contract.origin}{contract.external_seller ? ` · ${contract.external_seller}` : ''}</span></div></div>{contract.meterMatches?.length > 0 && <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800"><strong>Coincidencia detectada:</strong> este medidor aparece en {contract.meterMatches.map((match) => `${match.number} (${match.customerName})`).join(', ')}.</div>} {isAdmin && contract.meter_number && <div className="mt-4 border-t border-slate-100 pt-4"><p className="text-xs font-bold uppercase tracking-wide text-slate-400">Revisión manual en el otro sistema</p><div className="mt-2 flex flex-col gap-2 sm:flex-row"><Select value={contract.meter_review_status} onChange={(e) => onReview(contract, e.target.value, notes)}><option value="pendiente">Pendiente</option><option value="verificado">Verificado</option><option value="observado">Observado</option></Select><Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Observación" /><Button size="sm" onClick={() => onReview(contract, contract.meter_review_status, notes)}>Guardar revisión</Button></div></div>}</Card>;
}
