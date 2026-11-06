import React, { useCallback, useEffect, useState } from 'react';
import { ExternalLink } from 'lucide-react';
import api from '../../../services/api';
import { Alert, Badge, Button, Card, Input } from '../../../components/ui';
import { useAuth } from '../../../context/AuthContext';

const EMPTY_ZONE = { name: '', google_maps_url: '' };

export default function RegisterCoverageZone() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission('coverage.manage');
  const canEdit = canManage || hasPermission('coverage.change');
  const [zones, setZones] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [form, setForm] = useState(EMPTY_ZONE);
  const [editingId, setEditingId] = useState(null);
  const [editingForm, setEditingForm] = useState(EMPTY_ZONE);

  const loadZones = useCallback(async () => {
    if (!canManage) return;
    setLoading(true);
    setError('');
    try {
      setZones(await api.getManagedCoverageZones());
    } catch (err) {
      setError(err?.error || 'No se pudieron cargar las zonas de cobertura.');
    } finally {
      setLoading(false);
    }
  }, [canManage]);

  useEffect(() => { loadZones(); }, [loadZones]);

  const submitZone = async (event) => {
    event.preventDefault();
    setError('');
    setMessage('');
    try {
      await api.createCoverageZone(form);
      setForm(EMPTY_ZONE);
      setMessage('Nuevo barrio creado correctamente.');
      await loadZones();
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
    <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <header>
        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-brand-600">
          Administración del catálogo
        </p>
        <h1 className="mt-1 text-2xl font-black tracking-tight text-slate-900">
          Registrar zona
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-500">
          Registra el nombre del barrio y su enlace de Google Maps. Las zonas pueden
          editarse o desactivarse sin eliminar su historial.
        </p>
      </header>

      {message && <Alert type="success">{message}</Alert>}
      {error && <Alert type="error">{error}</Alert>}

      <Card className="p-5 sm:p-6">
        <form onSubmit={submitZone} className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Nombre del barrio o zona"
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
            <Button type="submit">Guardar zona</Button>
          </div>
        </form>
      </Card>

      {canManage && (
        <Card className="overflow-hidden">
          <div className="border-b border-slate-100 px-5 py-4">
            <h2 className="text-sm font-black text-slate-800">Zonas registradas</h2>
            <p className="mt-1 text-xs text-slate-500">
              Edita nombres y enlaces, o cambia la disponibilidad en Comercial.
            </p>
          </div>
          {loading ? (
            <div className="py-12 text-center text-sm font-medium text-slate-400" role="status">
              Cargando zonas...
            </div>
          ) : zones.length ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[620px] text-sm">
                <thead>
                  <tr className="border-b border-slate-100">
                    {['Zona / barrio', 'URL de Google Maps', 'Estado', 'Acciones'].map((label) => (
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
                  {zones.map((zone) => (
                    <tr key={zone.id} className="hover:bg-brand-50/30">
                      <td className="px-5 py-4 font-semibold text-slate-800">
                        {editingId === zone.id ? (
                          <form
                            id={`edit-zone-${zone.id}`}
                            onSubmit={(event) => saveEdit(event, zone)}
                            className="min-w-52"
                          >
                            <Input
                              aria-label="Nombre del barrio o zona"
                              value={editingForm.name}
                              onChange={(event) => setEditingForm({
                                ...editingForm,
                                name: event.target.value,
                              })}
                              required
                              maxLength={120}
                            />
                          </form>
                        ) : zone.name}
                      </td>
                      <td className="max-w-xs px-5 py-4 text-xs text-slate-500">
                        {editingId === zone.id ? (
                          <Input
                            aria-label="URL de Google Maps"
                            type="url"
                            form={`edit-zone-${zone.id}`}
                            value={editingForm.google_maps_url}
                            onChange={(event) => setEditingForm({
                              ...editingForm,
                              google_maps_url: event.target.value,
                            })}
                            required
                            maxLength={500}
                          />
                        ) : (
                          <a
                            href={zone.google_maps_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex max-w-full items-center gap-1 break-all text-brand-700 hover:underline"
                          >
                            <span className="truncate">{zone.google_maps_url || '—'}</span>
                            {zone.google_maps_url && (
                              <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                            )}
                          </a>
                        )}
                      </td>
                      <td className="px-5 py-4">
                        <Badge color={zone.is_active ? 'green' : 'slate'}>
                          {zone.is_active ? 'Activa' : 'Inactiva'}
                        </Badge>
                      </td>
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
                          ) : canEdit ? (
                            <Button
                              type="button"
                              size="sm"
                              variant="secondary"
                              onClick={() => beginEdit(zone)}
                            >
                              Editar
                            </Button>
                          ) : null}
                          <Button
                            type="button"
                            size="sm"
                            variant={zone.is_active ? 'danger' : 'success'}
                            onClick={() => toggleZone(zone)}
                          >
                            {zone.is_active ? 'Desactivar' : 'Activar'}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="px-5 py-12 text-center text-sm text-slate-500">
              No hay zonas registradas.
            </p>
          )}
        </Card>
      )}
    </main>
  );
}
