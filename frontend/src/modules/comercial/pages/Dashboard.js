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

const MOVEMENT_OPTIONS = [
  { value: 'all', label: 'Todas las solicitudes' },
  { value: 'nuevo_contrato', label: 'Nuevos contratos' },
  { value: 'recontrataciones', label: 'Recontrataciones' },
  { value: 'retiros', label: 'Retiros' },
  { value: 'cambios_plan', label: 'Cambios de plan' },
  { value: 'adiciones', label: 'Adiciones' },
  { value: 'otros', label: 'Otros' },
];

const PERIOD_OPTIONS = [
  ['today', 'Hoy'],
  ['week', 'Esta semana'],
  ['month', 'Este mes'],
  ['custom', 'Rango personalizado'],
];

const CHART_COLORS = ['#12894d', '#7c3aed', '#e56b5d', '#3b82f6', '#d69e2e', '#64748b'];
const COMPARISON_COLORS = {
  altas: '#1d4ed8',
  retiros: '#f97316',
};
const SERVICE_COLORS = {
  internet: '#7c3aed',
  tv: '#db2777',
  tv_digital: '#0891b2',
  combo_analog: '#65a30d',
  combo_digital: '#a16207',
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

function MetricCard({ label, count, total, icon: Icon, tone, detail }) {
  const tones = {
    green: 'border-brand-200 bg-brand-50/60 text-brand-700',
    red: 'border-red-200 bg-red-50/70 text-red-700',
    blue: 'border-blue-200 bg-blue-50/70 text-blue-700',
    slate: 'border-slate-200 bg-slate-50 text-slate-700',
  };
  return (
    <Card className="relative overflow-hidden p-5">
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
    </Card>
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

export default function Dashboard() {
  const { isAdmin } = useAuth();
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const requestId = useRef(0);

  const visiblePeriod = isAdmin ? period : 'today';
  const range = useMemo(
    () => (visiblePeriod === 'custom' ? appliedCustomRange : getPresetRange(visiblePeriod)),
    [visiblePeriod, appliedCustomRange],
  );

  useEffect(() => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError('');

    api.getDashboardStats(range.from, range.to, movementType)
      .then((data) => {
        if (currentRequest !== requestId.current) return;
        setStats(data);
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
  const categories = analytics?.categorias || [];
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
            <h1 className="max-w-xl text-3xl font-black tracking-tight sm:text-4xl">Solicitudes de clientes</h1>
            <p className="mt-2 max-w-lg text-sm leading-6 text-green-100/65">
              Una lectura clara de las solicitudes comerciales, retiros y cambios registrados por GO VISTA.
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
          {PERIOD_OPTIONS.filter(([value]) => isAdmin || value === 'today').map(([value, label]) => (
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
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <MetricCard label="Nuevos contratos" count={analytics?.nuevo_contrato?.count} total={analytics?.nuevo_contrato?.total} icon={ArrowUpRight} tone="green" />
            <MetricCard label="Recontrataciones" count={analytics?.recontrataciones?.count} total={analytics?.recontrataciones?.total} icon={RefreshCw} tone="blue" />
            <MetricCard label="Retiros" count={analytics?.retiros?.count} total={analytics?.retiros?.total} icon={ArrowDownRight} tone="red" />
            <MetricCard label="Cambios de plan" count={analytics?.cambios_plan?.count} total={analytics?.cambios_plan?.total} icon={RefreshCw} tone="blue" />
            <MetricCard label="Balance neto" count={analytics?.balance_neto} icon={Activity} tone="slate" detail="Nuevos + recontrataciones - retiros" />
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
                        <Bar name="Altas comerciales" dataKey="altas_comerciales" fill={COMPARISON_COLORS.altas} radius={[5, 5, 0, 0]} />
                        <Bar name="Retiros" dataKey="retiros" fill={COMPARISON_COLORS.retiros} radius={[5, 5, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </ChartCard>
                <ChartCard eyebrow="Ritmo de actividad" title="Evolución de solicitudes comerciales">
                  <div className="h-[300px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={series} margin={{ top: 4, right: 4, left: -18, bottom: 4 }}>
                        <CartesianGrid stroke="#e8eee9" vertical={false} />
                        <XAxis dataKey="date" tickFormatter={readableShortDate} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                        <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                        <Tooltip content={<ChartTooltip />} />
                        <Legend iconType="circle" wrapperStyle={{ fontSize: 11, paddingTop: 12 }} />
                        <Line name="Movimientos" type="monotone" dataKey="movimientos" stroke="#0d2b1b" strokeWidth={3} dot={{ r: 3, fill: '#00d67b', strokeWidth: 0 }} activeDot={{ r: 5 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </ChartCard>
              </section>

              <section className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
                <ChartCard eyebrow="Composición del período" title="Distribución por servicio">
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
                <ChartCard eyebrow="Lectura operativa" title="Desglose por categoría">
                  <div className="space-y-4 pt-2">
                    {categories.map((item, index) => (
                      <div key={item.type}>
                        <div className="mb-1.5 flex items-center justify-between gap-3 text-sm">
                          <span className="flex items-center gap-2 font-semibold text-slate-600"><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: CHART_COLORS[index] }} />{item.label}</span>
                          <span className="font-black tabular-nums text-slate-800">{number(item.count)}</span>
                        </div>
                        <div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full" style={{ width: `${Math.min((item.count / Math.max(analytics?.series?.reduce((sum, row) => sum + row.movimientos, 0), 1)) * 100, 100)}%`, backgroundColor: CHART_COLORS[index] }} /></div>
                      </div>
                    ))}
                  </div>
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
    </div>
  );
}
