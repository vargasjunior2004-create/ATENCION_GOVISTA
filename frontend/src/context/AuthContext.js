import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import api, { setOnAuthExpired } from '../services/api';

const AuthContext = createContext(null);

const INACTIVITY_TIMEOUT = 3 * 60 * 1000; // 3 minutos

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });

  const logoutTimer = useRef(null);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    if (logoutTimer.current) clearTimeout(logoutTimer.current);
  }, []);

  useEffect(() => {
    setOnAuthExpired(logout);
    return () => setOnAuthExpired(null);
  }, [logout]);

  const resetTimer = useCallback(() => {
    if (logoutTimer.current) clearTimeout(logoutTimer.current);
    logoutTimer.current = setTimeout(logout, INACTIVITY_TIMEOUT);
  }, [logout]);

  useEffect(() => {
    if (!user) return;

    const events = ['click'];
    events.forEach(e => document.addEventListener(e, resetTimer, { passive: true }));
    resetTimer();

    return () => {
      if (logoutTimer.current) clearTimeout(logoutTimer.current);
      events.forEach(e => document.removeEventListener(e, resetTimer));
    };
  }, [user, resetTimer]);

  const login = async (name, password) => {
    const data = await api.login(name, password);
    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    setUser(data.user);
    return data;
  };

  const value = {
    user,
    token: localStorage.getItem('token'),
    login,
    logout,
    isAdmin: user?.role === 'admin',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider');
  return ctx;
}
