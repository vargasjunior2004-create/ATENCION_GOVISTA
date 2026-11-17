import React, { useState } from 'react';
import { ArrowRight, Search, UserRoundSearch } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../../../services/api';
import { Alert, Button, Card, Input } from '../../../components/ui';

function contractLabel(service) {
  return `${service.plan || 'Plan no informado'} · ${service.service_type || 'Servicio no informado'}`;
}

export default function CustomersList() {
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  const search = async (event) => {
    event?.preventDefault();
    const kardex = code.trim();
    const customerName = name.trim();
    if (!kardex && !customerName) {
      setCustomers([]);
      setSearched(true);
      setError('Introduce un Kardex o el nombre del cliente para buscar.');
      return;
    }

    setLoading(true);
    setSearched(true);
    setError('');
    try {
      setCustomers(await api.searchCustomersByCriteria({
        code: kardex,
        name: customerName,
      }));
    } catch (err) {
      setCustomers([]);
      setError(err?.error || 'No fue posible consultar los clientes.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-black uppercase tracking-[0.18em] text-brand-600">Gestión Comercial</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-slate-900">Buscar clientes</h1>
        <p className="mt-1 text-sm text-slate-500">Consulta un cliente por su Kardex o por su nombre.</p>
      </header>

      <Card className="p-5">
        <form onSubmit={search} className="grid gap-4 md:grid-cols-[1fr_1fr_auto] md:items-end">
          <Input
            label="Kardex"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="Ej. 25369-1"
          />
          <Input
            label="Nombre del cliente"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Ej. Yessenia Rios"
          />
          <Button type="submit" disabled={loading}>
            <Search className="h-4 w-4" />
            {loading ? 'Buscando...' : 'Buscar'}
          </Button>
        </form>
        <p className="mt-3 text-xs text-slate-400">
          Si completas ambos campos, se utilizará el Kardex.
        </p>
      </Card>

      {error && <Alert type="error">{error}</Alert>}

      {loading && (
        <Card className="p-8 text-center text-sm text-slate-500">
          Buscando clientes...
        </Card>
      )}

      {!loading && searched && !error && customers.length === 0 && (
        <Card className="p-10 text-center">
          <UserRoundSearch className="mx-auto h-10 w-10 text-slate-300" />
          <p className="mt-3 font-semibold text-slate-600">No se encontraron clientes</p>
          <p className="mt-1 text-sm text-slate-400">Prueba con otro Kardex o nombre.</p>
        </Card>
      )}

      {!loading && customers.length > 0 && (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 bg-slate-50">
                <tr>
                  {['Kardex', 'Cliente', 'Contratos GO VISTA', 'Servicios SOFTV', 'Estado', ''].map((label) => (
                    <th key={label} className="px-5 py-3 text-xs font-bold uppercase tracking-wide text-slate-400">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {customers.map((customer) => (
                  <tr key={customer.id} className="hover:bg-slate-50">
                    <td className="whitespace-nowrap px-5 py-4 font-mono font-semibold text-slate-700">{customer.code}</td>
                    <td className="px-5 py-4">
                      <p className="font-bold text-slate-800">{customer.name}</p>
                      <p className="mt-1 text-xs text-slate-400">
                        {customer.phone || 'Teléfono no registrado'}
                      </p>
                    </td>
                    <td className="max-w-xs px-5 py-4 text-xs text-slate-600">
                      {customer.services?.length
                        ? customer.services.map(contractLabel).join(' · ')
                        : 'Sin contratos registrados'}
                    </td>
                    <td className="max-w-xs px-5 py-4 text-xs text-sky-700">
                      {customer.softvServices?.length
                        ? customer.softvServices.map((service) => service.raw_name).join(' · ')
                        : 'Sin servicios SOFTV'}
                    </td>
                    <td className="whitespace-nowrap px-5 py-4">
                      <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold capitalize text-emerald-700">
                        {customer.status}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <Link
                        to={`/comercial/clientes/${customer.id}`}
                        className="inline-flex items-center gap-1 text-xs font-bold text-brand-700 hover:text-brand-900"
                      >
                        Abrir ficha <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
