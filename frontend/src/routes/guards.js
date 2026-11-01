import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function SessionLoader() {
  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="flex items-center gap-3 text-sm font-medium text-slate-500" role="status">
        <span className="h-5 w-5 rounded-full border-2 border-blue-200 border-t-blue-600 animate-spin" />
        Verificando la sesión...
      </div>
    </main>
  );
}

export function PublicRoute() {
  const { token, sessionReady } = useAuth();

  if (!sessionReady) return <SessionLoader />;
  return token ? <Navigate to="/" replace /> : <Outlet />;
}

export function ProtectedRoute() {
  const { token, sessionReady } = useAuth();

  if (!sessionReady) return <SessionLoader />;
  return token ? <Outlet /> : <Navigate to="/login" replace />;
}

export function AdminRoute({ permission, children }) {
  const { isAdmin, hasPermission } = useAuth();
  const allowed = permission ? hasPermission(permission) : isAdmin;
  return allowed
    ? (children || <Outlet />)
    : <Navigate to="/comercial/dashboard" replace />;
}
