import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  CalendarDays,
  Download,
  FileText,
  Filter,
  Image,
  LayoutDashboard,
  RefreshCw,
  ShieldCheck,
  SlidersHorizontal,
  TrendingUp,
  CalendarClock,
  ClipboardList,
  Clock3,
  UserCheck,
  UserRound,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import api from '../../../services/api';
import { Alert, Button, Card, Input, Select } from '../../../components/ui';
import { useAuth } from '../../../context/AuthContext';
import DashboardDrilldownModal from '../components/DashboardDrilldownModal';

const MOVEMENT_OPTIONS = [
  { value: 'all', label: 'Todas las solicitudes comerciales' },
  { value: 'nuevo_contrato', label: 'Nuevos contratos' },
  { value: 'recontrataciones', label: 'Recontrataciones' },
  { value: 'retiros', label: 'Retiros' },
  { value: 'cambios_plan', label: 'Cambios de plan' },
  { value: 'adiciones', label: 'Adiciones' },
  { value: 'traslados', label: 'Traslado Externo' },
];

const PERIOD_OPTIONS = [
  ['today', 'Hoy'],
  ['week', 'Esta semana'],
  ['month', 'Este mes'],
  ['custom', 'Rango personalizado'],
];

const PLAN_COLORS = ['#fb923c', '#06b6d4', '#84cc16', '#f472b6', '#a78bfa'];
const CHANNEL_COLORS = ['#0e7490', '#7c3aed', '#ea580c', '#16a34a', '#db2777', '#2563eb'];
const SERVICE_COLORS = {
  internet: '#0e7490',
  tv: '#ca8a04',
  tv_digital: '#2563eb',
  combo_analog: '#f9f508',
  combo_digital: '#a10785',
};

function todayInBolivia() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/La_Paz',
  }).format(new Date());
}

