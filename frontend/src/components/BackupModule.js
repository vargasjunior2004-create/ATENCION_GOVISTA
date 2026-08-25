import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Button, Card, Alert } from './ui';

function formatBytes(bytes) {
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

export default function BackupModule() {
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [msg, setMsg] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [confirmCreate, setConfirmCreate] = useState(false);

  const loadBackups = useCallback(async () => {
    try {
      const data = await api.getBackups();
      setBackups(data);
    } catch (err) {
      console.error(err);
      setMsg('Error al cargar backups');
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
      const res = await api.createBackup();
      setMsg(`Backup creado: ${res.backup.filename}`);
      loadBackups();
    } catch (err) {
      setMsg(err.error || 'Error al crear backup');
    } finally {
      setCreating(false);
    }
  };

  const handleDownload = async (backup) => {
    try {
      const blob = await api.downloadBackup(backup.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = backup.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setMsg('Error al descargar backup');
    }
  };

  const handleDelete = async (backup) => {
    try {
      await api.deleteBackup(backup.id);
      setMsg('Backup eliminado');
      setConfirmDelete(null);
      loadBackups();
    } catch (err) {
      setMsg(err.error || 'Error al eliminar backup');
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

  const latestBackup = backups.length > 0 ? backups[0] : null;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Copias de Seguridad</h1>
          <p className="text-sm text-slate-400 mt-1">Backup y restauracion de la base de datos</p>
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
          {creating ? 'Creando...' : 'Crear backup ahora'}
        </Button>
      </div>

      {msg && (
        <Alert type={msg.includes('Error') ? 'error' : 'success'}>
          {msg}
        </Alert>
      )}

      {/* Latest backup info */}
      <Card className="p-6">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">
          Ultimo Backup
        </h3>
        {latestBackup ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-slate-400">Fecha</p>
              <p className="text-sm font-bold text-slate-700">{formatDate(latestBackup.created_at)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Tipo</p>
              <span className={`inline-block text-xs font-bold px-2 py-0.5 rounded-full ${
                latestBackup.backup_type === 'automatic'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-green-100 text-green-700'
              }`}>
                {latestBackup.backup_type === 'automatic' ? 'Automatico' : 'Manual'}
              </span>
            </div>
            <div>
              <p className="text-xs text-slate-400">Tamano</p>
              <p className="text-sm font-bold text-slate-700">{formatBytes(latestBackup.size)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Estado</p>
              <span className={`inline-block text-xs font-bold px-2 py-0.5 rounded-full ${
                latestBackup.status === 'success'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-red-100 text-red-700'
              }`}>
                {latestBackup.status === 'success' ? 'Correcto' : 'Fallido'}
              </span>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-400">No hay backups registrados</p>
        )}
      </Card>

      {/* History */}
      <div>
        <h3 className="text-lg font-black text-slate-900 mb-4">Historial</h3>
        {backups.length === 0 ? (
          <Card className="p-8 text-center">
            <p className="text-slate-400">No hay backups registrados</p>
          </Card>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">Fecha</th>
                  <th className="text-left text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">Tipo</th>
                  <th className="text-left text-xs font-bold text-slate-400 uppercase tracking-wider py-3 px-4">Tamaño</th>
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
                      <span className={`inline-block text-xs font-bold px-2 py-0.5 rounded-full ${
                        b.backup_type === 'automatic'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-green-100 text-green-700'
                      }`}>
                        {b.backup_type === 'automatic' ? 'Automatico' : 'Manual'}
                      </span>
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
                      <span className={`inline-block text-xs font-bold px-2 py-0.5 rounded-full ${
                        b.status === 'success'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}>
                        {b.status === 'success' ? 'Correcto' : 'Fallido'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleDownload(b)}
                        >
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                          </svg>
                          Descargar
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setConfirmDelete(b)}
                        >
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                          </svg>
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info */}
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
              <li>Backups automaticos se crean diariamente a las 23:30 (America/La_Paz)</li>
              <li>Se conservan los ultimos 7 backups automaticos</li>
              <li>Los backups manuales no se eliminan automaticamente</li>
              <li>Cada backup incluye un checksum SHA-256 para verificacion de integridad</li>
              <li>La restauracion debe realizarse manualmente desde la linea de comandos</li>
            </ul>
          </div>
        </div>
      </Card>

      {/* Confirm Create Modal */}
      {confirmCreate && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-3xl shadow-2xl max-w-md w-full p-6 space-y-4">
            <div className="text-center">
              <h2 className="text-xl font-black text-slate-900">Crear Backup</h2>
              <p className="text-xs text-slate-400 mt-1">Se creara una copia de seguridad de la base de datos</p>
            </div>
            <div className="flex gap-3">
              <Button variant="secondary" size="lg" className="flex-1" onClick={() => setConfirmCreate(false)}>
                Cancelar
              </Button>
              <Button size="lg" className="flex-1" onClick={handleCreateBackup} disabled={creating}>
                {creating ? 'Creando...' : 'Confirmar'}
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
              <h2 className="text-xl font-black text-slate-900">Eliminar Backup</h2>
              <p className="text-xs text-slate-400 mt-1">
                Se eliminara permanentemente: {confirmDelete.filename}
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
