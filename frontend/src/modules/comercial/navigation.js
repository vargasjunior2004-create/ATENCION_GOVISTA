import {
  Database,
  FilePlus2,
  History,
  LayoutDashboard,
  LayoutGrid,
  Package,
  Percent,
  Tag,
  Users,
} from 'lucide-react';

export const moduleReturnItem = {
  to: '/',
  label: 'Volver a módulos',
  icon: LayoutGrid,
};

export const commercialNavigation = [
  {
    to: '/comercial/dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    end: true,
  },
  {
    to: '/comercial/solicitudes/nueva',
    label: 'Registrar Solicitud',
    icon: FilePlus2,
    end: true,
  },
  {
    to: '/comercial/solicitudes',
    label: 'Historial de Solicitudes',
    icon: History,
    end: true,
  },
];

export const commercialAdminNavigation = [
  {
    to: '/comercial/planes',
    label: 'Planes',
    icon: Package,
  },
  {
    to: '/comercial/motivos',
    label: 'Motivos',
    icon: Tag,
  },
  {
    to: '/comercial/promociones',
    label: 'Promociones',
    icon: Percent,
  },
  {
    to: '/comercial/usuarios',
    label: 'Usuarios',
    icon: Users,
  },
  {
    to: '/comercial/backups',
    label: 'Copias de Seguridad',
    icon: Database,
  },
];
