import React, { useCallback, useEffect, useState } from 'react';
import api from '../services/api';
import { Alert, Badge, Button, Card, Input } from './ui';

const emptyForm = { nombre: '', descripcion: '', activo: true };

function errorMessage(err, fallback) {
  if (!err) return fallback;
  if (typeof err.error === 'string') return err.error;
  if (err.error && typeof err.error === 'object') {
    const first = Object.values(err.error)[0];
    if (first) return Array.isArray(first) ? first[0] : String(first);
  }
  return fallback;
}

function fechaCorta(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString('es-BO');
}

export default function CanalesCaptacionModule() {
  const [canales, setCanales] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const loadCanales = useCallback(async () => {
    setLoadError('');
    try {
      setCanales(await api.getCanalesCaptacion());
    } catch (err) {
      setLoadError(errorMessage(
        err, 'No se pudieron cargar los canales de captación.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadCanales(); }, [loadCanales]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const openNew = () => {
    setForm({ ...emptyForm });
    setEditingId(null);
    setError('');
    setShowForm(true);
  };

  const openEdit = (canal) => {
    setForm({
      nombre: canal.nombre,
      descripcion: canal.descripcion || '',
      activo: canal.activo,
    });
    setEditingId(canal.id);
    setError('');
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    const payload = {
      nombre: form.nombre,
      descripcion: form.descripcion,
      activo: form.activo,
    };
    try {
      if (editingId) {
        await api.updateCanalCaptacion(editingId, payload);
      } else {
        await api.createCanalCaptacion(payload);
      }
      setShowForm(false);
      await loadCanales();
    } catch (err) {
      setError(errorMessage(err, 'Error al guardar el canal de captación'));
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (canal) => {
    try {
      await api.updateCanalCaptacion(canal.id, { activo: !canal.activo });
      await loadCanales();
    } catch (err) {
      alert(errorMessage(err, 'Error al cambiar el estado del canal'));
    }
  };

  if (loading) {
    return <p className="text-center text-slate-400 py-20">Cargando...</p>;
  }

  const activos = canales.filter((canal) => canal.activo).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">
            Canales de captación
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Medios por los que los clientes conocen nuestros servicios
          </p>
        </div>
        <Button onClick={openNew}>+ Agregar Canal</Button>
      </div>

      {loadError && <Alert type="error">{loadError}</Alert>}

      <Card className="p-5 flex flex-wrap items-center gap-4">
        <p className="text-sm text-slate-600">
          <span className="font-semibold text-slate-900">{canales.length}</span> canales registrados
        </p>
        <Badge color="green">{activos} activos</Badge>
        <Badge color="slate">{canales.length - activos} inactivos</Badge>
      </Card>

      {showForm && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setShowForm(false)}
        >
          <Card
            className="w-full max-w-lg p-6 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-black text-slate-900">
              {editingId ? 'Editar Canal' : 'Nuevo Canal'}
            </h3>
            {error && <Alert type="error">{error}</Alert>}
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Nombre *"
                name="nombre"
                value={form.nombre}
                onChange={handleChange}
                required
                maxLength={120}
                placeholder="Ej: Instagram"
              />
              <Input
                label="Descripción (opcional)"
                name="descripcion"
                value={form.descripcion}
                onChange={handleChange}
                maxLength={255}
                placeholder="Detalle del medio de captación"
              />
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  name="activo"
                  checked={form.activo}
                  onChange={handleChange}
                  className="w-4 h-4 rounded border-slate-300"
                />
                Activo para nuevas solicitudes
              </label>
              <div className="flex gap-3 pt-2">
                <Button type="submit" disabled={saving}>
                  {saving ? 'Guardando...' : 'Guardar'}
                </Button>
                <Button
                  variant="secondary"
                  type="button"
                  onClick={() => setShowForm(false)}
                >
                  Cancelar
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {canales.length === 0 && !loadError && (
        <Card className="p-12 text-center">
          <p className="text-sm text-slate-400">
            Aún no hay canales. Agrega el primero para ofrecerlo en el formulario.
          </p>
        </Card>
      )}

      {canales.length > 0 && (
        <Card className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                {['Canal', 'Descripción', 'Estado', 'Actualizado', ''].map((h) => (
                  <th
                    key={h}
                    className="text-left px-4 py-3.5 text-[11px] font-bold uppercase tracking-wider text-slate-400"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {canales.map((canal) => (
                <tr
                  key={canal.id}
                  className={`hover:bg-brand-50/30 transition-colors ${!canal.activo ? 'opacity-50' : ''}`}
                >
                  <td className="px-4 py-3 font-medium text-slate-900">{canal.nombre}</td>
                  <td className="px-4 py-3 text-slate-500">{canal.descripcion || '—'}</td>
                  <td className="px-4 py-3">
                    <Badge color={canal.activo ? 'green' : 'slate'}>
                      {canal.activo ? 'Activo' : 'Inactivo'}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{fechaCorta(canal.updated_at)}</td>
                  <td className="px-4 py-3 space-x-1 text-right">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(canal)}>
                      Editar
                    </Button>
                    <Button
                      variant={canal.activo ? 'secondary' : 'success'}
                      size="sm"
                      onClick={() => toggleActive(canal)}
                    >
                      {canal.activo ? 'Desactivar' : 'Activar'}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {canales.length > 0 && (
        <div className="md:hidden space-y-3">
          {canales.map((canal) => (
            <Card
              key={canal.id}
              className={`p-4 space-y-2 ${!canal.activo ? 'opacity-50' : ''}`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="font-semibold text-slate-900">{canal.nombre}</p>
                <Badge color={canal.activo ? 'green' : 'slate'}>
                  {canal.activo ? 'Activo' : 'Inactivo'}
                </Badge>
              </div>
              {canal.descripcion && (
                <p className="text-sm text-slate-500">{canal.descripcion}</p>
              )}
              <p className="text-xs text-slate-400">
                Actualizado: {fechaCorta(canal.updated_at)}
              </p>
              <div className="flex gap-2 pt-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openEdit(canal)}
                  className="flex-1"
                >
                  Editar
                </Button>
                <Button
                  variant={canal.activo ? 'secondary' : 'success'}
                  size="sm"
                  onClick={() => toggleActive(canal)}
                  className="flex-1"
                >
                  {canal.activo ? 'Desactivar' : 'Activar'}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
