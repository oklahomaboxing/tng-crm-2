import React, {useEffect, useState} from 'react';
import {Alert, Box, Button, CircularProgress, MenuItem, Stack, TextField, Typography} from '@mui/material';
import TicketDoorScanner from '../components/tickets/TicketDoorScanner';

const API=(import.meta.env.VITE_API_URL || 'https://sea-lion-app-2-gxyfr.ondigitalocean.app').replace(/\/$/,'');

export default function EventCheckIn() {
 const [mode,setMode]=useState('checkin');
 const [events,setEvents]=useState([]),[eventId,setEventId]=useState('');
 const [loading,setLoading]=useState(true),[error,setError]=useState(''),[retry,setRetry]=useState(0);
 useEffect(()=>{
  const controller=new AbortController();let active=true;
  setLoading(true);setError('');
  (async()=>{
   try {
    const response=await fetch(API+'/api/boxing/events',{headers:{Authorization:'Bearer '+localStorage.getItem('token')},signal:controller.signal});
    const data=await response.json();
    if(!response.ok)throw Error(response.status===401?'Your session expired. Sign in again.':typeof data.detail==='string'?data.detail:'Could not load events.');
    const now=new Date(),today=`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
    const rows=(Array.isArray(data)?data:[]).slice().sort((a,b)=>{
     const aDate=a.event_date || '9999-99-99',bDate=b.event_date || '9999-99-99';
     const aPast=aDate<today,bPast=bDate<today;
     return aPast!==bPast?(aPast?1:-1):aDate.localeCompare(bDate);
    });
    if(active)setEvents(rows);
   }catch(e){if(active && e.name!=='AbortError')setError(e.message || 'Could not load events.');}
   finally{if(active)setLoading(false);}
  })();
  return()=>{active=false;controller.abort();};
 },[retry]);
 const selected=events.find(event=>String(event.id)===eventId);
 return <Box sx={{maxWidth:1000,mx:'auto'}}>
  <Typography variant="overline" color="error.main" fontWeight={800}>FIGHT NIGHT / DOOR OPERATIONS</Typography>
  <Typography variant="h4" fontWeight={900}>Event Check-In</Typography>
  <Typography color="text.secondary" sx={{mt:1,mb:3}}>Check in ticket holders here. Select the event, then scan the admission QR from their ticket.</Typography>
  <Alert severity="info" sx={{mb:3}}>For gym membership check-ins, use Front Desk. A successful event scan admits the ticket and prevents reuse.</Alert>
  {loading && <CircularProgress aria-label="Loading events"/>}
  {error && <Stack spacing={1}><Alert severity="error">{error}</Alert><Button onClick={()=>setRetry(n=>n+1)}>Retry loading events</Button></Stack>}
  {!loading && !error && <>
   {!events.length?<Alert severity="info">No events are available. Create an event in Promoter first.</Alert>:<TextField select fullWidth label="Event for ticket check-in" value={eventId} onChange={e=>setEventId(e.target.value)}>
    <MenuItem value="">Choose an event</MenuItem>
    {events.map(event=><MenuItem key={event.id} value={String(event.id)}>{event.name} · {event.event_date || 'Date to be announced'}</MenuItem>)}
   </TextField>}
   {selected?<>
    <Box sx={{mt:3,p:2,borderLeft:'4px solid #d71920',backgroundColor:'white',borderRadius:1}}><Typography variant="h6" fontWeight={800}>{selected.name}</Typography><Typography color="text.secondary">{selected.event_date || 'Date to be announced'}{selected.venue?' · '+selected.venue:''}</Typography></Box>
    <Stack direction="row" spacing={1} sx={{mt:2}}><Button variant={mode==='checkin'?'contained':'outlined'} onClick={()=>setMode('checkin')}>Door check-in</Button><Button color="warning" variant={mode==='activation'?'contained':'outlined'} onClick={()=>setMode('activation')}>Activate paper ticket</Button></Stack>
    <TicketDoorScanner key={`event-door-${eventId}-${mode}`} eventId={Number(eventId)} mode={mode}/>
   </>:events.length>0 && <Alert severity="warning" sx={{mt:3}}>Choose the correct event before starting the ticket scanner.</Alert>}
  </>}
 </Box>;
}
