import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Button, Card, Alert } from './ui';

function formatDate(d) {
  return d.toISOString().split('T')[0];
}

function getMonday(d) {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  date.setDate(diff);
  return date;
}

function MetricCard({ label, count, total, icon }) {
  return (
    <Card className="p-6 relative overflow-hidden group">
      <div className="absolute top-0 right-0 w-24 h-24 bg-brand-500/5 rounded-full -mr-8 -mt-8 transition-transform duration-300 group-hover:scale-110" />
      <div className="relative">
        <div className="flex items-center justify-between mb-4">
          <div className="w-10 h-10 rounded-xl bg-brand-500/10 flex items-center justify-center text-brand-600">
            {icon}
          </div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">{label}</span>
        </div>
        <div className="stat-number text-4xl mb-1">{count}</div>
        <p className="text-xs text-slate-400 mb-3 font-medium">instalaciones</p>
        <div className="flex items-center gap-2">
          <div className="h-1 flex-1 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-brand-500 to-vista-accent rounded-full" style={{ width: `${Math.min(total / 50, 100)}%` }} />
          </div>
          <span className="text-sm font-bold text-brand-700 tabular-nums">{total.toFixed(2)} Bs</span>
        </div>
      </div>
    </Card>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState({ today: { count: 0, total: 0 }, week: { count: 0, total: 0 }, month: { count: 0, total: 0 } });
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generatingXlsx, setGeneratingXlsx] = useState(false);
  const [generatingFoto, setGeneratingFoto] = useState(false);
  const [msg, setMsg] = useState('');

  const loadStats = useCallback(async () => {
    try {
      const now = new Date();
      const today = formatDate(now);
      const monthStart = formatDate(new Date(now.getFullYear(), now.getMonth(), 1));
      const weekStart = formatDate(getMonday(now));
      const res = await api.getSales(monthStart, today, '', 1, 9999);
      const monthSales = res.items || [];
      const todaySales = monthSales.filter((s) => s.date === today);
      const weekSales = monthSales.filter((s) => s.date >= weekStart && s.date <= today);
      const sumTotal = (arr) => arr.reduce((acc, s) => acc + parseFloat(s.total), 0);
      setStats({
        today: { count: todaySales.length, total: sumTotal(todaySales) },
        week: { count: weekSales.length, total: sumTotal(weekSales) },
        month: { count: monthSales.length, total: sumTotal(monthSales) },
      });
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
      const today = formatDate(new Date());
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
      const today = formatDate(new Date());
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
      const today = formatDate(new Date());
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

  const hasTodaySales = stats.today.count > 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">Resumen de ventas diarias</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="lg"
            onClick={handleGenerateXLSX}
            disabled={generatingXlsx}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            {generatingXlsx ? 'Generando...' : 'Excel'}
          </Button>
          <Button
            variant="secondary"
            size="lg"
            onClick={handleGenerateFoto}
            disabled={generatingFoto}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z" />
            </svg>
            {generatingFoto ? 'Generando...' : 'Foto'}
          </Button>
          <Button
            variant={hasTodaySales ? 'primary' : 'secondary'}
            size="lg"
            onClick={handleGenerateReport}
            disabled={generating}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            {generating ? 'Generando...' : hasTodaySales ? 'Planilla PDF' : 'Sin ventas hoy'}
          </Button>
        </div>
      </div>

      {msg && <Alert type={msg.includes('Sin ventas') ? 'error' : 'success'}>{msg}</Alert>}

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <MetricCard
          label="Hoy"
          count={stats.today.count}
          total={stats.today.total}
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
            </svg>
          }
        />
        <MetricCard
          label="Esta Semana"
          count={stats.week.count}
          total={stats.week.total}
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
            </svg>
          }
        />
        <MetricCard
          label="Este Mes"
          count={stats.month.count}
          total={stats.month.total}
          icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
            </svg>
          }
        />
      </div>
    </div>
  );
}
