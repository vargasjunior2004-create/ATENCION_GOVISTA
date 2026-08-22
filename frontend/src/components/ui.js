import React from 'react';

const variants = {
  primary: 'bg-gradient-to-r from-brand-700 to-brand-600 hover:from-brand-800 hover:to-brand-700 text-white shadow-sm btn-glow',
  success: 'bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-700 hover:to-emerald-600 text-white shadow-sm',
  danger: 'bg-gradient-to-r from-red-600 to-red-500 hover:from-red-700 hover:to-red-600 text-white shadow-sm',
  secondary: 'bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200',
  ghost: 'bg-transparent hover:bg-slate-50 text-slate-600',
};

const sizes = {
  sm: 'px-3 py-1.5 text-xs font-semibold rounded-lg',
  md: 'px-4 py-2.5 text-sm font-semibold rounded-xl',
  lg: 'px-6 py-3 text-sm font-semibold rounded-xl',
};

export function Button({ variant = 'primary', size = 'md', children, className = '', ...props }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 transition-all duration-200
        focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:ring-offset-2
        disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none
        ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Input({ label, error, className = '', ...props }) {
  return (
    <div className="space-y-1.5">
      {label && <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</label>}
      <input
        className={`w-full px-4 py-3 text-sm border-0 rounded-xl bg-slate-50 text-slate-900
          placeholder-slate-400 transition-all duration-200
          focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:bg-white
          ${error ? 'ring-2 ring-red-400/40 bg-red-50' : ''}
          ${className}`}
        {...props}
      />
      {error && <p className="text-xs text-red-500 font-medium">{error}</p>}
    </div>
  );
}

export function Select({ label, error, children, className = '', ...props }) {
  return (
    <div className="space-y-1.5">
      {label && <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</label>}
      <select
        className={`w-full px-4 py-3 text-sm border-0 rounded-xl bg-slate-50 text-slate-900
          transition-all duration-200 appearance-none cursor-pointer
          focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:bg-white
          ${error ? 'ring-2 ring-red-400/40 bg-red-50' : ''}
          ${className}`}
        {...props}
      >
        {children}
      </select>
      {error && <p className="text-xs text-red-500 font-medium">{error}</p>}
    </div>
  );
}

export function Alert({ type = 'error', children }) {
  const styles = {
    error: 'bg-red-50 text-red-700 border border-red-200/60',
    success: 'bg-emerald-50 text-emerald-700 border border-emerald-200/60',
    info: 'bg-blue-50 text-blue-700 border border-blue-200/60',
  };
  return (
    <div className={`px-4 py-3 rounded-xl text-sm font-medium ${styles[type]}`}>
      {children}
    </div>
  );
}

export function Badge({ color = 'slate', children, className = '' }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200/50',
    amber: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200/50',
    violet: 'bg-violet-50 text-violet-700 ring-1 ring-violet-200/50',
    green: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/50',
    red: 'bg-red-50 text-red-700 ring-1 ring-red-200/50',
    slate: 'bg-slate-100 text-slate-600 ring-1 ring-slate-200/50',
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider ${colors[color]} ${className}`}>
      {children}
    </span>
  );
}

export function Card({ children, className = '', ...props }) {
  return (
    <div className={`card-modern ${className}`} {...props}>
      {children}
    </div>
  );
}

export function TotalDisplay({ value, label = 'Total' }) {
  return (
    <div className="flex items-baseline justify-between py-1">
      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</span>
      <span className="text-lg font-extrabold text-brand-700 tabular-nums">{parseFloat(value).toFixed(2)} Bs</span>
    </div>
  );
}
