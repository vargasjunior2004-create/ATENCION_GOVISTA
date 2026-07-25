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

function MetricCard({ label, count, total }) {
  return (
    <Card className="p-5 text-center">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">{label}</p>
      <p className="text-5xl font-bold text-brand-700 tabular-nums leading-none mb-1">{count}</p>
      <p className="text-xs text-slate-400 mb-3">instalaciones</p>
      <p className="text-base font-semibold text-green-600 tabular-nums">{total.toFixed(2)} Bs</p>
    </Card>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState({ today: { count: 0, total: 0 }, week: { count: 0, total: 0 }, month: { count: 0, total: 0 } });
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generatingXlsx, setGeneratingXlsx] = useState(false);
  const [msg, setMsg] = useState('');

  const loadStats = useCallback(async () => {
    try {
      const now = new Date();
      const today = formatDate(now);
      const monthStart = formatDate(new Date(now.getFullYear(), now.getMonth(), 1));
      const weekStart = formatDate(getMonday(now));
      const monthSales = await api.getSales(monthStart, today);
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

      let pdfUrl = '';
      try {
        const linkData = await api.getPDFLink(today, today);
        pdfUrl = linkData.url;
      } catch { /* ignorable */ }

      const { count, total } = stats.today;
      const text = `Planilla de ventas ${today} — ${count} clientes nuevos, Total: ${total.toFixed(2)} Bs` +
        (pdfUrl ? `\nDescargar planilla: ${pdfUrl}` : '');
      window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank');
      setMsg('PDF descargado. Se abrio WhatsApp con el mensaje.');
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

  if (loading) return <p className="text-center text-slate-400 py-20">Cargando...</p>;

  const hasTodaySales = stats.today.count > 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="lg"
            onClick={handleGenerateXLSX}
            disabled={generatingXlsx}
          >
            {generatingXlsx ? 'Generando...' : 'Exportar Excel'}
          </Button>
          <Button
            variant={hasTodaySales ? 'success' : 'secondary'}
            size="lg"
            onClick={handleGenerateReport}
            disabled={generating}
          >
            {generating ? 'Generando...' : hasTodaySales ? 'Generar Planilla (PDF)' : 'Sin ventas hoy'}
          </Button>
        </div>
      </div>

      {msg && <Alert type={msg.includes('Sin ventas') ? 'error' : 'info'}>{msg}</Alert>}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard label="Hoy" count={stats.today.count} total={stats.today.total} />
        <MetricCard label="Esta Semana" count={stats.week.count} total={stats.week.total} />
        <MetricCard label="Este Mes" count={stats.month.count} total={stats.month.total} />
      </div>
    </div>
  );
}
