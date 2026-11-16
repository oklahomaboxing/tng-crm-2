import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, Card, Chip, CircularProgress, MenuItem, Stack, Tab, Tabs, TextField, Typography } from '@mui/material';
import ExpandMoreRoundedIcon from '@mui/icons-material/ExpandMoreRounded';
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
  return <Accordion disableGutters><AccordionSummary expandIcon={<ExpandMoreRoundedIcon/>}><Box sx={{minWidth:0}}><Typography fontWeight={800}>{row.name}</Typography><Typography color="text.secondary">{purse?'Purse':'Commission'}: {money(due)} · Paid: {money(paid)} · {paid==null?'Payment status unknown':`Remaining: ${money(Math.max(0,due-paid))}`}</Typography>
    </Box></AccordionSummary><AccordionDetails>
    {purse&&<Typography variant="caption">{row.basis.join(' / ')}</Typography>}
    <Stack direction={{xs:'column',md:'row'}} spacing={2} sx={{mt:2}}>
      <TextField label="Total paid to date ($)" value={amount} onChange={e=>setAmount(e.target.value)} inputProps={{inputMode:'decimal'}} disabled={busy}/>
      <TextField label="Payment date (optional)" type="date" InputLabelProps={{shrink:true}} value={date} onChange={e=>setDate(e.target.value)} disabled={busy}/>
      <TextField label="Payment note / reference" value={notes} onChange={e=>setNotes(e.target.value)} inputProps={{maxLength:1000}} sx={{flex:1}} disabled={busy}/>
      <Button variant="contained" onClick={save} disabled={busy||amount===''}>{busy?'Saving…':purse?'Save paid purse':'Save commission payment'}</Button>
    </Stack>{error&&<Alert severity="error" sx={{mt:1}}>{error}</Alert>}
  </AccordionDetails></Accordion>;
}
function ExpenseRow({row,eventId,reload}){
  const [kind,setKind]=useState(row.treatment),[busy,setBusy]=useState(false),[error,setError]=useState('');
  async function save(){setBusy(true);try{await axios.put(`${BASE}/api/events/${eventId}/recap/expenses/${row.id}`,{treatment:kind,version:row.version},{headers:auth()});await reload();}catch(e){setError(e.response?.data?.detail||'Unable to save.');}finally{setBusy(false);}}
  return <Card variant="outlined" sx={{p:2}}><Stack spacing={2} direction={{xs:'column',md:'row'}} alignItems={{md:'center'}}><Box sx={{flex:1}}><Typography fontWeight={700}>{row.name}</Typography><Typography>Actual: {money(row.actual_cents)} · {row.paid?'Marked paid':'Not marked paid'}</Typography></Box><TextField select label="Recap treatment" value={kind} onChange={e=>setKind(e.target.value)} sx={{minWidth:230}}>{[['other','Other event expense'],['fighter_pay','Already included in purses'],['ticket_commission','Already included in commissions'],['state_assessment','State assessment'],['exclude','Exclude from recap']].map(([v,l])=><MenuItem key={v} value={v}>{l}</MenuItem>)}</TextField><Button onClick={save} disabled={busy||kind===row.treatment}>Save treatment</Button></Stack>{error&&<Alert severity="error">{String(error)}</Alert>}</Card>;
}
function DataTable({heads,rows}) {return <Box sx={{minWidth:0,maxWidth:'100%',overflowX:'auto','& table':{width:'100%',borderCollapse:'collapse'},'& th,& td':{textAlign:'left',p:1.5,borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap'}}}><table><thead><tr>{heads.map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{rows.map((r,i)=><tr key={i}>{r.map((v,j)=><td key={j}>{v}</td>)}</tr>)}</tbody></table></Box>;}
export default function EventRecap({eventId,onOpenTickets,onOpenExpenses,onOpenContracts}){
  const [data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[tab,setTab]=useState(0),[comparison,setComparison]=useState(null),[offset,setOffset]=useState(0),[advanced,setAdvanced]=useState(false),[search,setSearch]=useState('');
  async function load(){setBusy(true);setError('');try{const r=await axios.get(`${BASE}/api/events/${eventId}/recap`,{headers:auth()});setData(r.data);}catch(e){setError(e.response?.data?.detail||'Unable to load event recap. Please retry.');}finally{setBusy(false);}}
  useEffect(()=>{setData(null);setTab(0);load();},[eventId]);
  useEffect(()=>{if(!advanced)return;axios.get(`${BASE}/api/events/recaps?limit=20&offset=${offset}`,{headers:auth()}).then(r=>setComparison(r.data)).catch(()=>setComparison(null));},[advanced,offset,eventId,data?.generated_at]);
  async function download(ext){try{const r=await axios.get(`${BASE}/api/events/${eventId}/recap.${ext}`,{headers:auth(),responseType:'blob'});const u=URL.createObjectURL(r.data),a=document.createElement('a');a.href=u;a.download=`tng_event_${eventId}_recap.${ext}`;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}catch{setError('Export failed. Please retry.');}}
  if(!data)return <Box>{error?<Alert severity="error">{String(error)}</Alert>:<CircularProgress/>}<Button onClick={load}>Retry</Button></Box>;
  const s=data.summary;
  const matches=r=>r.name.toLowerCase().includes(search.trim().toLowerCase());
  return <Stack spacing={2} sx={{minWidth:0,width:'100%'}}>
    <Stack direction="row" sx={{justifyContent:'space-between',alignItems:'center',gap:1,flexWrap:'wrap'}}><Typography variant="h5">Event Recap</Typography><Chip size="small" label={data.provisional?'Provisional':'Recorded amounts'} color={data.provisional?'warning':'success'}/></Stack>
    {error&&<Alert severity="error">{String(error)}</Alert>}
    <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(3,minmax(0,1fr))'},gap:1.5}}>{[[s.other_income_cents>0?'Total income':'Ticket sales',s.other_income_cents>0?s.total_recorded_income_cents:s.ticket_sales_cents],['Total costs',s.total_cost_cents],['Event result',s.recorded_result_cents]].map(([label,value])=><Card key={label} sx={{p:2}}><Typography color="text.secondary">{label}</Typography><Typography variant="h4" color={value<0?'error.main':undefined}>{money(value)}</Typography></Card>)}</Box>
    <Typography variant="body2" color="text.secondary">Fighter breakdown and purse totals: current bout card only. Ticket sales and seller commissions: whole event.</Typography>
    {s.excluded_off_card_purse_records>0&&<Alert severity="warning">{s.excluded_off_card_purse_records} off-card purse payment record(s), {money(s.excluded_off_card_purse_paid_cents)}, excluded. Payment history is saved.</Alert>}
    <Tabs value={tab} onChange={(_,v)=>{setTab(v);setSearch('');}} variant="scrollable" scrollButtons="auto"><Tab label="Summary"/><Tab label="Paid Purses"/><Tab label="Commissions"/></Tabs>
    {tab===0&&<><DataTable heads={['Fighter','Ticket sales','Net purse','Purse paid','Commission']} rows={data.fighters.map(r=>[r.name,money(r.ticket_sales_cents),money(r.net_obligation_cents),money(r.purse_paid_cents),money(r.commission_cost_cents)])}/>{!data.fighters.length&&<Typography>No fighters on the current bout card.</Typography>}</>}
    {tab>0&&<><Typography variant="body2" color="text.secondary">Select a name to update the total already paid. Saving records the payment; it sends no money.</Typography><TextField label={tab===1?'Find a fighter':'Find a seller'} value={search} onChange={e=>setSearch(e.target.value)} fullWidth/>{(tab===1?data.fighters:data.sellers.filter(r=>r.seller_id!=null)).filter(matches).map(r=><PaymentRow key={tab===1?`${eventId}-p-${r.fighter_id}-${r.purse_version}`:`${eventId}-c-${r.seller_id}-${r.previous_payout_id}`} row={r} kind={tab===1?'purses':'commissions'} eventId={eventId} reload={load}/>)}</>}
    {!!data.warnings.length&&<Box component="details" sx={{border:'1px solid',borderColor:'divider',borderRadius:2,p:2}}><Box component="summary" sx={{cursor:'pointer',fontWeight:700}}>Review {data.warnings.length} accounting note(s)</Box><Stack spacing={1} sx={{mt:2}}>{data.warnings.map(w=><Typography variant="body2" key={w}>{w}</Typography>)}</Stack></Box>}
    <Box component="details" onToggle={e=>setAdvanced(e.currentTarget.open)} sx={{border:'1px solid',borderColor:'divider',borderRadius:2,p:2}}><Box component="summary" sx={{cursor:'pointer',fontWeight:700}}>Expenses, downloads & details</Box><Stack spacing={2} sx={{mt:2}}>
      <Stack direction="row" useFlexGap sx={{gap:1,flexWrap:'wrap'}}><Button onClick={()=>download('pdf')}>Download PDF</Button><Button onClick={()=>download('csv')}>Download CSV</Button><Button onClick={load} disabled={busy}>Refresh</Button><Button onClick={onOpenExpenses}>Edit expenses</Button><Button onClick={onOpenTickets}>Ticket sales</Button><Button onClick={onOpenContracts}>Contracts</Button></Stack>
      <Typography variant="body2">{data.basis}</Typography><Typography variant="body2">State assessment: {money(s.state_assessment_cents)} ({s.assessment_basis==='recorded_actual'?'recorded actual':'5% estimate'}). Other collected income: {money(s.other_income_cents)}. Other expenses: {money(s.other_expenses_cents)}.</Typography>
      <Typography variant="caption">Updated {new Date(data.generated_at).toLocaleString('en-US',{timeZone:'America/Chicago'})} Oklahoma City time</Typography>
      {data.expenses.map(r=><ExpenseRow key={`${eventId}-${r.id}-${r.version}`} row={r} eventId={eventId} reload={load}/>)}
      {comparison&&<Box sx={{minWidth:0}}><Typography variant="h6">Compare events</Typography><DataTable heads={['Event','Date','Ticket sales','Result']} rows={comparison.events.map(r=>[r.event.name,r.event.date,money(r.summary.ticket_sales_cents),money(r.summary.recorded_result_cents)])}/><Button disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-20))}>Previous</Button><Button disabled={offset+20>=comparison.total} onClick={()=>setOffset(offset+20)}>Next</Button></Box>}
    </Stack></Box>
  </Stack>;
}
