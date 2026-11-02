import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ExternalLink, MapPinned, Search } from 'lucide-react';
import api from '../../../services/api';
import { Alert, Badge, Card, Input } from '../../../components/ui';

export default function CoverageZones() {
  const [zones, setZones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');

  const loadZones = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setZones(await api.getCoverageZones());
    } catch (err) {
      setError(err?.error || 'No se pudieron cargar las zonas de cobertura.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadZones(); }, [loadZones]);

  const activeCount = zones.filter((zone) => zone.is_active).length;
  const filteredZones = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase('es');
    if (!normalizedQuery) return zones;
    return zones.filter(
      (zone) => zone.name.toLocaleLowerCase('es').includes(normalizedQuery),
    );
  }, [query, zones]);

  return (
    <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6 sm:py-10 lg:px-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-brand-600">
            Consulta de cobertura
          </p>
          <h1 className="mt-1 text-2xl font-black tracking-tight text-slate-900">
            Zonas y barrios
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-500">
            Busca un barrio y abre su ubicación en Google My Maps sin salir de GO VISTA.
          </p>
        </div>
        <Badge color="green">{activeCount} zonas activas</Badge>
      </header>

      {error && <Alert type="error">{error}</Alert>}

      <Card className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <div>
            <h2 className="text-sm font-black text-slate-800">Catálogo de cobertura</h2>
            <p className="mt-1 text-xs text-slate-400">
              {zones.length} barrios registrados
            </p>
          </div>
          <div className="relative w-full sm:max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              aria-label="Buscar zona por nombre"
              className="pl-9"
              placeholder="Buscar barrio..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center text-sm font-medium text-slate-400" role="status">
            Cargando zonas...
          </div>
        ) : filteredZones.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  {['Zona / barrio', 'Descripción', 'Estado'].map((label) => (
                    <th
                      key={label}
                      className="px-5 py-3 text-left text-[11px] font-bold uppercase tracking-wider text-slate-400"
                    >
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {filteredZones.map((zone) => (
                  <tr key={zone.id} className="transition-colors hover:bg-brand-50/30">
                    <td className="px-5 py-4 font-semibold text-slate-800">
                      {zone.google_maps_url ? (
                        <a
                          href={zone.google_maps_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 text-brand-700 underline-offset-2 hover:underline focus:outline-none focus:ring-2 focus:ring-brand-500/40"
                        >
                          {zone.name}
                          <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                        </a>
                      ) : (
                        zone.name
                      )}
                    </td>
                    <td className="max-w-sm px-5 py-4 text-xs text-slate-500">
                      {zone.description || '—'}
                    </td>
                    <td className="px-5 py-4">
                      <Badge color={zone.is_active ? 'green' : 'slate'}>
                        {zone.is_active ? 'Activa' : 'Inactiva'}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-5 py-14 text-center">
            <MapPinned className="mx-auto h-8 w-8 text-slate-300" />
            <p className="mt-3 text-sm font-semibold text-slate-600">
              {query
                ? 'No hay zonas que coincidan con la búsqueda.'
                : 'No hay zonas registradas.'}
            </p>
          </div>
        )}
      </Card>
    </main>
  );
}
