import React, { useCallback, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { BarChart3, ClipboardList, Headphones, Menu, Plus, X } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import useReducedMotion from '../../hooks/useReducedMotion';
import Brand from '../../components/layout/Brand';
import AccountMenu from '../../components/layout/AccountMenu';
import AtencionesErrorBoundary from './AtencionesErrorBoundary';

const navigation = [
  { to: '/atenciones/dashboard', label: 'Dashboard', icon: BarChart3, end: true },
  { to: '/atenciones/listado', label: 'Atenciones', icon: ClipboardList, end: true },
  { to: '/atenciones/registrar', label: 'Registrar atención', icon: Plus, end: true },
];

export default function AtencionesLayout() {
  const { isAdmin } = useAuth();
  const reducedMotion = useReducedMotion();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarHover, setSidebarHover] = useState(false);
  const showSidebar = mobileOpen || sidebarHover;
  const closeMobile = useCallback(() => setMobileOpen(false), []);
  const transitionClass = reducedMotion ? '' : 'transition-all duration-300 ease-out';

  const linkClass = ({ isActive }) => (
    `flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-200 group ${
      isActive
        ? 'bg-vista-accent/15 text-vista-accent shadow-sm'
        : 'text-green-300/60 hover:bg-white/5 hover:text-white'
    }`
  );

  return (
    <div className="min-h-screen bg-slate-50">
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={closeMobile}
          role="presentation"
        />
      )}

      <div
        className="fixed bottom-0 left-0 top-0 z-[55] hidden w-3 lg:block"
        onMouseEnter={() => setSidebarHover(true)}
        onMouseLeave={() => setSidebarHover(false)}
      />

      <aside
        onMouseEnter={() => setSidebarHover(true)}
        onMouseLeave={() => setSidebarHover(false)}
        className={`fixed bottom-0 left-0 top-0 z-50 flex w-64 flex-col gradient-sidebar ${
          transitionClass
        } ${showSidebar ? 'translate-x-0' : '-translate-x-full'} ${
          showSidebar && !reducedMotion ? 'shadow-2xl shadow-black/30' : ''
        }`}
      >
        <div className="border-b border-white/5 px-5 py-6">
          <Brand subtitle="Gestión de Atenciones" />
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `${linkClass({ isActive })} mb-3 border border-white/10`}
            onClick={closeMobile}
          >
            <Headphones className="h-5 w-5" />
            Volver a módulos
          </NavLink>
          {navigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={linkClass} onClick={closeMobile}>
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          ))}
          {isAdmin && (
            <p className="px-4 pt-5 text-[10px] font-bold uppercase tracking-[0.15em] text-green-400/30">
              Administración disponible desde el módulo correspondiente
            </p>
          )}
        </nav>

        <div className="border-t border-white/5 px-4 py-4">
          <AccountMenu variant="sidebar" />
        </div>
      </aside>

      <button
        type="button"
        onClick={() => setMobileOpen((open) => !open)}
        className="fixed left-4 top-4 z-50 rounded-xl border border-white/10 bg-vista-sidebar p-2.5 text-white shadow-lg lg:hidden"
        aria-label={mobileOpen ? 'Cerrar menú' : 'Abrir menú'}
      >
        {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      <main className="min-h-screen" onClick={closeMobile}>
        <div className="p-4 pt-16 sm:p-6 lg:p-8 lg:pt-8">
          <AtencionesErrorBoundary><Outlet /></AtencionesErrorBoundary>
        </div>
      </main>
    </div>
  );
}
