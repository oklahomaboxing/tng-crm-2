import React, { useEffect, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, Skeleton, Stack, Typography } from '@mui/material';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import useOperationsOverview from '../hooks/useOperationsOverview';
import { WorkQueue, UpcomingEvents } from '../components/workspace/OperationsPanels';
import { API, authHeaders } from '../services/api';
const dollars=value=>value==null||!Number.isFinite(Number(value))?'—':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(Number(value));
const count=value=>value==null||!Number.isFinite(Number(value))?'—':new Intl.NumberFormat('en-US').format(value);
const clock=value=>new Date(value).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit',timeZone:'America/Chicago'});
const eventDate=value=>value?new Date(value+'T12:00:00').toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',year:'numeric'}):'Date to be announced';
function Metric({label,value,note,loading,accent='#d71932'}){
 return <Card sx={{height:'100%',borderTop:`3px solid ${accent}`}}><CardContent sx={{height:'100%',boxSizing:'border-box'}}><Typography sx={{fontSize:15,fontWeight:750,color:'text.primary'}}>{label}</Typography>{loading?<Skeleton height={56}/>:<Typography sx={{my:1,fontSize:{xs:34,sm:42},fontWeight:850,lineHeight:1.2,letterSpacing:'-.04em',overflowWrap:'anywhere'}}>{value}</Typography>}<Typography sx={{fontSize:13,color:'text.secondary',lineHeight:1.6}}>{note}</Typography></CardContent></Card>
}
export default function Dashboard({dash,leader,load,onNavigate,userName,error}){
 const operations=useOperationsOverview();
 const [facts,setFacts]=useState(null),[eventError,setEventError]=useState(''),[eventLoading,setEventLoading]=useState(true),[version,setVersion]=useState(0),[refreshing,setRefreshing]=useState(false);
 useEffect(()=>{
  const abort=new AbortController();setEventError('');setEventLoading(true);
  fetch(`${API}/api/assistant/snapshot`,{headers:authHeaders(),signal:abort.signal,cache:'no-store'}).then(async r=>{const d=await r.json();if(!r.ok||!d.members)throw Error('Event figures could not be refreshed. Any previous figures shown may be out of date.');if(!abort.signal.aborted)setFacts(d)}).catch(e=>{if(!abort.signal.aborted)setEventError(e.message)}).finally(()=>{if(!abort.signal.aborted)setEventLoading(false)});
  return()=>abort.abort();
 },[version]);
 async function refresh(){setRefreshing(true);setVersion(v=>v+1);operations.refresh();try{await load()}finally{setRefreshing(false)}}
 const busy=refreshing||operations.loading||eventLoading;
 const memberStats=[['Active members','active_members','Current gym memberships','#087b63'],['Expiring in 7 days','expiring_members','Included in active members','#a65d09'],['Expired memberships','expired_members','Membership has ended','#d71932'],['Check-ins today','today_checkins','Recorded gym attendance','#087f9b']];
 return <Stack spacing={3}>
  <Box component="header" sx={{display:'flex',justifyContent:'space-between',gap:2,alignItems:'center',flexWrap:'wrap'}}><Box><Typography variant="h4">Dashboard</Typography><Typography color="text.secondary" sx={{mt:.5}}>Welcome{userName?`, ${userName.split(' ')[0]}`:''}. Here is today at TNG.</Typography></Box><Button variant="outlined" startIcon={<RefreshRoundedIcon/>} disabled={busy} onClick={refresh}>{busy?'Refreshing…':'Refresh'}</Button></Box>
  <Card component="section" aria-label="USA Boxing Officials" sx={{borderLeft:'4px solid',borderColor:'primary.main'}}><CardContent sx={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:2,flexWrap:'wrap'}}><Box><Typography variant="h6">USA Boxing Officials</Typography><Typography color="text.secondary">Find officials, add contacts, coordinate event work and read replies.</Typography></Box><Stack direction="row" spacing={1} useFlexGap sx={{flexWrap:'wrap'}}><Button variant="contained" onClick={()=>onNavigate('USA Boxing Officials')}>Open officials</Button></Stack></CardContent></Card>
  {error&&<Alert severity="error">{error}</Alert>}
  <Box component="section" aria-label="Membership and attendance" sx={{display:'grid',gridTemplateColumns:{xs:'repeat(2,minmax(0,1fr))',lg:'repeat(4,minmax(0,1fr))'},gap:1.5}}>{memberStats.map(([label,key,note,accent])=><Metric key={key} label={label} value={count(dash?.[key])} note={note} accent={accent} loading={!dash&&!error}/>)}</Box>
  <Box component="nav" aria-label="Daily actions" sx={{display:'flex',gap:1,flexWrap:'wrap'}}>{[['Members','Members'],['Events','TNG BOXING EVENTS'],['Fight Recap','Fight Recap'],['Chef & Concessions','Chef & Concessions'],['Messages','Text Inbox'],['Reports','Reports']].map(([label,page])=><Button key={page} variant={page==='Members'?'contained':'outlined'} onClick={()=>onNavigate(page)}>{label}</Button>)}</Box>
  <Box sx={{display:'grid',gridTemplateColumns:{xs:'minmax(0,1fr)',lg:'minmax(0,1fr) minmax(0,1fr)'},gap:2,alignItems:'start'}}>
   <WorkQueue data={operations.data} loading={operations.loading} error={operations.error} onNavigate={onNavigate} limit={3}/>
   <Card component="section" aria-label="Current event"><CardContent><Typography variant="h6" sx={{mb:2}}>Boxing event</Typography>{eventError&&<Alert severity="warning" sx={{mb:2}}>{eventError}</Alert>}{eventLoading&&!facts?<Skeleton height={160}/>:facts?.event?<>
     <Typography variant="h5">{facts.event.name}</Typography><Typography variant="body2" color="text.secondary" sx={{mt:1}}>{eventDate(facts.event.date)} · {facts.event.venue||'Venue to be announced'}</Typography>
     <Box sx={{display:'grid',gridTemplateColumns:'repeat(2,minmax(0,1fr))',gap:2,my:3}}><Box><Typography variant="body2" color="text.secondary">Paid tickets</Typography><Typography variant="h4">{facts.tickets?(facts.tickets.unknown_quantity_orders?'At least ':'')+count(facts.tickets.paid_quantity):'—'}</Typography></Box><Box><Typography variant="body2" color="text.secondary">Ticket payments</Typography><Typography variant="h4" sx={{overflowWrap:'anywhere'}}>{facts.tickets?dollars(facts.tickets.gross_paid_cents/100):'—'}</Typography></Box></Box>
     <Typography variant="caption" color="text.secondary">Recorded paid orders; payments include fees. {count(facts.card?.bouts?.length)} bouts on the card.</Typography>
     <Box sx={{display:'flex',gap:1,flexWrap:'wrap',mt:2}}><Button variant="contained" onClick={()=>onNavigate('TNG BOXING EVENTS',{eventId:facts.event.id})}>Open event</Button><Button onClick={()=>onNavigate('TNG BOXING EVENTS',{eventId:facts.event.id,eventSection:'matchmaking'})}>Find a match</Button><Button onClick={()=>onNavigate('TNG BOXING EVENTS',{eventId:facts.event.id,eventSection:'offers'})}>Review offers</Button><Button onClick={()=>onNavigate('TNG BOXING EVENTS',{eventId:facts.event.id,eventSection:'recap'})}>Purses & recap</Button></Box>
    </>:!eventError&&<Typography color="text.secondary">No event selected for this overview.</Typography>}</CardContent></Card>
  </Box>
  <Box component="details" sx={{border:'1px solid',borderColor:'divider',borderRadius:2,p:2,bgcolor:'background.paper'}}><Box component="summary" sx={{cursor:'pointer',fontWeight:750}}>More dashboard details</Box><Stack spacing={3} sx={{mt:3}}>
    <Box><Typography variant="h6">Gym sales this month</Typography><Typography sx={{mt:1}}>Revenue: {dollars(dash?.revenue_this_month)} · Paid sales: {count(dash?.sales_this_month)}</Typography><Button onClick={()=>onNavigate('Reports')}>Open reports</Button></Box>
    <Box><Typography variant="h6" sx={{mb:1}}>Recent check-ins</Typography>{dash?.recent_checkins?.length?dash.recent_checkins.slice(0,6).map((r,i)=><Stack key={i} direction="row" sx={{justifyContent:'space-between',gap:2,py:1,borderBottom:'1px solid',borderColor:'divider'}}><Typography>{r.member}</Typography><Typography color="text.secondary">{r.time?clock(r.time+(/(?:Z|[+-]\d\d:\d\d)$/.test(r.time)?'':'Z')):'—'}</Typography></Stack>):<Typography color="text.secondary">{dash?'No recent check-ins.':'Attendance unavailable.'}</Typography>}<Button onClick={()=>onNavigate('Member Check-In')}>Member check-in</Button></Box>
    <Box><Typography variant="h6" sx={{mb:1}}>Sales team</Typography>{leader?.length?leader.slice(0,5).map((r,i)=><Stack key={r.rep_id||i} direction="row" sx={{justifyContent:'space-between',gap:2,py:1}}><Typography>{r.name}</Typography><Typography>{dollars(r.revenue||0)}</Typography></Stack>):<Typography color="text.secondary">No leaderboard data available.</Typography>}</Box>
    <UpcomingEvents data={operations.data} loading={operations.loading} onNavigate={onNavigate}/>
  </Stack></Box>
 </Stack>;
}
