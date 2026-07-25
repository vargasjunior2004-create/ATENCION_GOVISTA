import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './components/Login';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import SaleForm from './components/SaleForm';
import SalesList from './components/SalesList';
import PlansModule from './components/PlansModule';
import UsersModule from './components/UsersModule';
import CashCountModule from './components/CashCountModule';

function ProtectedRoute() {
  const { token } = useAuth();
  return token ? <Outlet /> : <Navigate to="/login" replace />;
}

function AdminRoute() {
  const { isAdmin } = useAuth();
  return isAdmin ? <Outlet /> : <Navigate to="/" replace />;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/nueva-venta" element={<SaleForm />} />
              <Route path="/ventas" element={<SalesList />} />
              <Route path="/arqueo" element={<CashCountModule />} />
              <Route element={<AdminRoute />}>
                <Route path="/planes" element={<PlansModule />} />
                <Route path="/usuarios" element={<UsersModule />} />
              </Route>
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
