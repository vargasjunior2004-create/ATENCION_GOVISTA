import React from 'react';
import { Card } from '../../components/ui';
import { useAuth } from '../../context/AuthContext';
import AccountMenu from '../../components/layout/AccountMenu';

export default function ProfilePage() {
  const { user } = useAuth();
  return <div className="mx-auto max-w-2xl space-y-5"><header><p className="text-xs font-black uppercase tracking-[0.18em] text-brand-600">Mi Perfil</p><h1 className="mt-2 text-2xl font-black text-slate-900">Datos de acceso</h1></header><Card className="space-y-4 p-5"><p className="text-sm text-slate-500">Usuario</p><p className="text-lg font-black text-slate-900">{user?.name}</p><p className="text-sm text-slate-500">Usa el menú de cuenta para cambiar tu contraseña o cerrar sesión.</p><AccountMenu variant="header" /></Card></div>;
}
