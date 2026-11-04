import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import Login from '../components/Login';
import ModuleSelector from '../components/modules/ModuleSelector';
import CanalesCaptacionModule from '../components/CanalesCaptacionModule';
import MotivosModule from '../components/MotivosModule';
import PlansModule from '../components/PlansModule';
import PromotionsModule from '../components/PromotionsModule';
import ComercialLayout from '../modules/comercial/ComercialLayout';
import Dashboard from '../modules/comercial/pages/Dashboard';
import SaleForm from '../modules/comercial/pages/SaleForm';
import SalesList from '../modules/comercial/pages/SalesList';
import CustomersList from '../modules/comercial/pages/CustomersList';
import CustomerDetail from '../modules/comercial/pages/CustomerDetail';
import ContractDetail from '../modules/comercial/pages/ContractDetail';
import TransferTariffs from '../modules/comercial/pages/TransferTariffs';
import CoverageLayout from '../modules/cobertura/CoverageLayout';
import CoverageDashboard from '../modules/cobertura/pages/CoverageDashboard';
import CoverageZones from '../modules/cobertura/pages/CoverageZones';
import RegisterCoverageZone from '../modules/cobertura/pages/RegisterCoverageZone';
import { AdminRoute, ProtectedRoute, PublicRoute } from './guards';
import LegacyRedirect from './LegacyRedirect';
import EquipmentPage from '../modules/equipos/EquipmentPage';
import AdministracionLayout from '../modules/administracion/AdministracionLayout';
import UsersPage from '../modules/administracion/pages/UsersPage';
import RolesPage from '../modules/administracion/pages/RolesPage';
import AuditPage from '../modules/administracion/pages/AuditPage';
import BackupsPage from '../modules/administracion/pages/BackupsPage';
import SecurityPage from '../modules/administracion/pages/SecurityPage';

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicRoute />}>
        <Route path="/login" element={<Login />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<ModuleSelector />} />
        <Route path="/equipos" element={<EquipmentPage />} />
        <Route path="/administracion" element={<AdminRoute permission="sistema.acceso.view"><AdministracionLayout /></AdminRoute>}>
          <Route index element={<Navigate to="usuarios" replace />} />
          <Route path="usuarios" element={<AdminRoute permission="usuarios.accounts.view"><UsersPage /></AdminRoute>} />
          <Route path="roles" element={<AdminRoute permission="roles.roles.view"><RolesPage /></AdminRoute>} />
          <Route path="auditoria" element={<AdminRoute permission="auditoria.eventos.view"><AuditPage /></AdminRoute>} />
          <Route path="respaldos" element={<AdminRoute permission="respaldos.backups.view"><BackupsPage /></AdminRoute>} />
          <Route path="seguridad" element={<AdminRoute permission="seguridad.politicas.view"><SecurityPage /></AdminRoute>} />
        </Route>
        <Route
          path="/cobertura"
          element={<AdminRoute permission="coverage.view"><CoverageLayout /></AdminRoute>}
        >
          <Route index element={<CoverageDashboard />} />
          <Route path="consultar" element={<CoverageZones />} />
          <Route
            path="registrar"
            element={<AdminRoute permission="coverage.create"><RegisterCoverageZone /></AdminRoute>}
          />
        </Route>
        <Route
          path="/cobertura/zonas"
          element={<LegacyRedirect to="/cobertura/consultar" />}
        />

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
            path="canales-captacion"
            element={<AdminRoute permission="captacion.manage"><CanalesCaptacionModule /></AdminRoute>}
          />
          <Route
            path="promociones"
            element={<AdminRoute permission="commercial_config.manage"><PromotionsModule /></AdminRoute>}
          />
          <Route
            path="tarifas-traslados"
            element={<AdminRoute permission="commercial_config.manage"><TransferTariffs /></AdminRoute>}
          />
        </Route>

        <Route path="/nueva-venta" element={<LegacyRedirect to="/comercial/solicitudes/nueva" />} />
        <Route path="/ventas" element={<LegacyRedirect to="/comercial/solicitudes" />} />
        <Route path="/planes" element={<LegacyRedirect to="/comercial/planes" />} />
        <Route path="/motivos" element={<LegacyRedirect to="/comercial/motivos" />} />
        <Route path="/canales-captacion" element={<LegacyRedirect to="/comercial/canales-captacion" />} />
        <Route path="/promociones" element={<LegacyRedirect to="/comercial/promociones" />} />
        <Route path="/usuarios" element={<LegacyRedirect to="/administracion/usuarios" />} />
        <Route path="/backups" element={<LegacyRedirect to="/administracion/respaldos" />} />
        <Route
          path="/comercial/cobertura/zonas"
          element={<LegacyRedirect to="/cobertura/consultar" />}
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
