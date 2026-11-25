import React,{useEffect,useState}from'react';
import{Button,Dialog,DialogContent,DialogTitle,Stack,Typography}from'@mui/material';
// This entry appears only after Unity's successful build writes the manifest.
// The existing App route continues to authorize admins before mounting this game.
export default function UnityBoxingLaunch({onLaunch}){
 const[available,setAvailable]=useState(false),[open,setOpen]=useState(false);
 useEffect(()=>{const controller=new AbortController();fetch('/boxing-unity/manifest.json',{signal:controller.signal,cache:'no-store'}).then(r=>r.ok?r.json():null).then(m=>{if(m?.entry==='index.html'&&m?.engine==='Unity 6')setAvailable(true);}).catch(()=>{});return()=>controller.abort();},[]);
 if(!available)return null;
 return <><Button variant="contained" onClick={()=>{onLaunch?.();setOpen(true);}}>Play Unity version</Button><Dialog open={open} fullScreen onClose={()=>setOpen(false)}><DialogTitle><Stack direction="row" sx={{justifyContent:'space-between',alignItems:'center'}}><Typography component="span">TNG Boxing · Unity</Typography><Button onClick={()=>setOpen(false)}>Return to TNGOS</Button></Stack></DialogTitle><DialogContent sx={{p:0,display:'flex',minHeight:0}}><iframe title="TNG Boxing Unity arena" src="/boxing-unity/index.html" allow="fullscreen; autoplay; gamepad" allowFullScreen style={{border:0,width:'100%',height:'100%'}}/></DialogContent></Dialog></>;
}
