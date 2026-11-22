import React,{useEffect,useRef,useState} from 'react';
import {Alert,Badge,Button,Snackbar,Tooltip} from '@mui/material';
import SmsRoundedIcon from '@mui/icons-material/SmsRounded';
const API=(import.meta.env.VITE_API_URL||'https://sea-lion-app-2-gxyfr.ondigitalocean.app').replace(/\/$/,'');
export default function MessageNotifications({onNavigate}){
 const [summary,setSummary]=useState(null),[error,setError]=useState(false),[alert,setAlert]=useState(false);
 const last=useRef(null);
 useEffect(()=>{
  let alive=true,busy=false;const controller=new AbortController();
  async function refresh(){
   if(busy||document.hidden)return;busy=true;
   try{
    const r=await fetch(API+'/api/messages/summary',{headers:{Authorization:`Bearer ${localStorage.getItem('token')}`},cache:'no-store',signal:controller.signal});
    if(!r.ok)throw Error('Unavailable');const d=await r.json();
    if(alive){setError(false);setSummary(d);if(d.latest_unread_id&&(last.current===null||d.latest_unread_id>last.current))setAlert(true);if(!d.unread_messages)setAlert(false);last.current=Math.max(last.current||0,d.latest_unread_id||0);}
   }catch(e){if(alive&&e.name!=='AbortError')setError(true);}finally{busy=false;}
  }
  refresh();const timer=setInterval(refresh,15000);
  document.addEventListener('visibilitychange',refresh);window.addEventListener('focus',refresh);window.addEventListener('tng-messages-read',refresh);
  return()=>{alive=false;controller.abort();clearInterval(timer);document.removeEventListener('visibilitychange',refresh);window.removeEventListener('focus',refresh);window.removeEventListener('tng-messages-read',refresh);};
 },[]);
 function open(){setAlert(false);onNavigate('Text Inbox');}
 const count=summary?.unread_messages||0;
 return <><Tooltip title={error?'Message updates unavailable. Open Text Inbox or reconnect.':'All SMS conversations · checks for replies every 15 seconds'}><Button color="inherit" onClick={open} aria-label={error?'Open Text Inbox; message updates unavailable':`Open Text Inbox; ${count} unread messages`} startIcon={<Badge badgeContent={error?'!':count} color={error?'warning':'error'} max={99}><SmsRoundedIcon/></Badge>} sx={{px:1,minWidth:44}}>Messages</Button></Tooltip><Snackbar open={alert&&!error&&count>0} autoHideDuration={8000} onClose={()=>setAlert(false)} anchorOrigin={{vertical:'bottom',horizontal:'right'}}><Alert severity="info" onClose={()=>setAlert(false)} action={<Button color="inherit" size="small" onClick={open}>Open inbox</Button>}>{count} unread text message{count===1?'':'s'}. Open Text Inbox to read and reply.</Alert></Snackbar></>;
}
