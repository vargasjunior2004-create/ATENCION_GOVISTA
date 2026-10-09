import { useState, useEffect } from 'react';
import api from '../services/api';

// Los tipos de solicitud son un catalogo administrable, asi que el frontend
// no los codifica: se piden al backend. Lo unico que vive aqui es el color y
// el texto corto de cada MODO, que son presentacion, no reglas de negocio.
export const MODO_COLOR = {
  nuevo: 'green',
  retiro: 'red',
  cambio_plan: 'amber',
  adicion: 'blue',
  simple: 'slate',
};

export const MODO_LABEL = {
  nuevo: 'NUEVO CONTRATO',
  retiro: 'RETIRO',
  cambio_plan: 'CAMBIO DE PLAN',
  adicion: 'ADICION',
  simple: 'SIN REGLAS ESPECIALES',
};

/**
 * Catalogo de tipos de solicitud activos.
 *
 * El formulario decide que campos mostrar a partir del `modo` que devuelve
 * cada tipo, no comparando nombres. Por eso agregar un tipo con reglas
 * especiales desde el panel no requiere tocar este archivo.
 */
export default function useRequestTypes() {
  const [tipos, setTipos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let vivo = true;
    api.getActiveRequestTypes()
      .then((data) => { if (vivo) setTipos(data); })
      .catch(() => { if (vivo) setTipos([]); })
      .finally(() => { if (vivo) setLoading(false); });
    return () => { vivo = false; };
  }, []);

  const byCode = Object.fromEntries(tipos.map((t) => [t.code, t]));

  // Un code desconocido cae en 'simple', que es el mismo criterio del backend.
  const modoOf = (code) => byCode[code]?.modo || 'simple';

  const nombreOf = (code) => byCode[code]?.nombre || code || '';

  return { tipos, byCode, modoOf, nombreOf, loading };
}