import React,{lazy,Suspense,useState}from'react';
import{Box,Button,Dialog,Stack,Typography}from'@mui/material';
const Game=lazy(()=>import('../pages/TngBoxingGame'));
export default function BoxingGameLauncher({onOpen}){
 const[open,setOpen]=useState(false);
 return <><Button variant="outlined" onClick={()=>{onOpen?.();setOpen(true);}}>Play TNG Boxing Game</Button><Dialog fullScreen open={open} onClose={()=>setOpen(false)}><Stack spacing={2} sx={{p:{xs:1,sm:3},minHeight:'100vh',bgcolor:'background.default'}}><Button sx={{alignSelf:'flex-end'}} onClick={()=>setOpen(false)}>Close game</Button><Box><Suspense fallback={<Typography>Loading TNG Boxing Game…</Typography>}>{open&&<Game/>}</Suspense></Box></Stack></Dialog></>;
}
