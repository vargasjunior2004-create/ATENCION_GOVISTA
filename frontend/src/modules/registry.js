import { Briefcase, Headphones, MapPinned, Router } from 'lucide-react';

export const MODULES = [
  {
    id: 'comercial',
    name: 'Gestión Comercial',
    description: 'Solicitudes comerciales, contratos, cambios de plan y reportes.',
    icon: Briefcase,
    to: '/comercial',
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
