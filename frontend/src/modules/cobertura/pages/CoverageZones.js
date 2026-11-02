import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ExternalLink, MapPinned, Search } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../../../services/api';
import { Alert, Badge, Button, Card, Input } from '../../../components/ui';
import Brand from '../../../components/layout/Brand';
import AccountMenu from '../../../components/layout/AccountMenu';
import { useAuth } from '../../../context/AuthContext';

const EMPTY_ZONE = { name: '', google_maps_url: '' };

function zoneStatus(zone) {
  if (zone.is_pending) return 'Pendiente de habilitación';
  return zone.is_active ? 'Activa' : 'Inactiva';
}

export default function CoverageZones() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission('coverage.manage');
  const canEdit = canManage || hasPermission('coverage.change');
  const canRegister = hasPermission('coverage.create');
  const [zones, setZones] = useState([]);
  const [registrations, setRegistrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [form, setForm] = useState(EMPTY_ZONE);
  const [editingId, setEditingId] = useState(null);
  const [editingForm, setEditingForm] = useState(EMPTY_ZONE);

  const loadZones = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setZones(await (
        canEdit
          ? api.getManagedCoverageZones()
          : api.getCoverageZones()
      ));
    } catch (err) {
      setError(err?.error || 'No se pudieron cargar las zonas de cobertura.');
    } finally {
      setLoading(false);
    }
  }, [canEdit]);

  const loadRegistrations = useCallback(async () => {
    if (!canRegister || canManage) return;
    try {
      setRegistrations(await api.getCoverageZoneRegistrations());
    } catch (err) {
      setError(err?.error || 'No se pudo cargar el estado de tus registros.');
    }
  }, [canManage, canRegister]);

  useEffect(() => { loadZones(); }, [loadZones]);
  useEffect(() => { loadRegistrations(); }, [loadRegistrations]);

  const activeCount = zones.filter((zone) => zone.is_active).length;
  const filteredZones = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase('es');
    if (!normalizedQuery) return zones;
    return zones.filter(
      (zone) => zone.name.toLocaleLowerCase('es').includes(normalizedQuery),
    );
  }, [query, zones]);

  const submitZone = async (event) => {
    event.preventDefault();
    setError('');
    setMessage('');
    try {
      if (canManage) {
        await api.createCoverageZone(form);
        setMessage('Nuevo barrio creado correctamente.');
      } else {
        await api.registerCoverageZone(form);
        setMessage('Nuevo barrio creado correctamente.');
      }
      setForm(EMPTY_ZONE);
      await Promise.all([loadZones(), loadRegistrations()]);
    } catch (err) {
      setError(err?.error || 'No se pudo registrar el barrio.');
    }
  };

  const beginEdit = (zone) => {
    setEditingId(zone.id);
    setEditingForm({
      name: zone.name,
      google_maps_url: zone.google_maps_url || '',
    });
  };

  const saveEdit = async (event, zone) => {
    event.preventDefault();
    setError('');
    setMessage('');
    try {
      await api.updateCoverageZone(zone.id, editingForm);
      setEditingId(null);
      setMessage('Barrio actualizado correctamente.');
      await loadZones();
    } catch (err) {
      setError(err?.error || 'No se pudo actualizar el barrio.');
    }
  };

  const toggleZone = async (zone) => {
    setError('');
    setMessage('');
    const activating = !zone.is_active;
    try {
      await api.updateCoverageZone(zone.id, { is_active: activating });
      setMessage(
        activating
          ? 'Barrio activado correctamente.'
          : 'Barrio desactivado correctamente.',
      );
      await loadZones();
    } catch (err) {
      setError(err?.error || 'No se pudo actualizar el estado del barrio.');
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
              Consulta de cobertura
            </p>
            <h1 className="mt-1 text-2xl font-black tracking-tight text-slate-900">
              Zonas y barrios
            </h1>
            <p className="mt-1 max-w-xl text-sm text-slate-500">
              Busca un barrio y abre su ubicación en Google My Maps sin salir de GO VISTA.
            </p>
          </div>
          <Badge color="green">{activeCount} zonas activas</Badge>
        </header>

        {message && <Alert type="success">{message}</Alert>}
        {error && <Alert type="error">{error}</Alert>}

        {(canManage || (canRegister && !canManage)) && (
          <Card className="p-5">
            <h2 className="text-sm font-black text-slate-800">
              {canManage ? 'Agregar barrio al catálogo' : 'Registrar barrio nuevo'}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {canManage
                ? 'El barrio quedará disponible para las consultas comerciales.'
                : 'El registro quedará pendiente y no aparecerá en Comercial hasta que sea habilitado.'}
            </p>
            <form onSubmit={submitZone} className="mt-4 grid gap-3 sm:grid-cols-2">
              <Input
                label="Nombre del barrio"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
                required
                maxLength={120}
              />
              <Input
                label="URL de Google Maps"
                type="url"
                value={form.google_maps_url}
                onChange={(event) => setForm({
                  ...form,
                  google_maps_url: event.target.value,
                })}
                required
                maxLength={500}
              />
              <div className="sm:col-span-2">
                <Button type="submit">Guardar barrio</Button>
              </div>
            </form>
          </Card>
        )}

        {canRegister && !canManage && (
          <Card className="p-5">
            <h2 className="text-sm font-black text-slate-800">Estado de mis registros</h2>
            {registrations.length ? (
              <div className="mt-3 space-y-2">
                {registrations.map((zone) => (
                  <div
                    key={zone.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-100 p-3"
                  >
                    <div>
                      <p className="text-sm font-semibold text-slate-800">{zone.name}</p>
                      <p className="text-xs text-slate-400">
                        Registrado {new Date(zone.created_at).toLocaleString('es-BO')}
                      </p>
                    </div>
                    <Badge color={zone.is_pending ? 'amber' : zone.is_active ? 'green' : 'slate'}>
                      {zoneStatus(zone)}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-sm text-slate-500">Aún no registraste barrios.</p>
            )}
          </Card>
        )}

        <Card className="overflow-hidden">
          <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
            <div>
              <h2 className="text-sm font-black text-slate-800">Catálogo de cobertura</h2>
              <p className="mt-1 text-xs text-slate-400">
                {zones.length} barrios registrados
              </p>
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
              <table className="w-full min-w-[520px] text-sm">
                <thead>
                  <tr className="border-b border-slate-100">
                    {['Zona / barrio', 'Descripción', 'Estado', ...(canEdit ? ['Acciones'] : [])].map((label) => (
                      <th
                        key={label}
                        className="px-5 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-slate-400"
                      >
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {filteredZones.map((zone) => (
                    <tr key={zone.id} className="transition-colors hover:bg-brand-50/30">
                      <td className="px-5 py-4 font-semibold text-slate-800">
                        {editingId === zone.id ? (
                          <form
                            id={`edit-zone-${zone.id}`}
                            onSubmit={(event) => saveEdit(event, zone)}
                            className="min-w-60 space-y-2"
                          >
                            <Input
                              aria-label="Nombre del barrio"
                              value={editingForm.name}
                              onChange={(event) => setEditingForm({
                                ...editingForm,
                                name: event.target.value,
                              })}
                              required
                              maxLength={120}
                            />
                            <Input
                              aria-label="URL de Google Maps"
                              type="url"
                              value={editingForm.google_maps_url}
                              onChange={(event) => setEditingForm({
                                ...editingForm,
                                google_maps_url: event.target.value,
                              })}
                              maxLength={500}
                            />
                          </form>
                        ) : zone.google_maps_url ? (
                          <a
                            href={zone.google_maps_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 text-brand-700 underline-offset-2 hover:underline focus:outline-none focus:ring-2 focus:ring-brand-500/40"
                          >
                            {zone.name}
                            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                          </a>
                        ) : (
                          zone.name
                        )}
                      </td>
                      <td className="max-w-sm px-5 py-4 text-xs text-slate-500">
                        {zone.description || '—'}
                      </td>
                      <td className="px-5 py-4">
                        <Badge color={zone.is_pending ? 'amber' : zone.is_active ? 'green' : 'slate'}>
                          {zone.is_pending ? zoneStatus(zone) : zone.is_active ? 'Activa' : 'Inactiva'}
                        </Badge>
                      </td>
                      {canEdit && (
                        <td className="px-5 py-4">
                          <div className="flex flex-wrap gap-2">
                            {editingId === zone.id ? (
                              <>
                                <Button
                                  type="submit"
                                  size="sm"
                                  form={`edit-zone-${zone.id}`}
                                >
                                  Guardar
                                </Button>
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="secondary"
                                  onClick={() => setEditingId(null)}
                                >
                                  Cancelar
                                </Button>
                              </>
                            ) : (
                              <Button
                                type="button"
                                size="sm"
                                variant="secondary"
                                onClick={() => beginEdit(zone)}
                              >
                                Editar
                              </Button>
                            )}
                            {canManage && (
                              <Button
                                type="button"
                                size="sm"
                                variant={zone.is_active ? 'danger' : 'success'}
                                onClick={() => toggleZone(zone)}
                              >
                                {zone.is_active ? 'Desactivar' : 'Habilitar'}
                              </Button>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-5 py-14 text-center">
              <MapPinned className="mx-auto h-8 w-8 text-slate-300" />
              <p className="mt-3 text-sm font-semibold text-slate-600">
                {query
                  ? 'No hay zonas que coincidan con la búsqueda.'
                  : 'No hay zonas registradas.'}
              </p>
            </div>
          )}
        </Card>
      </main>
    </div>
  );
}
