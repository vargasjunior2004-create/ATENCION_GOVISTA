import React from 'react';
import { MapPin, Menu, UserRound, X, LogOut } from 'lucide-react';
import { Link, NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Brand from '../../components/layout/Brand';

export default function UbicacionesLayout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = React.useState(false);
  const links = [
    { to: '/ubicaciones', label: 'Inicio', icon: MapPin, end: true },
    { to: '/ubicaciones/registrar', label: 'Ubicación de Clientes', icon: MapPin },
    { to: '/ubicaciones/perfil', label: 'Mi Perfil', icon: UserRound },
  ];
  return <div className="min-h-screen bg-slate-50"><aside className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-vista-sidebar p-4 text-white transition-transform ${open ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}><Link to="/" onClick={() => setOpen(false)} aria-label="Volver al inicio" className="rounded-xl outline-none focus:ring-2 focus:ring-vista-accent/70"><Brand subtitle="Técnico de Campo" /></Link><nav className="mt-8 space-y-2">{links.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={() => setOpen(false)} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold ${isActive ? 'bg-white/15 text-white' : 'text-green-200/70 hover:bg-white/10'}`}><Icon className="h-5 w-5" />{label}</NavLink>)}</nav><button type="button" onClick={logout} className="mt-auto flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold text-green-200/70 hover:bg-white/10"><LogOut className="h-5 w-5" />Cerrar sesión</button><p className="mt-4 px-4 text-xs text-green-200/50">{user?.name}</p></aside><button type="button" onClick={() => setOpen(!open)} className="fixed left-4 top-4 z-40 rounded-xl bg-vista-sidebar p-3 text-white lg:hidden" aria-label="Abrir menú">{open ? <X /> : <Menu />}</button><main className="min-h-screen lg:pl-72"><div className="p-4 pt-20 sm:p-6 sm:pt-20 lg:p-8"><Outlet /></div></main></div>;
}
