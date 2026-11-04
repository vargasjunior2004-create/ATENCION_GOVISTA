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
  RefreshCw,
  SlidersHorizontal,
  TrendingUp,
  UserCheck,
  Users,
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
import DashboardDrilldownModal from '../components/DashboardDrilldownModal';

const MOVEMENT_OPTIONS = [
  { value: 'all', label: 'Todas las solicitudes comerciales' },
  { value: 'nuevo_contrato', label: 'Nuevos contratos' },
  { value: 'recontrataciones', label: 'Recontrataciones' },
  { value: 'retiros', label: 'Retiros' },
  { value: 'cambios_plan', label: 'Cambios de plan' },
  { value: 'adiciones', label: 'Adiciones' },
  { value: 'otros', label: 'Traslado Externo' },
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

function ProductivityPanel({ data, from, to, movementType }) {
  const [selectedUser, setSelectedUser] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const summary = data?.summary || {};
  const users = data?.users || [];

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
  const isPersonal = data?.scope === 'personal';
  const visibleItems = detail?.items || data?.items || [];
  return (
    <ChartCard
      eyebrow={isPersonal ? 'Mi productividad' : 'Supervisión comercial'}
      title={isPersonal ? 'Mi actividad de solicitudes' : 'Actividad de solicitudes por usuario'}
      className="lg:col-span-2"
    >
      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        {isPersonal && <div className="sm:col-span-3 rounded-xl border border-brand-100 bg-brand-50/50 px-4 py-3"><p className="text-sm font-black text-slate-800">{data?.viewer?.name}</p><p className="mt-1 text-xs text-slate-500">Rol: {data?.viewer?.role || '—'}</p></div>}
        <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-blue-600">Solicitudes registradas</p>
          <p className="mt-2 text-2xl font-black text-slate-900">{number(summary.registered)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{isPersonal ? 'Actividad personal' : 'Usuarios con actividad'}</p>
          <p className="mt-2 text-2xl font-black text-slate-900">{isPersonal ? (summary.registered ? 'Activa' : 'Sin actividad') : number(summary.activeUsers)}</p>
          {isPersonal && <p className="mt-1 text-[11px] text-slate-400">Basada en tus registros del periodo.</p>}
        </div>
        <div className="rounded-xl border border-amber-100 bg-amber-50/60 p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-amber-700">Solicitudes atendidas</p>
          <p className="mt-2 text-lg font-black text-slate-700">No disponible</p>
          <p className="mt-1 text-[11px] text-amber-700">El sistema no registra responsable de atención.</p>
        </div>
      </div>
      {!isPersonal ? (
        <div className="space-y-3">
          {users.length ? users.map((item) => (
            <button
              type="button"
              key={item.userId}
              onClick={() => setSelectedUser((current) => (current === item.userId ? null : item.userId))}
              className={`block w-full rounded-xl p-3 text-left ${selectedUser === item.userId ? 'bg-brand-50 ring-1 ring-brand-200' : 'hover:bg-slate-50'}`}
            >
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="flex min-w-0 items-center gap-2 font-bold text-slate-700"><UserCheck className="h-4 w-4 shrink-0 text-brand-600" />{item.userName}</span>
                <strong className="tabular-nums text-slate-900">{number(item.registered)}</strong>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-brand-600" style={{ width: `${(item.registered / maxRegistered) * 100}%` }} /></div>
              <p className="mt-1 text-[11px] text-slate-400">Última actividad: {item.lastActivity ? new Date(item.lastActivity).toLocaleString('es-BO') : '—'}</p>
            </button>
          )) : <p className="py-6 text-center text-sm text-slate-400">No hay usuarios con actividad en este periodo.</p>}
        </div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
          <div className="h-[240px] w-full"><ResponsiveContainer width="100%" height="100%"><LineChart data={data?.series || []} margin={{ top: 4, right: 4, left: -18, bottom: 4 }}><CartesianGrid stroke="#e8eee9" vertical={false} /><XAxis dataKey="date" tickFormatter={readableShortDate} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} /><YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} /><Tooltip content={<ChartTooltip />} /><Legend iconType="circle" wrapperStyle={{ fontSize: 11, paddingTop: 12 }} /><Line name="Registradas" dataKey="registered" stroke="#0e7490" strokeWidth={2} dot={{ r: 3 }} /></LineChart></ResponsiveContainer></div>
          <div className="flex items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/60 p-6 text-center"><div><Users className="mx-auto mb-2 h-7 w-7 text-slate-300" /><p className="text-sm font-semibold text-slate-600">Actividad personal</p><p className="mt-1 text-xs text-slate-400">La evolución muestra únicamente tus solicitudes registradas.</p></div></div>
        </div>
      )}
      {(selectedUser || isPersonal) && (
        <div className="mt-5 border-t border-slate-100 pt-4">
          <div className="mb-3 flex items-center justify-between"><p className="text-sm font-black text-slate-800">{isPersonal ? 'Mi actividad reciente' : 'Solicitudes del usuario seleccionado'}</p>{selectedUser && <button type="button" className="text-xs font-bold text-brand-700" onClick={() => setSelectedUser(null)}>Cerrar detalle</button>}</div>
          {detailLoading ? <p className="text-sm text-slate-400">Cargando solicitudes...</p> : visibleItems.length ? <div className="overflow-x-auto"><table className="w-full min-w-[820px] text-left text-xs"><thead><tr className="text-slate-400"><th className="p-2">Fecha</th><th className="p-2">Cliente</th><th className="p-2">Solicitud</th><th className="p-2">Servicio</th><th className="p-2">Plan</th><th className="p-2">Registró</th><th className="p-2">Estado</th></tr></thead><tbody>{visibleItems.map((item) => <tr key={item.id} className="border-t border-slate-100"><td className="p-2">{item.createdAt ? new Date(item.createdAt).toLocaleString('es-BO') : item.date}</td><td className="p-2">{item.clientName} <span className="text-slate-400">({item.clientCode})</span></td><td className="p-2">{item.requestType}</td><td className="p-2">{item.serviceType}</td><td className="p-2">{item.Plan?.label || '—'}</td><td className="p-2">{item.registeredBy?.name || '—'}</td><td className="p-2">{item.status || 'No registrado'}</td></tr>)}</tbody></table></div> : <p className="text-sm text-slate-400">No hay solicitudes en este periodo.</p>}
        </div>
      )}
    </ChartCard>
  );
}

