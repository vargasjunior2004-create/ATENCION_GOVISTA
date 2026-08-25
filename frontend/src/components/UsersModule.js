import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Button, Input, Select, Card, Alert, Badge } from './ui';

const emptyUser = { name: '', email: '', password: '', role: 'ventas' };

export default function UsersModule() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...emptyUser });
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState('');

  const loadUsers = useCallback(async () => {
    try { setUsers(await api.getUsers()); } catch (err) { console.error(err); } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    const UPPERCASE_FIELDS = ['name'];
    const finalValue = UPPERCASE_FIELDS.includes(name) ? value.toUpperCase() : value;
    setForm((p) => ({ ...p, [name]: finalValue }));
  };

  const openNew = () => { setForm({ ...emptyUser }); setEditingId(null); setShowForm(true); setError(''); };
  const openEdit = (user) => {
    setForm({ name: user.name, email: user.email, password: '', role: user.role });
    setEditingId(user.id); setShowForm(true); setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault(); setError('');
    try {
      const payload = { name: form.name, email: form.email, role: form.role };
      if (form.password) payload.password = form.password;
      if (editingId) {
        await api.updateUser(editingId, payload);
      } else {
        if (!form.password) { setError('La contrasena es requerida para nuevos usuarios'); return; }
        await api.createUser({ ...payload, password: form.password });
      }
      setShowForm(false); loadUsers();
    } catch (err) { setError(err.error || 'Error al guardar usuario'); }
  };

  const toggleActive = async (user) => {
    try { await api.updateUser(user.id, { active: !user.active }); loadUsers(); } catch (err) { alert(err.error || 'Error'); }
  };

  if (loading) return <p className="text-center text-slate-400 py-20">Cargando...</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Usuarios</h1>
          <p className="text-sm text-slate-400 mt-1">Gestion de cuentas de usuario</p>
        </div>
        <Button onClick={openNew}>+ Agregar Usuario</Button>
      </div>

      {/* Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setShowForm(false)}>
          <Card className="w-full max-w-lg p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-black text-slate-900">{editingId ? 'Editar Usuario' : 'Nuevo Usuario'}</h3>
            {error && <Alert type="error">{error}</Alert>}
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input label="Nombre" name="name" value={form.name} onChange={handleChange} required />
              <Input label="Email" name="email" type="email" value={form.email} onChange={handleChange} required />
              <Input
                label={editingId ? 'Nueva contrasena (dejar vacio para no cambiar)' : 'Contrasena (unica por usuario)'}
                name="password" type="password" value={form.password} onChange={handleChange}
                placeholder="Debe ser unica para cada usuario"
                {...(!editingId && { required: true })}
              />
              <Select label="Rol" name="role" value={form.role} onChange={handleChange}>
                <option value="ventas">Movimientos</option>
                <option value="admin">Administrador</option>
              </Select>
              <div className="flex gap-3 pt-2">
                <Button type="submit">Guardar</Button>
                <Button variant="secondary" type="button" onClick={() => setShowForm(false)}>Cancelar</Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Desktop table */}
      <Card className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              {['Nombre', 'Email', 'Rol', 'Estado', ''].map((h) => (
                <th key={h} className="text-left px-5 py-3.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {users.map((u) => (
              <tr key={u.id} className={`hover:bg-brand-50/30 transition-colors ${!u.active ? 'opacity-50' : ''}`}>
                <td className="px-5 py-3.5 font-medium text-slate-900">{u.name}</td>
                <td className="px-5 py-3.5 text-slate-500">{u.email}</td>
                <td className="px-4 py-3"><Badge color={u.role === 'admin' ? 'amber' : 'blue'}>{u.role}</Badge></td>
                <td className="px-4 py-3">
                  <Badge color={u.active ? 'green' : 'red'}>{u.active ? 'Activo' : 'Inactivo'}</Badge>
                </td>
                <td className="px-4 py-3 space-x-1">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(u)}>Editar</Button>
                  <Button variant={u.active ? 'danger' : 'success'} size="sm" onClick={() => toggleActive(u)}>
                    {u.active ? 'Desactivar' : 'Activar'}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Mobile cards */}
      <div className="md:hidden space-y-3">
        {users.map((u) => (
          <Card key={u.id} className={`p-4 space-y-2 ${!u.active ? 'opacity-50' : ''}`}>
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-slate-900">{u.name}</p>
                <p className="text-sm text-slate-500">{u.email}</p>
              </div>
              <div className="flex gap-1.5">
                <Badge color={u.role === 'admin' ? 'amber' : 'blue'}>{u.role}</Badge>
                <Badge color={u.active ? 'green' : 'red'}>{u.active ? 'Activo' : 'Inactivo'}</Badge>
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <Button variant="ghost" size="sm" onClick={() => openEdit(u)} className="flex-1">Editar</Button>
              <Button variant={u.active ? 'danger' : 'success'} size="sm" onClick={() => toggleActive(u)} className="flex-1">
                {u.active ? 'Desactivar' : 'Activar'}
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
