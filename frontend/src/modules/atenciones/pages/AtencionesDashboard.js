import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, BarChart3, Clock3, MessageSquare, Phone, RefreshCw,
  ShieldAlert, Timer,
} from 'lucide-react';
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import api from '../../../services/api';
import { SERVICE_TYPES } from '../../comercial/serviceTypes';
import { Alert, Button, Card, Input, Select } from '../../../components/ui';

const EMPTY_DASHBOARD = {
  summary: {
    total_attentions: 0,
    total_complaints: 0,
    total_duration_seconds: 0,
    average_duration_seconds: 0,
  },
  by_agent: [],
  by_channel: [],
  by_attention_type: [],
  by_classification: [],
  by_service: [],
  by_plan: [],
  by_action: [],
  series: [],
  agent_options: [],
};

const COLORS = ['#15803d', '#2563eb', '#7c3aed', '#ea580c', '#0891b2', '#be123c'];
const SERVICE_LABELS = Object.fromEntries(SERVICE_TYPES.map((item) => [item.value, item.label]));

function normalizeDashboard(data) {
  return Object.keys(EMPTY_DASHBOARD).reduce((result, key) => ({
    ...result,
    [key]: data?.[key] ?? EMPTY_DASHBOARD[key],
  }), EMPTY_DASHBOARD);
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const remainingSeconds = total % 60;
  return `${hours}h ${String(minutes).padStart(2, '0')}m ${String(remainingSeconds).padStart(2, '0')}s`;
}

function formatDate(value) {
  if (!value) return '';
  return new Date(value).toLocaleDateString('es-BO', { day: '2-digit', month: 'short' });
}

function percentage(value, total) {
  return total ? `${Math.round((value * 100) / total)}%` : '0%';
}

function chartRow(item) {
  return item?.payload || item || {};
}

