import React from 'react';
import { ExternalLink, MapPinned } from 'lucide-react';
import { Alert, Card } from '../../../components/ui';

const MAP_VIEW_URL = 'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg&ll=-11.04767248853305%2C-68.77711685000001&z=12';
const MAP_EMBED_URL = 'https://www.google.com/maps/d/embed?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg&ll=-11.04767248853305%2C-68.77711685000001&z=12';

export default function CoverageDashboard() {
  return (
    <main className="mx-auto max-w-7xl space-y-5 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-brand-600">
            Panel principal
          </p>
          <h1 className="mt-1 text-2xl font-black tracking-tight text-slate-900">
            Mapa general de cobertura
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">
            Vista general de las zonas en Google My Maps.
          </p>
        </div>
        <a
          href={MAP_VIEW_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-bold text-brand-700 transition-colors hover:bg-brand-50 focus:outline-none focus:ring-2 focus:ring-brand-500/40"
        >
          <ExternalLink className="h-4 w-4" aria-hidden="true" />
          Abrir mapa en Google My Maps
        </a>
      </header>

      <Card className="overflow-hidden p-2 sm:p-3">
        <div className="relative h-[70vh] min-h-[480px] w-full overflow-hidden rounded-xl bg-slate-100">
          <iframe
            title="Mapa general de zonas de cobertura GO VISTA"
            src={MAP_EMBED_URL}
            className="h-full w-full border-0"
            loading="lazy"
            allowFullScreen
            referrerPolicy="strict-origin-when-cross-origin"
          />
        </div>
      </Card>

      <Alert type="info">
        <span className="inline-flex items-center gap-2">
          <MapPinned className="h-4 w-4 shrink-0" aria-hidden="true" />
          Si Google My Maps no se muestra dentro del panel, usa “Abrir mapa en Google My Maps”.
        </span>
      </Alert>
    </main>
  );
}
