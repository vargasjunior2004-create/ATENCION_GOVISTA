import { useCallback, useEffect, useState } from 'react';
import api from '../services/api';

/**
 * Canales de captación activos para el formulario comercial.
 *
 * El catálogo es administrable: el frontend no codifica la lista. Se
 * recarga al montar el formulario y expone `reload()` para refrescarlo
 * después de crear o desactivar canales.
 */
export default function useCanalesCaptacion() {
  const [canales, setCanales] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const reload = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getActiveCanalesCaptacion();
      setCanales(data);
    } catch (err) {
      setCanales([]);
      setError(err?.error || 'No se pudieron cargar los canales de captación.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const byId = Object.fromEntries(canales.map((canal) => [canal.id, canal]));
  const nombreOf = (id) => byId[id]?.nombre || '';

  return { canales, loading, error, byId, nombreOf, reload };
}
