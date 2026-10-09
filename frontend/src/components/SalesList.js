import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Button, Input, Select, Card, Alert, Badge } from './ui';
import useRequestTypes, { MODO_COLOR } from '../hooks/useRequestTypes';
import useMotivos from '../hooks/useMotivos';

const typeColor = { internet: 'blue', tv: 'amber', combo: 'violet' };

// '-- Seleccione --' y 'Todos' se anteponen al catalogo que llega del backend.
const REQUEST_FILTER_PREFIX = [
  { value: '', label: '-- Seleccione --' },
  { value: 'all', label: 'Todos los movimientos' },
];

const SERVICE_TYPES = [
  { value: '', label: '-- Seleccione --' },
  { value: 'all', label: 'Todos los tipos de servicio' },
  { value: 'internet', label: 'Internet' },
  { value: 'tv', label: 'TV Cable' },
  { value: 'tv_digital', label: 'TV Digital' },
  { value: 'combo_analog', label: 'Internet + TV Analoga' },
  { value: 'combo_digital', label: 'Internet + TV Digital' },
];

const FAMILY_LABELS = { internet: 'INTERNET', tv: 'TV', combo: 'COMBO' };

// Filtro obligatorio de visualizacion: controla si la columna Motivo aparece
// en la tabla y en los reportes. Nunca altera los movimientos consultados.
const SHOW_MOTIVOS_OPTIONS = [
  { value: '', label: '-- Seleccione --' },
  { value: 'si', label: 'Si, mostrar motivos' },
  { value: 'no', label: 'No mostrar motivos' },
];

const SERVICE_TYPE_TO_PLAN_TYPE = {
  internet: 'internet', tv: 'tv', tv_digital: 'tv',
  combo_analog: 'combo', combo_digital: 'combo',
};

const FAMILY_DEFAULT_SERVICE = {
  internet: 'internet', tv: 'tv', combo: 'combo_analog',
};

const SERVICE_LABEL_BY_VALUE = {
  internet: 'Internet', tv: 'TV Cable', tv_digital: 'TV Digital',
  combo_analog: 'Internet + TV Analoga', combo_digital: 'Internet + TV Digital',
};

function SaleCard({ sale, isAdmin, onEdit, onDelete, requestMode, requestLabel, showMotivos }) {
  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="font-semibold text-slate-900">{sale.clientName}</p>
          <p className="text-sm text-slate-400">{sale.clientCode} &middot; {sale.date}</p>
        </div>
        <Badge color={MODO_COLOR[requestMode(sale.requestType)]}>{requestLabel(sale)}</Badge>
      </div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-500">
          {requestMode(sale.requestType) === 'cambio_plan' && sale.previousPlan
            ? <>{sale.previousPlan.label} <span className="text-amber-500">&rarr;</span> {sale.Plan?.label || '-'}</>
            : (sale.Plan?.label || '-')}
        </span>
        <span className="font-bold text-brand-700 tabular-nums">{parseFloat(sale.total).toFixed(2)} Bs</span>
      </div>
      {sale.isServiceChange && sale.previousService && (
        <div className="text-xs font-semibold text-violet-700 bg-violet-50 border border-violet-200 rounded-lg px-2 py-1 inline-block">
          Cambio de servicio: {sale.previousService.label} &rarr; {FAMILY_LABELS[SERVICE_TYPE_TO_PLAN_TYPE[sale.serviceType]] || sale.serviceType}
        </div>
      )}
      {sale.promotion_name && (
        <div className="flex items-center gap-2 text-xs">
          <Badge color="emerald">Promo: {sale.promotion_name}</Badge>
          {sale.applied_installation != null && sale.requestType !== 'adicion' && (
            <span className="text-slate-500">Inst: {parseFloat(sale.applied_installation).toFixed(2)}</span>
          )}
          {sale.applied_monthly != null && (
            <span className="text-slate-500">Mensual: {parseFloat(sale.applied_monthly).toFixed(2)}</span>
          )}
        </div>
      )}
        <div className="space-y-1 pt-2 border-t border-slate-100">
          {showMotivos && sale.changeReason && (
            <div className="text-xs text-slate-500">
              <span className="font-semibold text-slate-600">Motivo:</span> {sale.changeReason}
            </div>
          )}
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">por {sale.creator?.name || '-'}</span>
            {isAdmin && (
              <div className="flex gap-2">
                <Button variant="ghost" size="sm" onClick={() => onEdit(sale)}>Editar</Button>
                <Button variant="danger" size="sm" onClick={() => onDelete(sale)}>Eliminar</Button>
              </div>
            )}
          </div>
        </div>
    </Card>
  );
}

