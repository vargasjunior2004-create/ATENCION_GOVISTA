import React, { useEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, LoaderCircle, Search, X } from 'lucide-react';
import api from '../../../services/api';
import SalePreviewModal from '../../../components/SalePreview';

const CATEGORY_LABELS = {
  nuevo_contrato: 'Nuevos contratos',
  recontrataciones: 'Recontrataciones',
  retiros: 'Retiros',
  cambios_plan: 'Cambios de plan',
};

const INDICATOR_LABELS = {
  ...CATEGORY_LABELS,
  altas_comerciales: 'Altas comerciales',
  balance_neto: 'Balance neto',
  zone: 'Detalle por zona',
  channel: 'Canales de captación',
};

const SERVICE_LABELS = {
  internet: 'Internet',
  tv: 'TV analógica',
  tv_digital: 'TV digital',
  combo_analog: 'Internet + TV analógica',
  combo_digital: 'Internet + TV digital',
};

function displayDate(value) {
  if (!value) return '—';
  const [year, month, day] = value.split('-');
  return `${day}/${month}/${year}`;
}

function previewData(sale) {
  return {
    ...sale,
    date: displayDate(sale.date),
    requestLabel: sale.requestTypeLabel || CATEGORY_LABELS[sale.requestType] || sale.requestType,
    serviceLabel: SERVICE_LABELS[sale.serviceType] || sale.serviceType,
    planLabel: sale.Plan?.label,
    creatorName: sale.creator?.name,
    motivo: sale.changeReason || sale.motivoNombre,
    promotionName: sale.promotion_name,
    installation: sale.applied_installation,
    monthly: sale.applied_monthly,
    canalCaptacionNombre: sale.canalCaptacion?.nombre,
    previousPlanLabel: sale.previousPlan?.label,
    previousServiceLabel: sale.previousService?.label,
    transferCurrentAddress: sale.traslado?.currentAddress,
    transferNewAddress: sale.traslado?.newAddress,
    transferReferences: sale.traslado?.references,
    transferHasSketch: sale.traslado?.hasPhysicalSketch,
    equipmentDelivered: sale.equipmentDelivered,
    equipmentSerial: sale.equipmentSerial,
    equipmentRecoveryRequired: sale.equipmentRecoveryRequired,
  };
}

