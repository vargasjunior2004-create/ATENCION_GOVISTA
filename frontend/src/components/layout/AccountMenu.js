import React, { useCallback, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, KeyRound, LogOut } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../ui';
import ChangePasswordModal from './ChangePasswordModal';

export default function AccountMenu({ variant = 'sidebar' }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);

  const closePassword = useCallback(() => setPasswordOpen(false), []);
  const isSidebar = variant === 'sidebar';
  const roleLabel = user?.roles?.map((role) => role.name).join(' · ')
    || (user?.role === 'admin' ? 'ADMINISTRADOR' : 'OPERADOR');
  const roleColor = user?.isSystemAdmin || user?.role === 'admin' ? 'amber' : 'blue';

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
    navigate('/login', { replace: true });
  };

  const openPassword = () => {
    setMenuOpen(false);
    setPasswordOpen(true);
  };

  const menuItems = (
    <>
      <button
        type="button"
        onClick={openPassword}
        className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
      >
        <KeyRound className="w-4 h-4" />
        Cambiar Contrasena
      </button>
      <div className="border-t border-slate-100 my-1" />
      <button
        type="button"
        onClick={handleLogout}
        className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 transition-colors"
      >
        <LogOut className="w-4 h-4" />
        Cerrar Sesion
      </button>
    </>
  );

  return (
    <div className={`relative ${isSidebar ? '' : 'shrink-0'}`}>
      <button
        type="button"
        onClick={() => setMenuOpen((open) => !open)}
        className={isSidebar
          ? 'w-full flex items-center gap-3 mb-3 p-1 -m-1 rounded-xl hover:bg-white/5 transition-colors'
          : 'flex items-center gap-2 sm:gap-3 p-1.5 sm:px-2 rounded-xl hover:bg-white/10 transition-colors'}
        aria-expanded={menuOpen}
        aria-haspopup="menu"
      >
        <div className="w-8 h-8 rounded-lg bg-vista-accent/15 flex items-center justify-center text-vista-accent text-xs font-bold shrink-0">
          {user?.name?.charAt(0) || '?'}
        </div>
        {isSidebar ? (
          <div className="flex-1 min-w-0 text-left">
            <p className="text-sm text-white font-medium truncate">{user?.name}</p>
            <Badge color={roleColor} className="text-[9px] mt-0.5">{roleLabel}</Badge>
          </div>
        ) : (
          <div className="hidden sm:block text-left">
            <p className="text-sm text-white font-medium truncate max-w-[150px]">{user?.name}</p>
            <p className="text-[9px] text-green-300/50 font-bold uppercase tracking-wider">{roleLabel}</p>
          </div>
        )}
        <ChevronDown className={`w-4 h-4 transition-transform ${isSidebar ? 'text-white/40' : 'text-green-300/50'} ${menuOpen ? 'rotate-180' : ''}`} />
      </button>

      {menuOpen && (
        <div
          role="menu"
          className={`absolute bg-white rounded-xl shadow-xl border border-slate-100 py-1 z-50
            ${isSidebar ? 'bottom-full left-0 right-0 mb-2' : 'right-0 top-full mt-2 w-56'}`}
        >
          {menuItems}
        </div>
      )}

      {createPortal(
        <ChangePasswordModal open={passwordOpen} onClose={closePassword} />,
        document.body
      )}
    </div>
  );
}
