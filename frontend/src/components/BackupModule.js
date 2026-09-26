import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Button, Card, Alert } from './ui';

function formatBytes(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  const hours = String(d.getHours()).padStart(2, '0');
  const mins = String(d.getMinutes()).padStart(2, '0');
  return `${day}/${month}/${year} ${hours}:${mins}`;
}

const STATUS_LABEL = {
  pending: 'Pendiente',
  running: 'En proceso',
  success: 'Completado',
  failed: 'Fallido',
};

const STATUS_STYLE = {
  pending: 'bg-slate-100 text-slate-600',
  running: 'bg-blue-100 text-blue-700',
  success: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
};

export default function BackupModule() {
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [msg, setMsg] = useState('');
  const [msgType, setMsgType] = useState('success');
  const [confirmCreate, setConfirmCreate] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const loadBackups = useCallback(async () => {
    try {
      const data = await api.getBackups();
      setBackups(data);
    } catch (err) {
      console.error(err);
      setMsg('Error al cargar el historial de respaldos');
      setMsgType('error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadBackups(); }, [loadBackups]);

  const handleCreateBackup = async () => {
    setCreating(true);
    setMsg('');
    setConfirmCreate(false);
    try {
      const { blob, filename } = await api.createBackup();

      // Descarga directa al navegador
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setMsg(`Respaldo generado y enviado a descarga: ${filename}`);
      setMsgType('success');
      loadBackups();
    } catch (err) {
      setMsg(err.message || 'No se pudo generar el respaldo');
      setMsgType('error');
      loadBackups();
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (backup) => {
    try {
      await api.deleteBackup(backup.id);
      setMsg('Registro del historial eliminado');
      setMsgType('success');
      setConfirmDelete(null);
      loadBackups();
    } catch (err) {
      setMsg(err.error || 'Error al eliminar el registro');
      setMsgType('error');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-brand-500/20 border-t-brand-500 rounded-full animate-spin" />
          <p className="text-sm text-slate-400 font-medium">Cargando...</p>
        </div>
      </div>
    );
  }

  const lastSuccess = backups.find((b) => b.status === 'success') || null;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Copias de Seguridad</h1>
          <p className="text-sm text-slate-400 mt-1">
            Descargar un respaldo de la base de datos
          </p>
        </div>
        <Button
          variant="primary"
          size="lg"
          onClick={() => setConfirmCreate(true)}
          disabled={creating}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {creating ? 'Generando...' : 'Generar respaldo'}
        </Button>
      </div>

      {msg && (
        <Alert type={msgType}>
          {msg}
        </Alert>
      )}

      {/* Ultimo respaldo correcto */}
      <Card className="p-6">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">
          Ultimo respaldo completado
        </h3>
        {lastSuccess ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-slate-400">Fecha</p>
              <p className="text-sm font-bold text-slate-700">{formatDate(lastSuccess.finished_at || lastSuccess.created_at)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Archivo</p>
              <p className="text-sm font-bold text-slate-700 break-all">{lastSuccess.filename}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Tamano</p>
              <p className="text-sm font-bold text-slate-700">{formatBytes(lastSuccess.size)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Verificado</p>
              <span className={`inline-block text-xs font-bold px-2 py-0.5 rounded-full ${
                lastSuccess.verified ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'
              }`}>
                {lastSuccess.verified ? 'Si' : 'No'}
              </span>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-400">Todavia no hay ningun respaldo completado</p>
        )}
      </Card>

      {/* Historial */}
      <div>
        <h3 className="text-lg font-black text-slate-900 mb-4">Historial</h3>
        {backups.length === 0 ? (
          <Card className="p-8 text-center">
            <p className="text-slate-400">No hay registros de respaldo</p>
          </Card>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">Fecha</th>
                  <th className="text-left text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">Archivo</th>
                  <th className="text-left text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">Tamano</th>
                  <th className="text-left text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">SHA-256</th>
                  <th className="text-left text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">Estado</th>
                  <th className="text-right text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">Accion</th>
                </tr>
              </thead>
              <tbody>
                {backups.map((b) => (
                  <tr key={b.id} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="py-3 px-4">
                      <span className="text-sm text-slate-700">{formatDate(b.created_at)}</span>
                      {b.creator && (
                        <span className="block text-xs text-slate-400">{b.creator.name}</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-xs text-slate-600 break-all">{b.filename}</span>
                      {b.error_message && (
                        <span className="block text-xs text-red-600 mt-1">{b.error_message}</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-sm text-slate-700">{formatBytes(b.size)}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-xs font-mono text-slate-400">
                        {b.checksum ? `${b.checksum.substring(0, 16)}...` : '—'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-block text-xs font-bold px-2 py-0.5 rounded-full ${STATUS_STYLE[b.status] || 'bg-slate-100 text-slate-600'}`}>
                        {STATUS_LABEL[b.status] || b.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setConfirmDelete(b)}
                        title="Este archivo ya fue eliminado del servidor; esto solo borra el registro del historial."
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                        </svg>
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Informacion importante */}
      <Card className="p-6 bg-blue-50 border-blue-200">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600 flex-shrink-0 mt-0.5">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
            </svg>
          </div>
          <div>
            <h4 className="text-sm font-bold text-blue-800">Informacion importante</h4>
            <ul className="text-xs text-blue-700 mt-1 space-y-1">
              <li>Los respaldos son <strong>manuales</strong>: debe generarlos usted, no hay ninguno automatico</li>
              <li>Cada archivo es un respaldo logico de PostgreSQL, restaurable con <code>pg_restore</code></li>
              <li>El archivo se borra del servidor apenas termina la descarga: guardelo usted en su computadora</li>
              <li>Se recomienda generar uno por mes y guardarlo en la carpeta local GO_VISTA_BACKUPS</li>
              <li>El archivo contiene datos personales de clientes: no lo comparta ni lo envie por correo</li>
              <li>Descargar el archivo NO significa que su restauracion haya sido comprobada</li>
            </ul>
          </div>
        </div>
      </Card>

      {/* Confirm Create Modal */}
      {confirmCreate && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-6 space-y-4">
            <div className="text-center">
              <h2 className="text-xl font-black text-slate-900">Generar respaldo</h2>
              <p className="text-xs text-slate-400 mt-1">
                Se generara un archivo .dump con todos los datos y se descargara a esta computadora
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="secondary" size="lg" className="flex-1" onClick={() => setConfirmCreate(false)}>
                Cancelar
              </Button>
              <Button size="lg" className="flex-1" onClick={handleCreateBackup} disabled={creating}>
                {creating ? 'Generando...' : 'Generar y descargar'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Confirm Delete Modal */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-6 space-y-4">
            <div className="text-center">
              <h2 className="text-xl font-black text-slate-900">Eliminar registro</h2>
              <p className="text-xs text-slate-400 mt-1">
                Se eliminara el registro: {confirmDelete.filename}
              </p>
              <p className="text-xs text-amber-600 mt-2">
                Esto solo borra la anotacion del historial. No elimina ningun archivo de su computadora.
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="secondary" size="lg" className="flex-1" onClick={() => setConfirmDelete(null)}>
                Cancelar
              </Button>
              <Button variant="danger" size="lg" className="flex-1" onClick={() => handleDelete(confirmDelete)}>
                Eliminar
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
