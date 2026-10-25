import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Clock } from 'lucide-react';

export default function ModuleCard({ module }) {
  const Icon = module.icon;
  const available = module.status === 'available';

  const content = (
    <>
      <div className="flex items-start justify-between gap-4">
        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center
          ${available ? 'bg-brand-50 text-brand-700' : 'bg-slate-100 text-slate-400'}`}
        >
          <Icon className="w-7 h-7" />
        </div>
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider
          ${available
            ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/60'
            : 'bg-slate-100 text-slate-500 ring-1 ring-slate-200/60'}`}
        >
          {available ? 'Disponible' : <><Clock className="w-3 h-3" /> Próximamente</>}
        </span>
      </div>

      <div className="mt-6">
        <h2 className={`text-lg font-bold tracking-tight ${available ? 'text-slate-900' : 'text-slate-500'}`}>
          {module.name}
        </h2>
        <p className="text-sm text-slate-500 mt-2 leading-relaxed">
          {module.description}
        </p>
      </div>

      <div className={`mt-6 pt-4 border-t flex items-center justify-between text-sm font-semibold
        ${available ? 'border-slate-100 text-brand-700' : 'border-slate-100 text-slate-400'}`}
      >
        <span>{available ? 'Entrar al módulo' : 'Disponible próximamente'}</span>
        {available && <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />}
      </div>
    </>
  );

  if (!available) {
    return (
      <div
        aria-disabled="true"
        className="card-modern p-6 flex flex-col h-full bg-white/70 border-dashed cursor-not-allowed"
      >
        {content}
      </div>
    );
  }

  return (
    <Link
      to={module.to}
      className="card-modern p-6 flex flex-col h-full group hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-brand-500/40"
    >
      {content}
    </Link>
  );
}
