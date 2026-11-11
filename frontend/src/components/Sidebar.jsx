import React, { useEffect, useState } from "react";
import {
  Box,
  Button, Collapse,
  Divider,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  TextField,
  InputAdornment,
} from "@mui/material";
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
  "Text Inbox": <CampaignRoundedIcon />,
  "Call Center": <DialpadRoundedIcon />,
  "System Overview": <HealthAndSafetyRoundedIcon />,
  "Renewal Reminders": <CampaignRoundedIcon />,
  "TNG Apparel": <StorefrontRoundedIcon />,
  "Security Center": <ShieldRoundedIcon />,
  Members: <PeopleAltRoundedIcon />,
  "TNGTrainer": <SportsMmaRoundedIcon />,
  Promoter: <SportsMmaRoundedIcon />,
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
  "User Management": <ManageAccountsRoundedIcon />,
};

export default function Sidebar({
  role = "rep",
  page,
  setPage,
  onNavigate,
}) {
  const [search, setSearch] = useState("");
  const filtered = searchWorkspaces(role,search);
  const [expanded,setExpanded]=useState(()=>Object.fromEntries(WORKSPACE_GROUPS.map(g=>[g.id,g.id==='home'||g.pages.includes(page)])));
  useEffect(()=>{const group=workspaceGroup(page);if(group)setExpanded({home:true,[group.id]:true});},[page,role]);

  function choosePage(item) {
    setSearch("");
    setPage(item);
    onNavigate?.();
  }

  return (
    <Box className="tng-sidebar"
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: "#09090b",
        color: "white",
      }}
    >
      <Box sx={{ px: 2.5, pt: 3, pb: 2.5 }}>
        <Box sx={{display:'flex',alignItems:'center',gap:1.5,mb:1}}><Box className="tng-brand-mark">TNG</Box><Box>
        <Typography variant="h5" letterSpacing={-0.6} sx={{fontWeight: 900}}>
          TNG <Box component="span" sx={{ color: "#e31b23" }}>OS</Box>
        </Typography>
        </Box></Box>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,.55)" }}>
          THE NEXT GENERATION · BOXING
        </Typography>
      </Box>

      <Divider sx={{ borderColor: "rgba(255,255,255,.09)" }} />

      <Box sx={{ px: 2, pt: 2 }}><TextField fullWidth value={search} onChange={e => setSearch(e.target.value)} placeholder="Find workspace" inputProps={{ 'aria-label': 'Find workspace' }} slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchRoundedIcon fontSize="small" sx={{ color: '#9c9ca6' }}/></InputAdornment> } }} sx={{ '& .MuiOutlinedInput-root': { color: 'white', bgcolor: '#19191e', '& fieldset': { borderColor: '#303038' } } }}/></Box>
      {!search&&<Box sx={{px:2,pt:2}}><Typography variant="caption" sx={{color:'#8995a6',fontWeight:800,letterSpacing:1}}>DAILY TOOLS</Typography><Box sx={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:.7,mt:1}}>{dailyWorkspaces(role).map(item=><Button key={item} onClick={()=>choosePage(item)} sx={{color:page===item?'#fff':'#bbc7d8',border:'1px solid',borderColor:page===item?'#ef3c5755':'#ffffff12',bgcolor:page===item?'#d7193222':'#ffffff04',fontSize:11,lineHeight:1.4,py:1,minHeight:44,textAlign:'center'}}>{item}</Button>)}</Box></Box>}
      <List component="nav" aria-label="Workspace navigation" sx={{ px: 1.25, py: 1.5, flex: 1, overflowY: "auto" }}>
        {WORKSPACE_GROUPS.map(group => {
          const groupItems = group.pages.filter(item => filtered.includes(item));
          if (!groupItems.length) return null;
          const open=!!search||!!expanded[group.id];
          return <React.Fragment key={group.id}>
          <ListItemButton component="button" aria-label={`Toggle ${group.label}`} aria-expanded={open} onClick={()=>setExpanded({...expanded,[group.id]:!expanded[group.id]})} sx={{width:'100%',mt:1,borderRadius:2,py:1.2,minHeight:44,color:'#93a1b4',gap:1}}><Box sx={{width:5,height:5,bgcolor:group.accent,borderRadius:'50%'}}/><Typography sx={{fontSize:10,fontWeight:850,letterSpacing:1.1,flex:1,textAlign:'left'}}>{group.label}</Typography><Typography sx={{fontSize:10,opacity:.6}}>{groupItems.length}</Typography><ExpandMoreRoundedIcon sx={{fontSize:16,transform:open?'rotate(180deg)':'none'}}/></ListItemButton>
          <Collapse in={open} timeout={150} unmountOnExit>
          {groupItems.map((item) => {
          const active = page === item;

          return (
            <ListItemButton
              key={item}
              onClick={() => choosePage(item)}
              selected={active}
              aria-current={active ? "page" : undefined}
              sx={{
                mb: 0.5,
                minHeight: 46,
                borderRadius: 2.5,
                color: active ? "white" : "rgba(255,255,255,.72)",
                bgcolor: active ? "#d7193224" : "transparent",border:'1px solid transparent',
                "&.Mui-selected, &.Mui-selected:hover": { bgcolor: "#d7193224", color: "white",borderColor:'#f6405a40',boxShadow:'inset 3px 0 0 #f6405a' },
                "&:hover": {
                  bgcolor: active ? "#d7193224" : "rgba(255,255,255,.05)",
                  color: "white",
                },
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: 38,
                  color: "inherit",
                }}
              >
                {ICONS[item]}
              </ListItemIcon>
              <ListItemText
                primary={item}
                secondary={item==='Promoter'?'Fighters & matchmaking':item==='TNG BOXING EVENTS'?'Cards, tickets & contracts':undefined}
                slotProps={{
                  secondary: {sx:{color:'#8796ad',fontSize:11}},
                  primary: {
                    sx: {
                      fontWeight: active ? 800 : 650,
                    },
                  },
                }}
              />
            </ListItemButton>
          );
          })}</Collapse></React.Fragment>;
        })}
        {!filtered.length && <Typography sx={{ p: 2, color: '#aaa' }}>No matching workspaces</Typography>}
      </List>

      <Box sx={{ p: 2 }}>
        <Box
          sx={{
            p: 1.5,
            borderRadius: 2.5,
            bgcolor: "rgba(255,255,255,.06)",
            border: "1px solid rgba(255,255,255,.08)",
          }}
        >
          <Typography variant="caption" sx={{ color: "rgba(255,255,255,.55)" }}>
            <span className="tng-status-dot"/>WORKSPACE ACCESS
          </Typography>
          <Typography sx={{fontWeight: 800,  textTransform: "capitalize" }}>
            {role}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}


