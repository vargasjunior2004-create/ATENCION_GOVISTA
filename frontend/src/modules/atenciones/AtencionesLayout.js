import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { BarChart3, ClipboardList, Headphones, Plus } from 'lucide-react';
import AtencionesErrorBoundary from './AtencionesErrorBoundary';

const navigation = [
  { to: '/atenciones/dashboard', label: 'Dashboard', icon: BarChart3 },
  { to: '/atenciones/listado', label: 'Atenciones', icon: ClipboardList },
  { to: '/atenciones/registrar', label: 'Registrar atención', icon: Plus },
];

export default function AtencionesLayout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-5 px-4 py-4 sm:px-6">
          <div className="mr-auto flex items-center gap-3">
            <Headphones className="h-6 w-6 text-brand-600" />
            <div>
              <p className="text-xs font-black uppercase tracking-[0.18em] text-brand-600">GO VISTA</p>
              <h1 className="font-black text-slate-900">Gestión de atenciones</h1>
            </div>
          </div>
          <nav className="flex gap-1">
            {navigation.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} className={({ isActive }) => (
                `flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-bold ${
                  isActive ? 'bg-brand-50 text-brand-700' : 'text-slate-500 hover:bg-slate-50'
                }`
              )}>
                <Icon className="h-4 w-4" /> <span className="hidden sm:inline">{label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <AtencionesErrorBoundary><Outlet /></AtencionesErrorBoundary>
      </main>
    </div>
  );
}
