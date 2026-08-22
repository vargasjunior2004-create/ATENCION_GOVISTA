import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button, Input, Alert } from './ui';

export default function Login() {
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(name, password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.error || 'Error al iniciar sesion');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex gradient-sidebar">
      {/* Left panel - brand */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden items-center justify-center">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-900 via-vista-dark to-vista-sidebar" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-vista-accent/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-vista-accent/5 rounded-full blur-3xl" />
        <div className="relative z-10 text-center px-12">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-vista-accent/10 mb-8">
            <svg className="w-10 h-10 text-vista-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
            </svg>
          </div>
          <h1 className="text-5xl font-black text-white tracking-tight mb-4">
            GO<span className="text-vista-accent">VISTA</span>
          </h1>
          <p className="text-green-300/70 text-lg font-medium">
            Planilla de Ventas Diaria
          </p>
          <p className="text-green-400/40 text-sm mt-2">
            Telecomunicaciones Bolivia
          </p>
        </div>
      </div>

      {/* Right panel - form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          {/* Mobile brand */}
          <div className="lg:hidden text-center mb-10">
            <h1 className="text-4xl font-black text-white tracking-tight mb-2">
              GO<span className="text-vista-accent">VISTA</span>
            </h1>
            <p className="text-green-300/60 text-sm">Planilla de Ventas Diaria</p>
          </div>

          <div className="bg-white/5 backdrop-blur-xl rounded-3xl p-8 border border-white/10 shadow-2xl">
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-white mb-2">Bienvenido</h2>
              <p className="text-green-300/50 text-sm">Ingresa a tu cuenta para continuar</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 text-red-300 px-4 py-3 rounded-xl text-sm font-medium">
                  {error}
                </div>
              )}
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-green-300/60 uppercase tracking-wider">Usuario</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  autoFocus
                  placeholder="Tu nombre de usuario"
                  className="w-full px-4 py-3.5 text-sm bg-white/5 border-0 rounded-xl text-white placeholder-green-300/30 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-vista-accent/30 focus:bg-white/10"
                />
              </div>
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-green-300/60 uppercase tracking-wider">Contrasena</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="Ingresa tu contrasena"
                  className="w-full px-4 py-3.5 text-sm bg-white/5 border-0 rounded-xl text-white placeholder-green-300/30 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-vista-accent/30 focus:bg-white/10"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 bg-gradient-to-r from-vista-accent to-emerald-500 hover:from-vista-accent/90 hover:to-emerald-600 text-vista-dark font-bold text-sm rounded-xl transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-vista-accent/20"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/></svg>
                    Ingresando...
                  </span>
                ) : 'Ingresar'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
