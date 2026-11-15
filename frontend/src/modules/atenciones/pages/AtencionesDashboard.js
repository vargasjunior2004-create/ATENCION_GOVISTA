import React, { useEffect, useState } from 'react';
import api from '../../../services/api';
import { Alert, Card } from '../../../components/ui';

function formatDuration(seconds) {
  const total = Number(seconds || 0);
  return `${Math.floor(total / 3600)}h ${Math.floor((total % 3600) / 60)}m`;
}

function MetricList({ title, rows, labelKey = 'name' }) {
  return (
    <Card className="p-5">
      <h2 className="mb-4 font-black text-slate-900">{title}</h2>
      <div className="space-y-3">
        {rows.length === 0 && <p className="text-sm text-slate-400">Sin datos para el periodo.</p>}
        {rows.map((row) => (
          <div key={`${row[labelKey]}-${row.id || row.agent_id || row.action_id}`} className="flex justify-between gap-3 text-sm">
            <span className="text-slate-600">{row[labelKey] || row.agent__name || row.action__name}</span>
            <strong className="text-slate-900">{row.total || row.attention_count || 0}</strong>
          </div>
        ))}
      </div>
    </Card>
  );
}

export default function AtencionesDashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getAtencionesDashboard().then(setDashboard).catch((err) => {
      setError(err.error || 'No fue posible cargar el dashboard.');
    });
  }, []);

  if (error) return <Alert type="error">{error}</Alert>;
  if (!dashboard) return <p className="text-sm text-slate-500">Cargando dashboard...</p>;

  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-black uppercase tracking-[0.18em] text-brand-600">Call Center</p>
        <h2 className="mt-1 text-3xl font-black text-slate-900">Productividad de atenciones</h2>
      </header>
      <Card className="p-5">
        <p className="text-sm font-bold text-slate-500">Atenciones finalizadas</p>
        <p className="mt-2 text-4xl font-black text-slate-900">{dashboard.total}</p>
      </Card>
      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="p-5">
          <h2 className="mb-4 font-black text-slate-900">Atenciones por agente</h2>
          <div className="space-y-3">
            {dashboard.by_agent.map((row) => (
              <div key={row.agent_id} className="flex justify-between text-sm">
                <span className="text-slate-600">{row.agent__name}</span>
                <span className="font-bold text-slate-900">
                  {row.attention_count} · {formatDuration(row.duration_seconds)}
                </span>
              </div>
            ))}
          </div>
        </Card>
        <MetricList title="Por canal" rows={dashboard.by_channel.map((row) => ({ ...row, name: row.channel__name }))} />
        <MetricList title="Por clasificación" rows={dashboard.by_classification.map((row) => ({ ...row, name: row.classification__name }))} />
        <MetricList title="Acciones ejecutadas" rows={dashboard.by_action.map((row) => ({ ...row, name: row.action__name }))} />
      </div>
    </div>
  );
}
