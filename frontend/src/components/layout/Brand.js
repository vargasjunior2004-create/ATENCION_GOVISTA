import React from 'react';

export default function Brand({ subtitle = 'Gestión Comercial', className = '' }) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div className="w-9 h-9 rounded-xl bg-vista-accent/15 flex items-center justify-center shrink-0">
        <svg className="w-5 h-5 text-vista-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
        </svg>
      </div>
      <div className="min-w-0">
        <h2 className="text-lg font-black text-white tracking-tight leading-none">
          GO<span className="text-vista-accent">VISTA</span>
        </h2>
        {subtitle && (
          <p className="text-[10px] text-green-400/40 font-medium uppercase tracking-wider mt-1 truncate">
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
