import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Alert, Box, Button, Card, Chip, CircularProgress, MenuItem, Stack, Tab, Tabs, TextField, Typography } from '@mui/material';
const BASE=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'');
const money=v=>v==null?'Not recorded':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'}).format(v/100);
const auth=()=>({Authorization:`Bearer ${localStorage.getItem('token')}`});
function PaymentRow({ row, kind, eventId, reload }) {
  const purse=kind==='purses', paid=purse?row.purse_paid_cents:row.commission_paid_cents;
  const [amount,setAmount]=useState(paid==null?'':(paid/100).toFixed(2));
  const [date,setDate]=useState((purse?row.purse_paid_date:row.paid_date)||'');
  const [notes,setNotes]=useState((purse?row.purse_notes:row.notes)||'');
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const due=purse?row.net_obligation_cents:row.commission_earned_cents;
  async function save(){setBusy(true);setError('');try {
    if(!/^\d+(\.\d{1,2})?$/.test(amount))throw Error('Enter a nonnegative amount with at most two decimal places.');
    await axios.put(`${BASE}/api/events/${eventId}/recap/${kind}/${purse?row.fighter_id:row.seller_id}`,{amount_paid:amount,paid_date:date||null,notes,...(purse?{version:row.purse_version}:{previous_id:row.previous_payout_id})},{headers:auth()});await reload();
  }catch(e){setError(e.response?.data?.detail && typeof e.response.data.detail==='string'?e.response.data.detail:e.message||'Unable to save.');}finally{setBusy(false);}}
  return <Card variant="outlined" sx={{p:2}}><Typography variant="h6">{row.name}</Typography><Typography color="text.secondary">{purse?'Net purse obligation':'Earned ticket commission'}: {money(due)} · Paid: {money(paid)} · {paid==null?'Payment status unknown':`Remaining: ${money(Math.max(0,due-paid))}`}</Typography>
    {purse&&<Typography variant="caption">{row.basis.join(' / ')}</Typography>}
    <Stack direction={{xs:'column',md:'row'}} spacing={2} sx={{mt:2}}>
      <TextField label="Total paid to date ($)" value={amount} onChange={e=>setAmount(e.target.value)} inputProps={{inputMode:'decimal'}} disabled={busy}/>
      <TextField label="Payment date (optional)" type="date" InputLabelProps={{shrink:true}} value={date} onChange={e=>setDate(e.target.value)} disabled={busy}/>
      <TextField label="Payment note / reference" value={notes} onChange={e=>setNotes(e.target.value)} inputProps={{maxLength:1000}} sx={{flex:1}} disabled={busy}/>
      <Button variant="contained" onClick={save} disabled={busy||amount===''}>{busy?'Saving…':purse?'Save paid purse':'Save commission payment'}</Button>
    </Stack>{error&&<Alert severity="error" sx={{mt:1}}>{error}</Alert>}
  </Card>;
}
function ExpenseRow({row,eventId,reload}){
  const [kind,setKind]=useState(row.treatment),[busy,setBusy]=useState(false),[error,setError]=useState('');
  async function save(){setBusy(true);try{await axios.put(`${BASE}/api/events/${eventId}/recap/expenses/${row.id}`,{treatment:kind,version:row.version},{headers:auth()});await reload();}catch(e){setError(e.response?.data?.detail||'Unable to save.');}finally{setBusy(false);}}
  return <Card variant="outlined" sx={{p:2}}><Stack spacing={2} direction={{xs:'column',md:'row'}} alignItems={{md:'center'}}><Box sx={{flex:1}}><Typography fontWeight={700}>{row.name}</Typography><Typography>Actual: {money(row.actual_cents)} · {row.paid?'Marked paid':'Not marked paid'}</Typography></Box><TextField select label="Recap treatment" value={kind} onChange={e=>setKind(e.target.value)} sx={{minWidth:230}}>{[['other','Other event expense'],['fighter_pay','Already included in purses'],['ticket_commission','Already included in commissions'],['state_assessment','State assessment'],['exclude','Exclude from recap']].map(([v,l])=><MenuItem key={v} value={v}>{l}</MenuItem>)}</TextField><Button onClick={save} disabled={busy||kind===row.treatment}>Save treatment</Button></Stack>{error&&<Alert severity="error">{String(error)}</Alert>}</Card>;
}
function DataTable({heads,rows}) {return <Box sx={{minWidth:0,maxWidth:'100%',overflowX:'auto','& table':{width:'100%',borderCollapse:'collapse'},'& th,& td':{textAlign:'left',p:1.5,borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap'}}}><table><thead><tr>{heads.map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i}>{r.map((v,j)=><td key={j}>{v}</td>)}</tr>)}</tbody></table></Box>;}
export default function EventRecap({eventId,onOpenTickets,onOpenExpenses,onOpenContracts}){
  const [data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[tab,setTab]=useState(0),[comparison,setComparison]=useState(null),[offset,setOffset]=useState(0);
  async function load(){setBusy(true);setError('');try{const r=await axios.get(`${BASE}/api/events/${eventId}/recap`,{headers:auth()});setData(r.data);}catch(e){setError(e.response?.data?.detail||'Unable to load event recap. Please retry.');}finally{setBusy(false);}}
  useEffect(()=>{setData(null);setTab(0);load();},[eventId]);
  useEffect(()=>{axios.get(`${BASE}/api/events/recaps?limit=20&offset=${offset}`,{headers:auth()}).then(r=>setComparison(r.data)).catch(()=>setComparison(null));},[offset,eventId,data?.generated_at]);
  async function download(ext){try{const r=await axios.get(`${BASE}/api/events/${eventId}/recap.${ext}`,{headers:auth(),responseType:'blob'});const u=URL.createObjectURL(r.data),a=document.createElement('a');a.href=u;a.download=`tng_event_${eventId}_recap.${ext}`;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}catch{setError('Export failed. Please retry.');}}
  if(!data)return <Box>{error?<Alert severity="error">{String(error)}</Alert>:<CircularProgress/>}<Button onClick={load}>Retry</Button></Box>;
  const s=data.summary;
  return <Stack spacing={2} sx={{minWidth:0,width:'100%',maxWidth:'100%'}}>
    <Stack direction="row" spacing={1} useFlexGap sx={{flexWrap:"wrap"}} alignItems="center"><Typography variant="h5" sx={{flex:1}}>Event Recap</Typography><Chip label={data.provisional?'Provisional · review costs':'Recorded amounts'} color={data.provisional?'warning':'success'}/><Button disabled={busy} onClick={load}>Refresh</Button><Button onClick={()=>download('pdf')}>Download PDF</Button><Button onClick={()=>download('csv')}>Download CSV</Button></Stack>
    {error&&<Alert severity="error">{String(error)}</Alert>}
    <Typography variant="caption">Updated {new Date(data.generated_at).toLocaleString('en-US',{timeZone:'America/Chicago'})} Oklahoma City time</Typography>
    <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(2,1fr)',lg:'repeat(4,1fr)'},gap:2}}>{[['Paid ticket sales',s.ticket_sales_cents],['Purse + seller costs',s.fighter_and_seller_cost_cents],['Tickets less purse + commission',s.ticket_contribution_cents],['Recorded event result',s.recorded_result_cents]].map(([label,value])=><Card key={label} sx={{p:2}}><Typography color="text.secondary">{label}</Typography><Typography variant="h4" color={value<0?'error.main':undefined}>{money(value)}</Typography></Card>)}</Box>
    <Tabs value={tab} onChange={(_,v)=>setTab(v)} variant="scrollable" scrollButtons="auto"><Tab label="Event Recap"/><Tab label="Paid Purses"/><Tab label="Ticket Commissions"/><Tab label="Expenses"/></Tabs>
    {tab===0&&<><Typography>{data.basis}</Typography><DataTable heads={['Fighter','Ticket sales','Gross purse','Travel + per diem','Deductions','Net purse','Commission cost','Ticket contribution']} rows={data.fighters.map(r=>[r.name,money(r.ticket_sales_cents),money(r.gross_purse_cents),money(r.travel_cents+r.per_diem_cents),money(r.deductions_cents),money(r.net_obligation_cents),money(r.commission_cost_cents),money(r.ticket_contribution_cents)])}/><Typography>Other collected income: {money(s.other_income_cents)} · State assessment: {money(s.state_assessment_cents)} ({s.assessment_basis==='recorded_actual'?'recorded actual':'5% estimate'}) · Other actual expenses: {money(s.other_expenses_cents)}</Typography><Typography>{s.unconfirmed_orders} unconfirmed orders excluded. Customer fees shown separately: {money(s.customer_fees_cents)}.</Typography></>}
    {tab===1&&<><Alert severity="info">Record purse payments already made. Enter the cumulative total paid to date, not an additional payment. Saving sends no money and does not change signed contracts.</Alert><Typography>Recorded paid: {money(s.purse_payments_recorded_cents)} · Remaining on recorded payments: {money(s.remaining_recorded_purses_cents)} · {s.purse_payment_status_unknown} fighter payment status(es) not recorded ({money(s.unreconciled_purse_obligations_cents)} obligations).</Typography>{data.fighters.length?data.fighters.map(r=><PaymentRow key={`${eventId}-${r.fighter_id}-${r.purse_version}`} row={r} kind="purses" eventId={eventId} reload={load}/>):<Typography>No fighters on this event card.</Typography>}</>}
    {tab===2&&<><Alert severity="info">Record ticket commissions separately from purses. Enter the cumulative amount already paid to each seller. Saving updates the seller payment record and sends no money.</Alert><Typography>Recorded paid: {money(s.commission_payments_recorded_cents)} · Earned balance without a recorded payment: {money(s.remaining_commissions_cents)} · {s.commission_payment_status_unknown} earned commission payment status(es) not recorded.</Typography>{data.sellers.filter(r=>r.seller_id!=null).map(r=><PaymentRow key={`${eventId}-${r.seller_id}-${r.previous_payout_id}`} row={r} kind="commissions" eventId={eventId} reload={load}/>)}</>}
    {tab===3&&<><Alert severity="info">Actual amounts come from Expenses. Classify amounts already included in purse or commission costs to prevent double counting. Text estimates are excluded.</Alert><Button onClick={onOpenExpenses}>Manage expense amounts</Button>{data.expenses.map(r=><ExpenseRow key={`${eventId}-${r.id}-${r.version}`} row={r} eventId={eventId} reload={load}/>)}</>}
    {!!data.warnings.length&&<Alert severity="warning"><Typography fontWeight={700}>Reconciliation needed</Typography>{data.warnings.map(w=><Typography variant="body2" key={w}>• {w}</Typography>)}</Alert>}
    <Stack direction="row" spacing={1}><Button onClick={onOpenTickets}>Ticket sales</Button><Button onClick={onOpenExpenses}>Expenses</Button><Button onClick={onOpenContracts}>Contracts</Button></Stack>
    {comparison&&<Box sx={{minWidth:0}}><Typography variant="h6">Compare events</Typography><Typography variant="body2">Select an event from the event workspace to manage its records.</Typography><DataTable heads={['Event','Date','Ticket sales','Purse + commission costs','Recorded result','Review']} rows={comparison.events.map(r=>[r.event.name,r.event.date,money(r.summary.ticket_sales_cents),money(r.summary.fighter_and_seller_cost_cents),money(r.summary.recorded_result_cents),r.provisional?'Provisional':'Recorded'])}/><Button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-20))}>Previous</Button><Button disabled={offset+20>=comparison.total} onClick={()=>setOffset(offset+20)}>Next</Button></Box>}
  </Stack>;
}