function ResultSummary({ breakdown, selectedCategory, onSelect }) {
  if (breakdown.length < 2) return null;
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {breakdown.map((item) => {
        const selected = selectedCategory === item.category;
        return (
          <button
            key={item.category}
            type="button"
            onClick={() => onSelect(item.category)}
            aria-pressed={selected}
            className={`rounded-xl border p-4 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500/30 ${
              selected
                ? 'border-brand-300 bg-brand-50/70'
                : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
          >
            <span className="text-xs font-bold uppercase tracking-wide text-slate-500">
              {item.label}
            </span>
            <span className="mt-1 block text-2xl font-black tabular-nums text-slate-900">
              {Number(item.count || 0).toLocaleString('es-BO')}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function RowDetails({
  sale, isRetirement, isPlanChange, isZone, isPlan, isChannel,
}) {
  return (
    <span className="grid gap-2 text-sm">
      <span>
        <span className="block font-bold text-slate-800">{sale.clientName}</span>
        <span className="text-xs text-slate-500">{sale.clientCode}</span>
      </span>
      <span className="grid grid-cols-2 gap-2 text-xs">
        {(isZone || isPlan) && (
          <>
            <span className="text-slate-500">Tipo de solicitud</span>
            <span className="text-right text-slate-700">{sale.requestTypeLabel || sale.requestType || '—'}</span>
          </>
        )}
        <span className="text-slate-500">Fecha</span>
        <span className="text-right text-slate-700">{displayDate(sale.date)}</span>
        <span className="text-slate-500">Servicio</span>
        <span className="text-right text-slate-700">{SERVICE_LABELS[sale.serviceType] || sale.serviceType || '—'}</span>
        {isPlanChange && (
          <>
            <span className="text-slate-500">Plan anterior</span>
            <span className="text-right text-slate-700">{sale.planFrom || sale.previousPlan?.label || '—'}</span>
          </>
        )}
        <span className="text-slate-500">Plan</span>
        <span className="text-right text-slate-700">{sale.Plan?.label || '—'}</span>
        {isRetirement && (
          <>
            <span className="text-slate-500">Motivo</span>
            <span className="text-right text-slate-700">{sale.changeReason || sale.motivoNombre || '—'}</span>
          </>
        )}
        <span className="text-slate-500">Registró</span>
        <span className="text-right text-slate-700">{sale.creator?.name || '—'}</span>
        {isChannel && (
          <>
            <span className="text-slate-500">Canal de captación</span>
            <span className="text-right text-slate-700">
              {sale.canalCaptacion?.nombre || 'Sin especificar'}
            </span>
          </>
        )}
        {isPlan && (
          <>
            <span className="text-slate-500">Zona / barrio</span>
            <span className="text-right text-slate-700">{sale.coverageZone?.name || '—'}</span>
          </>
        )}
      </span>
    </span>
  );
}

export default function DashboardDrilldownModal({
  indicator,
  from,
  to,
  movementType,
  periodLabel,
  zoneName,
  planName,
  catalogLabel,
  planType,
  channelKey,
  channelName,
  onClose,
}) {
  const isZone = indicator === 'zone';
  const isPlan = indicator === 'plan';
  const isChannel = indicator === 'channel';
  const relevantCategories = isZone || isPlan || isChannel
    ? []
    : indicator === 'altas_comerciales'
    ? ['nuevo_contrato', 'recontrataciones']
    : indicator === 'balance_neto'
      ? ['nuevo_contrato', 'recontrataciones', 'retiros']
      : [indicator];
  const [category, setCategory] = useState(relevantCategories[0] || '');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [previewSale, setPreviewSale] = useState(null);
  const requestId = useRef(0);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && !previewSale) onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [onClose, previewSale]);

  useEffect(() => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError('');
    setResult(null);
    const timer = setTimeout(() => {
      api.getDashboardDrilldown({
        indicator, category, zoneName, planName, catalogLabel, planType,
        channelKey,
        from, to, movementType, search, page,
      })
        .then((data) => {
          if (currentRequest === requestId.current) setResult(data);
        })
        .catch((err) => {
          if (currentRequest !== requestId.current) return;
          setError(err?.error || 'No se pudo cargar el detalle. Intenta nuevamente.');
          setResult(null);
        })
        .finally(() => {
          if (currentRequest === requestId.current) setLoading(false);
        });
    }, search ? 250 : 0);
    return () => clearTimeout(timer);
  }, [
    indicator, category, zoneName, planName, catalogLabel, planType,
    channelKey,
    from, to, movementType, search, page,
  ]);

  const selectCategory = (value) => {
    setCategory(value);
    setPage(1);
  };

  const isRetirement = category === 'retiros';
  const isPlanChange = category === 'cambios_plan';
  const sales = result?.items || [];
  const breakdown = result?.breakdown || [];
  const selectedLabel = isZone || isPlan || isChannel
    ? 'Solicitudes registradas'
    : CATEGORY_LABELS[category] || INDICATOR_LABELS[indicator];
  const resultCount = Number(result?.total || 0);
  const selectedCount = Number(isZone
    ? result?.zone_count
    : isPlan
      ? result?.plan_count
      : isChannel
        ? result?.channel_count
        : 0);
  const totalPages = result?.total_pages || 1;

  return (
    <>
      <div
        className="fixed inset-0 z-50 flex items-stretch justify-center bg-slate-950/60 backdrop-blur-sm sm:items-center sm:p-5"
        onMouseDown={(event) => {
          if (event.target === event.currentTarget) onClose();
        }}
      >
        <section
          role="dialog"
          aria-modal="true"
          aria-labelledby="dashboard-drilldown-title"
          className="flex h-full w-full max-w-6xl flex-col overflow-hidden bg-white shadow-2xl sm:h-[min(92vh,900px)] sm:rounded-2xl"
        >
          <header className="flex items-start justify-between gap-4 border-b border-slate-200 px-4 py-4 sm:px-7 sm:py-5">
            <div className="min-w-0">
              <p className="text-[10px] font-black uppercase tracking-[0.18em] text-brand-700">
                Detalle comercial
              </p>
              <h2 id="dashboard-drilldown-title" className="mt-1 text-xl font-black text-slate-900 sm:text-2xl">
                {(isZone
                  ? zoneName
                  : isPlan
                    ? planName || catalogLabel
                    : isChannel
                      ? channelName
                      : null)
                  || INDICATOR_LABELS[indicator]}
              </h2>
              <p className="mt-1 text-xs font-medium text-slate-500 sm:text-sm">
                Período: {periodLabel}
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Cerrar consulta"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
            >
              <X className="h-5 w-5" />
            </button>
          </header>

          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4 sm:gap-5 sm:p-7">
            {breakdown.length > 1 && (
              <div>
                <ResultSummary
                  breakdown={breakdown}
                  selectedCategory={category}
                  onSelect={selectCategory}
                />
                {indicator === 'balance_neto' && (
                  <p className="mt-3 text-xs font-semibold text-slate-500">
                    Resultado del balance neto:{' '}
                    <strong className="tabular-nums text-slate-800">
                      {Number(result?.indicator_count || 0).toLocaleString('es-BO')}
                    </strong>
                  </p>
                )}
              </div>
            )}

            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h3 className="text-base font-black text-slate-900">{selectedLabel}</h3>
                <p className="mt-1 text-xs text-slate-500" aria-live="polite">
                  {loading && !result
                    ? 'Consultando registros…'
                    : isZone || isPlan || isChannel
                      ? `${selectedCount.toLocaleString('es-BO')} solicitudes · ${resultCount.toLocaleString('es-BO')} registros encontrados`
                      : `${resultCount.toLocaleString('es-BO')} registros encontrados`}
                </p>
              </div>
              <label className="relative block w-full sm:max-w-sm">
                <span className="sr-only">Buscar por nombre o código de cliente</span>
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  type="search"
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setPage(1);
                  }}
                  placeholder="Nombre o código de cliente"
                  className="h-11 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-sm text-slate-800 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-500/15"
                />
              </label>
            </div>

            {error ? (
              <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                {error}
              </div>
            ) : loading && !result ? (
              <div className="flex min-h-48 flex-1 items-center justify-center rounded-xl border border-slate-200 bg-slate-50/60">
                <div className="text-center">
                  <LoaderCircle className="mx-auto mb-2 h-7 w-7 animate-spin text-brand-700" />
                  <p className="text-sm font-semibold text-slate-500">Cargando solicitudes…</p>
                </div>
              </div>
            ) : resultCount === 0 ? (
              <div className="flex min-h-48 flex-1 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50/60 px-6 text-center">
                <div>
                  <p className="font-bold text-slate-700">No hay registros para esta consulta</p>
                  <p className="mt-1 text-sm text-slate-500">
                    Prueba con otro período o término de búsqueda.
                  </p>
                </div>
              </div>
            ) : (
              <>
                <div className="hidden min-h-0 flex-1 overflow-auto rounded-xl border border-slate-200 md:block">
                  <table className="w-full min-w-[850px] text-left text-sm">
                    <thead className="sticky top-0 bg-slate-50 text-[11px] font-bold uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-4 py-3">Cliente</th>
                        {(isZone || isPlan) && <th className="px-4 py-3">Tipo de solicitud</th>}
                        <th className="px-4 py-3">Fecha</th>
                        <th className="px-4 py-3">Servicio</th>
                        {isPlanChange && <th className="px-4 py-3">Plan anterior</th>}
                        <th className="px-4 py-3">Plan</th>
                        {isRetirement && <th className="px-4 py-3">Motivo</th>}
                        <th className="px-4 py-3">Registró</th>
                        {isPlan && <th className="px-4 py-3">Zona / barrio</th>}
                        {isChannel && <th className="px-4 py-3">Canal de captación</th>}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {sales.map((sale) => (
                        <tr
                          key={sale.id}
                          tabIndex={0}
                          role="button"
                          aria-label={`Ver solicitud de ${sale.clientName}, código ${sale.clientCode}`}
                          onClick={() => setPreviewSale(sale)}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter' || event.key === ' ') {
                              event.preventDefault();
                              setPreviewSale(sale);
                            }
                          }}
                          className="cursor-pointer transition-colors hover:bg-brand-50/50 focus:bg-brand-50/50 focus:outline-none"
                        >
                          <td className="px-4 py-3">
                            <span className="block font-bold text-slate-800">{sale.clientName}</span>
                            <span className="text-xs text-slate-500">{sale.clientCode}</span>
                          </td>
                          {(isZone || isPlan) && <td className="px-4 py-3 text-slate-600">{sale.requestTypeLabel || sale.requestType || '—'}</td>}
                          <td className="px-4 py-3 text-slate-600">{displayDate(sale.date)}</td>
                          <td className="px-4 py-3 text-slate-600">{SERVICE_LABELS[sale.serviceType] || sale.serviceType || '—'}</td>
                          {isPlanChange && <td className="px-4 py-3 text-slate-600">{sale.planFrom || sale.previousPlan?.label || '—'}</td>}
                          <td className="px-4 py-3 text-slate-600">{sale.Plan?.label || '—'}</td>
                          {isRetirement && <td className="px-4 py-3 text-slate-600">{sale.changeReason || sale.motivoNombre || '—'}</td>}
                          <td className="px-4 py-3 text-slate-600">{sale.creator?.name || '—'}</td>
                          {isPlan && <td className="px-4 py-3 text-slate-600">{sale.coverageZone?.name || '—'}</td>}
                          {isChannel && <td className="px-4 py-3 text-slate-600">{sale.canalCaptacion?.nombre || 'Sin especificar'}</td>}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="space-y-2 md:hidden">
                  {sales.map((sale) => (
                    <button
                      key={sale.id}
                      type="button"
                      onClick={() => setPreviewSale(sale)}
                      className="w-full rounded-xl border border-slate-200 p-4 text-left transition-colors hover:border-brand-300 hover:bg-brand-50/40 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
                    >
                      <RowDetails
                        sale={sale}
                        isRetirement={isRetirement}
                        isPlanChange={isPlanChange}
                        isZone={isZone}
                        isPlan={isPlan}
                        isChannel={isChannel}
                      />
                    </button>
                  ))}
                </div>
                <footer className="flex items-center justify-between gap-3 border-t border-slate-100 pt-3">
                  <span className="text-xs font-medium text-slate-500">
                    Página {page} de {totalPages}
                  </span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setPage((current) => Math.max(1, current - 1))}
                      disabled={page <= 1 || loading}
                      aria-label="Página anterior"
                      className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                      disabled={page >= totalPages || loading}
                      aria-label="Página siguiente"
                      className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </footer>
              </>
            )}
          </div>
        </section>
      </div>
      <SalePreviewModal
        sale={previewSale && previewData(previewSale)}
        title="Detalle de la solicitud"
        subtitle="Consulta de solo lectura"
        onClose={() => setPreviewSale(null)}
      />
    </>
  );
}
