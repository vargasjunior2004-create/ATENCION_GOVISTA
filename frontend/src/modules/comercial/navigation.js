import {
  Database,
  FilePlus2,
  History,
  LayoutDashboard,
  LayoutGrid,
  Package,
  Percent,
  Tag,
  SlidersHorizontal,
  Users,
  UserRoundSearch,
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
  {
    to: '/comercial/clientes',
    label: 'Clientes',
    icon: UserRoundSearch,
    end: true,
  },
];

export const commercialAdminNavigation = [
  {
    to: '/comercial/planes',
    label: 'Planes',
    icon: Package,
    permission: 'commercial_config.manage',
  },
  {
    to: '/comercial/motivos',
    label: 'Motivos',
    icon: Tag,
    permission: 'commercial_config.manage',
  },
  {
    to: '/comercial/promociones',
    label: 'Promociones',
    icon: Percent,
    permission: 'commercial_config.manage',
  },
  {
    to: '/comercial/usuarios',
    label: 'Usuarios',
    icon: Users,
    permission: 'users.manage',
  },
  {
    to: '/comercial/backups',
    label: 'Copias de Seguridad',
    icon: Database,
  },
  {
    to: '/comercial/tarifas-traslados',
    label: 'Tarifas de traslados',
    icon: SlidersHorizontal,
    permission: 'commercial_config.manage',
  },
];
