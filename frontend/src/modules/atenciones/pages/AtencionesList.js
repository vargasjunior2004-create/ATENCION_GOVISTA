import React, { useEffect, useState } from 'react';
import api from '../../../services/api';
import { Alert, Button, Card } from '../../../components/ui';

export default function AtencionesList() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');
  const load = () => api.getAtenciones().then(setItems).catch((err) => setError(err.error || 'No fue posible cargar las atenciones.'));
  useEffect(load, []);
  const run = async (item, action) => {
    try { await action(item.id); load(); } catch (err) { setError(err.error || 'No fue posible actualizar la atención.'); }
  };
  return (
    <div className="space-y-5">
      <header><h2 className="text-3xl font-black text-slate-900">Atenciones registradas</h2><p className="mt-1 text-sm text-slate-500">El tiempo se inicia y finaliza en el servidor.</p></header>
      {error && <Alert type="error">{error}</Alert>}
      <div className="space-y-3">{items.map((item) => (
        <Card key={item.id} className="flex flex-wrap items-center gap-4 p-4">
          <div className="mr-auto"><p className="font-black text-slate-900">{item.customer_code} · {item.customer_name}</p><p className="text-sm text-slate-500">{item.classification} · {item.channel} · {item.status}</p></div>
          {item.status === 'open' && !item.started_at && <Button onClick={() => run(item, api.startAtencion)} variant="secondary">Iniciar</Button>}
          {item.status === 'open' && item.started_at && <Button onClick={() => run(item, api.finishAtencion)}>Finalizar</Button>}
        </Card>
      ))}</div>
    </div>
  );
}
