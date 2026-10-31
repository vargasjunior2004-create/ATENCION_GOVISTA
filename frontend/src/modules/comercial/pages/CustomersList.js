import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Search, UserRoundSearch } from 'lucide-react';
import api from '../../../services/api';
import { Button, Card, Input, Alert } from '../../../components/ui';

export default function CustomersList() {
  const [query, setQuery] = useState('');
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const search = async (event) => {
    event?.preventDefault();
    setLoading(true);
    setError('');
    try {
      setCustomers(await api.searchCustomers(query));
    } catch (err) {
      setError(err?.error || 'No fue posible consultar los clientes.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { search(); }, []);

  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-black uppercase tracking-[0.18em] text-brand-600">Gestión Comercial</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-slate-900">Clientes</h1>
        <p className="mt-1 text-sm text-slate-500">Consulta la ficha, contratos y trayectoria comercial de cada cliente.</p>
      </header>

      <Card className="p-5">
        <form onSubmit={search} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Input label="Buscar por CI, nombre, teléfono, kardex o medidor" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Escribe un dato del cliente" />
          </div>
          <Button type="submit" disabled={loading}><Search className="h-4 w-4" /> {loading ? 'Consultando...' : 'Buscar'}</Button>
        </form>
      </Card>

      {error && <Alert type="error">{error}</Alert>}
      {!loading && !error && customers.length === 0 && (
        <Card className="p-12 text-center">
          <UserRoundSearch className="mx-auto h-10 w-10 text-slate-300" />
          <p className="mt-3 font-semibold text-slate-600">No se encontraron clientes</p>
          <p className="mt-1 text-sm text-slate-400">Prueba con el CI, nombre, teléfono, kardex o medidor.</p>
        </Card>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {customers.map((customer) => (
          <Card key={customer.id} className="p-5 transition-shadow hover:shadow-md">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-lg font-black text-slate-900">{customer.name}</p>
                <p className="mt-1 text-sm text-slate-500">CI: {customer.ci || 'No registrado'} · Kardex: {customer.code}</p>
                <p className="mt-1 text-sm text-slate-500">Teléfono: {customer.phone || 'No registrado'}</p>
              </div>
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold capitalize text-emerald-700">{customer.status}</span>
            </div>
            <Link to={`/comercial/clientes/${customer.id}`} className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-brand-700 hover:text-brand-900">
              Abrir ficha <ArrowRight className="h-4 w-4" />
            </Link>
          </Card>
        ))}
      </div>
    </div>
  );
}
