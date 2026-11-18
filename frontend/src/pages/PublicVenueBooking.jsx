import React,{useEffect,useState}from'react';
import{Alert,Box,Card,CardContent,Stack,Typography}from'@mui/material';
import VenueBookingForm from'./VenueBookingForm';
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'');
export default function PublicVenueBooking(){
 const[info,setInfo]=useState(null),[error,setError]=useState('');
 useEffect(()=>{let live=true;fetch(API+'/api/venue/public',{cache:'no-store'}).then(async r=>{const d=await r.json();if(!r.ok)throw Error('Facility requests are unavailable. Please contact TNG.');if(live)setInfo(d);}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[]);
 return <Box sx={{minHeight:'100vh',bgcolor:'#070b12',py:{xs:3,md:6},px:2}}><Stack spacing={3} sx={{maxWidth:1000,mx:'auto'}}>
  <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:'1fr 1fr'},gap:3,alignItems:'center'}}>
   <Box><Typography variant="h2" color="primary" fontWeight={950}>TNG</Typography><Typography variant="overline" sx={{color:'#cbd5e1'}}>THE NEXT GENERATION</Typography><Typography variant="h3" color="white" sx={{mt:2,fontSize:{xs:32,md:44},fontWeight:850,lineHeight:1.15}}>Your next event starts here.</Typography><Typography sx={{color:'#aab8cb',mt:2}}>A distinctive Oklahoma City venue with a boxing ring and space for your next gathering, celebration or event.</Typography><Typography sx={{color:'#cbd5e1',mt:2,fontSize:14}}>TNG Boxing & Event Center · 8416 NW Expressway</Typography></Box>
   <Box component="img" src="/images/tng-venue-original.jpg" width={554} height={554} alt="TNG Boxing event space with a boxing ring and tables arranged for an event" sx={{display:'block',width:'100%',height:'auto',borderRadius:3,border:'1px solid #ffffff20'}}/>
  </Box>
  <Card sx={{width:'100%',maxWidth:760,alignSelf:'center'}}><CardContent sx={{p:{xs:2,sm:4}}}>
   {error?<Alert severity="error">{error}</Alert>:!info?<Typography>Loading facility details…</Typography>:!info.enabled?<Alert severity="info">Facility requests are currently closed. Contact marketing@tngboxinggym.com.</Alert>:<Stack spacing={3}><Box><Typography variant="h5">Request your event date</Typography><Typography color="text.secondary" sx={{mt:.5}}>{info.address}</Typography></Box><VenueBookingForm/><Typography variant="caption" color="text.secondary">Questions? marketing@tngboxinggym.com · (405) 864-4496</Typography></Stack>}
  </CardContent></Card>
 </Stack></Box>;
}