export default function SalesList() {
  const { isAdmin } = useAuth();
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  const [from, setFrom] = useState(today);
  const [to, setTo] = useState(today);
  const [requestType, setRequestType] = useState('');
  const [serviceType, setServiceType] = useState('');
  const [reportFormat, setReportFormat] = useState('');
  const [showMotivos, setShowMotivos] = useState('');
  const [sales, setSales] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingSale, setEditingSale] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [editError, setEditError] = useState('');
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({ total: 0, total_pages: 1 });
  const [generatingReport, setGeneratingReport] = useState(false);
  const [msg, setMsg] = useState('');
  const [deletingSale, setDeletingSale] = useState(null);

  // El catalogo es administrable: etiqueta y color del movimiento salen de
  // aqui, no de un mapa fijo por code.
  const { tipos: requestTypes, modoOf, nombreOf } = useRequestTypes();
  const { porCategoria } = useMotivos();
  const requestMode = (code) => modoOf(code);
  const requestLabel = (sale) => {
    if (modoOf(sale.requestType) === 'adicion' && sale.additionType) {
      return sale.additionType === 'adicion_internet' ? 'ADICION INTERNET' : 'ADICION TV';
    }
    return nombreOf(sale.requestType);
  };

  const showMotivosColumn = showMotivos === 'si';
  const hasSelection = requestType !== '' && serviceType !== '' && reportFormat !== '' && showMotivos !== '';

  const loadSales = useCallback(async (p = 1) => {
    if (!hasSelection) {
      setSales([]);
      setPagination({ total: 0, total_pages: 1, page: 1 });
      return;
    }
    setLoading(true);
    try {
      const res = await api.getSales(from, to, requestType, p, 25, serviceType);
      setSales(res.items);
      setPagination({ total: res.total, total_pages: res.total_pages, page: res.page });
      setPage(res.page);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [from, to, requestType, serviceType, hasSelection]);

  useEffect(() => { loadSales(1); }, [hasSelection]);
  useEffect(() => {
    if (isAdmin) api.getPlans().then(setPlans).catch(() => {});
  }, [isAdmin]);

  const startEdit = (sale) => {
    setEditingSale(sale);
    setEditForm({ date: sale.date, clientCode: sale.clientCode, clientName: sale.clientName, serviceType: sale.serviceType, requestType: sale.requestType, additionType: sale.additionType || '', planFromId: sale.previousPlan?.id || '', serviceTypeFrom: sale.serviceTypeFrom || '', planId: sale.planId, motivoId: sale.motivo || '', notes: sale.notes || '' });
    setEditError('');
  };

  const handleEditChange = (e) => {
    const { name, value } = e.target;
    const UPPERCASE_FIELDS = ['clientCode', 'clientName'];
    const finalValue = UPPERCASE_FIELDS.includes(name) ? value.toUpperCase() : value;
    setEditForm((prev) => {
      const next = { ...prev, [name]: finalValue };
      if (name === 'serviceType') { next.planId = ''; next.serviceTypeFrom = ''; }
      if (name === 'requestType') {
        const nuevoModo = modoOf(value);
        next.motivoId = '';
        if (nuevoModo !== 'adicion') next.additionType = '';
        if (nuevoModo !== 'cambio_plan') { next.planFromId = ''; next.serviceTypeFrom = ''; }
      }
      return next;
    });
  };

  const handleEditPreviousPlanChange = (e) => {
    const value = e.target.value;
    const picked = plans.find((p) => String(p.id) === String(value));
    setEditForm((prev) => ({
      ...prev,
      planFromId: value,
      serviceTypeFrom: picked ? (FAMILY_DEFAULT_SERVICE[picked.type] || '') : '',
    }));
  };

  const editModo = modoOf(editForm.requestType);
  const editMotivos = porCategoria(editModo === 'retiro' ? 'retiro' : 'cambio');
  const editPlanOptions = plans.filter((p) => p.type === SERVICE_TYPE_TO_PLAN_TYPE[editForm.serviceType]);
  const editCurrentPlans = editPlanOptions.filter((p) => !p.legacy);
  const editLegacyPlans = editModo === 'retiro'
    ? editPlanOptions.filter((p) => p.legacy)
    : [];
  const editPreviousOptions = editModo === 'cambio_plan'
    ? plans.filter((p) => String(p.id) !== String(editForm.planId))
    : [];

  const handleUpdate = async (e) => {
    e.preventDefault();
    setEditError('');
    try {
      const payload = { date: editForm.date, clientCode: editForm.clientCode, clientName: editForm.clientName, serviceType: editForm.serviceType, requestType: editForm.requestType, additionType: editModo === 'adicion' ? editForm.additionType : '', planFromId: editModo === 'cambio_plan' && editForm.planFromId ? Number(editForm.planFromId) : null, serviceTypeFrom: editModo === 'cambio_plan' && editForm.serviceTypeFrom ? editForm.serviceTypeFrom : null, planId: Number(editForm.planId), notes: editForm.notes };
      // Solo se envia si el usuario eligio un motivo; si no, el backend
      // conserva el motivo y el texto del registro original.
      if ((editModo === 'cambio_plan' || editModo === 'retiro') && editForm.motivoId) {
        payload.motivoId = Number(editForm.motivoId);
      }
      await api.updateSale(editingSale.id, payload);
      setEditingSale(null);
      loadSales(page);
    } catch (err) {
      setEditError(err.error || 'Error al editar');
    }
  };

  const handleDelete = async () => {
    if (!deletingSale) return;
    try {
      await api.deleteSale(deletingSale.id);
      setDeletingSale(null);
      loadSales(page);
      setMsg('Movimiento eliminado correctamente.');
    } catch (err) {
      setMsg(err.error || 'Error al eliminar');
      setDeletingSale(null);
    }
  };

  const handleGenerateReport = async () => {
    if (!requestType || !serviceType || !reportFormat) return;
    setGeneratingReport(true);
    setMsg('');
    try {
      let blob, ext, typeName, formatLabel;
      if (reportFormat === 'pdf') {
        blob = await api.getPDF(from, to, requestType, serviceType, showMotivosColumn);
        ext = 'pdf';
        formatLabel = 'PDF';
      } else {
        blob = await api.getXLSX(from, to, requestType, serviceType, showMotivosColumn);
        ext = 'xlsx';
        formatLabel = 'Excel';
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      typeName = nombreOf(requestType);
      a.download = `reporte-${typeName}-${from}-${to}.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setMsg(`Reporte ${formatLabel} generado correctamente.`);
    } catch (err) {
      setMsg(err.error || 'Error al generar reporte');
    } finally {
      setGeneratingReport(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight">Movimientos</h1>
        <p className="text-sm text-slate-400 mt-1">Historial de movimientos</p>
      </div>

      {/* Filters */}
      <Card className="p-5">
        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-7 items-end gap-3">
          <div>
            <Input label="Desde" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </div>
          <div>
            <Input label="Hasta" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </div>
          <div>
            <Select label="Movimiento" value={requestType} onChange={(e) => setRequestType(e.target.value)}>
              {[...REQUEST_FILTER_PREFIX, ...requestTypes.map((t) => ({ value: t.code, label: t.nombre }))].map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </Select>
          </div>
          <div>
            <Select label="Tipo Servicio" value={serviceType} onChange={(e) => setServiceType(e.target.value)}>
              {SERVICE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </Select>
          </div>
          <div>
            <Select label="Mostrar motivos" value={showMotivos} onChange={(e) => setShowMotivos(e.target.value)}>
              {SHOW_MOTIVOS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </Select>
          </div>
          <div>
            <Select label="Formato" value={reportFormat} onChange={(e) => setReportFormat(e.target.value)}>
              <option value="">-- Seleccione --</option>
              <option value="pdf">PDF</option>
              <option value="xlsx">Excel</option>
            </Select>
          </div>
          <Button variant="secondary" onClick={() => loadSales(1)}>Buscar</Button>
        </div>
        <div className="flex items-center gap-3 mt-3">
          <Button
            variant="primary"
            onClick={handleGenerateReport}
            disabled={!hasSelection || generatingReport}
            className={(!hasSelection) ? 'opacity-50 cursor-not-allowed' : ''}
          >
            {generatingReport ? 'Generando...' : 'Reporte'}
          </Button>
          {!hasSelection && (
            <p className="text-xs text-slate-400">Selecciona todos los filtros para habilitar el reporte</p>
          )}
        </div>
      </Card>

      {msg && <Alert type={msg.includes('Error') ? 'error' : 'success'}>{msg}</Alert>}

      {/* Delete confirmation modal */}
      {deletingSale && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setDeletingSale(null)}>
          <Card className="w-full max-w-sm p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Eliminar movimiento</h3>
                <p className="text-sm text-slate-500">Esta accion no se puede deshacer</p>
              </div>
            </div>
            <p className="text-sm text-slate-600">
              Seguro que deseas eliminar el movimiento de <strong>{deletingSale.clientName}</strong> ({deletingSale.clientCode})?
            </p>
            <div className="flex gap-3 pt-2">
              <Button variant="danger" onClick={handleDelete}>Si, eliminar</Button>
              <Button variant="secondary" onClick={() => setDeletingSale(null)}>Cancelar</Button>
            </div>
          </Card>
        </div>
      )}

      {/* Edit modal */}
      {editingSale && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setEditingSale(null)}>
          <Card className="w-full max-w-lg p-6 space-y-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-black text-slate-900">Editar Venta #{editingSale.id}</h3>
            {editError && <Alert type="error">{editError}</Alert>}
            <form onSubmit={handleUpdate} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input label="Fecha" type="date" name="date" value={editForm.date} onChange={handleEditChange} required />
                <Input label="Codigo Cliente" name="clientCode" value={editForm.clientCode} onChange={handleEditChange} required />
              </div>
              <Input label="Nombre" name="clientName" value={editForm.clientName} onChange={handleEditChange} required />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Select label="Movimiento" name="requestType" value={editForm.requestType} onChange={handleEditChange}>
                  {requestTypes.map((t) => (
                    <option key={t.code} value={t.code}>{t.nombre}</option>
                  ))}
                </Select>
                <Select label="Tipo" name="serviceType" value={editForm.serviceType} onChange={handleEditChange}>
                  <option value="internet">Internet</option>
                  <option value="tv">TV Cable</option>
                  <option value="tv_digital">TV Digital</option>
                  <option value="combo_analog">Internet + TV Analoga</option>
                  <option value="combo_digital">Internet + TV Digital</option>
                </Select>
              </div>
              {editModo === 'adicion' && (
                <Select label="Tipo de Adicion" name="additionType" value={editForm.additionType} onChange={handleEditChange} required>
                  <option value="">--Seleccione--</option>
                  <option value="adicion_internet">ADICION INTERNET</option>
                  <option value="adicion_tv">ADICION TV</option>
                </Select>
              )}
              {editModo === 'cambio_plan' && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Select label="Plan Anterior" name="planFromId" value={editForm.planFromId} onChange={handleEditPreviousPlanChange} required>
                    <option value="">--Seleccione plan anterior--</option>
                    {['internet', 'tv', 'combo'].map((family) => {
                      const group = editPreviousOptions.filter((p) => p.type === family);
                      if (!group.length) return null;
                      return (
                        <optgroup key={family} label={FAMILY_LABELS[family]}>
                          {group.map((p) => (
                            <option key={p.id} value={p.id}>{p.code} - {p.label} {p.legacy ? '(Anterior)' : ''}</option>
                          ))}
                        </optgroup>
                      );
                    })}
                  </Select>
                  <Select label="Servicio Anterior" name="serviceTypeFrom" value={editForm.serviceTypeFrom} onChange={handleEditChange} required disabled={!editForm.planFromId}>
                    <option value="">--Seleccione--</option>
                    {SERVICE_TYPES.filter((t) => t.value).map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </Select>
                </div>
              )}
              <Select label="Plan" name="planId" value={editForm.planId} onChange={handleEditChange} required>
                <option value="">Seleccionar...</option>
                <optgroup label="Planes vigentes">
                  {editCurrentPlans.map((p) => (
                    <option key={p.id} value={p.id}>{p.label}</option>
                  ))}
                </optgroup>
                {editLegacyPlans.length > 0 && (
                  <optgroup label="Planes anteriores">
                    {editLegacyPlans.map((p) => (
                      <option key={p.id} value={p.id}>{p.label}</option>
                    ))}
                  </optgroup>
                )}
              </Select>
              {(editModo === 'cambio_plan' || editModo === 'retiro') && (
                <Select
                  label={editModo === 'retiro' ? 'Motivo del Retiro' : 'Motivo del Cambio'}
                  name="motivoId"
                  value={editForm.motivoId}
                  onChange={handleEditChange}
                >
                  <option value="">--Sin cambios--</option>
                  {editMotivos.map((m) => (
                    <option key={m.id} value={m.id}>{m.nombre}</option>
                  ))}
                </Select>
              )}
              <Input label="Comentario" name="notes" value={editForm.notes} onChange={handleEditChange} placeholder="Opcional" />
              <div className="flex gap-3 pt-2">
                <Button type="submit">Guardar</Button>
                <Button variant="secondary" type="button" onClick={() => setEditingSale(null)}>Cancelar</Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Sales */}
      {!hasSelection ? (
        <Card className="p-16 text-center">
          <svg className="w-12 h-12 text-slate-200 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <p className="text-slate-500 font-medium">Selecciona filtros para mostrar informacion</p>
          <p className="text-xs text-slate-400 mt-1">Elige tipo de movimiento, tipo de servicio y formato, luego presiona Buscar</p>
        </Card>
      ) : loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-brand-500/20 border-t-brand-500 rounded-full animate-spin" />
            <p className="text-sm text-slate-400 font-medium">Cargando...</p>
          </div>
        </div>
      ) : sales.length === 0 ? (
        <Card className="p-16 text-center">
          <svg className="w-12 h-12 text-slate-200 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <p className="text-slate-400 text-sm">No hay movimientos en este periodo</p>
        </Card>
      ) : (
        <>
          {/* Desktop table */}
          <Card className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  {['Fecha', 'Cod.', 'Nombre', 'Movimiento', 'Plan', ...(showMotivosColumn ? ['Motivo'] : []), 'Total', 'Por', ''].map((h) => (
                    <th key={h} className="text-left px-5 py-3.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {sales.map((s) => (
                  <tr key={s.id} className="hover:bg-brand-50/30 transition-colors">
                    <td className="px-5 py-3.5 text-slate-500">{s.date}</td>
                    <td className="px-5 py-3.5 text-slate-500 font-mono text-xs">{s.clientCode}</td>
                    <td className="px-5 py-3.5 font-medium text-slate-900">{s.clientName}</td>
                    <td className="px-5 py-3.5"><Badge color={MODO_COLOR[requestMode(s.requestType)]}>{requestLabel(s)}</Badge></td>
                    <td className="px-5 py-3.5 text-slate-500">
                      {requestMode(s.requestType) === 'cambio_plan' && s.previousPlan
                        ? <>{s.previousPlan.label} <span className="text-amber-500">&rarr;</span> {s.Plan?.label || '-'}</>
                        : (s.Plan?.label || '-')}
                    </td>
                    {showMotivosColumn && (
                      <td className="px-5 py-3.5 text-slate-500 text-xs">{s.changeReason || '—'}</td>
                    )}
                    <td className="px-5 py-3.5 text-right font-bold text-brand-700 tabular-nums">{parseFloat(s.total).toFixed(2)} Bs</td>
                    <td className="px-5 py-3.5 text-slate-500 text-xs">{s.creator?.name || '-'}</td>
                    {isAdmin && (
                      <td className="px-5 py-3.5">
                        <div className="flex gap-1">
                          <Button variant="ghost" size="sm" onClick={() => startEdit(s)}>Editar</Button>
                          <Button variant="danger" size="sm" onClick={() => setDeletingSale(s)}>Eliminar</Button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          {/* Mobile cards */}
          <div className="md:hidden space-y-3">
            {sales.map((s) => (
              <SaleCard key={s.id} sale={s} isAdmin={isAdmin} onEdit={startEdit} onDelete={(sale) => setDeletingSale(sale)} requestMode={requestMode} requestLabel={requestLabel} showMotivos={showMotivosColumn} />
            ))}
          </div>

          {/* Pagination */}
          {pagination.total_pages > 1 && (
            <Card className="p-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-500">
                  {pagination.total} registros &middot; Pagina {pagination.page} de {pagination.total_pages}
                </p>
                <div className="flex items-center gap-1">
                  <button
                    disabled={page <= 1}
                    onClick={() => loadSales(page - 1)}
                    className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Anterior
                  </button>
                  {Array.from({ length: Math.min(pagination.total_pages, 5) }, (_, i) => {
                    let pNum;
                    if (pagination.total_pages <= 5) {
                      pNum = i + 1;
                    } else if (page <= 3) {
                      pNum = i + 1;
                    } else if (page >= pagination.total_pages - 2) {
                      pNum = pagination.total_pages - 4 + i;
                    } else {
                      pNum = page - 2 + i;
                    }
                    return (
                      <button
                        key={pNum}
                        onClick={() => loadSales(pNum)}
                        className={`w-9 h-9 text-sm rounded-lg font-medium transition-colors ${
                          pNum === page
                            ? 'bg-brand-600 text-white shadow-sm'
                            : 'text-slate-600 hover:bg-slate-100'
                        }`}
                      >
                        {pNum}
                      </button>
                    );
                  })}
                  <button
                    disabled={page >= pagination.total_pages}
                    onClick={() => loadSales(page + 1)}
                    className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Siguiente
                  </button>
                </div>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
