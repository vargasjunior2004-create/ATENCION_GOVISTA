import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { MODULES } from '../../modules/registry';
import Brand from '../layout/Brand';
import AccountMenu from '../layout/AccountMenu';
import ModuleCard from './ModuleCard';

export default function ModuleSelector() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="gradient-sidebar border-b border-white/5">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between gap-4">
          <Brand subtitle="Portal de módulos" />
          <AccountMenu variant="header" />
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14">
        <div className="max-w-2xl">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
            Espacio de trabajo
          </p>
          <h1 className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight mt-2">
            Selecciona un módulo
          </h1>
          <p className="text-sm sm:text-base text-slate-500 mt-3 leading-relaxed">
            {user?.name ? `Bienvenido, ${user.name}. ` : ''}
            Accede a las áreas disponibles para tu cuenta.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 mt-10">
          {MODULES.map((module) => (
            <ModuleCard key={module.id} module={module} />
          ))}
        </div>

        <p className="text-xs text-slate-400 mt-8 max-w-xl leading-relaxed">
          Los módulos marcados como próximamente todavía no están habilitados.
          No contienen información ni operaciones disponibles.
        </p>
      </main>
    </div>
  );
}