function calendarDate(value) {
  const [year, month, day] = value.split('-').map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

function formatCalendarDate(value) {
  return value.toISOString().slice(0, 10);
}

function getPresetRange(period) {
  const today = todayInBolivia();
  const current = calendarDate(today);

  if (period === 'today') return { from: today, to: today };
  if (period === 'week') {
    const mondayOffset = (current.getUTCDay() + 6) % 7;
    current.setUTCDate(current.getUTCDate() - mondayOffset);
    return { from: formatCalendarDate(current), to: today };
  }
  current.setUTCDate(1);
  return { from: formatCalendarDate(current), to: today };
}

function readableDate(value) {
  if (!value) return '';
  const [year, month, day] = value.split('-');
  return `${day}/${month}/${year}`;
}

function readableShortDate(value) {
  if (!value) return '';
  const [, month, day] = value.split('-');
  return `${day}/${month}`;
}

function number(value) {
  return Number(value || 0).toLocaleString('es-BO');
}

function money(value) {
  return Number(value || 0).toLocaleString('es-BO', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-xl">
      <p className="mb-1 text-[11px] font-bold uppercase tracking-wider text-slate-400">
        {readableDate(label) || label}
      </p>
      {payload.map((item) => (
        <div key={item.dataKey} className="flex items-center justify-between gap-5 text-xs">
          <span className="text-slate-500">{item.name}</span>
          <strong className="tabular-nums text-slate-800">{number(item.value)}</strong>
        </div>
      ))}
    </div>
  );
}

function EmptyChart({ message = 'No hay solicitudes comerciales en este período' }) {
  return (
    <div className="flex h-[280px] items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-6 text-center">
      <div>
        <Activity className="mx-auto mb-3 h-7 w-7 text-slate-300" strokeWidth={1.5} />
        <p className="text-sm font-semibold text-slate-500">{message}</p>
        <p className="mt-1 text-xs text-slate-400">Prueba otro período o filtro.</p>
      </div>
    </div>
  );
}

function MetricCard({ label, count, total, icon: Icon, tone, detail, onClick }) {
  const tones = {
    green: 'border-brand-200 bg-brand-50/60 text-brand-700',
    red: 'border-red-200 bg-red-50/70 text-red-700',
    blue: 'border-blue-200 bg-blue-50/70 text-blue-700',
    violet: 'border-violet-200 bg-violet-50/70 text-violet-700',
    slate: 'border-slate-200 bg-slate-50 text-slate-700',
  };
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Consultar ${label.toLowerCase()}: ${number(count)} registros`}
      className="card-modern group relative w-full cursor-pointer appearance-none overflow-hidden p-5 text-left transition-shadow hover:border-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
    >
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">{label}</p>
          <p className="mt-3 text-3xl font-black tracking-tight text-slate-900">{number(count)}</p>
        </div>
        <div className={`rounded-2xl border p-3 ${tones[tone]}`}>
          <Icon className="h-5 w-5" strokeWidth={1.8} />
        </div>
      </div>
      {total !== undefined ? (
        <div className="flex items-center justify-between border-t border-slate-100 pt-3">
          <span className="text-xs font-medium text-slate-400">Importe registrado</span>
          <span className="text-sm font-bold tabular-nums text-slate-700">{money(total)} Bs</span>
        </div>
      ) : (
        <p className="border-t border-slate-100 pt-3 text-xs font-medium text-slate-400">{detail}</p>
      )}
    </button>
  );
}

function ChartCard({ eyebrow, title, children, className = '' }) {
  return (
    <Card className={`p-5 sm:p-6 ${className}`}>
      <div className="mb-5">
        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-brand-600">{eyebrow}</p>
        <h2 className="mt-1 text-lg font-black tracking-tight text-slate-900">{title}</h2>
      </div>
      {children}
    </Card>
  );
}

function ProductivityTable({ items, title, onClose, loading }) {
  return (
    <div className="mt-6 border-t border-slate-100 pt-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="text-base font-black tracking-tight text-slate-900">{title}</h3>
        {onClose && (
          <button type="button" onClick={onClose} className="text-xs font-bold text-brand-700 hover:text-brand-900">
            Cerrar detalle
          </button>
        )}
      </div>
      {loading ? <p className="text-sm text-slate-400">Cargando solicitudes...</p> : items.length ? (
        <div className="overflow-x-auto rounded-xl border border-slate-100">
          <table className="w-full min-w-[720px] text-left text-xs">
            <thead className="bg-slate-50 text-[10px] font-black uppercase tracking-wider text-slate-400">
              <tr>
                <th className="px-4 py-3">Fecha y hora</th>
                <th className="px-4 py-3">Cliente</th>
                <th className="px-4 py-3">Tipo de solicitud</th>
                <th className="px-4 py-3">Plan o servicio</th>
                <th className="px-4 py-3">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {items.map((item) => (
                <tr key={item.id} className="text-slate-600 transition-colors hover:bg-brand-50/30">
                  <td className="whitespace-nowrap px-4 py-3 font-medium">{item.createdAt ? new Date(item.createdAt).toLocaleString('es-BO') : item.date || '—'}</td>
                  <td className="px-4 py-3"><span className="font-semibold text-slate-800">{item.clientName || '—'}</span><span className="ml-1 text-slate-400">{item.clientCode ? `(${item.clientCode})` : ''}</span></td>
                  <td className="px-4 py-3">{item.requestType || '—'}</td>
                  <td className="px-4 py-3">{item.Plan?.label || item.serviceType || '—'}</td>
                  <td className="px-4 py-3">{item.status || 'No registrado'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="rounded-xl bg-slate-50 px-4 py-5 text-sm text-slate-400">No hay solicitudes en este periodo.</p>}
    </div>
  );
}

const CATEGORY_COPY = {
  nuevo_contrato: {
    label: 'Nuevos contratos',
    description: 'Altas comerciales registradas en el período seleccionado.',
  },
  recontrataciones: {
    label: 'Recontrataciones',
    description: 'Clientes recuperados mediante una nueva contratación.',
  },
  retiros: {
    label: 'Retiros',
    description: 'Servicios y planes dados de baja en el período seleccionado.',
  },
  cambios_plan: {
    label: 'Cambios de plan',
    description: 'Transiciones de plan registradas por el equipo comercial.',
  },
  traslados: {
    label: 'Traslados externos',
    description: 'Solicitudes de traslado externo registradas.',
  },
  adiciones: {
    label: 'Adiciones',
    description: 'Servicios adicionales registrados en el período seleccionado.',
  },
};

function CategoryAnalyticsPanel({ analytics, movementType, onIndicator, onPlan, onZone, onChannel, onMotive }) {
  const copy = CATEGORY_COPY[movementType] || {
    label: movementType,
    description: 'Solicitudes registradas en el período seleccionado.',
  };
  const analysis = analytics?.category_analysis || {};
  const summary = analytics?.selected || { count: 0, total: 0 };
  const plans = analysis.plans || [];
  const services = analytics?.servicios || [];
  const zones = analysis.zonas || [];
  const motives = analysis.motivos || [];
  const transitions = analysis.transiciones || [];
  const series = analysis.series || [];
  const channels = analytics?.canales_captacion?.items || [];
  const maxPlan = Math.max(...plans.map((item) => item.count || 0), 1);
  const maxMotive = Math.max(...motives.map((item) => item.count || 0), 1);
  const maxTransition = Math.max(...transitions.map((item) => item.count || 0), 1);

  return (
    <div className="space-y-5">
      <div className="rounded-[1.35rem] border border-brand-100 bg-brand-50/45 p-5 sm:p-6">
        <p className="text-[10px] font-black uppercase tracking-[0.22em] text-brand-700">Análisis por solicitud</p>
        <h2 className="mt-1 text-2xl font-black tracking-tight text-slate-900">{copy.label}</h2>
        <p className="mt-1 text-sm text-slate-500">{copy.description}</p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2">
        <MetricCard
          label={`Total de ${copy.label.toLowerCase()}`}
          count={summary.count}
          total={summary.total}
          icon={movementType === 'retiros' ? ArrowDownRight : movementType === 'recontrataciones' ? RefreshCw : Activity}
          tone={movementType === 'retiros' ? 'red' : movementType === 'recontrataciones' ? 'violet' : 'green'}
          onClick={() => onIndicator?.(movementType)}
          detail="Consultar detalle de esta categoría"
        />
      </section>

      <ChartCard eyebrow="Comparativa diaria" title={`${copy.label} por día`}>
        {summary.count ? (
          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={series} margin={{ top: 4, right: 4, left: -18, bottom: 4 }}>
                <CartesianGrid stroke="#e8eee9" vertical={false} />
                <XAxis dataKey="date" tickFormatter={readableShortDate} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Bar name={copy.label} dataKey="count" fill={movementType === 'retiros' ? '#e82711' : movementType === 'recontrataciones' ? '#7c3aed' : '#15803d'} radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : <EmptyChart message={`No hay ${copy.label.toLowerCase()} en este período`} />}
      </ChartCard>

      <section className="grid gap-5 lg:grid-cols-2">
        <ChartCard eyebrow="Distribución" title="Por tipo de servicio">
          {services.length ? (
            <div className="h-[280px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={services} dataKey="count" nameKey="label" cx="50%" cy="46%" innerRadius={62} outerRadius={96} paddingAngle={3}>
                    {services.map((entry) => <Cell key={entry.serviceType} fill={SERVICE_COLORS[entry.serviceType] || '#64748b'} />)}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : <EmptyChart message="No hay información de servicios para esta categoría" />}
        </ChartCard>

        <ChartCard eyebrow="Planes" title={movementType === 'cambios_plan' ? 'Planes involucrados' : 'Distribución por plan'}>
          {plans.length ? (
            <div className="space-y-4">
              {plans.slice(0, 8).map((item, index) => (
                <button key={`${item.label}-${item.type}-${index}`} type="button" onClick={() => onPlan?.(item)} className="block w-full rounded-xl text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30">
                  <div className="mb-1.5 flex items-center justify-between gap-3 text-sm"><span className="flex min-w-0 items-center gap-2 font-semibold text-slate-600"><span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: PLAN_COLORS[index % PLAN_COLORS.length] }} /><span className="truncate">{item.label}</span></span><strong className="shrink-0 tabular-nums text-slate-800">{number(item.count)}</strong></div>
                  <div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full" style={{ width: `${(item.count / maxPlan) * 100}%`, backgroundColor: PLAN_COLORS[index % PLAN_COLORS.length] }} /></div>
                </button>
              ))}
            </div>
          ) : <EmptyChart message="No hay planes registrados para esta categoría" />}
        </ChartCard>
      </section>

      {zones.length > 0 && (
        <ChartCard eyebrow="Cobertura" title="Solicitudes por zona">
          <div className="space-y-4">{zones.map((zone) => <button key={zone.name} type="button" onClick={() => onZone?.(zone.name)} className="block w-full rounded-xl text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30"><div className="mb-1.5 flex items-center justify-between gap-3 text-sm"><span className="font-semibold text-slate-600">{zone.name}</span><span className="shrink-0 text-right"><strong className="tabular-nums text-slate-800">{number(zone.count)}</strong><span className="ml-2 text-xs font-medium tabular-nums text-slate-400">{zone.percentage}%</span></span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-brand-600" style={{ width: `${Math.max(zone.percentage, zone.count ? 2 : 0)}%` }} /></div></button>)}</div>
        </ChartCard>
      )}

      {movementType === 'nuevo_contrato' && channels.length > 0 && (
        <ChartCard eyebrow="Origen de nuevos clientes" title="Canales de captación">
          <div className="space-y-4">{channels.map((channel, index) => <button key={channel.key} type="button" onClick={() => onChannel?.(channel)} className="block w-full rounded-xl text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30"><div className="mb-1.5 flex items-center justify-between text-sm"><span className="font-semibold text-slate-600">{channel.name}</span><span className="tabular-nums text-slate-800"><strong>{number(channel.count)}</strong><span className="ml-2 text-xs text-slate-400">{channel.percentage}%</span></span></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full" style={{ width: `${Math.max(channel.percentage, channel.count ? 2 : 0)}%`, backgroundColor: CHANNEL_COLORS[index % CHANNEL_COLORS.length] }} /></div></button>)}</div>
        </ChartCard>
      )}

      {motives.length > 0 && (
        <ChartCard eyebrow="Motivos registrados" title={movementType === 'retiros' ? 'Motivos de retiro' : 'Motivo del cambio'}>
          <div className="space-y-4">{motives.map((motive) => <button key={motive.id} type="button" onClick={() => onMotive?.(motive)} className="block w-full rounded-xl text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30"><div className="mb-1.5 flex items-center justify-between text-sm"><span className="font-semibold text-slate-600">{motive.label}</span><strong className="tabular-nums text-slate-800">{number(motive.count)}</strong></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-violet-600" style={{ width: `${(motive.count / maxMotive) * 100}%` }} /></div></button>)}</div>
        </ChartCard>
      )}

      {transitions.length > 0 && (
        <ChartCard eyebrow="Transiciones" title="Planes de origen y destino">
          <div className="space-y-4">{transitions.slice(0, 8).map((transition, index) => <div key={`${transition.from}-${transition.to}-${index}`}><div className="mb-1.5 flex items-center justify-between gap-3 text-sm"><span className="min-w-0 truncate font-semibold text-slate-600">{transition.from} <span className="text-slate-400">→</span> {transition.to}</span><strong className="shrink-0 tabular-nums text-slate-800">{number(transition.count)}</strong></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-blue-600" style={{ width: `${(transition.count / maxTransition) * 100}%` }} /></div></div>)}</div>
        </ChartCard>
      )}
    </div>
  );
}

function ProductivityPanel({ data, from, to, movementType }) {
  const [selectedUser, setSelectedUser] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const summary = data?.summary || {};
  const users = data?.users || [];
  const isPersonal = data?.scope === 'personal';
  const series = data?.series || [];
  const today = todayInBolivia();
  const activityToday = series.find((item) => item.date === today)?.registered || 0;
  const latestActivity = users.reduce((latest, item) => (
    item.lastActivity && (!latest || item.lastActivity > latest) ? item.lastActivity : latest
  ), null);

  useEffect(() => {
    if (!selectedUser) {
      setDetail(null);
      return undefined;
    }
    let active = true;
    setDetailLoading(true);
    api.getCommercialProductivity(from, to, movementType, 1, 25, selectedUser)
      .then((result) => { if (active) setDetail(result); })
      .catch(() => { if (active) setDetail(null); })
      .finally(() => { if (active) setDetailLoading(false); });
    return () => { active = false; };
  }, [selectedUser, from, to, movementType]);

  const maxRegistered = Math.max(...users.map((item) => item.registered || 0), 1);
  const visibleItems = detail?.items || data?.items || [];

  if (isPersonal) {
    return (
      <section className="space-y-5 rounded-[1.35rem] border border-slate-200/80 bg-slate-50/70 p-4 shadow-sm sm:p-6">
        <div className="flex flex-col gap-1">
          <p className="text-[10px] font-black uppercase tracking-[0.22em] text-brand-700">Mi productividad</p>
          <h2 className="text-2xl font-black tracking-tight text-slate-900">Mi productividad</h2>
          <p className="text-sm text-slate-500">Resumen de tu actividad comercial.</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-blue-100 bg-blue-50/70 p-5 shadow-sm">
            <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-wider text-blue-700">Solicitudes registradas</p><p className="mt-3 text-4xl font-black tracking-tight text-slate-900">{number(summary.registered)}</p></div><div className="rounded-xl bg-white/80 p-3 text-blue-700"><ClipboardList className="h-5 w-5" /></div></div>
            <p className="mt-3 text-xs text-blue-700/70">Durante el periodo seleccionado</p>
          </div>
          <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 p-5 shadow-sm">
            <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-wider text-emerald-700">Actividad de hoy</p><p className="mt-3 text-4xl font-black tracking-tight text-slate-900">{number(activityToday)}</p></div><div className="rounded-xl bg-white/80 p-3 text-emerald-700"><CalendarClock className="h-5 w-5" /></div></div>
            <p className="mt-3 text-xs text-emerald-700/70">Solicitudes registradas hoy</p>
          </div>
        </div>

        <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="rounded-xl bg-slate-100 p-3 text-slate-600"><Clock3 className="h-5 w-5" /></div>
          <div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">Mi última actividad</p><p className="mt-1 text-base font-black text-slate-800">{latestActivity ? new Date(latestActivity).toLocaleString('es-BO') : 'Sin registros en este periodo'}</p></div>
        </div>

        <div className="grid gap-5 xl:grid-cols-[1.35fr_1fr]">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4"><p className="text-[10px] font-black uppercase tracking-[0.18em] text-brand-700">Evolución personal</p><h3 className="mt-1 text-base font-black text-slate-900">Solicitudes registradas</h3></div>
            <div className="h-[220px] w-full"><ResponsiveContainer width="100%" height="100%"><LineChart data={series} margin={{ top: 8, right: 4, left: -18, bottom: 4 }}><CartesianGrid stroke="#e8eee9" vertical={false} /><XAxis dataKey="date" tickFormatter={readableShortDate} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} /><YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} /><Tooltip content={<ChartTooltip />} /><Line name="Registradas" dataKey="registered" stroke="#15803d" strokeWidth={2.5} dot={{ r: 3, fill: '#15803d' }} /></LineChart></ResponsiveContainer></div>
          </div>
          <div className="rounded-2xl border border-emerald-100 bg-emerald-50/45 p-5 shadow-sm"><div className="flex items-center gap-3"><UserRound className="h-5 w-5 text-emerald-700" /><div><p className="text-sm font-black text-slate-800">{data?.viewer?.name}</p><p className="text-xs text-slate-500">{data?.viewer?.role || 'Usuario comercial'}</p></div></div><p className="mt-6 text-xs leading-5 text-emerald-800/70">Esta vista muestra únicamente tus registros. Los filtros actuales se aplican a toda la información personal.</p></div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <ProductivityTable items={visibleItems} title="Mis solicitudes recientes" loading={detailLoading} />
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-5 rounded-[1.35rem] border border-slate-200/80 bg-slate-50/70 p-4 shadow-sm sm:p-6">
      <div><p className="text-[10px] font-black uppercase tracking-[0.22em] text-brand-700">Supervisión comercial</p><h2 className="mt-1 text-2xl font-black tracking-tight text-slate-900">Actividad de solicitudes por usuario</h2><p className="mt-1 text-sm text-slate-500">Comparativa del equipo durante el periodo seleccionado.</p></div>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-blue-100 bg-blue-50/70 p-5 shadow-sm"><p className="text-xs font-bold uppercase tracking-wider text-blue-700">Solicitudes registradas</p><p className="mt-3 text-3xl font-black tracking-tight text-slate-900">{number(summary.registered)}</p><p className="mt-2 text-xs text-blue-700/70">Total del equipo</p></div>
        <div className="rounded-2xl border border-emerald-100 bg-emerald-50/70 p-5 shadow-sm"><p className="text-xs font-bold uppercase tracking-wider text-emerald-700">Usuarios con actividad</p><p className="mt-3 text-3xl font-black tracking-tight text-slate-900">{number(summary.activeUsers)}</p><p className="mt-2 text-xs text-emerald-700/70">Con registros en el periodo</p></div>
        <div className="rounded-2xl border border-violet-100 bg-violet-50/70 p-5 shadow-sm"><p className="text-xs font-bold uppercase tracking-wider text-violet-700">Última actividad</p><p className="mt-3 text-base font-black leading-7 text-slate-900">{latestActivity ? new Date(latestActivity).toLocaleString('es-BO') : 'Sin registros'}</p><p className="mt-1 text-xs text-violet-700/70">Registro más reciente del equipo</p></div>
      </div>
      <div>
        <div className="mb-3 flex items-center justify-between"><h3 className="text-base font-black text-slate-900">Actividad por usuario</h3><span className="text-xs text-slate-400">Ordenado por solicitudes</span></div>
        <div className="grid gap-3 md:grid-cols-2">
          {users.length ? users.map((item) => (
            <button
              type="button"
              key={item.userId}
              onClick={() => setSelectedUser((current) => (current === item.userId ? null : item.userId))}
              className={`block w-full rounded-2xl border p-4 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 ${selectedUser === item.userId ? 'border-brand-300 bg-brand-50 shadow-sm' : 'border-emerald-100 bg-emerald-50/45 hover:border-emerald-200 hover:bg-emerald-50'}`}
            >
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="flex min-w-0 items-center gap-2 font-bold text-slate-800"><span className="rounded-lg bg-white p-2 text-emerald-700 shadow-sm"><UserCheck className="h-4 w-4" /></span><span className="truncate">{item.userName}</span></span>
                <strong className="shrink-0 text-lg tabular-nums text-slate-900">{number(item.registered)}</strong>
              </div>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-white"><div className="h-full rounded-full bg-emerald-600 transition-all" style={{ width: `${(item.registered / maxRegistered) * 100}%` }} /></div>
              <p className="mt-2 text-[11px] text-slate-500">Última actividad: {item.lastActivity ? new Date(item.lastActivity).toLocaleString('es-BO') : '—'}</p>
            </button>
          )) : <p className="py-6 text-center text-sm text-slate-400">No hay usuarios con actividad en este periodo.</p>}
        </div>
      </div>
      {selectedUser && <ProductivityTable items={visibleItems} title="Solicitudes del usuario seleccionado" onClose={() => setSelectedUser(null)} loading={detailLoading} />}
    </section>
  );
}

export default function Dashboard() {
  const { isAdmin, user } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [period, setPeriod] = useState('today');
  const [movementType, setMovementType] = useState('all');
  const [customFrom, setCustomFrom] = useState(todayInBolivia);
  const [customTo, setCustomTo] = useState(todayInBolivia);
  const [appliedCustomRange, setAppliedCustomRange] = useState(() => ({
    from: todayInBolivia(),
    to: todayInBolivia(),
  }));
  const [customError, setCustomError] = useState('');
  const [stats, setStats] = useState(null);
  const [productivity, setProductivity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [drilldownIndicator, setDrilldownIndicator] = useState(null);
  const [drilldownZoneName, setDrilldownZoneName] = useState('');
  const [drilldownPlan, setDrilldownPlan] = useState(null);
  const [drilldownChannel, setDrilldownChannel] = useState(null);
  const [drilldownMotive, setDrilldownMotive] = useState(null);
  const requestId = useRef(0);
  const canSupervise = isAdmin || (user?.roles || []).some(
    (role) => ['gerente', 'jefe-comercial'].includes(role.code),
  );
  const showSupervisionTab = productivity?.scope === 'general' || (productivity == null && canSupervise);
  const productivityTab = showSupervisionTab
    ? { value: 'productivity', label: 'Supervisión comercial', icon: ShieldCheck }
    : { value: 'productivity', label: 'Mi productividad', icon: UserRound };
  const ProductivityIcon = productivityTab.icon;

  const canUseHistoricalFilters = productivity?.scope
    ? productivity.scope === 'general'
    : canSupervise;
  const visiblePeriod = canUseHistoricalFilters ? period : 'today';
  const range = useMemo(
    () => (visiblePeriod === 'custom' ? appliedCustomRange : getPresetRange(visiblePeriod)),
    [visiblePeriod, appliedCustomRange],
  );

  useEffect(() => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError('');

    Promise.all([
      api.getDashboardStats(range.from, range.to, movementType),
      api.getCommercialProductivity(range.from, range.to, movementType),
    ])
      .then(([data, productivityData]) => {
        if (currentRequest !== requestId.current) return;
        setStats(data);
        setProductivity(productivityData);
      })
      .catch((err) => {
        if (currentRequest !== requestId.current) return;
        setError(err?.error || 'No se pudieron cargar las estadísticas. Intenta nuevamente.');
      })
      .finally(() => {
        if (currentRequest === requestId.current) setLoading(false);
      });
  }, [range.from, range.to, movementType]);

  const analytics = stats?.analytics;
  const series = analytics?.series || [];
  const commercialSeries = series.map((item) => ({
    ...item,
    altas_comerciales: item.nuevo_contrato + item.recontrataciones,
  }));
  const services = analytics?.servicios || [];
  const plans = analytics?.planes || [];
  const zones = analytics?.zonas || [];
  const channelAnalysis = analytics?.canales_captacion;
  const channels = channelAnalysis?.items || [];
  const topPlans = plans.slice(0, 5);
  const planDemandCount = plans.reduce((sum, item) => sum + item.count, 0);
  const hasData = series.some((item) => item.movimientos > 0);
  const hasTodaySales = (stats?.selected?.count || 0) > 0;
  const selectedMovementLabel = MOVEMENT_OPTIONS.find(
    (item) => item.value === movementType,
  )?.label;
  const periodLabel = `${readableDate(range.from)} — ${readableDate(range.to)}`;

  const applyCustomRange = () => {
    if (!customFrom || !customTo) {
      setCustomError('Selecciona la fecha inicial y la fecha final.');
      return;
    }
    if (customFrom > customTo) {
      setCustomError('La fecha inicial no puede superar la fecha final.');
      return;
    }
    setCustomError('');
    setAppliedCustomRange({ from: customFrom, to: customTo });
  };

  const download = async (kind) => {
    try {
      const methods = {
        pdf: api.getDashboardPDF,
        xlsx: api.getDashboardXLSX,
        png: api.getDashboardPNG,
      };
      const blob = await methods[kind](movementType);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${kind === 'png' ? 'foto' : 'planilla'}-${todayInBolivia()}.${kind}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err?.error || 'No se pudo generar el reporte del día.');
    }
  };

  return (
    <div className="space-y-6 pb-8">
      <header className="relative overflow-hidden rounded-[1.5rem] bg-vista-sidebar px-5 py-6 text-white shadow-xl shadow-brand-900/10 sm:px-8 sm:py-8">
        <div className="absolute -right-16 -top-24 h-64 w-64 rounded-full border-[28px] border-vista-accent/10" />
        <div className="absolute bottom-0 left-0 h-1 w-full bg-gradient-to-r from-vista-accent via-brand-400 to-transparent" />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-3 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.22em] text-vista-accent">
              <TrendingUp className="h-4 w-4" /> Gestion comercial
            </div>
            <h1 className="max-w-xl text-3xl font-black tracking-tight sm:text-4xl">Solicitudes comerciales de clientes</h1>
            <p className="mt-2 max-w-lg text-sm leading-6 text-green-100/65">

              Una lectura clara de las solicitudes comerciales, retiros y cambios registrados por cada usuario.

            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
            <CalendarDays className="h-5 w-5 text-vista-accent" />
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-green-100/50">Período activo</p>
              <p className="mt-0.5 text-sm font-bold">{periodLabel}</p>
            </div>
          </div>
        </div>
      </header>

      <nav aria-label="Secciones del dashboard" className="flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
        <button
          type="button"
          onClick={() => setActiveTab('overview')}
          className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500/30 ${activeTab === 'overview' ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'}`}
        >
          <LayoutDashboard className="h-4 w-4" /> Dashboard general
        </button>
        <button
          type="button"
          onClick={() => setActiveTab(productivityTab.value)}
          className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500/30 ${activeTab === productivityTab.value ? 'bg-brand-700 text-white shadow-sm' : 'text-slate-500 hover:bg-brand-50 hover:text-brand-800'}`}
        >
          <ProductivityIcon className="h-4 w-4" /> {productivityTab.label}
        </button>
      </nav>

      <Card className="p-4 sm:p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="h-4 w-4 text-brand-600" />
            <h2 className="text-sm font-black text-slate-800">Filtros de análisis</h2>
          </div>
          {loading && stats && (
            <span className="flex items-center gap-2 text-xs font-semibold text-brand-600">
              <RefreshCw className="h-3.5 w-3.5 animate-spin" /> Actualizando
            </span>
          )}
        </div>
        {canUseHistoricalFilters ? (
          <>
            <div className="flex flex-wrap gap-2">
              {PERIOD_OPTIONS.map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => { setPeriod(value); setCustomError(''); }}
                  className={`rounded-xl px-3.5 py-2 text-xs font-bold transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500/30 ${period === value ? 'bg-brand-700 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_1.2fr_auto] md:items-end">
              {visiblePeriod === 'custom' ? (
                <>
                  <Input label="Desde" type="date" value={customFrom} onChange={(event) => setCustomFrom(event.target.value)} error={customError} />
                  <Input label="Hasta" type="date" value={customTo} onChange={(event) => setCustomTo(event.target.value)} />
                  <Select label="Tipo de solicitud" value={movementType} onChange={(event) => setMovementType(event.target.value)}>
                    {MOVEMENT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                  </Select>
                  <Button type="button" size="md" onClick={applyCustomRange}>Aplicar rango</Button>
                </>
              ) : (
                <div className="md:col-span-2">
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Período consultado</p>
                  <div className="flex h-[46px] items-center rounded-xl bg-slate-50 px-4 text-sm font-semibold text-slate-700">{periodLabel}</div>
                </div>
              )}
              {visiblePeriod !== 'custom' && (
                <Select label="Tipo de solicitud" value={movementType} onChange={(event) => setMovementType(event.target.value)}>
                  {MOVEMENT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </Select>
              )}
            </div>
          </>
        ) : (
          <div className="grid gap-3 md:grid-cols-[1fr_1fr] md:items-end">
            <div>
              <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Período consultado</p>
              <div className="flex h-[46px] items-center rounded-xl bg-slate-50 px-4 text-sm font-semibold text-slate-700">Hoy · {readableDate(range.from)}</div>
            </div>
            <Select label="Tipo de solicitud" value={movementType} onChange={(event) => setMovementType(event.target.value)}>
              {MOVEMENT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </Select>
          </div>
        )}
        {customError && visiblePeriod !== 'custom' && <p className="mt-2 text-xs font-semibold text-red-600">{customError}</p>}
        <p className="mt-3 flex items-center gap-1.5 text-xs text-slate-400"><Filter className="h-3.5 w-3.5" /> Mostrando {selectedMovementLabel?.toLowerCase()} entre {periodLabel}.</p>
      </Card>

      {error && <Alert type="error">{error}</Alert>}

      {loading && !stats ? (
        <Card className="flex min-h-[320px] items-center justify-center p-8">
          <div className="text-center">
            <RefreshCw className="mx-auto mb-3 h-8 w-8 animate-spin text-brand-600" />
            <p className="text-sm font-semibold text-slate-500">Consultando solicitudes comerciales ...</p>
          </div>
        </Card>
      ) : stats && (
        activeTab === 'productivity' ? (
          productivity ? (
            <ProductivityPanel
              data={productivity}
              from={range.from}
              to={range.to}
              movementType={movementType}
            />
          ) : (
            <Card className="flex min-h-[280px] items-center justify-center p-8">
              <p className="text-sm font-semibold text-slate-500">No se pudo cargar la productividad.</p>
            </Card>
          )
         ) : (
         movementType === 'all' ? (
         <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
            <MetricCard label="Nuevos contratos" count={analytics?.nuevo_contrato?.count} total={analytics?.nuevo_contrato?.total} icon={ArrowUpRight} tone="green" onClick={() => setDrilldownIndicator('nuevo_contrato')} />
             <MetricCard label="Recontrataciones" count={analytics?.recontrataciones?.count} total={analytics?.recontrataciones?.total} icon={RefreshCw} tone="violet" onClick={() => setDrilldownIndicator('recontrataciones')} />
            <MetricCard label="Retiros" count={analytics?.retiros?.count} total={analytics?.retiros?.total} icon={ArrowDownRight} tone="red" onClick={() => setDrilldownIndicator('retiros')} />
            <MetricCard
              label="Altas comerciales"
              count={(analytics?.nuevo_contrato?.count || 0) + (analytics?.recontrataciones?.count || 0)}
              icon={TrendingUp}
              tone="green"
              detail="Nuevos contratos + recontrataciones"
              onClick={() => setDrilldownIndicator('altas_comerciales')}
            />
            <MetricCard label="Cambios de plan" count={analytics?.cambios_plan?.count} total={analytics?.cambios_plan?.total} icon={RefreshCw} tone="blue" onClick={() => setDrilldownIndicator('cambios_plan')} />
            <MetricCard label="Balance neto" count={analytics?.balance_neto} icon={Activity} tone="slate" detail="Altas comerciales - retiros" onClick={() => setDrilldownIndicator('balance_neto')} />
          </section>

           {!hasData ? (
            <Card className="p-5 sm:p-6"><EmptyChart message="No hay solicitudes comerciales para analizar" /></Card>
          ) : (
            <>
              <section className="grid gap-5 xl:grid-cols-[1.35fr_1fr]">
                <ChartCard eyebrow="Comparativa diaria" title="Altas comerciales frente a retiros">
                  <div className="h-[300px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={commercialSeries} margin={{ top: 4, right: 4, left: -18, bottom: 4 }}>
                        <CartesianGrid stroke="#e8eee9" vertical={false} />
                        <XAxis dataKey="date" tickFormatter={readableShortDate} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                        <Tooltip content={<ChartTooltip />} />
                        <Legend iconType="circle" wrapperStyle={{ fontSize: 11, paddingTop: 12 }} />
                        <Bar name="Nuevos contratos" dataKey="nuevo_contrato" fill="#12e67c" radius={[5, 5, 0, 0]} />
                        <Bar name="Recontrataciones" dataKey="recontrataciones" fill="#7c3aed" radius={[5, 5, 0, 0]} />
                        <Bar name="Retiros" dataKey="retiros" fill="#e82711" radius={[5, 5, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </ChartCard>
                 <ChartCard eyebrow="Solicitudes por zona" title="Zonas de mayor demanda">
                  {zones.length ? (
                    <div className="space-y-4">
                      {zones.map((zone) => {
                        const width = Math.max(zone.percentage, zone.count ? 2 : 0);
                        return (
                          <button
                            key={zone.name}
                            type="button"
                            aria-label={`Consultar solicitudes de ${zone.name}`}
                            onClick={() => {
                              setDrilldownZoneName(zone.name);
                              setDrilldownIndicator('zone');
                            }}
                            className="block w-full rounded-xl text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30"
                          >
                            <div className="mb-1.5 flex items-center justify-between gap-3 text-sm">
                              <span className="min-w-0 truncate font-semibold text-slate-600">
                                {zone.name}
                              </span>
                              <span className="shrink-0 text-right">
                                <strong className="font-black tabular-nums text-slate-800">{number(zone.count)}</strong>
                                <span className="ml-2 text-xs font-medium tabular-nums text-slate-400">{zone.percentage}%</span>
                              </span>
                            </div>
                            <div
                              className="h-2 overflow-hidden rounded-full bg-slate-100"
                              aria-label={`${zone.percentage}%`}
                              role="progressbar"
                              aria-valuenow={zone.percentage}
                              aria-valuemin={0}
                              aria-valuemax={100}
                            >
                              <div
                                className="h-full rounded-full bg-brand-600 transition-all"
                                style={{ width: `${width}%` }}
                              />
                            </div>
                          </button>
                        );
                      })}

                    </div>
                  ) : (
                    <EmptyChart message="No hay solicitudes con zona para estos filtros" />
                  )}
                </ChartCard>
              </section>

              <section className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
                <ChartCard eyebrow="Composición del período" title="Distribución por tipo de servicio">
                  {services.length ? (
                    <div className="h-[300px] w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie data={services} dataKey="count" nameKey="label" cx="50%" cy="46%" innerRadius={62} outerRadius={96} paddingAngle={3}>
                            {services.map((entry) => <Cell key={entry.serviceType} fill={SERVICE_COLORS[entry.serviceType] || '#64748b'} />)}
                          </Pie>
                          <Tooltip content={<ChartTooltip />} />
                          <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  ) : <EmptyChart />}
                </ChartCard>
                <ChartCard eyebrow="Preferencias de clientes" title="Planes más solicitados">
                  {topPlans.length ? (
                    <div className="space-y-4 pt-2">
                      {topPlans.map((item, index) => (
                        <button
                          key={`${item.label}-${item.type}-${item.plan_name}-${item.catalog_label}`}
                          type="button"
                          aria-label={`Consultar solicitudes del plan ${item.label}`}
                          onClick={() => {
                            setDrilldownPlan(item);
                            setDrilldownIndicator('plan');
                          }}
                          className="block w-full rounded-xl text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30"
                        >
                          <div className="mb-1.5 flex items-center justify-between gap-3 text-sm">
                            <span className="flex min-w-0 items-center gap-2 font-semibold text-slate-600">
                              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: PLAN_COLORS[index % PLAN_COLORS.length] }} />
                              <span className="truncate">{item.label}<span className="ml-2 text-xs font-medium text-slate-400">{item.type_label}</span></span>
                            </span>
                            <span className="shrink-0 font-black tabular-nums text-slate-800">{number(item.count)}</span>
                          </div>
                          <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                            <div className="h-full rounded-full" style={{ width: `${(item.count / planDemandCount) * 100}%`, backgroundColor: PLAN_COLORS[index % PLAN_COLORS.length] }} />
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : <EmptyChart message="No hay altas comerciales con planes en este período" />}
                </ChartCard>
              </section>

              <section className="grid gap-5 lg:grid-cols-2">
                <ChartCard eyebrow="Origen de nuevos clientes" title="Canales de captación">
                  {channels.length ? (
                    <div className="space-y-4">
                      {channelAnalysis?.principal && (
                        <p className="text-xs font-medium text-slate-500">
                          Mayor captación:{' '}
                          <strong className="text-slate-800">
                            {channelAnalysis.principal.name}
                          </strong>
                        </p>
                      )}
                      {channels.map((channel, index) => {
                        const width = Math.max(channel.percentage, channel.count ? 2 : 0);
                        return (
                          <button
                            key={channel.key}
                            type="button"
                            aria-label={`Consultar nuevos contratos de ${channel.name}`}
                            onClick={() => {
                              setDrilldownChannel(channel);
                              setDrilldownIndicator('channel');
                            }}
                            className="block w-full rounded-xl text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/30"
                          >
                            <div className="mb-1.5 flex items-center justify-between gap-3 text-sm">
                              <span className="flex min-w-0 items-center gap-2 font-semibold text-slate-600">
                                <span
                                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                                  style={{ backgroundColor: CHANNEL_COLORS[index % CHANNEL_COLORS.length] }}
                                />
                                <span className="truncate">{channel.name}</span>
                              </span>
                              <span className="shrink-0 text-right">
                                <strong className="font-black tabular-nums text-slate-800">{number(channel.count)}</strong>
                                <span className="ml-2 text-xs font-medium tabular-nums text-slate-400">{channel.percentage}%</span>
                              </span>
                            </div>
                            <div
                              className="h-2 overflow-hidden rounded-full bg-slate-100"
                              aria-label={`${channel.percentage}%`}
                              role="progressbar"
                              aria-valuenow={channel.percentage}
                              aria-valuemin={0}
                              aria-valuemax={100}
                            >
                              <div
                                className="h-full rounded-full transition-all"
                                style={{
                                  width: `${width}%`,
                                  backgroundColor: CHANNEL_COLORS[index % CHANNEL_COLORS.length],
                                }}
                              />
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  ) : <EmptyChart message="No hay nuevos contratos en este período" />}
                </ChartCard>
              </section>
            </>
          )}

          <Card className="flex flex-col gap-4 border-brand-100 bg-brand-50/40 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-black text-slate-800">Reportes del día</p>
              <p className="mt-1 text-xs text-slate-500">Las exportaciones conservan su alcance actual: solicitudes comerciales de hoy.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" size="sm" disabled={!hasTodaySales} onClick={() => download('xlsx')}><Download className="h-4 w-4" /> Excel</Button>
              <Button variant="secondary" size="sm" disabled={!hasTodaySales} onClick={() => download('png')}><Image className="h-4 w-4" /> Foto</Button>
              <Button size="sm" disabled={!hasTodaySales} onClick={() => download('pdf')}><FileText className="h-4 w-4" /> PDF</Button>
            </div>
          </Card>
         </>
         ) : (
           <CategoryAnalyticsPanel
             analytics={analytics}
             movementType={movementType}
             onIndicator={(indicator) => setDrilldownIndicator(indicator)}
             onPlan={(plan) => {
               setDrilldownPlan(plan);
               setDrilldownIndicator('plan');
             }}
             onZone={(zone) => {
               setDrilldownZoneName(zone);
               setDrilldownIndicator('zone');
             }}
             onChannel={(channel) => {
               setDrilldownChannel(channel);
               setDrilldownIndicator('channel');
             }}
             onMotive={(motive) => {
               setDrilldownMotive(motive);
               setDrilldownIndicator('motive');
             }}
           />
         )
         )
      )}
      {drilldownIndicator && (
        <DashboardDrilldownModal
          indicator={drilldownIndicator}
          zoneName={drilldownZoneName}
          planName={drilldownPlan?.plan_name}
          catalogLabel={drilldownPlan?.catalog_label}
          planType={drilldownPlan?.type}
           channelKey={drilldownChannel?.key}
           channelName={drilldownChannel?.name}
           motiveId={drilldownMotive?.id}
           motiveName={drilldownMotive?.label}
          from={range.from}
          to={range.to}
          movementType={movementType}
          periodLabel={periodLabel}
          onClose={() => {
            setDrilldownIndicator(null);
            setDrilldownZoneName('');
             setDrilldownPlan(null);
             setDrilldownChannel(null);
             setDrilldownMotive(null);
           }}
        />
      )}
    </div>
  );
}
