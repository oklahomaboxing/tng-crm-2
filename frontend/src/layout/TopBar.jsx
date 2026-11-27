import React,{useState}from'react';
import{AppBar,Avatar,Box,Button,Divider,IconButton,Menu,MenuItem,Stack,Toolbar,Tooltip,Typography,ToggleButton,ToggleButtonGroup}from'@mui/material';
import MenuRoundedIcon from'@mui/icons-material/MenuRounded';
import AppsRoundedIcon from'@mui/icons-material/AppsRounded';
import RefreshRoundedIcon from'@mui/icons-material/RefreshRounded';
import MessageNotifications from'../components/MessageNotifications';
import WorkspaceSearch from'../components/workspace/WorkspaceSearch';
import{workspaceGroup}from'../navigation/workspaces';
function initials(name){return(name||'TNG').split(' ').filter(Boolean).slice(0,2).map(p=>p[0]?.toUpperCase()).join('');}
export default function TopBar({page,mode,onModeChange,onModules,moduleCenterOpen,role,userName,onMenu,onRefresh,onLogout,onNavigate}){
 const[anchor,setAnchor]=useState(null);
 const title=page==='TNG BOXING EVENTS'?'Events & fight cards':page==='Promoter'?'Pro matchmaking':page;
 return <AppBar className="tng-topbar" position="sticky" elevation={0} color="transparent" sx={{top:0,zIndex:t=>t.zIndex.drawer-1,bgcolor:'background.paper',color:'text.primary',borderBottom:'1px solid',borderColor:'divider'}}>
  <Toolbar sx={{minHeight:{xs:64,md:76},gap:{xs:.5,sm:1.5},px:{xs:1,sm:3}}}>
   <IconButton onClick={onMenu} sx={{display:{xs:'inline-flex',lg:'none'}}} aria-label="Open navigation"><MenuRoundedIcon/></IconButton>
   <Box sx={{flex:1,minWidth:0}}><Typography variant="overline" color="text.secondary" noWrap sx={{display:'block',lineHeight:1.6,letterSpacing:1}}>{workspaceGroup(page)?.label||'TNGOS'}</Typography><Typography noWrap sx={{fontSize:{xs:16,sm:20},fontWeight:750,lineHeight:1.4}}>{title}</Typography></Box>
   <Stack direction="row" sx={{alignItems:'center',gap:{xs:0,sm:.5}}}>
    <WorkspaceSearch disabled={moduleCenterOpen} role={role} onNavigate={onNavigate}/>
    {['admin','staff'].includes(role)&&<MessageNotifications compact onNavigate={onNavigate}/>}
    <Tooltip title="All workspaces"><IconButton onClick={onModules} aria-label="Open module center"><AppsRoundedIcon/></IconButton></Tooltip>
    <Tooltip title="Account and appearance"><IconButton onClick={e=>setAnchor(e.currentTarget)} aria-label="Account and appearance" aria-expanded={!!anchor} aria-haspopup="menu"><Avatar sx={{width:32,height:32,bgcolor:'primary.main',color:'#fff',fontSize:12,fontWeight:800}}>{initials(userName)}</Avatar></IconButton></Tooltip>
   </Stack>
   <Menu anchorEl={anchor} open={!!anchor} onClose={()=>setAnchor(null)} slotProps={{paper:{sx:{width:280}}}}>
    <Box sx={{px:2,py:1}}><Typography fontWeight={750}>{userName||'TNGOS'}</Typography><Typography variant="caption" color="text.secondary" sx={{textTransform:'capitalize'}}>{role} workspace</Typography></Box><Divider/>
    <Box sx={{p:2}}><Typography variant="caption" color="text.secondary" sx={{display:'block',mb:1}}>Display mode</Typography><ToggleButtonGroup size="small" exclusive fullWidth value={mode||'standard'} onChange={(_,v)=>{if(v)onModeChange?.(v)}} aria-label="Display mode"><ToggleButton value="standard">Standard</ToggleButton><ToggleButton value="command">Command</ToggleButton></ToggleButtonGroup></Box>
    {['Dashboard','System Overview'].includes(page)&&<MenuItem onClick={()=>{onRefresh?.();setAnchor(null);}}><RefreshRoundedIcon sx={{mr:1,fontSize:18}}/>Refresh overview metrics</MenuItem>}
    <MenuItem onClick={()=>{onModules?.();setAnchor(null);}}>Workspace & layout settings</MenuItem>
    {role==='admin'&&<MenuItem onClick={()=>{onNavigate?.('Clover');setAnchor(null);}}>Connections & synchronization</MenuItem>}
    <Divider/><MenuItem onClick={()=>{setAnchor(null);onLogout?.();}} sx={{color:'error.main'}}>Log out</MenuItem>
   </Menu>
  </Toolbar>
 </AppBar>;
}
