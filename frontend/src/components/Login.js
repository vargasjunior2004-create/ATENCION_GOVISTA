import React, { useState } from 'react';
import { AlertCircle, ArrowRight, Eye, EyeOff, Loader2, RadioTower } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(name, password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.error || 'No se pudo iniciar sesión. Revisa tus datos e inténtalo nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 lg:grid lg:grid-cols-[minmax(0,1.08fr)_minmax(420px,0.92fr)]">
      <section className="relative hidden min-h-screen overflow-hidden bg-[#0b1f33] text-white lg:flex">
        <div className="absolute inset-y-0 right-0 w-px bg-blue-300/20" aria-hidden="true" />
        <div className="absolute right-16 top-1/2 -translate-y-1/2 opacity-40" aria-hidden="true">
          <div className="flex items-end gap-2">
            <span className="h-12 w-1 rounded-full bg-blue-300/30" />
            <span className="h-20 w-1 rounded-full bg-blue-300/50" />
            <span className="h-32 w-1 rounded-full bg-blue-300/80" />
            <span className="h-24 w-1 rounded-full bg-blue-300/60" />
            <span className="h-16 w-1 rounded-full bg-blue-300/40" />
          </div>
          <div className="mt-3 h-px w-40 bg-blue-200/40" />
        </div>

        <div className="relative z-10 flex w-full flex-col justify-between p-10 xl:p-14">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-blue-300/25 bg-blue-300/10">
              <RadioTower className="h-5 w-5 text-blue-300" aria-hidden="true" />
            </div>
            <div>
              <p className="text-lg font-black tracking-tight">GO VISTA</p>
              <p className="mt-1 text-[10px] font-bold uppercase tracking-[0.22em] text-blue-200/60">
                Portal de Gestión
              </p>
            </div>
          </div>

          <div className="max-w-xl py-16">
            <p className="mb-5 text-xs font-bold uppercase tracking-[0.24em] text-blue-300">
              Operación conectada
            </p>
            <h1 className="max-w-lg text-4xl font-semibold leading-tight tracking-[-0.03em] text-white xl:text-5xl">
              Una vista clara para cada solicitud.
            </h1>
            <p className="mt-6 max-w-md text-base leading-7 text-blue-100/65">
              Gestión comercial y atención al cliente en un solo lugar, con la información que tu equipo necesita para avanzar.
            </p>
          </div>

          <div className="flex items-center gap-3 text-xs font-medium text-blue-100/45">
            <span className="h-2 w-2 rounded-full bg-blue-400" aria-hidden="true" />
            <span>GO VISTA / COBIJA, BOLIVIA</span>
          </div>
        </div>
      </section>

      <main className="flex min-h-screen items-center justify-center px-5 py-10 sm:px-8 lg:px-12">
        <div className="w-full max-w-md">
          <div className="mb-10 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm">
              <RadioTower className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-lg font-black tracking-tight text-slate-950">GO VISTA</p>
              <p className="mt-1 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">
                Portal de Gestión
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-7 shadow-[0_18px_45px_rgba(15,23,42,0.07)] sm:p-9">
            <div className="mb-8">
              <p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-blue-700">
                Acceso al portal
              </p>
              <h2 className="text-3xl font-semibold tracking-[-0.03em] text-slate-950">
                Iniciar sesión
              </h2>
              <p className="mt-3 text-sm leading-6 text-slate-500">
                Ingresa con tu nombre de usuario para continuar.
              </p>
            </div>

            {error && (
              <div
                className="mb-5 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm leading-5 text-red-700"
                role="alert"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5" aria-busy={loading}>
              <div>
                <label htmlFor="login-name" className="mb-2 block text-sm font-semibold text-slate-700">
                  Nombre de usuario
                </label>
                <input
                  id="login-name"
                  name="name"
                  type="text"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  autoComplete="username"
                  required
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3.5 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10"
                  placeholder="Escribe tu usuario"
                />
              </div>

              <div>
                <label htmlFor="login-password" className="mb-2 block text-sm font-semibold text-slate-700">
                  Contraseña
                </label>
                <div className="relative">
                  <input
                    id="login-password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    autoComplete="current-password"
                    required
                    className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3.5 pr-12 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10"
                    placeholder="Escribe tu contraseña"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((visible) => !visible)}
                    className="absolute inset-y-0 right-0 flex w-12 items-center justify-center rounded-r-xl text-slate-400 transition hover:text-slate-700 focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-500/15"
                    aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                    aria-pressed={showPassword}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3.5 text-sm font-bold text-white shadow-sm transition hover:bg-blue-700 focus:outline-none focus-visible:ring-4 focus-visible:ring-blue-500/20 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Ingresando...
                  </>
                ) : (
                  <>
                    Ingresar
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </>
                )}
              </button>
            </form>

            <p className="mt-8 border-t border-slate-100 pt-5 text-center text-xs leading-5 text-slate-400">
              Acceso protegido para usuarios autorizados de GO VISTA.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
