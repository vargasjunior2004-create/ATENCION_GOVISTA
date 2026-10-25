import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';

export default function LegacyRedirect({ to }) {
  const location = useLocation();
  return (
    <Navigate
      to={{ pathname: to, search: location.search, hash: location.hash }}
      replace
    />
  );
}
