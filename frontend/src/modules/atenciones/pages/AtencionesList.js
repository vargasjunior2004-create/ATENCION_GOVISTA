import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../../../services/api';
import { Alert, Button, Card } from '../../../components/ui';

export default function AtencionesList() {
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = async () => {
    setLoading(true);
    try {
      const data = await api.getAtenciones(Object.fromEntries(searchParams.entries()));
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.error || 'No fue posible cargar las atenciones.');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [searchParams]);
  const run = async (item, action) => {
    try { await action(item.id); await load(); } catch (err) { setError(err.error || 'No fue posible actualizar la atención.'); }
  };
  return (
    <div className="space-y-5">
      <header><h2 className="text-3xl font-black text-slate-900">Atenciones registradas</h2><p className="mt-1 text-sm text-slate-500">El tiempo se inicia y finaliza en el servidor.</p></header>
      {error && <Alert type="error">{error}</Alert>}
      {loading && <p className="text-sm text-slate-500">Cargando atenciones...</p>}
      {!loading && items.length === 0 && <Card className="p-6 text-center text-sm text-slate-500">No hay atenciones registradas.</Card>}
      <div className="space-y-3">{items.map((item) => (
        <Card key={item.id} className="flex flex-wrap items-center gap-4 p-4">
          <div className="mr-auto"><p className="font-black text-slate-900">{item.customer_code} · {item.customer_name}</p><p className="text-sm text-slate-500">{item.classification} · {item.channel} · {item.status}</p></div>
          {item.status === 'open' && !item.started_at && <Button onClick={() => run(item, (id) => api.startExistingAtencion(id))} variant="secondary">Iniciar</Button>}
          {item.status === 'open' && item.started_at && <Button onClick={() => run(item, api.finishAtencion)}>Finalizar</Button>}
        </Card>
      ))}</div>
    </div>
  );
}
