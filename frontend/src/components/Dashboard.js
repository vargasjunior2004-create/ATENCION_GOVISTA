import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Button, Card, Alert } from './ui';

function formatNum(n) {
  return parseFloat(n || 0).toFixed(2);
}

function MetricCard({ label, count, total, icon, color = 'brand' }) {
  const colors = {
    brand: {
      bg: 'bg-brand-500/5',
      iconBg: 'bg-brand-500/10',
      iconText: 'text-brand-600',
      bar: 'from-brand-500 to-vista-accent',
      totalText: 'text-brand-700',
    },
    red: {
      bg: 'bg-red-500/5',
      iconBg: 'bg-red-500/10',
      iconText: 'text-red-600',
      bar: 'from-red-500 to-red-400',
      totalText: 'text-red-700',
    },
    green: {
      bg: 'bg-green-500/5',
      iconBg: 'bg-green-500/10',
      iconText: 'text-green-600',
      bar: 'from-green-500 to-green-400',
      totalText: 'text-green-700',
    },
  };
  const c = colors[color] || colors.brand;

  return (
    <Card className="p-5 relative overflow-hidden group">
      <div className={`absolute top-0 right-0 w-20 h-20 ${c.bg} rounded-full -mr-6 -mt-6 transition-transform duration-300 group-hover:scale-110`} />
      <div className="relative">
        <div className="flex items-center justify-between mb-3">
          <div className={`w-9 h-9 rounded-xl ${c.iconBg} flex items-center justify-center ${c.iconText}`}>
            {icon}
          </div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">{label}</span>
        </div>
        <div className="stat-number text-3xl mb-1">{count}</div>
        <p className="text-xs text-slate-400 mb-2 font-medium">movimientos</p>
        <div className="flex items-center gap-2">
          <div className="h-1 flex-1 bg-slate-100 rounded-full overflow-hidden">
            <div className={`h-full bg-gradient-to-r ${c.bar} rounded-full`} style={{ width: `${Math.min(total / 50, 100)}%` }} />
          </div>
          <span className={`text-sm font-bold ${c.totalText} tabular-nums`}>{formatNum(total)} Bs</span>
        </div>
      </div>
    </Card>
  );
}

function SectionHeader({ title, color = 'brand' }) {
  const colors = {
    brand: 'text-brand-700 border-brand-200',
    red: 'text-red-700 border-red-200',
    green: 'text-green-700 border-green-200',
  };
  return (
    <div className={`border-l-4 pl-3 ${colors[color]}`}>
      <h2 className="text-lg font-black tracking-tight">{title}</h2>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generatingXlsx, setGeneratingXlsx] = useState(false);
  const [generatingFoto, setGeneratingFoto] = useState(false);
  const [msg, setMsg] = useState('');

  const loadStats = useCallback(async () => {
    try {
      const res = await api.getDashboardStats();
      setStats(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);

  const handleGenerateReport = async () => {
    setGenerating(true);
    setMsg('');
    try {
      const today = new Date().toISOString().slice(0, 10);
      const blob = await api.getPDF(today, today);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `planilla-${today}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setMsg('PDF descargado correctamente.');
    } catch (err) {
      setMsg(err.error || 'Sin ventas hoy para generar planilla');
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateXLSX = async () => {
    setGeneratingXlsx(true);
    setMsg('');
    try {
      const today = new Date().toISOString().slice(0, 10);
      const blob = await api.getXLSX(today, today);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `planilla-${today}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setMsg('Archivo Excel descargado.');
    } catch (err) {
      setMsg(err.error || 'Sin ventas hoy para generar el archivo');
    } finally {
      setGeneratingXlsx(false);
    }
  };

  const handleGenerateFoto = async () => {
    setGeneratingFoto(true);
    setMsg('');
    try {
      const today = new Date().toISOString().slice(0, 10);
      const blob = await api.getPNG(today, today);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `foto-${today}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setMsg('Foto descargada correctamente.');
    } catch (err) {
      setMsg(err.error || 'Sin ventas hoy para generar foto');
    } finally {
      setGeneratingFoto(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-brand-500/20 border-t-brand-500 rounded-full animate-spin" />
          <p className="text-sm text-slate-400 font-medium">Cargando...</p>
        </div>
      </div>
    );
  }

  const hasTodaySales = (stats?.movimientos?.today?.count || 0) > 0;

  const CalendarIcon = (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
    </svg>
  );
  const WeekIcon = (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
    </svg>
  );
  const MonthIcon = (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
    </svg>
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">Resumen general</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="lg" onClick={handleGenerateXLSX} disabled={generatingXlsx}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            {generatingXlsx ? 'Generando...' : 'Excel'}
          </Button>
          <Button variant="secondary" size="lg" onClick={handleGenerateFoto} disabled={generatingFoto}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z" />
            </svg>
            {generatingFoto ? 'Generando...' : 'Foto'}
          </Button>
          <Button variant={hasTodaySales ? 'primary' : 'secondary'} size="lg" onClick={handleGenerateReport} disabled={generating}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            {generating ? 'Generando...' : hasTodaySales ? 'Planilla PDF' : 'Sin ventas hoy'}
          </Button>
        </div>
      </div>

      {msg && <Alert type={msg.includes('Sin ventas') ? 'error' : 'success'}>{msg}</Alert>}

      {/* Movimientos del dia */}
      <div className="space-y-3">
        <SectionHeader title="Movimientos del Dia" color="brand" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <MetricCard
            label="Hoy"
            count={stats?.movimientos?.today?.count || 0}
            total={stats?.movimientos?.today?.total || 0}
            icon={CalendarIcon}
            color="brand"
          />
          <MetricCard
            label="Esta Semana"
            count={stats?.movimientos?.week?.count || 0}
            total={stats?.movimientos?.week?.total || 0}
            icon={WeekIcon}
            color="brand"
          />
          <MetricCard
            label="Este Mes"
            count={stats?.movimientos?.month?.count || 0}
            total={stats?.movimientos?.month?.total || 0}
            icon={MonthIcon}
            color="brand"
          />
        </div>
      </div>

      {/* Instalaciones */}
      <div className="space-y-3">
        <SectionHeader title="Instalaciones" color="green" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <MetricCard
            label="Hoy"
            count={stats?.instalaciones?.today?.count || 0}
            total={stats?.instalaciones?.today?.total || 0}
            icon={CalendarIcon}
            color="green"
          />
          <MetricCard
            label="Esta Semana"
            count={stats?.instalaciones?.week?.count || 0}
            total={stats?.instalaciones?.week?.total || 0}
            icon={WeekIcon}
            color="green"
          />
          <MetricCard
            label="Este Mes"
            count={stats?.instalaciones?.month?.count || 0}
            total={stats?.instalaciones?.month?.total || 0}
            icon={MonthIcon}
            color="green"
          />
        </div>
      </div>

      {/* Retiros */}
      <div className="space-y-3">
        <SectionHeader title="Retiros" color="red" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <MetricCard
            label="Hoy"
            count={stats?.retiros?.today?.count || 0}
            total={stats?.retiros?.today?.total || 0}
            icon={CalendarIcon}
            color="red"
          />
          <MetricCard
            label="Esta Semana"
            count={stats?.retiros?.week?.count || 0}
            total={stats?.retiros?.week?.total || 0}
            icon={WeekIcon}
            color="red"
          />
          <MetricCard
            label="Este Mes"
            count={stats?.retiros?.month?.count || 0}
            total={stats?.retiros?.month?.total || 0}
            icon={MonthIcon}
            color="red"
          />
        </div>
      </div>
    </div>
  );
}
