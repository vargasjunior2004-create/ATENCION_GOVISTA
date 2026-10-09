import { useState, useEffect } from 'react';
import api from '../services/api';

// Los motivos son un catalogo administrable: el frontend no codifica la
// lista. Cada motivo pertenece a una categoria ('cambio' o 'retiro') y solo
// se ofrece en el formulario que corresponde.
export const MOTIVO_CATEGORIA_LABEL = {
  cambio: 'Motivo del cambio',
  retiro: 'Motivo del retiro',
};

/**
 * Motivos activos, indexados por categoria e id.
 *
 * Devuelve `porCategoria(categoria)` para poblar el selector del formulario
 * y `nombreOf(id)` para mostrar el nombre del motivo guardado.
 */
export default function useMotivos() {
  const [motivos, setMotivos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let vivo = true;
    api.getActiveMotivos()
      .then((data) => { if (vivo) setMotivos(data); })
      .catch(() => { if (vivo) setMotivos([]); })
      .finally(() => { if (vivo) setLoading(false); });
    return () => { vivo = false; };
  }, []);

  const porCategoria = (categoria) =>
    motivos.filter((m) => m.categoria === categoria);

  const byId = Object.fromEntries(motivos.map((m) => [m.id, m]));

  const nombreOf = (id) => byId[id]?.nombre || '';

  return { motivos, porCategoria, byId, nombreOf, loading };
}
