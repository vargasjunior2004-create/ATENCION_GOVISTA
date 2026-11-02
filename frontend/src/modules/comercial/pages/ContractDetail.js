import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, FileText, Gauge } from 'lucide-react';
import api from '../../../services/api';
import { Alert, Card } from '../../../components/ui';

export default function ContractDetail() {
  const { id, contractId } = useParams();
  const [contract, setContract] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => { api.getContract(contractId).then(setContract).catch((err) => setError(err?.error || 'No fue posible cargar el contrato.')); }, [contractId]);
  if (error) return <div className="space-y-4"><Link to={`/comercial/clientes/${id}`} className="inline-flex items-center gap-2 text-sm font-bold text-brand-700"><ArrowLeft className="h-4 w-4" /> Volver a la ficha</Link><Alert type="error">{error}</Alert></div>;
  if (!contract) return <p className="py-20 text-center text-sm text-slate-400">Cargando contrato...</p>;
  return <div className="space-y-6"><Link to={`/comercial/clientes/${id}`} className="inline-flex items-center gap-2 text-sm font-bold text-brand-700"><ArrowLeft className="h-4 w-4" /> Volver a la ficha</Link><header><p className="text-xs font-black uppercase tracking-[0.18em] text-brand-600">Detalle de contrato</p><h1 className="mt-2 text-3xl font-black text-slate-900">{contract.number}</h1><p className="mt-1 text-sm text-slate-500">{contract.customer.name} · {contract.planLabel}</p></header><div className="grid gap-4 sm:grid-cols-2"><Card className="p-5"><FileText className="h-6 w-6 text-brand-600" /><h2 className="mt-3 font-black text-slate-900">Servicio</h2><p className="mt-1 text-sm text-slate-600">{contract.service_type} · {contract.status || 'Estado no informado'}</p><p className="mt-1 text-sm text-slate-600">Contratado: {contract.contracted_on}</p><p className="mt-1 text-sm text-slate-600">Origen: {contract.origin || 'No informado'}</p></Card><Card className="p-5"><Gauge className="h-6 w-6 text-brand-600" /><h2 className="mt-3 font-black text-slate-900">Medidor de luz</h2><p className="mt-1 text-sm text-slate-600">{contract.meter_number || 'No registrado'}</p><p className="mt-2 text-sm text-slate-600">Revisión: <strong>{contract.meter_review_status}</strong></p>{contract.meter_review_notes && <p className="mt-1 text-sm text-slate-500">{contract.meter_review_notes}</p>}</Card></div><Card className="p-5"><h2 className="font-black text-slate-900">Solicitud de origen</h2>{contract.sale ? <p className="mt-2 text-sm text-slate-600">{contract.sale.requestType} del {contract.sale.date}, registrada por {contract.sale.creator?.name || '—'}.</p> : <p className="mt-2 text-sm text-slate-500">No hay solicitud comercial vinculada.</p>}</Card></div>;
}
