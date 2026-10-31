import React, { useState } from 'react';
import { ArrowLeft, Box, ClipboardList, PackageCheck, Search, Tag } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import { Alert, Button, Card, Input } from '../../components/ui';

function Detail({ label, value }) {
  return (
    <div className="rounded-xl bg-slate-50 px-4 py-3">
      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p>
      <p className="mt-1 text-sm font-bold text-slate-800">{value || '—'}</p>
    </div>
  );
}

export default function EquipmentPage() {
  const [serie, setSerie] = useState('');
  const [equipment, setEquipment] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const search = async (event) => {
    event.preventDefault();
    const value = serie.trim();
    if (!value) {
      setError('Introduce un número de serie para comenzar la búsqueda.');
      setEquipment(null);
      return;
    }
    setLoading(true);
    setError('');
    setEquipment(null);
    try {
      setEquipment(await api.getEquipmentBySerial(value));
    } catch (err) {
      setError(err?.error || 'No fue posible consultar el equipo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="gradient-sidebar border-b border-white/5">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-5 sm:px-6">
          <div className="flex items-center gap-3 text-white">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-vista-accent/15 text-vista-accent"><Box className="h-5 w-5" /></span>
            <div><p className="text-[10px] font-black uppercase tracking-[0.18em] text-vista-accent">Gestión de equipos</p><h1 className="text-lg font-black">Consulta de inventario</h1></div>
          </div>
          <Link to="/" className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-xs font-bold text-white/80 hover:bg-white/10"><ArrowLeft className="h-4 w-4" /> Módulos</Link>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6 sm:py-10">
        <section>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">Fase 1 · Solo lectura</p>
          <h2 className="mt-2 text-3xl font-black tracking-tight text-slate-900">Identifica un equipo por su serie</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Consulta el artículo, la marca, el modelo y el tipo registrado en el catálogo de Supabase antes de iniciar cualquier operación.</p>
        </section>

        <Card className="p-5 sm:p-6">
          <form onSubmit={search} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1"><Input label="Número de serie" value={serie} onChange={(event) => setSerie(event.target.value)} placeholder="Escanea o escribe la serie" autoComplete="off" autoFocus /></div>
            <Button type="submit" disabled={loading}><Search className="h-4 w-4" /> {loading ? 'Consultando...' : 'Consultar equipo'}</Button>
          </form>
        </Card>

        {error && <Alert type="error">{error}</Alert>}

        {equipment && (
          <Card className="overflow-hidden p-0">
            <div className="flex items-center gap-3 border-b border-emerald-100 bg-emerald-50/70 px-5 py-4 sm:px-6"><PackageCheck className="h-6 w-6 text-emerald-600" /><div><p className="text-sm font-black text-emerald-900">Equipo encontrado</p><p className="text-xs text-emerald-700">La consulta no modifica ningún registro.</p></div></div>
            <div className="space-y-5 p-5 sm:p-6">
              <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">Serie física</p><p className="mt-1 text-2xl font-black tracking-tight text-slate-900">{equipment.serie}</p></div><span className="inline-flex items-center gap-2 rounded-full bg-brand-50 px-3 py-1.5 text-xs font-bold text-brand-700"><Tag className="h-3.5 w-3.5" /> Catálogo validado</span></div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"><Detail label="Código de artículo" value={equipment.articulo.codigo} /><Detail label="Descripción" value={equipment.articulo.descripcion} /><Detail label="Marca" value={equipment.articulo.marca} /><Detail label="Modelo" value={equipment.articulo.modelo} /><Detail label="Tipo de equipo" value={equipment.articulo.tipo.nombre} /><Detail label="ID de registro" value={equipment.id} /></div>
            </div>
          </Card>
        )}

        {!equipment && !error && <Card className="flex min-h-56 flex-col items-center justify-center p-8 text-center"><ClipboardList className="h-10 w-10 text-slate-300" /><p className="mt-3 text-sm font-bold text-slate-600">Aún no hay una consulta</p><p className="mt-1 text-xs text-slate-400">Introduce una serie para ver la ficha del equipo.</p></Card>}
      </main>
    </div>
  );
}
