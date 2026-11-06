import { Briefcase, Headphones, MapPinned, Router, ShieldCheck, MapPin } from 'lucide-react';

export const MODULES = [
  {
    id: 'ubicaciones',
    name: 'Ubicación de Clientes',
    description: 'Fotografías de fachada y ubicación de domicilios.',
    icon: MapPin,
    to: '/ubicaciones',
    permission: 'ubicaciones.clientes.view',
    status: 'available',
  },
  {
    id: 'comercial',
    name: 'Gestión Comercial',
    description: 'Solicitudes comerciales, contratos, cambios de plan y reportes.',
    icon: Briefcase,
    to: '/comercial',
    permission: 'comercial.view',
    status: 'available',
  },
  {
    id: 'administracion',
    name: 'Administración del Sistema',
    description: 'Usuarios, roles, auditoría, respaldos y seguridad.',
    icon: ShieldCheck,
    to: '/administracion',
    permission: 'sistema.acceso.view',
    status: 'available',
  },
  {
    id: 'cobertura',
    name: 'Cobertura',
    description: 'Mapa general, consulta y registro de zonas.',
    icon: MapPinned,
    to: '/cobertura',
    permission: 'coverage.view',
    status: 'available',
  },
  {
    id: 'atencion',
    name: 'Gestion operativa',
    description: 'Tickets, atenciones, quejas, reclamos y acciones de soporte.',
    icon: Headphones,
    status: 'soon',
  },
  {
    id: 'equipos',
    name: 'Gestión de Equipos',
    description: 'Inventario, equipos instalados en clientes, cambios e historial.',
    icon: Router,
    status: 'soon',
  },
];
