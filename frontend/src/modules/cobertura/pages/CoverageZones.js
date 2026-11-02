import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, MapPinned, Pencil, Plus, Search, ShieldCheck, ToggleLeft, ToggleRight, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../../../services/api';
import { Alert, Badge, Button, Card, Input } from '../../../components/ui';
import Brand from '../../../components/layout/Brand';
import AccountMenu from '../../../components/layout/AccountMenu';

const EMPTY_FORM = { name: '', description: '' };

export default function CoverageZones() {
  const [zones, setZones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingZone, setEditingZone] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const loadZones = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setZones(await api.getCoverageZones());
    } catch (err) {
      setError(err?.error || 'No se pudieron cargar las zonas de cobertura.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadZones(); }, [loadZones]);

  const activeCount = zones.filter((zone) => zone.is_active).length;
  const filteredZones = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase('es');
    if (!normalizedQuery) return zones;
    return zones.filter((zone) => zone.name.toLocaleLowerCase('es').includes(normalizedQuery));
  }, [query, zones]);

  const openNew = () => {
    setEditingZone(null);
    setForm(EMPTY_FORM);
    setError('');
    setDialogOpen(true);
  };

  const openEdit = (zone) => {
    setEditingZone(zone);
    setForm({ name: zone.name, description: zone.description || '' });
    setError('');
    setDialogOpen(true);
  };

  const closeDialog = () => {
    if (saving) return;
    setDialogOpen(false);
    setEditingZone(null);
  };

  const saveZone = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');
    try {
      if (editingZone) {
        await api.updateCoverageZone(editingZone.id, form);
        setMessage('Zona actualizada correctamente.');
      } else {
        await api.createCoverageZone(form);
        setMessage('Zona creada correctamente.');
      }
      setDialogOpen(false);
      setEditingZone(null);
      await loadZones();
    } catch (err) {
      setError(err?.error || 'No se pudo guardar la zona.');
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (zone) => {
    const nextActive = !zone.is_active;
    if (!nextActive && !window.confirm(
      `¿Desactivar "${zone.name}"? Las solicitudes históricas conservarán esta zona.`,
    )) return;

    setError('');
    setMessage('');
    try {
      await api.updateCoverageZone(zone.id, { is_active: nextActive });
      setMessage(nextActive ? 'Zona reactivada correctamente.' : 'Zona desactivada correctamente.');
      await loadZones();
    } catch (err) {
      setError(err?.error || 'No se pudo cambiar el estado de la zona.');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="gradient-sidebar border-b border-white/5">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <Brand subtitle="Gestión de cobertura" />
          <div className="flex items-center gap-3">
            <AccountMenu variant="header" />
            <Link
              to="/"
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-xs font-bold text-white/80 transition-colors hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-vista-accent/50"
            >
              <ArrowLeft className="h-4 w-4" />
              Módulos
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-brand-600">
            Gestión de cobertura
          </p>
          <h1 className="mt-1 text-2xl font-black tracking-tight text-slate-900">
            Zonas y barrios
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-500">
            Administra las zonas disponibles para contratos, recontrataciones y destinos de traslado.
          </p>
        </div>
        <Button type="button" onClick={openNew}>
          <Plus className="h-4 w-4" /> Agregar zona
        </Button>
      </header>

      {message && <Alert type="success">{message}</Alert>}
      {error && !dialogOpen && <Alert type="error">{error}</Alert>}

      <section className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_220px]">
        <Card className="flex items-center gap-4 p-5">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
            <MapPinned className="h-5 w-5" />
          </span>
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Zonas activas</p>
            <p className="mt-1 text-2xl font-black tabular-nums text-slate-900">{activeCount}</p>
          </div>
        </Card>
        <Card className="flex items-center gap-3 p-5">
          <ShieldCheck className="h-5 w-5 shrink-0 text-brand-600" />
          <p className="text-xs leading-5 text-slate-500">
            Las zonas se desactivan sin borrar su historial.
          </p>
        </Card>
      </section>

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <div>
            <h2 className="text-sm font-black text-slate-800">Catálogo de cobertura</h2>
            <p className="mt-1 text-xs text-slate-400">{zones.length} zonas registradas</p>
          </div>
          <div className="relative w-full sm:max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              aria-label="Buscar zona por nombre"
              className="pl-9"
              placeholder="Buscar barrio..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center text-sm font-medium text-slate-400" role="status">
            Cargando zonas...
          </div>
        ) : filteredZones.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  {['Zona / barrio', 'Descripción', 'Estado', 'Acciones'].map((label) => (
                    <th key={label} className="px-5 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {filteredZones.map((zone) => (
                  <tr key={zone.id} className="transition-colors hover:bg-brand-50/30">
                    <td className="px-5 py-4 font-semibold text-slate-800">{zone.name}</td>
                    <td className="max-w-sm px-5 py-4 text-xs text-slate-500">
                      {zone.description || '—'}
                    </td>
                    <td className="px-5 py-4">
                      <Badge color={zone.is_active ? 'green' : 'slate'}>
                        {zone.is_active ? 'Activa' : 'Inactiva'}
                      </Badge>
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-1">
                        <Button type="button" variant="ghost" size="sm" onClick={() => openEdit(zone)}>
                          <Pencil className="h-3.5 w-3.5" /> Editar
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleActive(zone)}
                          aria-label={`${zone.is_active ? 'Desactivar' : 'Reactivar'} ${zone.name}`}
                        >
                          {zone.is_active
                            ? <ToggleRight className="h-4 w-4 text-brand-600" />
                            : <ToggleLeft className="h-4 w-4" />}
                          {zone.is_active ? 'Desactivar' : 'Reactivar'}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-5 py-14 text-center">
            <MapPinned className="mx-auto h-8 w-8 text-slate-300" />
            <p className="mt-3 text-sm font-semibold text-slate-600">
              {query ? 'No hay zonas que coincidan con la búsqueda.' : 'No hay zonas registradas.'}
            </p>
          </div>
        )}
      </Card>

      {dialogOpen && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeDialog();
          }}
        >
          <Card
            role="dialog"
            aria-modal="true"
            aria-labelledby="coverage-zone-dialog-title"
            className="w-full max-w-lg space-y-5 p-6"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="coverage-zone-dialog-title" className="text-lg font-black text-slate-900">
                  {editingZone ? 'Editar zona' : 'Agregar zona'}
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  El nombre normaliza espacios y evita duplicados aunque cambien mayúsculas.
                </p>
              </div>
              <button
                type="button"
                onClick={closeDialog}
                className="rounded-lg p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
                aria-label="Cerrar"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {error && <Alert type="error">{error}</Alert>}

            <form onSubmit={saveZone} className="space-y-4">
              <Input
                label="Nombre de la zona *"
                value={form.name}
                maxLength={120}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                required
                autoFocus
              />
              <div className="space-y-1.5">
                <label htmlFor="coverage-zone-description" className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Descripción (opcional)
                </label>
                <textarea
                  id="coverage-zone-description"
                  value={form.description}
                  onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                  rows={3}
                  className="w-full resize-y rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:ring-2 focus:ring-brand-500/30"
                />
              </div>
              <div className="flex flex-wrap gap-3 pt-1">
                <Button type="submit" disabled={saving}>
                  {saving ? 'Guardando...' : editingZone ? 'Guardar cambios' : 'Crear zona'}
                </Button>
                <Button type="button" variant="secondary" onClick={closeDialog} disabled={saving}>
                  Cancelar
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
      </main>
    </div>
  );
}
