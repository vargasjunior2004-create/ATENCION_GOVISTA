import React, { useEffect, useState } from 'react';
import { ShieldCheck, UserPlus, XCircle } from 'lucide-react';
import api from '../../../services/api';
import { Alert, Badge, Button, Card, Input, Select } from '../../../components/ui';

export default function SecurityModule() {
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [users, setUsers] = useState([]);
  const [functions, setFunctions] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [form, setForm] = useState({ user: '', function: '', starts_at: '', ends_at: '', notes: '' });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const [roleData, permissionData, userData, functionData, assignmentData] = await Promise.all([
        api.getRoles(), api.getPermissions(), api.getUsers(), api.getTemporaryFunctions(), api.getTemporaryAssignments(),
      ]);
      setRoles(roleData); setPermissions(permissionData); setUsers(userData); setFunctions(functionData); setAssignments(assignmentData);
    } catch (err) { setError(err?.error || 'No fue posible cargar la configuración de seguridad.'); }
  };
  useEffect(() => { load(); }, []);

  const createAssignment = async (event) => {
    event.preventDefault(); setMessage(''); setError('');
    try {
      await api.createTemporaryAssignment(form);
      setForm({ user: '', function: '', starts_at: '', ends_at: '', notes: '' });
      setMessage('Función temporal asignada correctamente.'); load();
    } catch (err) { setError(err?.error || 'No fue posible asignar la función.'); }
  };

  const finish = async (id, status) => {
    try { await api.finishTemporaryAssignment(id, status); setMessage(status === 'finished' ? 'Asignación finalizada.' : 'Asignación revocada.'); load(); }
    catch (err) { setError(err?.error || 'No fue posible actualizar la asignación.'); }
  };

  return <div className="space-y-6"><header><p className="text-xs font-black uppercase tracking-[0.18em] text-brand-600">Administración</p><h1 className="mt-2 text-3xl font-black text-slate-900">Roles, permisos y funciones</h1><p className="mt-1 text-sm text-slate-500">La autorización se valida en el backend; esta pantalla solo administra la configuración.</p></header>{message && <Alert type="success">{message}</Alert>}{error && <Alert type="error">{error}</Alert>}<section className="grid gap-4 lg:grid-cols-2"><Card className="p-5"><div className="flex items-center gap-3"><ShieldCheck className="h-6 w-6 text-brand-600" /><div><h2 className="font-black text-slate-900">Roles permanentes</h2><p className="text-xs text-slate-500">{roles.length} roles configurados · {permissions.length} permisos disponibles</p></div></div><div className="mt-4 space-y-3">{roles.map((role) => <div key={role.id} className="rounded-xl border border-slate-200 p-3"><div className="flex items-center justify-between gap-3"><p className="font-bold text-slate-800">{role.name}</p><Badge color={role.is_system_role ? 'amber' : 'blue'}>{role.is_system_role ? 'Total' : `${role.permissions.length} permisos`}</Badge></div><p className="mt-1 text-xs text-slate-500">{role.description || role.code}</p></div>)}</div></Card><Card className="p-5"><div className="flex items-center gap-3"><UserPlus className="h-6 w-6 text-brand-600" /><div><h2 className="font-black text-slate-900">Asignar vendedor externo</h2><p className="text-xs text-slate-500">La función no cambia el cargo permanente.</p></div></div><form onSubmit={createAssignment} className="mt-4 space-y-3"><Select label="Trabajador" value={form.user} onChange={(e) => setForm({ ...form, user: e.target.value })} required><option value="">Seleccionar...</option>{users.filter((user) => user.active).map((user) => <option key={user.id} value={user.id}>{user.name}</option>)}</Select><Select label="Función" value={form.function} onChange={(e) => setForm({ ...form, function: e.target.value })} required><option value="">Seleccionar...</option>{functions.map((fn) => <option key={fn.id} value={fn.id}>{fn.name}</option>)}</Select><div className="grid gap-3 sm:grid-cols-2"><Input label="Inicio" type="datetime-local" value={form.starts_at} onChange={(e) => setForm({ ...form, starts_at: e.target.value })} required /><Input label="Fin previsto" type="datetime-local" value={form.ends_at} onChange={(e) => setForm({ ...form, ends_at: e.target.value })} required /></div><Input label="Observaciones" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /><Button type="submit">Asignar función</Button></form></Card></section><Card className="p-5"><h2 className="font-black text-slate-900">Historial de asignaciones temporales</h2><div className="mt-4 space-y-3">{assignments.length === 0 ? <p className="text-sm text-slate-500">No hay asignaciones registradas.</p> : assignments.map((assignment) => <div key={assignment.id} className="flex flex-col gap-3 rounded-xl border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-bold text-slate-800">{assignment.userName} · {assignment.functionName}</p><p className="text-xs text-slate-500">{new Date(assignment.starts_at).toLocaleString('es-BO')} — {new Date(assignment.ends_at).toLocaleString('es-BO')}</p><p className="text-xs text-slate-400">Asignó: {assignment.assignedByName || '—'}</p></div><div className="flex items-center gap-2"><Badge color={assignment.status === 'active' ? 'green' : 'slate'}>{assignment.status}</Badge>{['scheduled', 'active'].includes(assignment.status) && <><Button size="sm" variant="success" onClick={() => finish(assignment.id, 'finished')}>Finalizar</Button><Button size="sm" variant="danger" onClick={() => finish(assignment.id, 'revoked')}><XCircle className="h-4 w-4" /> Revocar</Button></>}</div></div>)}</div></Card></div>;
}
