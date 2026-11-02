import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import AccountMenu from '../../components/layout/AccountMenu';
import Brand from '../../components/layout/Brand';

const linkClass = ({ isActive }) => (
  `rounded-xl px-4 py-2.5 text-sm font-bold transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500/40 ${
    isActive
      ? 'bg-brand-700 text-white shadow-sm'
      : 'text-slate-600 hover:bg-brand-50 hover:text-brand-800'
  }`
);

export default function CoverageLayout() {
  const { hasPermission } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="gradient-sidebar border-b border-white/5">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-5 sm:px-6 lg:px-8">
          <Brand subtitle="Gestión de cobertura" />
          <AccountMenu variant="header" />
        </div>
      </header>
      <nav
        aria-label="Navegación de cobertura"
        className="border-b border-slate-200 bg-white"
      >
        <div className="mx-auto flex max-w-6xl flex-wrap gap-2 px-4 py-3 sm:px-6 lg:px-8">
          <NavLink end to="/cobertura" className={linkClass}>
            Panel principal
          </NavLink>
          <NavLink to="/cobertura/consultar" className={linkClass}>
            Consultar cobertura
          </NavLink>
          {hasPermission('coverage.create') && (
            <NavLink to="/cobertura/registrar" className={linkClass}>
              Registrar zona
            </NavLink>
          )}
        </div>
      </nav>
      <Outlet />
    </div>
  );
}
