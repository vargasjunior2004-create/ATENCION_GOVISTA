import React, { useCallback, useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import useReducedMotion from '../../hooks/useReducedMotion';
import Brand from '../../components/layout/Brand';
import AccountMenu from '../../components/layout/AccountMenu';
import {
  commercialAdminNavigation,
  commercialNavigation,
  moduleReturnItem,
} from './navigation';

export default function ComercialLayout() {
  const { isAdmin } = useAuth();
  const reducedMotion = useReducedMotion();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarHover, setSidebarHover] = useState(false);

  const showSidebar = mobileOpen || sidebarHover;
  const closeMobile = useCallback(() => setMobileOpen(false), []);
  const transitionClass = reducedMotion ? '' : 'transition-all duration-300 ease-out';

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-xl transition-all duration-200 group
     ${isActive
       ? 'bg-vista-accent/15 text-vista-accent shadow-sm'
       : 'text-green-300/60 hover:bg-white/5 hover:text-white'}`;

  return (
    <div className="min-h-screen bg-slate-50">
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden" onClick={closeMobile} />
      )}

      <div
        className="hidden lg:block fixed top-0 left-0 bottom-0 w-3 z-[55]"
        onMouseEnter={() => setSidebarHover(true)}
        onMouseLeave={() => setSidebarHover(false)}
      />

      <aside
        onMouseEnter={() => setSidebarHover(true)}
        onMouseLeave={() => setSidebarHover(false)}
        className={`fixed top-0 left-0 bottom-0 w-64 gradient-sidebar z-50 flex flex-col
          ${transitionClass}
          ${showSidebar ? 'translate-x-0' : '-translate-x-full'}
          ${showSidebar && !reducedMotion ? 'shadow-2xl shadow-black/30' : ''}`}
      >
        <div className="px-5 py-6 border-b border-white/5">
          <Brand subtitle="Gestión Comercial" />
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <NavLink
            to={moduleReturnItem.to}
            end
            className={({ isActive }) => `${linkClass({ isActive })} mb-3 border border-white/10`}
            onClick={closeMobile}
          >
            <moduleReturnItem.icon className="w-5 h-5" />
            {moduleReturnItem.label}
          </NavLink>

          {commercialNavigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={linkClass}
              onClick={closeMobile}
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </NavLink>
          ))}

          {isAdmin && (
            <>
              <div className="pt-5 pb-2 px-4">
                <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-green-400/30">Administracion</span>
              </div>
              {commercialAdminNavigation.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={linkClass}
                  onClick={closeMobile}
                >
                  <item.icon className="w-5 h-5" />
                  {item.label}
                </NavLink>
              ))}
            </>
          )}
        </nav>

        <div className="px-4 py-4 border-t border-white/5">
          <AccountMenu variant="sidebar" />
        </div>
      </aside>

      <button
        type="button"
        onClick={() => setMobileOpen((open) => !open)}
        className="fixed top-4 left-4 z-50 lg:hidden bg-vista-sidebar text-white p-2.5 rounded-xl shadow-lg border border-white/10"
        aria-label={mobileOpen ? 'Cerrar menú' : 'Abrir menú'}
      >
        {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      <main className="min-h-screen" onClick={closeMobile}>
        <div className="p-4 sm:p-6 lg:p-8 pt-16 lg:pt-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
