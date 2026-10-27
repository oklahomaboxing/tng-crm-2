import React, { useEffect, useRef, useState } from 'react';
import './TicketRecoveryPanel.css';
import './PaperTicketDesign.css';
const API = (import.meta.env.VITE_API_URL || 'https://sea-lion-app-2-gxyfr.ondigitalocean.app').replace(/\/$/, '');
const money = n => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format((n || 0)/100);
const headers = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}`, 'Content-Type': 'application/json' });
async function request(path, options = {}) {
  const response = await fetch(`${API}/api/ticketing${path}`, { ...options, headers: headers() });
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'The paper ticket request could not be completed');
  return body;
}
export default function PaperTicketPanel({ eventId, event = {}, sellers = [], ticketTypes = [], onChanged }) {
  const [batches, setBatches] = useState([]), [detail, setDetail] = useState(null), [selected, setSelected] = useState([]);
  const [seller, setSeller] = useState(''), [kind, setKind] = useState(''), [quantity, setQuantity] = useState(20);
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState('');
  const layout='fight-night';
  const [sheetUrl,setSheetUrl] = useState(''),[sheetLoading,setSheetLoading] = useState(false),[sheetError,setSheetError] = useState('');
  const allocation = useRef(null);
  useEffect(()=>{
    let live=true,objectUrl='';const controller=new AbortController();
    setSheetUrl('');setSheetError('');
    if(!kind){setSheetLoading(false);return()=>controller.abort();}
    setSheetLoading(true);
    const timer=setTimeout(async()=>{
      try{
        const params=new URLSearchParams({layout,ticket_type_id:kind});if(seller)params.set('seller_id',seller);
        const r=await fetch(`${API}/api/ticketing/events/${eventId}/paper-ticket-preview.pdf?${params}`,{headers:headers(),signal:controller.signal});
        if(!r.ok){const body=await r.json();throw Error(body.detail || 'Could not load the sheet preview.');}
        const blob=await r.blob();if(!live)return;
        objectUrl=URL.createObjectURL(blob);setSheetUrl(objectUrl);
      }catch(e){if(live && e.name!=='AbortError')setSheetError(e.message || 'Could not load the sheet preview.');}
      finally{if(live)setSheetLoading(false);}
    },400);
    return()=>{live=false;clearTimeout(timer);controller.abort();if(objectUrl)URL.revokeObjectURL(objectUrl);};
  },[eventId,kind,seller,layout]);
  async function load() { const body = await request(`/events/${eventId}/paper-batches`); setBatches(body.batches); }
  useEffect(() => { let live = true; request(`/events/${eventId}/paper-batches`).then(body => { if (live) setBatches(body.batches); }).catch(e => { if (live) setError(e.message); }); return () => { live = false; }; }, [eventId]);
  async function openBatch(id) { const body = await request(`/paper-batches/${id}`); setDetail(body); setSelected([]); }
  async function run(action) { if (busy) return; setBusy(true); setError(''); setNotice(''); try { await action(); } catch (e) { setError(`${e.message}. If the connection failed, refresh batches and check their status before retrying.`); } finally { setBusy(false); } }
  async function create() {
    const qty = Number(quantity);
    if (!Number.isInteger(qty) || qty < 1 || qty > 200) { setError('Choose between 1 and 200 tickets.'); return; }
    if (!seller || !kind) { setError('Select a fighter/seller and ticket type.'); return; }
    if (!window.confirm(`Allocate ${qty} paper tickets to this seller? Printing does not record a sale or activate admission. Staff must record each sale before the customer arrives.`)) return;
    await run(async () => {
      const signature = JSON.stringify([seller, kind, qty]);
      if (allocation.current?.signature !== signature) allocation.current = { signature, key: crypto.randomUUID() };
      const body = await request(`/events/${eventId}/paper-batches`, { method: 'POST', body: JSON.stringify({ seller_id: Number(seller), ticket_type_id: Number(kind), quantity: qty, request_key: allocation.current.key }) });
      await load(); await openBatch(body.id); allocation.current = null;
      setNotice(`Batch #${body.id} created. Download the PDF below and print at Actual Size (100%). These tickets are not active until sales are recorded.`);
    });
  }
  async function download(id) {
    await run(async () => {
      const response = await fetch(`${API}/api/ticketing/paper-batches/${id}/print.pdf?layout=${layout}`, { headers: headers() });
      if (!response.ok) { const body = await response.json(); throw new Error(body.detail || 'Could not download ticket PDF'); }
      const blob = await response.blob(), url = URL.createObjectURL(blob), a = document.createElement('a');
      a.href = url; a.download = `TNG-event-${eventId}-paper-batch-${id}.pdf`; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice('PDF downloaded. Print on US Letter at Actual Size (100%), then cut along the dashed lines. Reprints use the same QR codes; do not distribute extra copies.');
    });
  }
  async function preview() {
    await run(async () => {
      const params=new URLSearchParams({layout,ticket_type_id:kind});if(seller)params.set('seller_id',seller);
      const response=await fetch(`${API}/api/ticketing/events/${eventId}/paper-ticket-preview.pdf?${params}`,{headers:headers()});
      if(!response.ok){const body=await response.json();throw new Error(body.detail || 'Could not preview ticket design');}
      const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');
      a.href=url;a.download=`TNG-event-${eventId}-design-preview.pdf`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
      setNotice('Sample design downloaded. It creates no tickets or sales and cannot be used for entry.');
    });
  }
  async function update(action) {
    if (!detail || !selected.length) return;
    const total = selected.length * detail.price_cents;
    const question = action === 'record-sales' ? `Confirm customers paid ${money(total)} for these ${selected.length} paper tickets. This activates admission and records cash sales and fighter commissions. It does not charge a card, send messages, or record money remitted by the fighter to TNG.` : `Return ${selected.length} unsold tickets? Their QR codes will be invalid permanently. Sold tickets cannot be returned here.`;
    if (!window.confirm(question)) return;
    await run(async () => {
      const body = { ticket_ids: selected, ...(action === 'record-sales' ? { confirm_total_cents: total } : {}) };
      await request(`/paper-batches/${detail.id}/${action}`, { method: 'POST', body: JSON.stringify(body) });
      await load(); await openBatch(detail.id); onChanged?.();
      setNotice(action === 'record-sales' ? 'Sales recorded. Selected tickets are now active. Fighter remittance must be reconciled separately.' : 'Unsold tickets returned. Their QR codes can no longer admit anyone.');
    });
  }
  const available = detail?.tickets.filter(t => t.status === 'allocated') || [];
  return <section className="ticket-recovery" aria-label="Paper event tickets">
    <header><div><p className="recovery-eyebrow">FIGHTER DISTRIBUTION</p><h2>Print paper tickets</h2><p>Branded, numbered QR tickets with your saved event details, assigned to a fighter or seller.</p></div><button disabled={busy} onClick={() => run(async () => { await load(); if (detail) await openBatch(detail.id); })}>Refresh batches</button></header>
    <div className="paper-design-preview" aria-label="Ticket style illustration">
      <div className="paper-design-main"><img src="/tng-ticket-logo.jpg" alt="TNG The Next Generation Boxing"/><small>OFFICIAL EVENT ADMISSION</small><h3>{event?.name || 'Your event ticket'}</h3><p>{event?.event_date || 'Saved event date'} · {event?.venue || 'Saved event venue'}</p><div>{ticketTypes.find(t=>String(t.id)===kind)?.name || 'Choose ticket type'}<strong>{kind ? money(ticketTypes.find(t=>String(t.id)===kind)?.price_cents) : 'FACE VALUE'}</strong></div></div>
      <div className="paper-design-stub"><strong>EVENT PASS</strong><span className="paper-design-qr">QR</span><small>Unique ticket number</small><small>Assigned fighter / seller</small></div>
    </div>
    <p className="recovery-note">The system fills the PDF from this event’s saved name, date, venue, address and published doors / first-bout times. Missing details stay marked as unannounced. Preview before printing.</p>
    <p className="recovery-note"><strong>Print format: 4 landscape tickets per US Letter sheet.</strong></p>
    <p className="recovery-note">Printed tickets start inactive. Record sales here before customers arrive. Unsold allocations do not count as sales or commissions. Cash sales are staff-recorded, not Clover-verified. Keep a record of the money fighters remit to TNG separately.</p>
    <div className="recovery-filters"><label>Fighter / seller<select value={seller} onChange={e => setSeller(e.target.value)} disabled={busy}><option value="">Choose seller</option>{sellers.map(s => <option key={s.seller_id} value={s.seller_id}>{s.display_name}</option>)}</select></label>
      <label>Ticket type<select value={kind} onChange={e => setKind(e.target.value)} disabled={busy}><option value="">Choose ticket type</option>{ticketTypes.filter(t => t.active).map(t => <option key={t.id} value={t.id}>{t.name} · {money(t.price_cents)}</option>)}</select></label>
      <label>Quantity<input type="number" min="1" max="200" step="1" value={quantity} disabled={busy} onChange={e => setQuantity(e.target.value)} /></label></div>
    <div className="paper-sheet-review">
      <div><h3>Print sheet preview</h3><p>US Letter · 8.5 × 11 inches · 4 tickets per page</p><p>Review the actual PDF layout before creating a batch. Sample QR codes cannot admit anyone. This preview creates no tickets or sales.</p></div>
      <div className="paper-sheet-frame">
        {sheetUrl?<iframe title="US Letter ticket sheet preview" src={`${sheetUrl}#toolbar=0&navpanes=0&view=FitH`} />:<div className="paper-sheet-placeholder" aria-label={'4 ticket positions on Letter paper'}>
          <span>{sheetLoading?'Loading sheet preview…':kind?'Preview unavailable':'Choose a ticket type to see your print sheet'}</span>
          <div className="paper-sheet-slots">{Array.from({length:4},(_,n)=><div key={n}>TICKET {n+1}</div>)}</div>
        </div>}
      </div>
    </div>
    {sheetError && <p role="alert" className="recovery-error">{sheetError} Use Preview design PDF to try downloading the sample.</p>}
    <div className="recovery-actions"><button disabled={busy || !kind} onClick={preview}>Preview design PDF · no allocation</button><button disabled={busy || !seller || !kind} onClick={create}>{busy ? 'Working…' : 'Create paper ticket batch'}</button></div>
    {!sellers.length && <p>Add fighters to the fight card, or repair ticket links above, to make sellers available.</p>}
    {error && <p role="alert" className="recovery-error">{error}</p>}{notice && <p role="status" className="recovery-notice">{notice}</p>}
    <div className="recovery-table" style={{ marginTop: 20 }}><table><thead><tr><th>Batch / seller</th><th>Ticket type</th><th>Unsold</th><th>Sold / returned</th><th>Recorded sales</th><th>Actions</th></tr></thead><tbody>
      {batches.map(b => <tr key={b.id}><td><strong>#{b.id} · {b.seller_name}</strong><small>{b.quantity} allocated originally</small></td><td>{b.ticket_type_name}<span>{money(b.price_cents)} each</span></td><td>{b.allocated}</td><td>{b.sold} sold · {b.returned} returned</td><td>{money(b.sold_total_cents)}<small>Commission: {money(b.commission_cents)}</small></td><td><div className="recovery-actions"><button disabled={busy} onClick={() => run(() => openBatch(b.id))}>Manage #{b.id}</button><button disabled={busy || b.returned === b.quantity} onClick={() => download(b.id)}>Download PDF #{b.id}</button></div></td></tr>)}
      {!batches.length && <tr><td colSpan="6">No paper batches created for this event yet.</td></tr>}
    </tbody></table></div>
    {detail && <div style={{ marginTop: 24 }}><h3>Batch #{detail.id} · {detail.seller_name}</h3><p>Select the exact ticket numbers sold or returned. Face value was saved when this batch was allocated. Commission uses the fighter’s terms when each sale is recorded.</p>
      <div className="recovery-actions"><button disabled={busy || !available.length} onClick={() => setSelected(available.map(t => t.id))}>Select all unsold</button><button disabled={busy} onClick={() => setSelected([])}>Clear selection</button><button disabled={busy || !selected.length} onClick={() => update('record-sales')}>Record {selected.length} cash sales · {money(selected.length * detail.price_cents)}</button><button disabled={busy || !selected.length} onClick={() => update('return-unsold')}>Return selected unsold</button><button disabled={busy} onClick={() => download(detail.id)}>Download batch PDF</button></div>
      <div className="recovery-table"><table><thead><tr><th>Select</th><th>Ticket number</th><th>Status</th><th>Order</th></tr></thead><tbody>{detail.tickets.map(t => <tr key={t.id}><td><input style={{ width: 20 }} type="checkbox" aria-label={`Select ${t.ticket_number}`} disabled={busy || t.status !== 'allocated'} checked={selected.includes(t.id)} onChange={e => setSelected(current => e.target.checked ? [...current, t.id] : current.filter(id => id !== t.id))} /></td><td>{t.ticket_number}</td><td>{t.status === 'allocated' ? 'Unsold · inactive' : t.status === 'sold' ? 'Sale recorded' : 'Returned · invalid'}</td><td>{t.order_id ? `#${t.order_id}` : '—'}</td></tr>)}</tbody></table></div>
    </div>}
  </section>;
}
