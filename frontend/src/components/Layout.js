import React, { useState, useCallback, useEffect } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Badge, Button } from './ui';

const navItems = [
  { to: '/', label: 'Dashboard', icon: '□', end: true },
  { to: '/nueva-venta', label: 'Nueva Venta', icon: '+' },
  { to: '/ventas', label: 'Ventas', icon: '≡' },
  { to: '/arqueo', label: 'Arqueo de Caja', icon: '$' },
];

const adminItems = [
  { to: '/planes', label: 'Planes', icon: '★' },
  { to: '/usuarios', label: 'Usuarios', icon: '☺' },
];

function useReducedMotion() {
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handler = (e) => setReduced(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);
  return reduced;
}

export default function Layout() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const reducedMotion = useReducedMotion();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [edgeHover, setEdgeHover] = useState(false);
  const [sidebarPinned, setSidebarPinned] = useState(false);

  const sidebarVisible = edgeHover || sidebarPinned;
  const showSidebar = mobileOpen || sidebarVisible;

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const closeMobile = useCallback(() => setMobileOpen(false), []);

  const handleSidebarFocusIn = useCallback(() => setSidebarPinned(true), []);
  const handleSidebarFocusOut = useCallback((e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setSidebarPinned(false);
    }
  }, []);

  const handleEdgeEnter = useCallback(() => setEdgeHover(true), []);
  const handleEdgeLeave = useCallback(() => setEdgeHover(false), []);
  const handleSidebarEnter = useCallback(() => setSidebarPinned(true), []);
  const handleSidebarLeave = useCallback(() => setSidebarPinned(false), []);

  const transitionClass = reducedMotion
    ? ''
    : 'transition-transform duration-200 ease-out';

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-lg transition-colors
     ${isActive
       ? 'bg-white/15 text-white'
       : 'text-green-200 hover:bg-white/10 hover:text-white'}`;

  return (
    <div className="min-h-screen bg-green-50">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={closeMobile} />
      )}

      {/* Desktop edge hover trigger — invisible strip on the left edge */}
      <div
        className="hidden lg:block fixed top-0 left-0 bottom-0 w-4 z-[55]"
        onMouseEnter={handleEdgeEnter}
        onMouseLeave={handleEdgeLeave}
      />

      {/* Sidebar */}
      <aside
        onMouseEnter={handleSidebarEnter}
        onMouseLeave={handleSidebarLeave}
        onFocus={handleSidebarFocusIn}
        onBlur={handleSidebarFocusOut}
        className={`fixed top-0 left-0 bottom-0 w-64 bg-green-900 z-50 flex flex-col
          ${transitionClass}
          ${showSidebar ? 'translate-x-0' : '-translate-x-full'}
          ${showSidebar && !reducedMotion ? 'shadow-xl' : ''}`}
      >
        <div className="px-5 py-5 border-b border-white/10">
          <h2 className="text-lg font-bold text-white">SaleStracker</h2>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={linkClass} onClick={closeMobile}>
              <span className="w-5 text-center text-base">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
          {isAdmin && (
            <>
              <div className="pt-3 pb-1 px-4">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-green-400/80">Admin</span>
              </div>
              {adminItems.map((item) => (
                <NavLink key={item.to} to={item.to} className={linkClass} onClick={closeMobile}>
                  <span className="w-5 text-center text-base">{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
            </>
          )}
        </nav>

        <div className="px-4 py-4 border-t border-white/10">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-sm text-white font-medium truncate">{user?.name}</span>
            <Badge color={user?.role === 'admin' ? 'amber' : 'blue'} className="text-[10px]">{user?.role}</Badge>
          </div>
          <Button variant="danger" size="sm" className="w-full" onClick={handleLogout}>
            Cerrar sesion
          </Button>
        </div>
      </aside>

      {/* Mobile menu button */}
      <button onClick={() => setMobileOpen(!mobileOpen)}
        className="fixed top-3 left-3 z-50 lg:hidden bg-green-900 text-white p-2 rounded-lg shadow-lg">
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Main content */}
      <main className="min-h-screen" onClick={closeMobile}>
        <div className="p-4 sm:p-6 lg:p-8 pt-14 lg:pt-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
