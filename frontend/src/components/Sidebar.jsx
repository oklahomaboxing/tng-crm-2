import React from "react";
import {
  Box,
  Divider,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
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
export const ROLE_MENUS = {
  admin: [
    "Dashboard",
    "Members",
    "Products",
    "Front Desk",
    "Sales",
    "Leads",
    "Sales Reps",
    "QR Referrals",
    "Marketing Center",
    "Clover",
    "Duplicate Review",
    "AI Trainer",
    "Security Center",
    "Reports",
    "User Management",
  ],
  staff: [
    "Front Desk",
    "Members",
    "Sales",
    "Leads",
    "QR Referrals",
    "AI Trainer",
  ],
  rep: ["Sales", "Leads", "QR Referrals"],
};

const ICONS = {
  Dashboard: <DashboardRoundedIcon />,
  Members: <PeopleAltRoundedIcon />,
  Products: <Inventory2RoundedIcon />,
  "Front Desk": <QrCodeScannerRoundedIcon />,
  Sales: <PointOfSaleRoundedIcon />,
  Leads: <PersonSearchRoundedIcon />,
  "Sales Reps": <GroupsRoundedIcon />,
  "QR Referrals": <QrCode2RoundedIcon />,
  "Marketing Center": <CampaignRoundedIcon />,
  Clover: <SyncAltRoundedIcon />,
  "Duplicate Review": <ContentCopyRoundedIcon />,
  "AI Trainer": <SportsMmaRoundedIcon />,
  Reports: <AssessmentRoundedIcon />,
  "User Management": <ManageAccountsRoundedIcon />,
};

export default function Sidebar({
  role = "rep",
  page,
  setPage,
  onNavigate,
}) {
  const items = ROLE_MENUS[role] || ROLE_MENUS.rep;

  function choosePage(item) {
    setPage(item);
    onNavigate?.();
  }

  return (
    <Box
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: "#09090b",
        color: "white",
      }}
    >
      <Box sx={{ px: 2.5, pt: 2.5, pb: 2 }}>
        <Typography variant="h5" fontWeight={900} letterSpacing={-0.6}>
          TNG <Box component="span" sx={{ color: "#e31b23" }}>OS</Box>
        </Typography>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,.55)" }}>
          Earned Not Given
        </Typography>
      </Box>

      <Divider sx={{ borderColor: "rgba(255,255,255,.09)" }} />

      <List sx={{ px: 1.25, py: 1.5, flex: 1, overflowY: "auto" }}>
        {items.map((item) => {
          const active = page === item;

          return (
            <ListItemButton
              key={item}
              onClick={() => choosePage(item)}
              sx={{
                mb: 0.5,
                minHeight: 46,
                borderRadius: 2.5,
                color: active ? "white" : "rgba(255,255,255,.72)",
                bgcolor: active ? "#d71920" : "transparent",
                "&:hover": {
                  bgcolor: active ? "#d71920" : "rgba(255,255,255,.08)",
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
                primaryTypographyProps={{ fontWeight: active ? 800 : 650 }}
              />
            </ListItemButton>
          );
        })}
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
            ACCESS LEVEL
          </Typography>
          <Typography fontWeight={800} sx={{ textTransform: "capitalize" }}>
            {role}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
