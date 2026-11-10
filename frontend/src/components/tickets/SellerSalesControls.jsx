import React, { useEffect, useState } from 'react';
const API = (import.meta.env.VITE_API_URL || 'https://sea-lion-app-2-gxyfr.ondigitalocean.app').replace(/\/$/, '');
const headers = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}`, 'Content-Type': 'application/json' });
export default function SellerSalesControls({ eventId, sellers, onChanged }) {
  const [settings, setSettings] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  useEffect(() => {
    let alive = true;
    setSettings(null);
    fetch(`${API}/api/ticketing/events/${eventId}/sales-window`, { headers: headers() })
      .then(async r => { const data = await r.json(); if (!r.ok) throw Error(data.detail || 'Could not load sales settings'); return data; })
      .then(data => { if (alive) setSettings(data); }).catch(e => { if (alive) setMessage(e.message); });
    return () => { alive = false; };
  }, [eventId]);
  async function update(path, method, body) {
    setBusy(true); setMessage('');
    try {
      const r = await fetch(`${API}/api/ticketing/events/${eventId}/${path}`, { method, headers: headers(), body: JSON.stringify(body) });
      const data = await r.json();
      if (!r.ok) throw Error(data.detail || 'Could not save sales settings');
      if (path === 'sales-window') setSettings(data);
      await onChanged(); setMessage('Sales settings saved. Purchased tickets remain valid.');
    } catch (e) { setMessage(e.message); } finally { setBusy(false); }
  }
  return <section aria-label="Ticket sales controls" style={{ padding: 20, marginTop: 24, border: '1px solid #ddd', borderRadius: 12 }}>
    <h2>Ticket sales controls</h2>
    <p>Pause individual seller links or schedule an event cutoff. Existing purchases, commissions and admission remain unchanged.</p>
    {message && <p role="status">{message}</p>}
    {settings && <div>
      <label>Automatic cutoff — Oklahoma time <input type="datetime-local" value={settings.cutoff_local || ''} onChange={e => setSettings({ ...settings, cutoff_local: e.target.value })} /></label>
      <p>Leave blank for no automatic cutoff. Midnight after Friday is Saturday at 12:00 AM.</p>
      <fieldset disabled={busy}><legend>Sellers allowed after cutoff</legend>
        {sellers.map(s => <label key={s.seller_id} style={{ display: 'inline-block', margin: 8 }}><input type="checkbox" checked={settings.exempt_seller_ids.includes(s.seller_id)} onChange={e => setSettings({ ...settings, exempt_seller_ids: e.target.checked ? [...settings.exempt_seller_ids, s.seller_id] : settings.exempt_seller_ids.filter(id => id !== s.seller_id) })} /> {s.display_name}</label>)}
      </fieldset>
      <p><label>After cutoff, reroute customers to <select value={settings.redirect_seller_id || ''} onChange={e => setSettings({ ...settings, redirect_seller_id: Number(e.target.value) || null })}><option value="">No redirect</option>{sellers.filter(s => settings.exempt_seller_ids.includes(s.seller_id)).map(s => <option key={s.seller_id} value={s.seller_id}>{s.display_name}</option>)}</select></label></p>
      <button disabled={busy} onClick={() => update('sales-window', 'PUT', { cutoff_local: settings.cutoff_local || null, exempt_seller_ids: settings.exempt_seller_ids, redirect_seller_id: settings.exempt_seller_ids.includes(settings.redirect_seller_id) ? settings.redirect_seller_id : null })}>Save automatic cutoff</button>
    </div>}
    <div style={{ overflowX: 'auto', marginTop: 16 }}><table width="100%" cellPadding="10"><thead><tr><th align="left">Seller</th><th>New sales</th><th>Control</th></tr></thead><tbody>
      {sellers.map(s => <tr key={s.seller_id}><td>{s.display_name}</td><td align="center">{s.sales_status === 'paused' ? 'Paused' : s.sales_status === 'cutoff' ? 'Closed by cutoff' : 'Open'}{s.cutoff_exempt && ' · Cutoff exempt'}</td><td align="center"><button disabled={busy} onClick={() => update(`sellers/${s.seller_id}/sales`, 'PATCH', { active: !s.active })}>{s.active ? 'Deactivate sales' : 'Activate sales'}</button></td></tr>)}
    </tbody></table></div>
    <p style={{ color: '#666', fontSize: 13 }}>Activating a seller does not override the event cutoff. Unattributed website sales also close at the cutoff. Clover payment pages already opened may still accept payment; any confirmed payments will still receive tickets.</p>
  </section>;
}
