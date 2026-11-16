import React,{useState} from 'react';
import {Box,Button,IconButton,Stack,Tooltip,Typography} from '@mui/material';
import PushPinOutlinedIcon from '@mui/icons-material/PushPinOutlined';
import PushPinRoundedIcon from '@mui/icons-material/PushPinRounded';
import ContentCopyRoundedIcon from '@mui/icons-material/ContentCopyRounded';
import {workspaceWorkflow} from '../../navigation/workflows';
import {workspaceHash} from '../../navigation/workspaces';
export default function WorkspaceGuide({role,page,onNavigate,pinned,onPin,onModules}){
 const flow=workspaceWorkflow(role,page),[copied,setCopied]=useState('');
 if(!flow)return null;
 async function copy(){try{await navigator.clipboard.writeText(`${window.location.origin}/${workspaceHash(page)}`);setCopied('Workspace link copied');}catch{setCopied('Use your browser address bar to copy the link.');}setTimeout(()=>setCopied(''),4000);}
 return <Box component="section" aria-label="Workspace guide" className="tng-workspace-guide" sx={{mb:3,p:{xs:2,md:2.5},border:'1px solid',borderColor:'divider',borderRadius:3,bgcolor:'background.paper',position:'relative',overflow:'hidden'}}>
  <Stack direction="row" sx={{alignItems:'flex-start',gap:1,justifyContent:'space-between'}}><Box sx={{minWidth:0}}><Typography variant="overline" sx={{color:'primary.main'}}>{flow.group?.label} / WORKSPACE</Typography><Typography sx={{fontWeight:650,mt:.5,maxWidth:900}}>{flow.description}</Typography></Box><Stack direction="row"><Tooltip title={pinned?'Unpin this workspace':'Pin this workspace'}><IconButton onClick={()=>onPin(page)} aria-label={pinned?'Unpin this workspace':'Pin this workspace'} aria-pressed={pinned}>{pinned?<PushPinRoundedIcon color="primary"/>:<PushPinOutlinedIcon/>}</IconButton></Tooltip><Tooltip title="Copy workspace link"><IconButton onClick={copy} aria-label="Copy workspace link"><ContentCopyRoundedIcon fontSize="small"/></IconButton></Tooltip></Stack></Stack>
  <Box sx={{display:'flex',gap:1,flexWrap:'wrap',alignItems:'center',mt:1.5}}><Typography variant="caption" color="text.secondary" sx={{mr:.5}}>CONNECTED TOOLS</Typography>{flow.next.map(p=><Button key={p} size="small" variant="outlined" onClick={()=>onNavigate(p)} sx={{minHeight:36,fontSize:12}}>{p}</Button>)}<Button size="small" onClick={onModules} sx={{ml:{md:'auto'}}}>All modules</Button></Box><Typography variant="caption" role="status" color="text.secondary">{copied}</Typography>
 </Box>;
}
