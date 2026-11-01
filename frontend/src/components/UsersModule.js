import React, { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../services/api';
import { Alert, Badge, Button, Card, Input } from './ui';
import SecurityModule from '../modules/comercial/pages/SecurityModule';

const emptyUser = { name: '', password: '', roleIds: [] };

export default function UsersModule() {
  const [searchParams, setSearchParams] = useSearchParams();
  const section = searchParams.get('seccion') === 'seguridad'
    ? 'seguridad'
    : 'usuarios';
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...emptyUser });
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const loadUsers = useCallback(async () => {
    try {
      const [userData, roleData] = await Promise.all([
        api.getUsers(),
        api.getRoles(),
      ]);
      setUsers(userData);
      setRoles(roleData);
      setError('');
    } catch (err) {
      setError(err.error || 'No fue posible cargar usuarios y roles.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: name === 'name' ? value.toUpperCase() : value,
    }));
  };

  const openNew = () => {
    setForm({ ...emptyUser });
    setEditingId(null);
    setShowForm(true);
    setError('');
    setSuccess('');
  };

  const openEdit = (user) => {
    setForm({
      name: user.name,
      password: '',
      roleIds: (user.roles || [])
        .filter((role) => !role.is_system_role)
        .map((role) => role.id),
    });
    setEditingId(user.id);
    setShowForm(true);
    setError('');
    setSuccess('');
  };

  const toggleRole = (roleId) => {
    setForm((current) => ({
      ...current,
      roleIds: current.roleIds.includes(roleId)
        ? current.roleIds.filter((id) => id !== roleId)
        : [...current.roleIds, roleId],
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    if (!form.roleIds.length) {
      setError('Seleccione al menos un rol para la cuenta.');
      return;
    }
    if (!editingId && !form.password) {
      setError('La contraseña es requerida para nuevos usuarios.');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: form.name,
        roleIds: form.roleIds,
      };
      if (form.password) payload.password = form.password;
      if (editingId) {
        await api.updateUser(editingId, payload);
        setSuccess('Usuario y roles actualizados correctamente.');
      } else {
        await api.createUser(payload);
        setSuccess('Usuario creado con sus roles correctamente.');
      }
      setShowForm(false);
      await loadUsers();
    } catch (err) {
      setError(err.error || 'No fue posible guardar el usuario.');
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (user) => {
    setError('');
    setSuccess('');
    try {
      await api.updateUser(user.id, { active: !user.active });
      setSuccess(user.active ? 'Usuario desactivado.' : 'Usuario activado.');
      await loadUsers();
    } catch (err) {
      setError(err.error || 'No fue posible actualizar el usuario.');
    }
  };

  const editableRoles = roles.filter((role) => !role.is_system_role);

  if (loading) {
    return <p className="py-20 text-center text-slate-400">Cargando...</p>;
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-brand-600">
            Administración comercial
          </p>
          <h1 className="mt-2 text-2xl font-black tracking-tight text-slate-900">
            Usuarios y accesos
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Cuentas, roles y asignaciones temporales en un solo lugar.
          </p>
        </div>
        {section === 'usuarios' && (
          <Button onClick={openNew}>+ Agregar Usuario</Button>
        )}
      </header>

      <div
        className="flex gap-2 border-b border-slate-200"
        role="tablist"
        aria-label="Administración de usuarios"
      >
        {[
          { id: 'usuarios', label: 'Cuentas y roles' },
          { id: 'seguridad', label: 'Permisos y asignaciones' },
        ].map((tab) => (
          <button
            key={tab.id}
            id={`users-tab-${tab.id}`}
            type="button"
            role="tab"
            aria-selected={section === tab.id}
            aria-controls={`users-panel-${tab.id}`}
            onClick={() => setSearchParams(
              tab.id === 'usuarios' ? {} : { seccion: 'seguridad' },
            )}
            className={`-mb-px border-b-2 px-4 py-3 text-sm font-bold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600 ${
              section === tab.id
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {section === 'seguridad' ? (
        <div
          id="users-panel-seguridad"
          role="tabpanel"
          aria-labelledby="users-tab-seguridad"
        >
          <SecurityModule />
        </div>
      ) : (
        <section
          id="users-panel-usuarios"
          role="tabpanel"
          aria-labelledby="users-tab-usuarios"
          className="space-y-6"
        >
          {success && <Alert type="success">{success}</Alert>}
          {error && <Alert type="error">{error}</Alert>}

          {showForm && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/60 p-4 backdrop-blur-sm"
              onClick={() => setShowForm(false)}
            >
              <Card
                className="w-full max-w-lg space-y-4 p-6"
                onClick={(event) => event.stopPropagation()}
              >
                <div>
                  <h2 className="text-lg font-black text-slate-900">
                    {editingId
                      ? 'Editar usuario y roles'
                      : 'Crear usuario y asignar roles'}
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Los permisos de acceso se determinan por los roles seleccionados.
                  </p>
                </div>
                {error && <Alert type="error">{error}</Alert>}
                <form onSubmit={handleSubmit} className="space-y-4">
                  <Input
                    label="Nombre"
                    name="name"
                    value={form.name}
                    onChange={handleChange}
                    required
                  />
                  <Input
                    label={editingId
                      ? 'Nueva contraseña (dejar vacía para no cambiar)'
                      : 'Contraseña'}
                    name="password"
                    type="password"
                    value={form.password}
                    onChange={handleChange}
                    autoComplete="new-password"
                    {...(!editingId && { required: true })}
                  />
                  <fieldset className="space-y-2">
                    <legend className="text-sm font-semibold text-slate-700">
                      Roles de acceso
                    </legend>
                    {editableRoles.length === 0 ? (
                      <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                        No hay roles disponibles. Revise la sección Permisos y asignaciones.
                      </p>
                    ) : (
                      <div className="max-h-56 space-y-1 overflow-y-auto rounded-xl border border-slate-200 p-3">
                        {editableRoles.map((role) => (
                          <label
                            key={role.id}
                            className="flex cursor-pointer items-start gap-3 rounded-lg px-2 py-2 hover:bg-slate-50"
                          >
                            <input
                              type="checkbox"
                              checked={form.roleIds.includes(role.id)}
                              onChange={() => toggleRole(role.id)}
                              className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                            />
                            <span>
                              <span className="block text-sm font-bold text-slate-800">
                                {role.name}
                              </span>
                              <span className="block text-xs text-slate-500">
                                {role.description || role.code}
                              </span>
                            </span>
                          </label>
                        ))}
                      </div>
                    )}
                    <p className="text-xs text-slate-500">
                      Seleccione uno o varios roles. Las asignaciones se guardan junto con la cuenta.
                    </p>
                  </fieldset>
                  <div className="flex gap-3 pt-2">
                    <Button type="submit" disabled={saving || !editableRoles.length}>
                      {saving ? 'Guardando...' : 'Guardar'}
                    </Button>
                    <Button
                      variant="secondary"
                      type="button"
                      disabled={saving}
                      onClick={() => setShowForm(false)}
                    >
                      Cancelar
                    </Button>
                  </div>
                </form>
              </Card>
            </div>
          )}

          <Card className="hidden overflow-x-auto md:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  {['Nombre', 'Roles de acceso', 'Estado', ''].map((heading) => (
                    <th
                      key={heading}
                      className="px-5 py-3.5 text-left text-[11px] font-bold uppercase tracking-wider text-slate-400"
                    >
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {users.map((user) => (
                  <tr
                    key={user.id}
                    className={`transition-colors hover:bg-brand-50/30 ${!user.active ? 'opacity-50' : ''}`}
                  >
                    <td className="px-5 py-3.5 font-medium text-slate-900">
                      {user.name}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {(user.roles || []).length === 0 ? (
                          <Badge color="slate">Sin rol</Badge>
                        ) : user.roles.map((role) => (
                          <Badge
                            key={role.id}
                            color={role.is_system_role ? 'amber' : 'blue'}
                          >
                            {role.name}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge color={user.active ? 'green' : 'red'}>
                        {user.active ? 'Activo' : 'Inactivo'}
                      </Badge>
                    </td>
                    <td className="space-x-1 px-4 py-3">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEdit(user)}
                      >
                        Editar
                      </Button>
                      <Button
                        variant={user.active ? 'danger' : 'success'}
                        size="sm"
                        onClick={() => toggleActive(user)}
                      >
                        {user.active ? 'Desactivar' : 'Activar'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <div className="space-y-3 md:hidden">
            {users.map((user) => (
              <Card
                key={user.id}
                className={`space-y-3 p-4 ${!user.active ? 'opacity-50' : ''}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-slate-900">{user.name}</p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {(user.roles || []).length === 0 ? (
                        <Badge color="slate">Sin rol</Badge>
                      ) : user.roles.map((role) => (
                        <Badge
                          key={role.id}
                          color={role.is_system_role ? 'amber' : 'blue'}
                        >
                          {role.name}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <Badge color={user.active ? 'green' : 'red'}>
                    {user.active ? 'Activo' : 'Inactivo'}
                  </Badge>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => openEdit(user)}
                    className="flex-1"
                  >
                    Editar
                  </Button>
                  <Button
                    variant={user.active ? 'danger' : 'success'}
                    size="sm"
                    onClick={() => toggleActive(user)}
                    className="flex-1"
                  >
                    {user.active ? 'Desactivar' : 'Activar'}
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
