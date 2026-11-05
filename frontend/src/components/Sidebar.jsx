import React, { useState } from "react";
import {
  Box,
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
import GraphicEqRoundedIcon from '@mui/icons-material/GraphicEqRounded';
import DialpadRoundedIcon from '@mui/icons-material/DialpadRounded';
import TabletMacRoundedIcon from '@mui/icons-material/TabletMacRounded';
import { ROLE_MENUS, WORKSPACE_GROUPS } from "../navigation/workspaces";
export { ROLE_MENUS } from "../navigation/workspaces";

const ICONS = {
  Dashboard: <DashboardRoundedIcon />,
  "System Overview": <HealthAndSafetyRoundedIcon />,
  "Renewal Reminders": <CampaignRoundedIcon />,
  "TNG Apparel": <CampaignRoundedIcon />,
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
  const items = ROLE_MENUS[role] || [];
  const filtered = items.filter(item => item.toLowerCase().includes(search.toLowerCase()));

  function choosePage(item) {
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
      <List component="nav" aria-label="Workspace navigation" sx={{ px: 1.25, py: 1.5, flex: 1, overflowY: "auto" }}>
        {WORKSPACE_GROUPS.map(group => {
          const groupItems = group.pages.filter(item => filtered.includes(item));
          if (!groupItems.length) return null;
          return <React.Fragment key={group.label}>
          <Typography component="div" sx={{ px: 1.6, pt: 2, pb: 1, fontSize: 10, fontWeight: 800, letterSpacing: 1.5, color: '#81818e' }}>{group.label}</Typography>
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
                slotProps={{
                  primary: {
                    sx: {
                      fontWeight: active ? 800 : 650,
                    },
                  },
                }}
              />
            </ListItemButton>
          );
          })}</React.Fragment>;
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


