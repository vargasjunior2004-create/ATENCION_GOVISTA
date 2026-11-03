import React, { useCallback, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { ClipboardList, Database, KeyRound, Menu, ShieldCheck, Users, X } from 'lucide-react';
import Brand from '../../components/layout/Brand';
import AccountMenu from '../../components/layout/AccountMenu';
import { moduleReturnItem } from '../comercial/navigation';

const navigation = [
  { to: '/administracion/usuarios', label: 'Usuarios', icon: Users },
  { to: '/administracion/roles', label: 'Roles y permisos', icon: KeyRound },
  { to: '/administracion/auditoria', label: 'Auditoría', icon: ClipboardList },
  { to: '/administracion/respaldos', label: 'Respaldos', icon: Database },
  { to: '/administracion/seguridad', label: 'Seguridad', icon: ShieldCheck },
];

export default function AdministracionLayout() {
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  const linkClass = ({ isActive }) => `flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-xl ${isActive ? 'bg-vista-accent/15 text-vista-accent' : 'text-green-300/60 hover:bg-white/5 hover:text-white'}`;

  return (
    <div className="min-h-screen bg-slate-50">
      {open && <div className="fixed inset-0 bg-black/60 z-40 lg:hidden" onClick={close} />}
      <aside className={`fixed top-0 left-0 bottom-0 w-64 gradient-sidebar z-50 flex flex-col transition-transform duration-300 ${open ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}>
        <div className="px-5 py-6 border-b border-white/5"><Brand subtitle="Administración del Sistema" /></div>
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <NavLink to={moduleReturnItem.to} end className={({ isActive }) => `${linkClass({ isActive })} mb-3 border border-white/10`} onClick={close}>
            <moduleReturnItem.icon className="w-5 h-5" />{moduleReturnItem.label}
          </NavLink>
          {navigation.map((item) => <NavLink key={item.to} to={item.to} className={linkClass} onClick={close}>
            <item.icon className="w-5 h-5" />{item.label}
          </NavLink>)}
        </nav>
        <div className="px-4 py-4 border-t border-white/5"><AccountMenu variant="sidebar" /></div>
      </aside>
      <button type="button" onClick={() => setOpen((value) => !value)} className="fixed top-4 left-4 z-50 lg:hidden bg-vista-sidebar text-white p-2.5 rounded-xl" aria-label="Abrir menú">
        {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>
      <main className="min-h-screen lg:pl-64" onClick={close}><div className="p-4 sm:p-6 lg:p-8 pt-16 lg:pt-8"><Outlet /></div></main>
    </div>
  );
}
