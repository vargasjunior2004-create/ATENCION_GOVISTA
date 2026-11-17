import React from 'react';
import { Link } from 'react-router-dom';
import { Alert, Button } from '../../components/ui';

export default class AtencionesErrorBoundary extends React.Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    // Mantiene el detalle en consola para diagnosticar errores de renderizado.
    console.error('Error en el módulo de atenciones:', error);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <Alert type="error">No fue posible mostrar esta sección.</Alert>
        <div className="flex gap-2">
          <Button type="button" onClick={() => this.setState({ hasError: false })}>
            Intentar nuevamente
          </Button>
          <Link className="inline-flex items-center rounded-xl bg-slate-100 px-4 py-2.5 text-sm font-semibold text-slate-700" to="/atenciones/dashboard">
            Ir al dashboard
          </Link>
        </div>
      </div>
    );
  }
}