export default function Dashboard() {
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
  const requestId = useRef(0);

  const visiblePeriod = period;
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
  const hasTodaySales = (stats?.movimientos?.today?.count || 0) > 0;
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
      const blob = await methods[kind]();
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
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
            <MetricCard label="Nuevos contratos" count={analytics?.nuevo_contrato?.count} total={analytics?.nuevo_contrato?.total} icon={ArrowUpRight} tone="green" onClick={() => setDrilldownIndicator('nuevo_contrato')} />
            <MetricCard label="Recontrataciones" count={analytics?.recontrataciones?.count} total={analytics?.recontrataciones?.total} icon={RefreshCw} tone="blue" onClick={() => setDrilldownIndicator('recontrataciones')} />
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
                <ChartCard eyebrow="Solicitudes por zona" title="Top de 5 Zonas de mayor demanda">
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

              {productivity && (
                <ProductivityPanel
                  data={productivity}
                  from={range.from}
                  to={range.to}
                  movementType={movementType}
                />
              )}

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
          from={range.from}
          to={range.to}
          movementType={movementType}
          periodLabel={periodLabel}
          onClose={() => {
            setDrilldownIndicator(null);
            setDrilldownZoneName('');
            setDrilldownPlan(null);
            setDrilldownChannel(null);
          }}
        />
      )}
    </div>
  );
}
