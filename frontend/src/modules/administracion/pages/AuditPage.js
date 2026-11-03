import React, { useEffect, useState } from 'react';
import api from '../../../services/api';
import { Card } from '../../../components/ui';

export default function AuditPage() {
  const [events, setEvents] = useState([]);
  const [error, setError] = useState('');
  useEffect(() => {
    api.getAdminAudit().then((data) => setEvents(data.results || data)).catch((err) => setError(err.error || 'No fue posible cargar la auditoría.'));
  }, []);
  return <Card title="Auditoría del sistema">
    {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
    <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="text-left text-slate-500"><th className="p-3">Fecha</th><th className="p-3">Actor</th><th className="p-3">Acción</th><th className="p-3">Módulo</th><th className="p-3">Registro</th></tr></thead><tbody>
      {events.map((event) => <tr key={event.id} className="border-t border-slate-100"><td className="p-3">{event.createdAt ? new Date(event.createdAt).toLocaleString() : '—'}</td><td className="p-3">{event.actor}</td><td className="p-3">{event.action}</td><td className="p-3">{event.module || event.entity}</td><td className="p-3">{event.entityId}</td></tr>)}
    </tbody></table></div>
  </Card>;
}
