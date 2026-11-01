import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import Login from '../components/Login';
import ModuleSelector from '../components/modules/ModuleSelector';
import BackupModule from '../components/BackupModule';
import MotivosModule from '../components/MotivosModule';
import PlansModule from '../components/PlansModule';
import PromotionsModule from '../components/PromotionsModule';
import UsersModule from '../components/UsersModule';
import ComercialLayout from '../modules/comercial/ComercialLayout';
import Dashboard from '../modules/comercial/pages/Dashboard';
import SaleForm from '../modules/comercial/pages/SaleForm';
import SalesList from '../modules/comercial/pages/SalesList';
import CustomersList from '../modules/comercial/pages/CustomersList';
import CustomerDetail from '../modules/comercial/pages/CustomerDetail';
import ContractDetail from '../modules/comercial/pages/ContractDetail';
import TransferTariffs from '../modules/comercial/pages/TransferTariffs';
import { AdminRoute, ProtectedRoute, PublicRoute } from './guards';
import LegacyRedirect from './LegacyRedirect';
import EquipmentPage from '../modules/equipos/EquipmentPage';

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicRoute />}>
        <Route path="/login" element={<Login />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<ModuleSelector />} />
        <Route path="/equipos" element={<EquipmentPage />} />

        <Route path="/comercial" element={<ComercialLayout />}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="solicitudes" element={<SalesList />} />
          <Route path="solicitudes/nueva" element={<SaleForm />} />
          <Route path="clientes" element={<CustomersList />} />
          <Route path="clientes/:id" element={<CustomerDetail />} />
          <Route path="clientes/:id/contratos/:contractId" element={<ContractDetail />} />

          <Route
            path="planes"
            element={<AdminRoute permission="commercial_config.manage"><PlansModule /></AdminRoute>}
          />
          <Route
            path="motivos"
            element={<AdminRoute permission="commercial_config.manage"><MotivosModule /></AdminRoute>}
          />
          <Route
            path="promociones"
            element={<AdminRoute permission="commercial_config.manage"><PromotionsModule /></AdminRoute>}
          />
          <Route
            path="usuarios"
            element={<AdminRoute permission="users.manage"><UsersModule /></AdminRoute>}
          />
          <Route path="backups" element={<AdminRoute><BackupModule /></AdminRoute>} />
          <Route
            path="tarifas-traslados"
            element={<AdminRoute permission="commercial_config.manage"><TransferTariffs /></AdminRoute>}
          />
          <Route
            path="seguridad"
            element={(
              <AdminRoute permission="users.manage">
                <Navigate to="/comercial/usuarios?seccion=seguridad" replace />
              </AdminRoute>
            )}
          />
        </Route>

        <Route path="/nueva-venta" element={<LegacyRedirect to="/comercial/solicitudes/nueva" />} />
        <Route path="/ventas" element={<LegacyRedirect to="/comercial/solicitudes" />} />
        <Route path="/planes" element={<LegacyRedirect to="/comercial/planes" />} />
        <Route path="/motivos" element={<LegacyRedirect to="/comercial/motivos" />} />
        <Route path="/promociones" element={<LegacyRedirect to="/comercial/promociones" />} />
        <Route path="/usuarios" element={<LegacyRedirect to="/comercial/usuarios" />} />
        <Route path="/backups" element={<LegacyRedirect to="/comercial/backups" />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
