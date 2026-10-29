import React,{useEffect,useState} from 'react';
import {Alert,Box,Button,Card,CardContent,Chip,CircularProgress,Stack,TextField,Typography} from '@mui/material';
import EventWorkspace from './EventWorkspace';
const API=(import.meta.env.VITE_API_URL || 'https://sea-lion-app-2-gxyfr.ondigitalocean.app').replace(/\/$/,'');

export default function TngBoxingEvents({initialEventId}){
 const[events,setEvents]=useState([]),[selected,setSelected]=useState(null),[error,setError]=useState(''),[loading,setLoading]=useState(true),[refresh,setRefresh]=useState(0),[search,setSearch]=useState(''),[showAll,setShowAll]=useState(false);
 useEffect(()=>{if(Number.isSafeInteger(Number(initialEventId)) && Number(initialEventId)>0)setSelected(Number(initialEventId));},[initialEventId]);
 useEffect(()=>{
  let live=true;const controller=new AbortController();setLoading(true);setError('');
  (async()=>{try{
   const r=await fetch(API+'/api/boxing/events',{headers:{Authorization:'Bearer '+localStorage.getItem('token')},signal:controller.signal});const d=await r.json();
   if(!r.ok)throw Error(r.status===401?'Your session expired. Sign in again.':typeof d.detail==='string'?d.detail:'Could not load boxing events.');
   if(live)setEvents((Array.isArray(d)?d:[]).slice().sort((a,b)=>(a.event_date || '9999').localeCompare(b.event_date || '9999')));
  }catch(e){if(live && e.name!=='AbortError')setError(e.message);}finally{if(live)setLoading(false);}})();
  return()=>{live=false;controller.abort();};
 },[refresh]);
 if(selected)return <EventWorkspace eventId={selected} onBack={()=>setSelected(null)}/>;
 const now=new Date(),today=`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
 const rows=events.filter(e=>(showAll || ((!e.event_date || e.event_date>=today) && !['completed','cancelled','canceled','archived'].includes(String(e.status).toLowerCase()))) && `${e.name} ${e.venue}`.toLowerCase().includes(search.toLowerCase()));
 const dateLabel=value=>{if(!/^\d{4}-\d{2}-\d{2}$/.test(value || ''))return value || 'Date to be announced';const[y,m,d]=value.split('-').map(Number);return new Date(y,m-1,d).toLocaleDateString(undefined,{month:'long',day:'numeric',year:'numeric'});};
 return <Box>
  <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2} sx={{mb:3}}><Box><Typography variant="overline" color="error.main" fontWeight={800}>TNG PROMOTIONS</Typography><Typography variant="h4" fontWeight={900}>TNG BOXING EVENTS</Typography><Typography color="text.secondary" sx={{mt:1}}>Open an event to manage its fight card, tickets, contracts and event operations.</Typography></Box><Button variant="outlined" onClick={()=>setRefresh(n=>n+1)} disabled={loading}>Refresh events</Button></Stack>
  <Stack direction={{xs:'column',sm:'row'}} spacing={2} sx={{mb:3}}><TextField label="Find an event" value={search} onChange={e=>setSearch(e.target.value)} size="small"/><Button variant={showAll?'contained':'outlined'} onClick={()=>setShowAll(v=>!v)}>{showAll?'Showing all events':'Show past and other events'}</Button></Stack>
  {loading?<CircularProgress aria-label="Loading boxing events"/>:error?<Alert severity="error">{error}</Alert>:<Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'repeat(2,minmax(0,1fr))',xl:'repeat(3,minmax(0,1fr))'},gap:2}}>
   {rows.map(e=><Card key={e.id} sx={{borderTop:'4px solid #d71920'}}><CardContent><Chip label={e.status || 'Planning'} size="small" sx={{mb:2}}/><Typography variant="h5" fontWeight={900}>{e.name}</Typography><Typography sx={{mt:1}} fontWeight={700}>{dateLabel(e.event_date)}</Typography><Typography color="text.secondary" sx={{mt:1}}>{e.venue || 'Venue to be announced'}</Typography><Typography variant="body2" color="text.secondary" sx={{mt:1,mb:3}}>{e.venue_address}</Typography><Button variant="contained" fullWidth aria-label={`Open ${e.name}`} onClick={()=>setSelected(e.id)}>Open event</Button></CardContent></Card>)}
   {!rows.length && <Alert severity="info">No matching events. Try showing all events or change your search.</Alert>}
  </Box>}
 </Box>;
}
