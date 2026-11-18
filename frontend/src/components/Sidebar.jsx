import React, { useEffect, useState } from "react";
import {
  Box,
  Button, Collapse,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  TextField,
  InputAdornment,
} from "@mui/material";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import RestaurantRoundedIcon from "@mui/icons-material/RestaurantRounded";
import DashboardRoundedIcon from "@mui/icons-material/DashboardRounded";
import PeopleAltRoundedIcon from "@mui/icons-material/PeopleAltRounded";
import Inventory2RoundedIcon from "@mui/icons-material/Inventory2Rounded";
import QrCodeScannerRoundedIcon from "@mui/icons-material/QrCodeScannerRounded";
import PointOfSaleRoundedIcon from "@mui/icons-material/PointOfSaleRounded";
import PersonSearchRoundedIcon from "@mui/icons-material/PersonSearchRounded";
import GroupsRoundedIcon from "@mui/icons-material/GroupsRounded";
import QrCode2RoundedIcon from "@mui/icons-material/QrCode2Rounded";
import SyncAltRoundedIcon from "@mui/icons-material/SyncAltRounded";
import ContentCopyRoundedIcon from "@mui/icons-material/ContentCopyRounded";
import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";
import AssessmentRoundedIcon from "@mui/icons-material/AssessmentRounded";
import ManageAccountsRoundedIcon from "@mui/icons-material/ManageAccountsRounded";
import CampaignRoundedIcon from "@mui/icons-material/CampaignRounded";
import SchoolRoundedIcon from "@mui/icons-material/SchoolRounded";
import EventRoundedIcon from "@mui/icons-material/EventRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import HealthAndSafetyRoundedIcon from "@mui/icons-material/HealthAndSafetyRounded";
import ShieldRoundedIcon from "@mui/icons-material/ShieldRounded";
import VideoLibraryRoundedIcon from "@mui/icons-material/VideoLibraryRounded";
import StorefrontRoundedIcon from "@mui/icons-material/StorefrontRounded";
import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import DialpadRoundedIcon from '@mui/icons-material/DialpadRounded';
import TabletMacRoundedIcon from '@mui/icons-material/TabletMacRounded';
import { ROLE_MENUS, WORKSPACE_GROUPS, searchWorkspaces, dailyWorkspaces, workspaceGroup } from "../navigation/workspaces";
export { ROLE_MENUS } from "../navigation/workspaces";

const ICONS = {
  Dashboard: <DashboardRoundedIcon />,
  "Venue & Event Bookings": <EventRoundedIcon />,
  "Chef & Concessions": <RestaurantRoundedIcon />,
  "Text Inbox": <CampaignRoundedIcon />,
  "Call Center": <DialpadRoundedIcon />,
  "System Overview": <HealthAndSafetyRoundedIcon />,
  "Renewal Reminders": <CampaignRoundedIcon />,
  "TNG Apparel": <StorefrontRoundedIcon />,
  "Security Center": <ShieldRoundedIcon />,
  Members: <PeopleAltRoundedIcon />,
  "TNGTrainer": <SportsMmaRoundedIcon />,
  "TNG Boxing Game": <SportsMmaRoundedIcon />,
  Promoter: <SportsMmaRoundedIcon />,
  "Amateur Matchmaker": <SportsMmaRoundedIcon />,
  "Manager Portal": <GroupsRoundedIcon />,
  "Fight Calendar": <EventRoundedIcon />,
  "TNG BOXING EVENTS": <EventRoundedIcon />,
  Products: <Inventory2RoundedIcon />,
  "Member Check-In": <DialpadRoundedIcon />,
  "Check-In Kiosk": <TabletMacRoundedIcon />,
  "Event Check-In": <QrCode2RoundedIcon />,
  Sales: <PointOfSaleRoundedIcon />,
  "My Sales": <PointOfSaleRoundedIcon />,
  Leads: <PersonSearchRoundedIcon />,
  "Sales Reps": <GroupsRoundedIcon />,
  "QR Referrals": <QrCode2RoundedIcon />,
  "Marketing Center": <CampaignRoundedIcon />,
  Clover: <SyncAltRoundedIcon />,
  "Duplicate Review": <ContentCopyRoundedIcon />,
  Reports: <AssessmentRoundedIcon />,
  "Fighter Portal Videos": <VideoLibraryRoundedIcon />,
  "Investor Center": <AssessmentRoundedIcon />,
  "User Management": <ManageAccountsRoundedIcon />,
};

