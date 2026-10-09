import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Button, Input, Select, Card, Alert, Badge } from './ui';

const MODOS = [
  { value: 'simple', label: 'Sin reglas especiales', color: 'slate' },
  { value: 'nuevo', label: 'Nuevo contrato', color: 'green' },
  { value: 'retiro', label: 'Retiro', color: 'red' },
  { value: 'cambio_plan', label: 'Cambio de plan', color: 'violet' },
  { value: 'adicion', label: 'Adicion', color: 'blue' },
];

const MODO_COLOR = Object.fromEntries(MODOS.map((m) => [m.value, m.color]));
const MODO_LABEL = Object.fromEntries(MODOS.map((m) => [m.value, m.label]));

const STATE_FILTERS = [
  { value: 'all', label: 'Todos los estados' },
  { value: 'active', label: 'Activos' },
  { value: 'inactive', label: 'Inactivos' },
];

const emptyForm = { code: '', nombre: '', descripcion: '', modo: 'simple', activo: true, orden: 0 };

// El code es la llave que guarda cada movimiento, asi que tiene que quedar
// estable y en minúsculas. Se deriva del nombre para no tener que escribirlo.
function slugify(text) {
  return text
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 20);
}

export default function RequestTypesModule() {
  const [tipos, setTipos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...emptyForm });
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');
  const [deletingTipo, setDeletingTipo] = useState(null);
  const [modoFilter, setModoFilter] = useState('all');
  const [stateFilter, setStateFilter] = useState('all');
  const [applied, setApplied] = useState(null);

  const loadTipos = useCallback(async () => {
    try {
      setTipos(await api.getRequestTypes());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadTipos(); }, [loadTipos]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => {
      const next = { ...prev, [name]: type === 'checkbox' ? checked : value };
      // Mientras se escribe el nombre en un alta, el code se propone solo.
      // En edicion no se toca: cambiarlo dejaria los movimientos previos
      // apuntando a un code que ya no existe.
      if (!editingId && name === 'nombre' && !prev.codeTouched) {
        next.code = slugify(value);
      }
      return next;
    });
  };

  const handleCodeChange = (e) => {
    const value = e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-');
    setForm((prev) => ({ ...prev, code: value, codeTouched: true }));
  };

  const openNew = () => {
    setForm({ ...emptyForm });
    setEditingId(null);
    setShowForm(true);
    setError('');
  };

  const openEdit = (tipo) => {
    setForm({
      code: tipo.code,
      nombre: tipo.nombre,
      descripcion: tipo.descripcion || '',
      modo: tipo.modo,
      activo: tipo.activo,
      orden: tipo.orden ?? 0,
    });
    setEditingId(tipo.id);
    setShowForm(true);
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const payload = {
      code: form.code,
      nombre: form.nombre,
      descripcion: form.descripcion,
      modo: form.modo,
      activo: form.activo,
      orden: Number(form.orden) || 0,
    };
    try {
      editingId ? await api.updateRequestType(editingId, payload) : await api.createRequestType(payload);
      setShowForm(false);
      loadTipos();
    } catch (err) {
      setError(err.error || 'Error al guardar el tipo de solicitud');
    }
  };

  const toggleActive = async (tipo) => {
    try {
      await api.updateRequestType(tipo.id, { activo: !tipo.activo });
      loadTipos();
    } catch (err) {
      alert(err.error || 'Error al cambiar el estado');
    }
  };

  const handleDelete = async () => {
    if (!deletingTipo) return;
    try {
      await api.deleteRequestType(deletingTipo.id);
      setDeletingTipo(null);
      loadTipos();
    } catch (err) {
      alert(err.error || 'Error al eliminar el tipo de solicitud');
      setDeletingTipo(null);
    }
  };

  if (loading) return <p className="text-center text-slate-400 py-20">Cargando...</p>;

  const hasSelection = modoFilter !== 'all' || stateFilter !== 'all';

  // `applied` guarda lo que se ejecuto con Buscar, igual que en Planes:
  // cambiar un filtro no altera la tabla hasta volver a buscar.
  const filtered = !applied ? [] : tipos.filter((t) => {
    if (applied.modo !== 'all' && t.modo !== applied.modo) return false;
    if (applied.state === 'active' && !t.activo) return false;
    if (applied.state === 'inactive' && t.activo) return false;
    return true;
  });

  const handleSearch = () => {
    if (hasSelection) setApplied({ modo: modoFilter, state: stateFilter });
  };

  const clearFilters = () => {
    setModoFilter('all');
    setStateFilter('all');
    setApplied(null);
  };

  const modoCount = (value) => value === 'all' ? tipos.length : tipos.filter((t) => t.modo === value).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Tipos de Solicitud</h1>
          <p className="text-sm text-slate-400 mt-1">Catalogo de solicitudes disponibles</p>
        </div>
        <Button onClick={openNew}>+ Agregar Tipo</Button>
      </div>

      {/* Filtros */}
      <Card className="p-5 space-y-4">
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Modo</p>
          <div className="flex flex-wrap gap-2">
            {[{ value: 'all', label: 'Todos' }, ...MODOS].map((m) => (
              <Button
                key={m.value}
                variant={modoFilter === m.value ? 'primary' : 'secondary'}
                size="sm"
                onClick={() => setModoFilter(m.value)}
                aria-pressed={modoFilter === m.value}
              >
                {m.label} ({modoCount(m.value)})
              </Button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 items-end">
          <Select label="Estado" value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
            {STATE_FILTERS.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </Select>
          <div className="flex gap-3">
            <Button onClick={handleSearch} disabled={!hasSelection}>Buscar</Button>
            <Button variant="secondary" onClick={clearFilters}>Limpiar</Button>
          </div>
        </div>

        {!hasSelection && (
          <p className="text-xs text-slate-400">Selecciona al menos un filtro para buscar</p>
        )}
        {applied && (
          <p className="text-xs text-slate-500">
            Mostrando {filtered.length} de {tipos.length} tipos
          </p>
        )}
      </Card>

      {/* Confirmacion de borrado */}
      {deletingTipo && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setDeletingTipo(null)}>
          <Card className="w-full max-w-sm p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Eliminar tipo</h3>
                <p className="text-sm text-slate-500">Esta accion no se puede deshacer</p>
              </div>
            </div>
            <p className="text-sm text-slate-600">
              Seguro que deseas eliminar el tipo <strong>{deletingTipo.nombre}</strong> ({deletingTipo.code})?
            </p>
            <Alert type="info">
              Si ya tiene movimientos registrados no se podra borrar. En ese caso desactivalo para que
              deje de ofrecerse sin romper el historial.
            </Alert>
            <div className="flex gap-3 pt-2">
              <Button variant="danger" onClick={handleDelete}>Si, eliminar</Button>
              <Button variant="secondary" onClick={() => setDeletingTipo(null)}>Cancelar</Button>
            </div>
          </Card>
        </div>
      )}

      {/* Modal de alta / edicion */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowForm(false)}>
          <Card className="w-full max-w-lg p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-black text-slate-900">
              {editingId ? 'Editar Tipo de Solicitud' : 'Nuevo Tipo de Solicitud'}
            </h3>
            {error && <Alert type="error">{error}</Alert>}
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label={editingId ? 'Codigo' : 'Codigo *'}
                name="code"
                value={form.code}
                onChange={handleCodeChange}
                required
                placeholder="Ej: baja-temporal"
              />
              <Input label="Nombre *" name="nombre" value={form.nombre} onChange={handleChange} required placeholder="Ej: Baja temporal" />
              <Input
                label="Descripcion (opcional)"
                name="descripcion"
                value={form.descripcion}
                onChange={handleChange}
                placeholder="Que usa esta solicitud"
              />
              <Select label="Modo *" name="modo" value={form.modo} onChange={handleChange}>
                {MODOS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </Select>

              <div className="rounded-xl bg-amber-50 border border-amber-200 p-4 space-y-2">
                <p className="text-xs font-bold text-amber-800 uppercase tracking-wider">Como se cobra</p>
                <p className="text-xs text-amber-900 leading-relaxed">
                  {form.modo === 'simple' && 'Se cobra mensualidad + instalacion, igual que un nuevo contrato. Elige otro modo solo si el movimiento realmente no lleva instalacion.'}
                  {form.modo === 'nuevo' && 'Se cobra mensualidad + instalacion, y cuenta como instalacion en el dashboard.'}
                  {form.modo === 'retiro' && 'Solo cobra mensualidad, sin instalacion. Habilita los planes anteriores del catalogo y cuenta en el bloque de Retiros.'}
                  {form.modo === 'cambio_plan' && 'Solo cobra mensualidad. Obliga a registrar el plan anterior y su servicio, y muestra la conversion en los reportes.'}
                  {form.modo === 'adicion' && 'Solo cobra mensualidad. Obliga a indicar si se anade Internet o TV, y solo admite planes Combo.'}
                </p>
              </div>

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

      {/* Estado inicial: sin consulta ejecutada */}
      {!applied && (
        <Card className="p-12 text-center">
          <p className="text-sm text-slate-400">Selecciona un filtro y presiona Buscar para ver los tipos</p>
        </Card>
      )}

      {/* Sin coincidencias */}
      {applied && filtered.length === 0 && (
        <Card className="p-12 text-center space-y-3">
          <p className="text-sm font-semibold text-slate-700">No hay tipos que coincidan con los filtros</p>
          <p className="text-xs text-slate-400">Prueba con otra combinacion o restablece los filtros</p>
          <Button variant="secondary" onClick={clearFilters}>Limpiar filtros</Button>
        </Card>
      )}

      {/* Tabla de escritorio */}
      {applied && filtered.length > 0 && (
        <Card className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                {['Codigo', 'Nombre', 'Descripcion', 'Modo', 'Estado', ''].map((h) => (
                  <th key={h} className="text-left px-4 py-3.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filtered.map((t) => (
                <tr key={t.id} className={`hover:bg-brand-50/30 transition-colors ${!t.activo ? 'opacity-50' : ''}`}>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{t.code}</td>
                  <td className="px-4 py-3 font-medium text-slate-900">{t.nombre}</td>
                  <td className="px-4 py-3 text-slate-500">{t.descripcion || '-'}</td>
                  <td className="px-4 py-3"><Badge color={MODO_COLOR[t.modo] || 'slate'}>{MODO_LABEL[t.modo] || t.modo}</Badge></td>
                  <td className="px-4 py-3">
                    <Badge color={t.activo ? 'green' : 'slate'}>{t.activo ? 'Activo' : 'Inactivo'}</Badge>
                  </td>
                  <td className="px-4 py-3 space-x-1">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(t)}>Editar</Button>
                    <Button variant="danger" size="sm" onClick={() => setDeletingTipo(t)}>Eliminar</Button>
                    <Button variant={t.activo ? 'secondary' : 'success'} size="sm" onClick={() => toggleActive(t)}>
                      {t.activo ? 'Desactivar' : 'Activar'}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Tarjetas moviles */}
      {applied && filtered.length > 0 && (
        <div className="md:hidden space-y-3">
          {filtered.map((t) => (
            <Card key={t.id} className={`p-4 space-y-2 ${!t.activo ? 'opacity-50' : ''}`}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-slate-900">{t.nombre}</p>
                  <p className="text-xs text-slate-400 font-mono">{t.code}</p>
                </div>
                <div className="flex gap-1.5">
                  <Badge color={MODO_COLOR[t.modo] || 'slate'}>{MODO_LABEL[t.modo] || t.modo}</Badge>
                  <Badge color={t.activo ? 'green' : 'slate'}>{t.activo ? 'Activo' : 'Inactivo'}</Badge>
                </div>
              </div>
              {t.descripcion && <p className="text-sm text-slate-500">{t.descripcion}</p>}
              <div className="flex gap-2 pt-1">
                <Button variant="ghost" size="sm" onClick={() => openEdit(t)} className="flex-1">Editar</Button>
                <Button variant="danger" size="sm" onClick={() => setDeletingTipo(t)} className="flex-1">Eliminar</Button>
                <Button variant={t.activo ? 'secondary' : 'success'} size="sm" onClick={() => toggleActive(t)} className="flex-1">
                  {t.activo ? 'Desactivar' : 'Activar'}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}