function SummaryCard({ label, value, detail, icon: Icon, color, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-left"
      disabled={!onClick}
    >
      <Card className={`h-full p-5 transition-transform ${onClick ? 'hover:-translate-y-0.5' : ''}`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className={`text-xs font-black uppercase tracking-wider ${color}`}>{label}</p>
            <p className="mt-3 text-3xl font-black tabular-nums text-slate-900">{value}</p>
            <p className="mt-2 text-xs text-slate-500">{detail}</p>
          </div>
          <Icon className={`h-5 w-5 ${color}`} />
        </div>
      </Card>
    </button>
  );
}

function ChartCard({ title, children }) {
  return (
    <Card className="min-w-0 p-5">
      <h3 className="mb-4 font-black text-slate-900">{title}</h3>
      {children}
    </Card>
  );
}

function EmptyChart() {
  return <div className="flex h-64 items-center justify-center text-sm text-slate-400">Sin datos para los filtros seleccionados.</div>;
}

function BreakdownList({ rows, total, label, valueLabel, onSelect }) {
  if (!rows.length) return <EmptyChart />;
  return (
    <div className="space-y-3">
      {rows.map((row, index) => (
        <button
          type="button"
          key={`${label(row)}-${row.id || row.agent_id || row.plan_id || index}`}
          onClick={() => onSelect(row)}
          className="block w-full rounded-xl text-left hover:bg-slate-50"
        >
          <div className="mb-1 flex items-center justify-between gap-3 text-sm">
            <span className="truncate font-semibold text-slate-600">{label(row)}</span>
            <span className="shrink-0 tabular-nums text-slate-800">
              <strong>{valueLabel(row)}</strong>
              <span className="ml-2 text-xs text-slate-400">{percentage(row.total || row.attention_count, total)}</span>
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.max(2, ((row.total || row.attention_count) * 100) / Math.max(total, 1))}%`,
                backgroundColor: COLORS[index % COLORS.length],
              }}
            />
          </div>
        </button>
      ))}
    </div>
  );
}

export default function AtencionesDashboard() {
  const navigate = useNavigate();
  const [catalogs, setCatalogs] = useState([]);
  const [plans, setPlans] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [filters, setFilters] = useState({
    from: '', to: '', agent: '', channel: '', attention_type: '',
    classification: '', service_type: '', plan: '',
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const requestId = useRef(0);

  const loadDashboard = () => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError('');
    api.getAtencionesDashboard(filters)
      .then((data) => {
        if (currentRequest === requestId.current) setDashboard(normalizeDashboard(data));
      })
      .catch((err) => {
        if (currentRequest === requestId.current) {
          setError(err?.error || 'No fue posible cargar el dashboard.');
        }
      })
      .finally(() => {
        if (currentRequest === requestId.current) setLoading(false);
      });
  };

  useEffect(() => {
    let active = true;
    Promise.all([api.getAtencionCatalogs(), api.getActivePlans()])
      .then(([catalogData, planData]) => {
        if (!active) return;
        setCatalogs(Array.isArray(catalogData) ? catalogData : []);
        setPlans(Array.isArray(planData) ? planData : []);
      })
      .catch((err) => {
        if (active) setError(err?.error || 'No fue posible cargar los filtros.');
      });
    loadDashboard();
    return () => { active = false; };
  }, []);

  const options = (type) => catalogs.filter((item) => item.catalog_type === type);
  const updateFilter = (field) => (event) => {
    setFilters((current) => ({ ...current, [field]: event.target.value }));
  };
  const servicePlans = useMemo(() => (
    filters.service_type
      ? plans.filter((plan) => {
        const family = { internet: 'internet', tv: 'tv', tv_digital: 'tv', combo_analog: 'combo', combo_digital: 'combo' }[filters.service_type];
        return plan.type === family;
      })
      : plans
  ), [filters.service_type, plans]);

  const goToList = (extra = {}) => {
    const query = new URLSearchParams();
    Object.entries({ ...filters, ...extra }).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    navigate(`/atenciones/listado${query.toString() ? `?${query}` : ''}`);
  };

  if (error && !dashboard) return <Alert type="error">{error}</Alert>;
  if (!dashboard && loading) return <p className="text-sm text-slate-500">Cargando dashboard...</p>;

  const data = dashboard || EMPTY_DASHBOARD;
  const summary = data.summary || EMPTY_DASHBOARD.summary;
  const total = Number(summary.total_attentions || data.total || 0);
  const channelLabel = (row) => row.channel__name || 'Sin canal';
  const attentionTypeLabel = (row) => row.attention_type__name || 'Sin tipo';
  const classificationLabel = (row) => row.classification__name || 'Sin clasificación';
  const agentLabel = (row) => row.agent__name || 'Sin agente';
  const serviceLabel = (row) => SERVICE_LABELS[row.service_type] || row.service_type || 'Sin servicio';
  const planLabel = (row) => row.plan_name || 'Sin plan';

  return (
    <div className="space-y-6 pb-8">
      <header className="rounded-[1.5rem] bg-vista-sidebar px-5 py-7 text-white shadow-xl sm:px-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.2em] text-vista-accent">
              <Activity className="h-4 w-4" /> Call Center
            </p>
            <h1 className="mt-2 text-3xl font-black tracking-tight">Productividad de atenciones</h1>
            <p className="mt-2 max-w-xl text-sm text-green-100/70">Analiza tiempos, quejas, canales y acciones con datos persistidos en el servidor.</p>
          </div>
          {loading && <RefreshCw className="h-5 w-5 animate-spin text-vista-accent" />}
        </div>
      </header>

      <Card className="p-5">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div><h2 className="font-black text-slate-900">Filtros de análisis</h2><p className="text-sm text-slate-500">Actualiza todos los indicadores al aplicar el filtro.</p></div>
          <Button type="button" onClick={loadDashboard} disabled={loading}>Actualizar</Button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Input label="Desde" type="date" value={filters.from} onChange={updateFilter('from')} />
          <Input label="Hasta" type="date" value={filters.to} onChange={updateFilter('to')} />
          <Select label="Agente" value={filters.agent} onChange={updateFilter('agent')}>
            <option value="">Todos los agentes</option>
            {data.agent_options.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}
          </Select>
          <Select label="Canal" value={filters.channel} onChange={updateFilter('channel')}>
            <option value="">Todos los canales</option>
            {options('channel').filter((item) => ['mensaje', 'llamada'].includes(item.code)).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </Select>
          <Select label="Tipo de atención" value={filters.attention_type} onChange={updateFilter('attention_type')}>
            <option value="">Todos los tipos</option>
            {options('attention_type').map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </Select>
          <Select label="Clasificación" value={filters.classification} onChange={updateFilter('classification')}>
            <option value="">Todas</option>
            {options('classification').map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </Select>
          <Select label="Tipo de servicio" value={filters.service_type} onChange={updateFilter('service_type')}>
            <option value="">Todos los servicios</option>
            {SERVICE_TYPES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </Select>
          <Select label="Tipo de plan" value={filters.plan} onChange={updateFilter('plan')}>
            <option value="">Todos los planes</option>
            {servicePlans.map((plan) => <option key={plan.id} value={plan.id}>{plan.label}</option>)}
          </Select>
        </div>
      </Card>

      {error && <Alert type="error">{error}</Alert>}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="Atenciones" value={total} detail="Atenciones finalizadas" icon={Activity} color="text-brand-700" onClick={() => goToList({ status: 'finished' })} />
        <SummaryCard label="Quejas y reclamos" value={summary.total_complaints || 0} detail="Del periodo seleccionado" icon={ShieldAlert} color="text-red-700" onClick={() => goToList({ complaints: 'true' })} />
        <SummaryCard label="Horas acumuladas" value={formatDuration(summary.total_duration_seconds)} detail="Suma de duraciones" icon={Clock3} color="text-violet-700" />
        <SummaryCard label="Promedio" value={formatDuration(summary.average_duration_seconds)} detail="Por atención finalizada" icon={Timer} color="text-blue-700" />
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.5fr_1fr]">
        <ChartCard title="Evolución de atenciones y quejas">
          {data.series.length ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.series} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                  <CartesianGrid stroke="#e8eee9" vertical={false} />
                  <XAxis dataKey="day" tickFormatter={formatDate} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip />
                  <Line type="monotone" name="Atenciones" dataKey="total" stroke="#15803d" strokeWidth={2.5} />
                  <Line type="monotone" name="Quejas y reclamos" dataKey="complaints" stroke="#dc2626" strokeWidth={2.5} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : <EmptyChart />}
        </ChartCard>
        <ChartCard title="Distribución por canal">
          {data.by_channel.length ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={data.by_channel} dataKey="total" nameKey="channel__name" innerRadius={58} outerRadius={92} onClick={(row) => goToList({ channel: chartRow(row).channel_id })}>
                    {data.by_channel.map((row, index) => <Cell key={row.channel_id} fill={COLORS[index % COLORS.length]} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : <EmptyChart />}
        </ChartCard>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="Atenciones por agente">
          {data.by_agent.length ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.by_agent} layout="vertical" margin={{ top: 5, right: 15, left: 20, bottom: 5 }}>
                  <CartesianGrid stroke="#e8eee9" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis type="category" dataKey="agent__name" width={90} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="attention_count" name="Atenciones" fill="#15803d" radius={[0, 5, 5, 0]} onClick={(row) => goToList({ agent: chartRow(row).agent_id })} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <EmptyChart />}
        </ChartCard>
        <ChartCard title="Tipos de atención">
          <BreakdownList rows={data.by_attention_type} total={total} label={attentionTypeLabel} valueLabel={(row) => row.total} onSelect={(row) => goToList({ attention_type: row.attention_type_id })} />
        </ChartCard>
        <ChartCard title="Clasificación de problemas">
          <BreakdownList rows={data.by_classification} total={total} label={classificationLabel} valueLabel={(row) => row.total} onSelect={(row) => goToList({ classification: row.classification_id })} />
        </ChartCard>
        <ChartCard title="Acciones de soporte">
          <BreakdownList rows={data.by_action} total={data.by_action.reduce((sum, row) => sum + row.total, 0)} label={(row) => row.action__name || 'Sin acción'} valueLabel={(row) => row.total} onSelect={(row) => goToList({ action: row.action_id })} />
        </ChartCard>
        <ChartCard title="Quejas por servicio">
          <BreakdownList rows={data.by_service} total={total} label={serviceLabel} valueLabel={(row) => row.total} onSelect={(row) => goToList({ service_type: row.service_type })} />
        </ChartCard>
        <ChartCard title="Quejas por plan">
          <BreakdownList rows={data.by_plan} total={total} label={planLabel} valueLabel={(row) => row.total} onSelect={(row) => goToList({ plan: row.plan_id })} />
        </ChartCard>
      </section>

      <div className="flex flex-wrap gap-3 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1"><MessageSquare className="h-3.5 w-3.5" /> Mensajes</span>
        <span className="inline-flex items-center gap-1"><Phone className="h-3.5 w-3.5" /> Llamadas</span>
        <span className="inline-flex items-center gap-1"><BarChart3 className="h-3.5 w-3.5" /> Haz clic en un gráfico para consultar sus registros.</span>
      </div>
    </div>
  );
}
