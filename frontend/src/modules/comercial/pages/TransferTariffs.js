import React, { useEffect, useState } from 'react';
import { History, Pencil, Save, X } from 'lucide-react';
import api from '../../../services/api';
import { Alert, Badge, Button, Card, Input, Select } from '../../../components/ui';

export default function TransferTariffs() {
  const [tariffs, setTariffs] = useState([]);
  const [editing, setEditing] = useState(null);
  const [history, setHistory] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = () => api.getTransferTariffs().then(setTariffs).catch((err) => setError(err.error || 'No se pudieron cargar las tarifas.'));
  useEffect(() => { load(); }, []);

  const save = async (event) => {
    event.preventDefault();
    setError('');
    try {
      await api.updateTransferTariff(editing.id, {
        name: editing.name,
        amount: Number(editing.amount),
        active: editing.active,
      });
      setEditing(null);
      setMessage('Tarifa actualizada correctamente.');
      load();
    } catch (err) {
      setError(err.error || 'No se pudo actualizar la tarifa.');
    }
  };

  const showHistory = async (tariff) => {
    setError('');
    try {
      setHistory({ tariff, items: await api.getTransferTariffHistory(tariff.id) });
    } catch (err) {
      setError(err.error || 'No se pudo cargar el historial.');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-brand-600">Configuración comercial</p>
        <h1 className="mt-1 text-2xl font-black tracking-tight text-slate-900">Tarifas de traslados</h1>
        <p className="mt-1 text-sm text-slate-400">Administra los importes vigentes sin alterar los registros históricos.</p>
      </div>
      {message && <Alert type="success">{message}</Alert>}
      {error && <Alert type="error">{error}</Alert>}

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-slate-100">{['Servicio', 'Importe', 'Estado', 'Actualizado por', 'Actualizado', ''].map((label) => <th key={label} className="px-5 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-slate-400">{label}</th>)}</tr></thead>
            <tbody className="divide-y divide-slate-50">
              {tariffs.map((tariff) => (
                <tr key={tariff.id} className="hover:bg-brand-50/30">
                  <td className="px-5 py-4 font-semibold text-slate-800">{tariff.name}</td>
                  <td className="px-5 py-4 font-black tabular-nums text-brand-700">{Number(tariff.amount).toFixed(2)} Bs</td>
                  <td className="px-5 py-4"><Badge color={tariff.active ? 'green' : 'slate'}>{tariff.active ? 'Activa' : 'Inactiva'}</Badge></td>
                  <td className="px-5 py-4 text-xs text-slate-500">{tariff.updatedBy?.name || '—'}</td>
                  <td className="px-5 py-4 text-xs text-slate-500">{tariff.updated_at ? new Date(tariff.updated_at).toLocaleString('es-BO') : '—'}</td>
                  <td className="px-5 py-4"><div className="flex gap-1"><Button variant="ghost" size="sm" onClick={() => setEditing({ ...tariff })}><Pencil className="h-3.5 w-3.5" />Editar</Button><Button variant="ghost" size="sm" onClick={() => showHistory(tariff)}><History className="h-3.5 w-3.5" />Historial</Button></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setEditing(null)}>
          <Card className="w-full max-w-md space-y-5 p-6" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-start justify-between"><div><h2 className="text-lg font-black text-slate-900">Editar tarifa</h2><p className="mt-1 text-xs text-slate-400">{editing.name}</p></div><button type="button" onClick={() => setEditing(null)} className="text-slate-400 hover:text-slate-700"><X className="h-5 w-5" /></button></div>
            <form onSubmit={save} className="space-y-4">
              <Input label="Nombre" value={editing.name} onChange={(event) => setEditing({ ...editing, name: event.target.value })} required />
              <Input label="Importe (Bs)" type="number" min="0" step="0.01" value={editing.amount} onChange={(event) => setEditing({ ...editing, amount: event.target.value })} required />
              <Select label="Estado" value={String(editing.active)} onChange={(event) => setEditing({ ...editing, active: event.target.value === 'true' })}><option value="true">Activa</option><option value="false">Inactiva</option></Select>
              <div className="flex gap-3"><Button type="submit"><Save className="h-4 w-4" />Guardar</Button><Button type="button" variant="secondary" onClick={() => setEditing(null)}>Cancelar</Button></div>
            </form>
          </Card>
        </div>
      )}

      {history && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setHistory(null)}>
          <Card className="w-full max-w-lg space-y-5 p-6" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-start justify-between"><div><h2 className="text-lg font-black text-slate-900">Historial de tarifa</h2><p className="mt-1 text-xs text-slate-400">{history.tariff.name}</p></div><button type="button" onClick={() => setHistory(null)} className="text-slate-400 hover:text-slate-700"><X className="h-5 w-5" /></button></div>
            <div className="space-y-3">{history.items.map((item) => <div key={item.id} className="rounded-xl bg-slate-50 p-3 text-xs"><div className="flex justify-between font-bold text-slate-700"><span>{item.action}</span><span>{new Date(item.created_at).toLocaleString('es-BO')}</span></div><p className="mt-1 text-slate-500">{Number(item.previous_amount).toFixed(2)} Bs → {Number(item.new_amount).toFixed(2)} Bs · {item.changedBy?.name || 'Sistema'}</p></div>)}{history.items.length === 0 && <p className="text-sm text-slate-400">No hay cambios registrados.</p>}</div>
          </Card>
        </div>
      )}
    </div>
  );
}