export default function Sidebar({
  role = "rep",
  pinned = [],
  onModules,
  page,
  setPage,
  onNavigate,
}) {
  const [search, setSearch] = useState("");
  const filtered = searchWorkspaces(role,search);
  const [openGroup,setOpenGroup]=useState(()=>workspaceGroup(page)?.id||null);
  const [shortcutsOpen,setShortcutsOpen]=useState(false);
  useEffect(()=>{setOpenGroup(workspaceGroup(page)?.id||null);setShortcutsOpen(false);setSearch("");},[page,role]);
  const shortcuts=(pinned.length?pinned:dailyWorkspaces(role)).filter(item=>(ROLE_MENUS[role]||[]).includes(item));
  const groupNames={home:'Overview',gym:'Gym & members',boxing:'Boxing & events',retail:'Shop & sales',growth:'Marketing & messages',admin:'Administration'};
  function tool(item,shortcut=false){const active=page===item;return <ListItemButton key={item} component="button" aria-current={active?'page':undefined} selected={active} onClick={()=>choosePage(item)} sx={{width:'100%',minHeight:42,borderRadius:1.5,mb:.3,pl:shortcut?1.5:2.25,color:active?'#fff':'#b5c2d4',textAlign:'left','&.Mui-selected, &.Mui-selected:hover':{bgcolor:'#d7193226',color:'#fff',boxShadow:'inset 2px 0 #ed3c55'},'&:hover':{bgcolor:'#ffffff09',color:'#fff'}}}><ListItemIcon sx={{minWidth:30,color:active?'#fa7187':'#8fa1bb','& svg':{fontSize:18}}}>{ICONS[item]||<DashboardRoundedIcon/>}</ListItemIcon><ListItemText primary={item} slotProps={{primary:{sx:{fontSize:12.5,fontWeight:active?800:550,lineHeight:1.4}}}}/></ListItemButton>;}

  function choosePage(item) {
    setSearch("");
    setPage(item);
    onNavigate?.();
  }

  return (
    <Box className="tng-sidebar" sx={{height:'100%',display:'flex',flexDirection:'column',color:'#fff',bgcolor:'#090d14'}}>
      <Box sx={{px:2.25,py:2,display:'flex',alignItems:'center',gap:1.5}}>
        <Box className="tng-brand-mark" sx={{width:34,height:34,fontSize:15}}>TNG</Box>
        <Box><Typography sx={{fontSize:19,fontWeight:900,letterSpacing:-.6}}>TNG <Box component="span" sx={{color:'#ed3c55'}}>OS</Box></Typography><Typography sx={{fontSize:9,color:'#8091a9',letterSpacing:1.5}}>THE NEXT GENERATION</Typography></Box>
      </Box>
      <Box sx={{px:1.75,pb:1.5}}><TextField fullWidth value={search} onChange={e=>setSearch(e.target.value)} placeholder="Find a tool…" slotProps={{htmlInput:{'aria-label':'Find workspace'},input:{startAdornment:<InputAdornment position="start"><SearchRoundedIcon sx={{fontSize:18,color:'#8fa1bb'}}/></InputAdornment>,endAdornment:search?<InputAdornment position="end"><IconButton size="small" aria-label="Clear workspace search" onClick={()=>setSearch('')} sx={{color:'#bbc7d8',minWidth:32,minHeight:32}}><CloseRoundedIcon sx={{fontSize:16}}/></IconButton></InputAdornment>:null}}} sx={{'& .MuiOutlinedInput-root':{color:'#fff',bgcolor:'#ffffff05',fontSize:12.5,'& fieldset':{borderColor:'#ffffff12'}},'& input':{py:1.25}}}/></Box>
      <Box sx={{flex:1,minHeight:0,overflowY:'auto',px:1.25,pb:1.5}}>
        {!search&&shortcuts.length>0&&<Box sx={{mb:1.5,border:'1px solid #ffffff0e',borderRadius:2,overflow:'hidden'}}>
          <ListItemButton component="button" aria-label={pinned.length?'Toggle pinned tools':'Toggle daily tools'} aria-expanded={shortcutsOpen} onClick={()=>{setShortcutsOpen(v=>!v);setOpenGroup(null);}} sx={{width:'100%',minHeight:42,color:'#c2cedf',px:1.5,textAlign:'left'}}><Typography sx={{fontSize:12,fontWeight:750,flex:1}}>{pinned.length?'Pinned tools':'Daily tools'}</Typography><ExpandMoreRoundedIcon sx={{fontSize:18,transform:shortcutsOpen?'rotate(180deg)':'none'}}/></ListItemButton>
          <Collapse in={shortcutsOpen} timeout={120} unmountOnExit><Box sx={{px:.5,pb:.5}}>{shortcuts.map(item=>tool(item,true))}</Box></Collapse>
        </Box>}
        <List component="nav" aria-label="Workspace navigation" disablePadding>
          {search?<><Typography sx={{px:1.25,py:1,fontSize:10,color:'#8091a9',letterSpacing:1}}>SEARCH RESULTS · {filtered.length}</Typography>{filtered.map(item=>tool(item,true))}{!filtered.length&&<Typography sx={{p:1.5,color:'#a5b3c7',fontSize:12}}>No tools match your search.</Typography>}</>:WORKSPACE_GROUPS.map(group=>{
            const items=group.pages.filter(item=>filtered.includes(item));if(!items.length)return null;const open=openGroup===group.id;
            return <Box key={group.id} sx={{mb:.5}}><ListItemButton component="button" aria-label={`Toggle ${group.label}`} aria-expanded={open} onClick={()=>{setOpenGroup(open?null:group.id);setShortcutsOpen(false);}} sx={{width:'100%',minHeight:46,borderRadius:2,px:1.25,gap:1.25,color:open?'#f0f5ff':'#a8b7cc',bgcolor:open?'#ffffff06':'transparent',textAlign:'left'}}><Box sx={{width:6,height:6,bgcolor:group.accent,borderRadius:1,flexShrink:0}}/><Typography sx={{flex:1,fontSize:12.5,fontWeight:open?800:650}}>{groupNames[group.id]||group.label}</Typography><ExpandMoreRoundedIcon sx={{fontSize:18,color:'#7f91aa',transform:open?'rotate(180deg)':'none'}}/></ListItemButton><Collapse in={open} timeout={120} unmountOnExit><Box sx={{ml:1.5,mt:.5,mb:1,borderLeft:'1px solid #ffffff12',pl:.5}}>{items.map(item=>tool(item))}</Box></Collapse></Box>;
          })}
        </List>
      </Box>
      <Box sx={{px:1.75,py:1.25,borderTop:'1px solid #ffffff0c'}}><Button fullWidth onClick={onModules} sx={{justifyContent:'flex-start',color:'#a9b9cf',fontSize:11.5,minHeight:36}}>All tools & layout</Button><Box sx={{display:'flex',alignItems:'center',justifyContent:'space-between',px:1,pt:.75}}><Typography sx={{fontSize:10,color:'#73849d'}}>WORKSPACE</Typography><Typography sx={{fontSize:10,color:'#b1c0d5',textTransform:'capitalize'}}>{role}</Typography></Box></Box>
    </Box>
  );
}
