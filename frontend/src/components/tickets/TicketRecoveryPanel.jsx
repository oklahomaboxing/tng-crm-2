import React, { useEffect, useState } from 'react';
import './TicketRecoveryPanel.css';
const API = (import.meta.env.VITE_API_URL || 'https://sea-lion-app-2-gxyfr.ondigitalocean.app').replace(/\/$/, '');
const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format((value || 0) / 100);
const headers = () => ({ Authorization: `Bearer ${localStorage.getItem('token')}`, 'Content-Type': 'application/json' });

export default function TicketRecoveryPanel({ eventId, onChanged }) {
  const [data, setData] = useState(null), [q, setQ] = useState(''), [issue, setIssue] = useState('all');
  const [page, setPage] = useState(1), [revision, setRevision] = useState(0), [loading, setLoading] = useState(true);
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [busy, setBusy] = useState(null);
  const [selected, setSelected] = useState(null), [cloverOrder, setCloverOrder] = useState(''), [checkout, setCheckout] = useState('');
  const [ticketUrl, setTicketUrl] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams({ q, issue, page, page_size: 25 });
        const response = await fetch(`${API}/api/ticketing/events/${eventId}/recovery-dashboard?${params}`, { headers: headers(), signal: controller.signal });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Could not load order recovery');
        setData(result);
      } catch (e) { if (e.name !== 'AbortError') setError(e.message); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [eventId, q, issue, page, revision]);

  async function action(order, type) {
    if (busy) return;
    setBusy(order.order_id); setError(''); setNotice(''); setTicketUrl('');
    try {
      const path = type === 'view' ? 'ticket-page' : type === 'verify' ? 'reconcile-clover' : 'recover';
      const response = await fetch(`${API}/api/ticketing/orders/${order.order_id}/${path}`, {
        method: type === 'view' ? 'GET' : 'POST', headers: headers(),
        ...(type === 'verify' ? { body: JSON.stringify({ clover_order_id: cloverOrder.trim(), confirm_checkout_id: checkout.trim() }) } : {}),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Request could not be completed');
      setTicketUrl(result.ticket_url || '');
      setNotice(type === 'view' ? `Order #${order.order_id}: ticket page ready.` : `Order #${order.order_id} processed. Review the updated ticket and delivery statuses below. Provider acceptance does not confirm handset delivery.`);
      if (type !== 'view') { setSelected(null); setRevision(v => v + 1); onChanged?.(); }
    } catch (e) { setError(`${e.message}. If the connection failed, refresh statuses before retrying.`); }
    finally { setBusy(null); }
  }
  const summary = data?.summary;
  return <section className="ticket-recovery" aria-label="Ticket recovery">
    <header><div><p className="recovery-eyebrow">CUSTOMER SUPPORT</p><h2>Orders & ticket recovery</h2><p>Find paid purchases, missing tickets, delivery problems, and fighter credit.</p></div>
      <button type="button" disabled={loading || !!busy} onClick={() => setRevision(v => v + 1)}>Refresh statuses</button></header>
    {summary && <div className="recovery-stats">
      {[[money(summary.paid_total_cents), 'Recorded paid sales'], [summary.needs_attention, 'Paid orders needing attention'], [summary.pending_orders, 'Payment pending'], [summary.unattributed_paid_orders, 'Paid orders without seller'], [money(summary.commission_earned_cents), 'Commission earned']].map(([value, label]) => <div key={label}><strong>{value}</strong><span>{label}</span></div>)}
    </div>}
    <p className="recovery-note">Commission is earned on valid or used tickets; it is not a payout balance. Pending payment does not prove a customer paid. Email “sent” means accepted by the provider; SMS “delivered” is a carrier confirmation.</p>
    <div className="recovery-filters"><label>Search orders<input value={q} placeholder="Customer, receipt, fighter, or payment reference" onChange={e => { setQ(e.target.value); setPage(1); }} /></label>
      <label>Show<select value={issue} onChange={e => { setIssue(e.target.value); setPage(1); }}><option value="all">All orders</option><option value="attention">Paid orders needing attention</option><option value="pending">Payment pending</option><option value="unattributed">Paid orders without seller</option></select></label></div>
    {error && <p role="alert" className="recovery-error">{error}</p>}
    {notice && <div role="status" className="recovery-notice">{notice} {ticketUrl && <a href={ticketUrl} target="_blank" rel="noopener noreferrer">Open private ticket page</a>}</div>}
    {loading ? <p role="status">Loading orders…</p> : !error && data && <>
      <div className="recovery-table"><table><thead><tr><th>Customer / order</th><th>Payment</th><th>Tickets / fighter</th><th>Delivery</th><th>Next step</th></tr></thead><tbody>
        {data.orders.map(order => <tr key={order.order_id}>
          <td><strong>{order.buyer_name}</strong><span>{order.buyer_email}</span><span>#{order.order_id} · {order.receipt_number}</span><small>{order.created_at ? new Date(`${order.created_at}Z`).toLocaleString() : ''}</small></td>
          <td><strong>{money(order.total_cents)}</strong>{order.payment_provider === 'paper_cash' && <small>Paper cash sale · staff recorded</small>}<span className={`recovery-badge ${order.payment_status === 'paid' ? 'paid' : ''}`}>{order.payment_status}</span>{order.payment_id && <small>Payment: {order.payment_id}</small>}{order.clover_checkout_id && <small>Checkout: {order.clover_checkout_id}</small>}</td>
          <td><strong>{order.issued_tickets} / {order.expected_tickets ?? '?'} issued</strong><span>{order.usable_tickets} valid or used</span><span>{order.seller_name || (order.seller_id ? `Seller #${order.seller_id}` : 'No seller attribution')}</span><small>Commission: {money(order.commission_cents)}</small></td>
          <td>{order.payment_provider === 'paper_cash' ? <span>Printed ticket · no messages</span> : order.deliveries.length ? order.deliveries.map(d => <div className="recovery-delivery" key={d.channel}><strong>{d.channel.toUpperCase()}: {d.status}</strong><small>{d.attempts} attempt(s){d.last_error ? ` · ${d.last_error}` : ''}</small></div>) : <span>Not queued</span>}</td>
          <td>{order.issues.map(text => <small className="recovery-warning" key={text}>{text}</small>)}<div className="recovery-actions">
            {order.payment_status === 'paid' && order.usable_tickets > 0 && <button disabled={!!busy} onClick={() => action(order, 'view')}>View tickets</button>}
            {order.can_recover && order.issues.length > 0 && <button disabled={!!busy} onClick={() => { if (window.confirm(`Recover order #${order.order_id}? This may issue missing tickets and retry unsuccessful ticket notifications to the saved customer contacts. Accepted deliveries are skipped. No payment is charged.`)) action(order, 'recover'); }}>Recover / retry</button>}
            {order.payment_status === 'paid' && !order.can_recover && order.issues.length > 0 && <small>Manual ticket review required; automatic recovery is blocked.</small>}
            {data.can_reconcile && ['pending', 'failed'].includes(order.payment_status) && order.clover_checkout_id && <button disabled={!!busy} onClick={() => { setSelected(order); setCloverOrder(''); setCheckout(''); setError(''); }}>Verify Clover payment</button>}
            {order.payment_status === 'pending' && !order.clover_checkout_id && <small>No checkout recorded. Investigate before issuing tickets.</small>}
          </div></td>
        </tr>)}
        {!data.orders.length && <tr><td colSpan="5">No orders match these filters.</td></tr>}
      </tbody></table></div>
      <footer><span>{data.total} matching orders · Page {page} of {Math.max(1, Math.ceil(data.total / 25))}</span><div><button disabled={page <= 1 || !!busy} onClick={() => setPage(p => p - 1)}>Previous</button> <button disabled={page * 25 >= data.total || !!busy} onClick={() => setPage(p => p + 1)}>Next</button></div></footer>
    </>}
    {selected && <div className="recovery-modal"><form role="dialog" aria-modal="true" aria-labelledby="reconcile-title" onSubmit={e => { e.preventDefault(); action(selected, 'verify'); }}>
      <h3 id="reconcile-title">Verify payment for order #{selected.order_id}</h3>{error && <p role="alert" className="recovery-error">{error}</p>}<p>Confirm in Clover that this receipt belongs to this customer's checkout. The server checks payment amounts, payment association, refunds, and duplicate assignment before issuing tickets. Matching amounts alone are not enough.</p>
      <p>{selected.buyer_name} · {money(selected.total_cents)}</p><p>Saved checkout: <strong>{selected.clover_checkout_id}</strong></p>
      <label>Clover order ID<input required maxLength={100} pattern="[A-Za-z0-9_-]+" value={cloverOrder} onChange={e => setCloverOrder(e.target.value)} /></label>
      <label>Re-enter the saved checkout ID<input required value={checkout} onChange={e => setCheckout(e.target.value)} /></label>
      <p>This action may issue tickets and send ticket notifications after payment is verified. It does not charge the customer.</p>
      <div className="recovery-actions"><button type="button" disabled={!!busy} onClick={() => setSelected(null)}>Cancel</button><button disabled={!!busy || checkout.trim() !== selected.clover_checkout_id || !cloverOrder.trim()}>{busy ? 'Verifying…' : 'Verify payment & recover'}</button></div>
    </form></div>}
  </section>;
}
