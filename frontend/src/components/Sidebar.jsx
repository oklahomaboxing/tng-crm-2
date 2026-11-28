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
import { ROLE_MENUS, WORKSPACE_GROUPS, searchWorkspaces, workspaceGroup } from "../navigation/workspaces";
export { ROLE_MENUS } from "../navigation/workspaces";

const ICONS = {
  "TNG NeuroLab": <SchoolRoundedIcon/>,
  "USA Boxing Officials": <GroupsRoundedIcon/>,
  "Oklahoma Boxing Clubs": <GroupsRoundedIcon/>,
  "Fight Recap": <AssessmentRoundedIcon/>,
  Dashboard: <DashboardRoundedIcon />,
  "Venue & Event Bookings": <EventRoundedIcon />,
  "Chef & Concessions": <RestaurantRoundedIcon />,
  "Club Inbox": <CampaignRoundedIcon/>,
  "Venue Inbox": <CampaignRoundedIcon/>,
  "Text Inbox": <CampaignRoundedIcon />,
  "Officials Inbox": <CampaignRoundedIcon />,
  "Call Center": <DialpadRoundedIcon />,
  "System Overview": <HealthAndSafetyRoundedIcon />,
  "Renewal Reminders": <CampaignRoundedIcon />,
  "TNG Apparel": <StorefrontRoundedIcon />,
  "Security Center": <ShieldRoundedIcon />,
  Members: <PeopleAltRoundedIcon />,
  "Announcer & DJ": <SportsMmaRoundedIcon />,
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
  const filtered = searchWorkspaces(role,search).filter(item=>item!=='Officials Inbox');
  const [openGroup,setOpenGroup]=useState(()=>workspaceGroup(page)?.id||null);
  useEffect(()=>{setOpenGroup(workspaceGroup(page)?.id||null);setSearch("");},[page,role]);
  const shortcuts=pinned.filter(item=>item!=='Officials Inbox'&&(ROLE_MENUS[role]||[]).includes(item));
  const groupNames={home:'Overview',gym:'Gym & members',boxing:'TNG PROMOTIONS',operations:'Facility management',retail:'Shop & sales',growth:'Marketing & messages',admin:'Administration'};
  const labels={'TNG BOXING EVENTS':'Events & fight cards','Promoter':'Pro matchmaking','TNGTrainer':'Training','TNG Boxing Game':'Boxing Game'};
  const groupIcons={home:<DashboardRoundedIcon/>,gym:<PeopleAltRoundedIcon/>,operations:<EventRoundedIcon/>,boxing:<SportsMmaRoundedIcon/>,retail:<StorefrontRoundedIcon/>,growth:<CampaignRoundedIcon/>,admin:<ManageAccountsRoundedIcon/>};
  function tool(item,shortcut=false){const active=page===item;return <ListItemButton key={item} component="button" aria-current={active?'page':undefined} selected={active} onClick={()=>choosePage(item)} sx={{width:'100%',minHeight:40,borderRadius:'6px',mb:'2px',px:1.5,color:'#fff',textAlign:'left',border:'1px solid transparent','&.Mui-selected, &.Mui-selected:hover':{bgcolor:'#b41d33',borderColor:'#e03a50',color:'#fff',boxShadow:'none'},'&:hover':{bgcolor:'#ffffff0b',color:'#fff'}}}><ListItemIcon sx={{minWidth:28,color:'#e4eaf3','& svg':{fontSize:17}}}>{ICONS[item]||<DashboardRoundedIcon/>}</ListItemIcon><ListItemText primary={labels[item]||item} slotProps={{primary:{sx:{fontSize:13,fontWeight:active?700:500,lineHeight:1.35}}}}/></ListItemButton>;}

  function choosePage(item) {
    setSearch("");
    setPage(item);
    onNavigate?.();
  }

  return (
    <Box className="tng-sidebar" sx={{height:'100%',display:'flex',flexDirection:'column',color:'#fff',bgcolor:'#090d14'}}>
      <Box sx={{px:2.25,py:2.5,display:'flex',alignItems:'center',gap:1.5}}>
        <Box className="tng-brand-mark" sx={{width:34,height:34,fontSize:15}}>TNG</Box>
        <Box><Typography sx={{fontSize:19,fontWeight:900,letterSpacing:-.6}}>TNG <Box component="span" sx={{color:'#ed3c55'}}>OS</Box></Typography><Typography sx={{fontSize:9,color:'#8091a9',letterSpacing:1.5}}>THE NEXT GENERATION</Typography></Box>
      </Box>
      <Box sx={{px:1.75,pb:1.5}}><TextField fullWidth value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search workspace" slotProps={{htmlInput:{'aria-label':'Find workspace'},input:{startAdornment:<InputAdornment position="start"><SearchRoundedIcon sx={{fontSize:18,color:'#8fa1bb'}}/></InputAdornment>,endAdornment:search?<InputAdornment position="end"><IconButton size="small" aria-label="Clear workspace search" onClick={()=>setSearch('')} sx={{color:'#bbc7d8',minWidth:32,minHeight:32}}><CloseRoundedIcon sx={{fontSize:16}}/></IconButton></InputAdornment>:null}}} sx={{'& .MuiOutlinedInput-root':{color:'#fff',borderRadius:'8px',bgcolor:'#ffffff05',fontSize:12.5,'& fieldset':{borderColor:'#ffffff12'}},'& input':{py:1.25}}}/></Box>
      <Box sx={{flex:1,minHeight:0,overflowY:'auto',px:1.25,pb:1.5}}>
        {!search&&shortcuts.length>0&&<Box sx={{mb:2}}><Typography sx={{px:1.5,mb:.75,fontSize:10,color:'#8294ad',letterSpacing:1.4}}>PINNED</Typography>{shortcuts.map(item=>tool(item,true))}</Box>}
        <List component="nav" aria-label="Workspace navigation" disablePadding>
          {search?<><Typography sx={{px:1.25,py:1,fontSize:10,color:'#8091a9',letterSpacing:1}}>SEARCH RESULTS · {filtered.length}</Typography>{filtered.map(item=>tool(item,true))}{!filtered.length&&<Typography sx={{p:1.5,color:'#a5b3c7',fontSize:12}}>No tools match your search.</Typography>}</>:WORKSPACE_GROUPS.map(group=>{
            const priority=['TNG BOXING EVENTS','Fight Recap','USA Boxing Officials','Oklahoma Boxing Clubs','Club Inbox','Venue Inbox','Promoter','Amateur Matchmaker','Fight Calendar','Event Check-In'];const items=group.pages.filter(item=>filtered.includes(item)).sort((a,b)=>{if(group.id!=='boxing')return 0;const ai=priority.indexOf(a),bi=priority.indexOf(b);return (ai<0?99:ai)-(bi<0?99:bi);});if(!items.length)return null;const open=openGroup===group.id;
            return <Box key={group.id} sx={{mb:.75}}><ListItemButton component="button" aria-label={`Toggle ${group.label}`} aria-expanded={open} onClick={()=>setOpenGroup(open?null:group.id)} sx={{width:'100%',minHeight:42,borderRadius:'6px',px:1.5,gap:1.25,color:'#ff526c',textAlign:'left','&:hover':{bgcolor:'#ffffff08'}}}><Box sx={{display:'flex',color:'#ff526c','& svg':{fontSize:18}}}>{groupIcons[group.id]}</Box><Typography sx={{flex:1,fontSize:12,fontWeight:700,letterSpacing:.2}}>{groupNames[group.id]||group.label}</Typography><ExpandMoreRoundedIcon sx={{fontSize:17,color:'#7f91aa',transform:open?'rotate(180deg)':'none'}}/></ListItemButton><Collapse in={open} timeout={120} unmountOnExit><Box sx={{ml:1.5,mt:.25,mb:1,pl:1,borderLeft:'1px solid #2c384a'}}>{group.id==='boxing'?[['EVENT PLANNING',['TNG BOXING EVENTS','Promoter','Amateur Matchmaker','Fight Calendar','Fighter Portal Videos','Manager Portal']],['FIGHT NIGHT',['Event Check-In','Announcer & DJ','Fight Recap']],['BOXING NETWORK',['USA Boxing Officials','Oklahoma Boxing Clubs','Club Inbox','Officials Inbox']]].map(([title,pages])=>{const visible=pages.filter(p=>items.includes(p));return visible.length?<Box key={title} sx={{mt:1.5}}><Typography sx={{fontSize:9,letterSpacing:1.1,color:'#fff',px:1.5,mb:.75}}>{title}</Typography>{visible.map(item=>tool(item))}</Box>:null;}):items.map(item=>tool(item))}</Box></Collapse></Box>;
          })}
        </List>
      </Box>
      <Box sx={{px:1.75,py:1,borderTop:'1px solid #ffffff0c'}}><Button fullWidth onClick={onModules} sx={{justifyContent:'flex-start',color:'#a9b9cf',fontSize:11.5,minHeight:36}}>Customize workspace</Button><Box sx={{display:'flex',alignItems:'center',justifyContent:'space-between',px:1,pt:.75}}><Typography sx={{fontSize:10,color:'#73849d'}}>WORKSPACE</Typography><Typography sx={{fontSize:10,color:'#b1c0d5',textTransform:'capitalize'}}>{role}</Typography></Box></Box>
    </Box>
  );
}
