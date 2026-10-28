import React from 'react';

function PreviewRow({ label, value, emphasis = false }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-slate-400">{label}:</span>
      <span className={emphasis ? 'font-bold text-brand-700 text-lg text-right' : 'font-medium text-right'}>
        {value || '—'}
      </span>
    </div>
  );
}

function amountLabel(value) {
  return value == null || value === '' ? '—' : `${value} Bs`;
}

export function SalePreviewDetails({ sale }) {
  const isChange = Boolean(sale.previousPlanLabel);
  const isRehire = sale.requestType === 'recontratacion';

  return (
    <div className="bg-slate-50 rounded-2xl p-4 space-y-2 text-sm">
      <PreviewRow label="Fecha" value={sale.date} />
      <PreviewRow label="Kardex" value={sale.clientCode} />
      <PreviewRow label="Cliente" value={sale.clientName} />
      <PreviewRow label="Solicitud" value={sale.requestLabel} />
      {isChange ? (
        <>
          <PreviewRow label="Servicio anterior" value={sale.previousServiceLabel} />
          <PreviewRow label="Plan anterior" value={sale.previousPlanLabel} />
          <PreviewRow label="Servicio nuevo" value={sale.serviceLabel} />
        </>
      ) : (
        <PreviewRow label="Servicio" value={sale.serviceLabel} />
      )}
      <PreviewRow label="Plan" value={sale.planLabel} />
      {sale.promotionName && <PreviewRow label="Promoción" value={sale.promotionName} />}
      <PreviewRow label="Instalación" value={amountLabel(sale.installation)} />
      <PreviewRow label="Mensualidad" value={amountLabel(sale.monthly)} />
      <PreviewRow label="Monto" value={sale.total == null ? '—' : `Bs. ${sale.total}`} emphasis />
      {isRehire && sale.debtAmount != null && (
        <>
          <PreviewRow label="Adeudo" value={amountLabel(sale.debtAmount)} />
          <PreviewRow label="Total a cobrar" value={amountLabel(sale.totalToCollect)} emphasis />
        </>
      )}
      {isRehire && sale.equipmentRetained != null && (
        <PreviewRow label="Conserva router/ONU" value={sale.equipmentRetained ? 'Sí' : 'No'} />
      )}
      {isRehire && sale.requiresTechnicalVisit != null && (
        <PreviewRow label="Requiere visita técnica" value={sale.requiresTechnicalVisit ? 'Sí' : 'No'} />
      )}
      {sale.motivo && <PreviewRow label="Motivo" value={sale.motivo} />}
      {sale.notes && <PreviewRow label="Comentarios" value={sale.notes} />}
    </div>
  );
}

export default function SalePreviewModal({ sale, title = 'Vista previa', subtitle = 'Consulta los datos de la solicitud', onClose, onConfirm, confirmLabel = 'Confirmar', loading = false }) {
  if (!sale) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-6 space-y-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sale-preview-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="text-center">
          <h2 id="sale-preview-title" className="text-xl font-black text-slate-900">{title}</h2>
          <p className="text-xs text-slate-400 mt-1">{subtitle}</p>
        </div>
        <SalePreviewDetails sale={sale} />
        <div className="flex gap-3">
          <button type="button" className="flex-1 px-4 py-3 text-sm font-semibold rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200" onClick={onClose}>
            {onConfirm ? 'Cancelar' : 'Cerrar'}
          </button>
          {onConfirm && (
            <button type="button" className="flex-1 px-4 py-3 text-sm font-semibold rounded-xl bg-gradient-to-r from-brand-700 to-brand-600 hover:from-brand-800 hover:to-brand-700 text-white shadow-sm disabled:opacity-40" onClick={onConfirm} disabled={loading}>
              {loading ? 'Guardando...' : confirmLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
