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
 return <Box component="section" aria-label="Workspace guide" className="tng-workspace-guide" sx={{mb:2,borderBottom:'1px solid',borderColor:'divider',pb:1.5}}>
  <Stack direction="row" sx={{alignItems:'center',gap:1,justifyContent:'space-between'}}><Typography variant="caption" color="text.secondary" sx={{maxWidth:800}}>{flow.description}</Typography><Stack direction="row"><Tooltip title={pinned?'Unpin this workspace':'Pin this workspace'}><IconButton onClick={()=>onPin(page)} aria-label={pinned?'Unpin this workspace':'Pin this workspace'} aria-pressed={pinned}>{pinned?<PushPinRoundedIcon color="primary"/>:<PushPinOutlinedIcon/>}</IconButton></Tooltip><Tooltip title="Copy workspace link"><IconButton onClick={copy} aria-label="Copy workspace link"><ContentCopyRoundedIcon fontSize="small"/></IconButton></Tooltip></Stack></Stack>
  {flow.next.length>0&&<Box component="details" sx={{mt:.5}}><Typography component="summary" variant="caption" sx={{cursor:'pointer',color:'text.secondary'}}>Related workspaces</Typography><Box sx={{display:'flex',gap:1,flexWrap:'wrap',mt:1}}>{flow.next.map(p=><Button key={p} size="small" variant="outlined" onClick={()=>onNavigate(p)}>{p}</Button>)}<Button size="small" onClick={onModules}>All modules</Button></Box></Box>}<Typography variant="caption" role="status" color="text.secondary">{copied}</Typography>
 </Box>;
}
