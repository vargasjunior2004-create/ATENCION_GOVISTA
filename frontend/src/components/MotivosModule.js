import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Button, Input, Select, Card, Alert, Badge } from './ui';

const CATEGORIAS = [
  { value: 'cambio', label: 'Motivo del cambio', color: 'amber' },
  { value: 'retiro', label: 'Motivo del retiro', color: 'red' },
];

const CATEGORIA_COLOR = Object.fromEntries(CATEGORIAS.map((c) => [c.value, c.color]));
const CATEGORIA_LABEL = Object.fromEntries(CATEGORIAS.map((c) => [c.value, c.label]));

const emptyForm = { categoria: 'cambio', nombre: '', descripcion: '', activo: true, orden: 0 };

export default function MotivosModule() {
  const [motivos, setMotivos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');
  const [deletingMotivo, setDeletingMotivo] = useState(null);
  const [categoriaFilter, setCategoriaFilter] = useState('all');

  const loadMotivos = useCallback(async () => {
    try {
      setMotivos(await api.getMotivos());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadMotivos(); }, [loadMotivos]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const openNew = () => {
    setForm({ ...emptyForm });
    setEditingId(null);
    setShowForm(true);
    setError('');
  };

  const openEdit = (motivo) => {
    setForm({
      categoria: motivo.categoria,
      nombre: motivo.nombre,
      descripcion: motivo.descripcion || '',
      activo: motivo.activo,
      orden: motivo.orden ?? 0,
    });
    setEditingId(motivo.id);
    setShowForm(true);
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const payload = {
      categoria: form.categoria,
      nombre: form.nombre,
      descripcion: form.descripcion,
      activo: form.activo,
      orden: Number(form.orden) || 0,
    };
    try {
      if (editingId) {
        await api.updateMotivo(editingId, payload);
      } else {
        await api.createMotivo(payload);
      }
      setShowForm(false);
      loadMotivos();
    } catch (err) {
      setError(err.error || 'Error al guardar el motivo');
    }
  };

  const toggleActive = async (motivo) => {
    try {
      await api.updateMotivo(motivo.id, { activo: !motivo.activo });
      loadMotivos();
    } catch (err) {
      alert(err.error || 'Error al cambiar el estado');
    }
  };

  const handleDelete = async () => {
    if (!deletingMotivo) return;
    try {
      await api.deleteMotivo(deletingMotivo.id);
      setDeletingMotivo(null);
      loadMotivos();
    } catch (err) {
      alert(err.error || 'Error al eliminar el motivo');
      setDeletingMotivo(null);
    }
  };

  if (loading) return <p className="text-center text-slate-400 py-20">Cargando...</p>;

  const filtered = categoriaFilter === 'all'
    ? motivos
    : motivos.filter((m) => m.categoria === categoriaFilter);

  const categoriaCount = (value) =>
    value === 'all' ? motivos.length : motivos.filter((m) => m.categoria === value).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Motivos</h1>
          <p className="text-sm text-slate-400 mt-1">
            Motivos de cambio y de retiro disponibles en el formulario
          </p>
        </div>
        <Button onClick={openNew}>+ Agregar Motivo</Button>
      </div>

      <Card className="p-5 space-y-3">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Categoria</p>
        <div className="flex flex-wrap gap-2">
          {[{ value: 'all', label: 'Todos' }, ...CATEGORIAS].map((c) => (
            <Button
              key={c.value}
              variant={categoriaFilter === c.value ? 'primary' : 'secondary'}
              size="sm"
              onClick={() => setCategoriaFilter(c.value)}
              aria-pressed={categoriaFilter === c.value}
            >
              {c.label} ({categoriaCount(c.value)})
            </Button>
          ))}
        </div>
        <p className="text-xs text-slate-500">Mostrando {filtered.length} de {motivos.length} motivos</p>
      </Card>

      {/* Confirmacion de borrado */}
      {deletingMotivo && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setDeletingMotivo(null)}>
          <Card className="w-full max-w-sm p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Eliminar motivo</h3>
                <p className="text-sm text-slate-500">Esta accion no se puede deshacer</p>
              </div>
            </div>
            <p className="text-sm text-slate-600">
              Seguro que deseas eliminar el motivo <strong>{deletingMotivo.nombre}</strong>?
            </p>
            <Alert type="info">
              Si ya tiene movimientos registrados no se podra borrar. En ese caso desactivalo para que
              deje de ofrecerse sin romper el historial.
            </Alert>
            <div className="flex gap-3 pt-2">
              <Button variant="danger" onClick={handleDelete}>Si, eliminar</Button>
              <Button variant="secondary" onClick={() => setDeletingMotivo(null)}>Cancelar</Button>
            </div>
          </Card>
        </div>
      )}

      {/* Modal de alta / edicion */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowForm(false)}>
          <Card className="w-full max-w-lg p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-black text-slate-900">
              {editingId ? 'Editar Motivo' : 'Nuevo Motivo'}
            </h3>
            {error && <Alert type="error">{error}</Alert>}
            <form onSubmit={handleSubmit} className="space-y-4">
              <Select label="Categoria *" name="categoria" value={form.categoria} onChange={handleChange}>
                {CATEGORIAS.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </Select>
              <Input label="Nombre *" name="nombre" value={form.nombre} onChange={handleChange} required placeholder="Ej: MEJOR CALIDAD" />
              <Input
                label="Descripcion (opcional)"
                name="descripcion"
                value={form.descripcion}
                onChange={handleChange}
                placeholder="Detalle del motivo"
              />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-end">
                <Input label="Orden" name="orden" type="number" value={form.orden} onChange={handleChange} />
                <label className="flex items-center gap-2 pb-3 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    name="activo"
                    checked={form.activo}
                    onChange={handleChange}
                    className="w-4 h-4 rounded border-slate-300"
                  />
                  Activo
                </label>
              </div>
              <div className="flex gap-3 pt-2">
                <Button type="submit">Guardar</Button>
                <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Cancelar</Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {motivos.length === 0 && (
        <Card className="p-12 text-center">
          <p className="text-sm text-slate-400">Aun no hay motivos. Agrega el primero para ofrecerlo en el formulario.</p>
        </Card>
      )}

      {filtered.length > 0 && (
        <Card className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                {['Categoria', 'Nombre', 'Descripcion', 'Orden', 'Estado', ''].map((h) => (
                  <th key={h} className="text-left px-4 py-3.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filtered.map((m) => (
                <tr key={m.id} className={`hover:bg-brand-50/30 transition-colors ${!m.activo ? 'opacity-50' : ''}`}>
                  <td className="px-4 py-3">
                    <Badge color={CATEGORIA_COLOR[m.categoria] || 'slate'}>
                      {CATEGORIA_LABEL[m.categoria] || m.categoria}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-900">{m.nombre}</td>
                  <td className="px-4 py-3 text-slate-500">{m.descripcion || '-'}</td>
                  <td className="px-4 py-3 text-slate-500">{m.orden}</td>
                  <td className="px-4 py-3">
                    <Badge color={m.activo ? 'green' : 'slate'}>{m.activo ? 'Activo' : 'Inactivo'}</Badge>
                  </td>
                  <td className="px-4 py-3 space-x-1">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(m)}>Editar</Button>
                    <Button variant="danger" size="sm" onClick={() => setDeletingMotivo(m)}>Eliminar</Button>
                    <Button variant={m.activo ? 'secondary' : 'success'} size="sm" onClick={() => toggleActive(m)}>
                      {m.activo ? 'Desactivar' : 'Activar'}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {filtered.length > 0 && (
        <div className="md:hidden space-y-3">
          {filtered.map((m) => (
            <Card key={m.id} className={`p-4 space-y-2 ${!m.activo ? 'opacity-50' : ''}`}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-slate-900">{m.nombre}</p>
                  <p className="text-xs text-slate-400">Orden {m.orden}</p>
                </div>
                <div className="flex gap-1.5">
                  <Badge color={CATEGORIA_COLOR[m.categoria] || 'slate'}>
                    {CATEGORIA_LABEL[m.categoria] || m.categoria}
                  </Badge>
                  <Badge color={m.activo ? 'green' : 'slate'}>{m.activo ? 'Activo' : 'Inactivo'}</Badge>
                </div>
              </div>
              {m.descripcion && <p className="text-sm text-slate-500">{m.descripcion}</p>}
              <div className="flex gap-2 pt-1">
                <Button variant="ghost" size="sm" onClick={() => openEdit(m)} className="flex-1">Editar</Button>
                <Button variant="danger" size="sm" onClick={() => setDeletingMotivo(m)} className="flex-1">Eliminar</Button>
                <Button variant={m.activo ? 'secondary' : 'success'} size="sm" onClick={() => toggleActive(m)} className="flex-1">
                  {m.activo ? 'Desactivar' : 'Activar'}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
