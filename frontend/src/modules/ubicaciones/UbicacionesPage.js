import React, { useEffect, useRef, useState } from 'react';
import { Camera, CheckCircle2, ExternalLink, History, LocateFixed, MapPin, Search, Upload, UserRound } from 'lucide-react';
import api from '../../services/api';
import { Alert, Badge, Button, Card, Input } from '../../components/ui';

async function compressPhoto(file) {
  if (!file || file.size <= 5 * 1024 * 1024) return file;
  const image = await new Promise((resolve, reject) => {
    const value = new Image();
    value.onload = () => resolve(value);
    value.onerror = reject;
    value.src = URL.createObjectURL(file);
  });
  const scale = Math.min(1, 1800 / Math.max(image.width, image.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(image.width * scale);
  canvas.height = Math.round(image.height * scale);
  canvas.getContext('2d').drawImage(image, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve) => canvas.toBlob(
    (blob) => resolve(new File([blob], 'fachada.jpg', { type: 'image/jpeg' })),
    'image/jpeg', 0.84,
  ));
}

function mapsUrl(location) {
  if (location.maps_url) return location.maps_url;
  if (location.latitude != null && location.longitude != null) {
    return `https://www.google.com/maps?q=${location.latitude},${location.longitude}`;
  }
  return '';
}

export default function UbicacionesPage() {
  const [query, setQuery] = useState('');
  const [customers, setCustomers] = useState([]);
  const [customer, setCustomer] = useState(null);
  const [location, setLocation] = useState(null);
  const [history, setHistory] = useState([]);
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState('');
  const [gps, setGps] = useState(null);
  const [mapsUrlValue, setMapsUrlValue] = useState('');
  const [source, setSource] = useState('gps');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const inputRef = useRef(null);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const chooseCustomer = async (item) => {
    setCustomer(item); setCustomers([]); setError(''); setMessage(''); setLocation(null); setHistory([]);
    try {
      const existing = await api.searchLocationCustomers(item.code);
      const found = existing.find((value) => value.customer === item.id);
      if (found) {
        setLocation(found);
        setMapsUrlValue(found.maps_url || '');
        setSource(found.source || 'gps');
        setGps(found.latitude != null ? { latitude: found.latitude, longitude: found.longitude, accuracy_meters: found.accuracy_meters } : null);
        if (Number(found.accuracy_meters) > 50) setMessage('Advertencia: el último GPS tiene una precisión superior a 50 metros.');
      }
    } catch (err) { setError(err.error || 'No fue posible consultar la ubicación existente'); }
  };

  const search = async () => {
    setError('');
    if (!query.trim()) return setCustomers([]);
    try { setCustomers(await api.searchCustomers(query.trim())); } catch (err) { setError(err.error || 'No fue posible buscar el cliente'); }
  };

  const capturePhoto = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const optimized = await compressPhoto(file);
      setPhoto(optimized);
      if (preview) URL.revokeObjectURL(preview);
      setPreview(URL.createObjectURL(optimized));
    } catch { setError('No fue posible preparar la fotografía'); }
    event.target.value = '';
  };

  const captureGps = () => {
    setError('');
    if (!navigator.geolocation) return setError('Este dispositivo no permite capturar GPS');
    navigator.geolocation.getCurrentPosition(
      ({ coords, timestamp }) => {
        setGps({ latitude: coords.latitude, longitude: coords.longitude, accuracy_meters: coords.accuracy, captured_at: new Date(timestamp).toISOString() });
        setSource('gps');
        setMessage(coords.accuracy > 50 ? 'Ubicación capturada. Advertencia: precisión superior a 50 metros.' : 'Ubicación GPS capturada.');
      },
      () => setError('Permiso de ubicación denegado o no disponible. Puedes pegar un enlace de Google Maps.'),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  };

  const save = async () => {
    setError(''); setMessage('');
    if (!customer) return setError('Busca y selecciona un cliente válido');
    if (!location && !photo) return setError('La fotografía de fachada es obligatoria');
    if (source === 'gps' && !gps) return setError('Captura la ubicación GPS');
    if (source === 'maps_url' && !mapsUrlValue.trim()) return setError('Pega una URL de Google Maps');
    const data = new FormData();
    if (!location) data.append('customer', customer.id);
    if (photo) data.append('photo', photo);
    data.append('source', source);
    if (gps) {
      data.append('latitude', gps.latitude); data.append('longitude', gps.longitude);
      if (gps.accuracy_meters != null) data.append('accuracy_meters', gps.accuracy_meters);
      if (gps.captured_at) data.append('captured_at', gps.captured_at);
    }
    if (mapsUrlValue) data.append('maps_url', mapsUrlValue.trim());
    setBusy(true);
    try {
      const result = location ? await api.updateCustomerLocation(location.id, data) : await api.createCustomerLocation(data);
      setLocation(result); setPhoto(null); setMessage('Ubicación del cliente guardada correctamente.');
      setPreview('');
    } catch (err) { setError(err.error || 'No fue posible guardar la ubicación'); }
    finally { setBusy(false); }
  };

  const loadHistory = async () => {
    if (!location) return;
    try { setHistory(await api.getCustomerLocationHistory(location.id)); } catch (err) { setError(err.error || 'No fue posible cargar el historial'); }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <header>
        <p className="text-xs font-black uppercase tracking-[0.18em] text-brand-600">Ubicación de Clientes</p>
        <h1 className="mt-2 text-2xl font-black text-slate-900">Registrar fachada y ubicación</h1>
        <p className="mt-1 text-sm text-slate-500">Busca el kardex, toma una foto y registra el domicilio.</p>
      </header>
      {message && <Alert type="success">{message}</Alert>}
      {error && <Alert type="error">{error}</Alert>}
      <Card className="space-y-3 p-4 sm:p-6">
        <div className="flex gap-2">
          <Input label="Código de cliente / kardex" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()} placeholder="Ej. KDX-12345" />
          <Button type="button" className="mt-6 shrink-0" onClick={search} aria-label="Buscar cliente"><Search className="h-5 w-5" /></Button>
        </div>
        {customers.length > 0 && <div className="divide-y rounded-xl border border-slate-200">{customers.map((item) => <button type="button" key={item.id} onClick={() => chooseCustomer(item)} className="flex w-full items-center gap-3 p-3 text-left hover:bg-slate-50"><UserRound className="h-5 w-5 text-brand-600" /><span><strong className="block text-sm">{item.code}</strong><span className="text-xs text-slate-500">{item.name}</span></span></button>)}</div>}
        {customer && <div className="rounded-xl bg-brand-50 p-3"><p className="text-xs font-bold uppercase text-brand-700">Cliente seleccionado</p><p className="mt-1 font-black text-slate-900">{customer.code} · {customer.name}</p></div>}
      </Card>

      {customer && <>
        <Card className="space-y-4 p-4 sm:p-6">
          <div className="flex items-center justify-between"><h2 className="font-black text-slate-900">Fotografía de fachada</h2><Camera className="h-5 w-5 text-brand-600" /></div>
          {preview || location?.photoUrl ? <img src={preview || location.photoUrl} alt="Fachada del cliente" className="max-h-64 w-full rounded-xl object-cover" /> : <div className="rounded-xl border-2 border-dashed border-slate-200 p-8 text-center text-sm text-slate-400">Aún no hay fotografía</div>}
          <input ref={inputRef} className="hidden" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={capturePhoto} />
          <Button type="button" variant="secondary" className="w-full py-3" onClick={() => inputRef.current?.click()}><Camera className="h-5 w-5" /> {location ? 'Reemplazar fotografía' : 'Tomar fotografía de fachada'}</Button>
        </Card>

        <Card className="space-y-4 p-4 sm:p-6">
          <h2 className="font-black text-slate-900">Ubicación del domicilio</h2>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2"><Button type="button" variant={source === 'gps' ? 'primary' : 'secondary'} className="py-3" onClick={captureGps}><LocateFixed className="h-5 w-5" /> Capturar ubicación</Button><Button type="button" variant={source === 'maps_url' ? 'primary' : 'secondary'} className="py-3" onClick={() => setSource('maps_url')}><MapPin className="h-5 w-5" /> Pegar Google Maps</Button></div>
          {source === 'gps' && gps && <div className="rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800"><CheckCircle2 className="mr-2 inline h-4 w-4" /> GPS capturado: {Number(gps.latitude).toFixed(6)}, {Number(gps.longitude).toFixed(6)}{gps.accuracy_meters != null && ` · precisión ${Math.round(gps.accuracy_meters)} m`}</div>}
          {source === 'maps_url' && <Input label="Enlace de Google Maps" value={mapsUrlValue} onChange={(e) => setMapsUrlValue(e.target.value)} placeholder="https://maps.google.com/..." />}
          {(mapsUrl(location) || (source === 'gps' && gps)) && <a className="inline-flex items-center gap-2 text-sm font-bold text-brand-700" target="_blank" rel="noreferrer" href={mapsUrl({ maps_url: mapsUrlValue, latitude: gps?.latitude || location?.latitude, longitude: gps?.longitude || location?.longitude })}><ExternalLink className="h-4 w-4" /> Abrir en Google Maps</a>}
          <Button type="button" className="w-full py-4 text-base" disabled={busy} onClick={save}><Upload className="h-5 w-5" /> {busy ? 'Guardando...' : 'GUARDAR UBICACIÓN DEL CLIENTE'}</Button>
        </Card>

        {location && <Card className="p-4 sm:p-6"><div className="flex items-center justify-between gap-3"><div><p className="text-xs font-bold uppercase text-slate-400">Última actualización</p><p className="mt-1 text-sm font-bold text-slate-800">{new Date(location.updated_at).toLocaleString('es-BO')}</p><p className="text-xs text-slate-500">Responsable: {location.updatedBy}</p></div><Button type="button" variant="secondary" onClick={loadHistory}><History className="h-4 w-4" /> Historial</Button></div>{history.length > 0 && <div className="mt-4 space-y-2">{history.map((item) => <div key={item.id} className="rounded-lg bg-slate-50 p-3 text-xs"><strong>{item.change_type === 'created' ? 'Registro inicial' : 'Actualización'}</strong> · {item.changedBy} · {new Date(item.changed_at).toLocaleString('es-BO')}</div>)}</div>}</Card>}
      </>}
    </div>
  );
}
