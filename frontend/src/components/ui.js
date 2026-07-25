import React from 'react';

const variants = {
  primary: 'bg-brand-700 hover:bg-brand-800 text-white shadow-sm',
  success: 'bg-green-600 hover:bg-green-700 text-white shadow-sm',
  danger: 'bg-red-600 hover:bg-red-700 text-white shadow-sm',
  secondary: 'bg-slate-200 hover:bg-slate-300 text-slate-700',
  ghost: 'bg-transparent hover:bg-slate-100 text-slate-600',
};

const sizes = {
  sm: 'px-2.5 py-1 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
};

export function Button({ variant = 'primary', size = 'md', children, className = '', ...props }) {
  return (
    <button
      className={`inline-flex items-center justify-center font-medium rounded-lg transition-colors
        focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Input({ label, error, className = '', ...props }) {
  return (
    <div className="space-y-1">
      {label && <label className="block text-sm font-semibold text-slate-700">{label}</label>}
      <input
        className={`w-full px-4 py-3 text-base border rounded-lg bg-white text-slate-900
          placeholder-slate-400 transition-colors
          focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500
          ${error ? 'border-red-400 focus:ring-red-500 focus:border-red-500' : 'border-slate-300'}
          ${className}`}
        {...props}
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

export function Select({ label, error, children, className = '', ...props }) {
  return (
    <div className="space-y-1">
      {label && <label className="block text-sm font-semibold text-slate-700">{label}</label>}
      <select
        className={`w-full px-4 py-3 text-base border rounded-lg bg-white text-slate-900
          transition-colors appearance-none
          focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500
          ${error ? 'border-red-400' : 'border-slate-300'}
          ${className}`}
        {...props}
      >
        {children}
      </select>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

export function Alert({ type = 'error', children }) {
  const styles = {
    error: 'bg-red-50 text-red-700 border border-red-200',
    success: 'bg-green-50 text-green-700 border border-green-200',
    info: 'bg-blue-50 text-blue-700 border border-blue-200',
  };
  return (
    <div className={`px-4 py-3 rounded-lg text-sm font-medium ${styles[type]}`}>
      {children}
    </div>
  );
}

export function Badge({ color = 'slate', children, className = '' }) {
  const colors = {
    blue: 'bg-blue-100 text-blue-800',
    amber: 'bg-amber-100 text-amber-800',
    violet: 'bg-violet-100 text-violet-800',
    green: 'bg-green-100 text-green-800',
    red: 'bg-red-100 text-red-800',
    slate: 'bg-slate-200 text-slate-600',
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${colors[color]} ${className}`}>
      {children}
    </span>
  );
}

export function Card({ children, className = '', ...props }) {
  return (
    <div className={`bg-white rounded-xl border border-slate-200 shadow-sm ${className}`} {...props}>
      {children}
    </div>
  );
}

export function TotalDisplay({ value, label = 'Total' }) {
  return (
    <div className="flex items-baseline justify-between py-1">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-lg font-bold text-green-700 tabular-nums">{parseFloat(value).toFixed(2)} Bs</span>
    </div>
  );
}
