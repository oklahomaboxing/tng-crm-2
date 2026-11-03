import React from "react";
import WorkspaceSearch from "../components/workspace/WorkspaceSearch";
import {
  AppBar,
  Avatar,
  Box,
  Button,
  Chip,
  IconButton,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import MenuRoundedIcon from "@mui/icons-material/MenuRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import SyncRoundedIcon from "@mui/icons-material/SyncRounded";
import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";

function initials(name) {
  return (name || "TNG")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export default function TopBar({
  page,
  role,
  userName,
  onMenu,
  onRefresh,
  onSync,
  onLogout,
  onNavigate,
  syncing,
}) {
  return (
    <AppBar
      className="tng-topbar"
      position="sticky"
      elevation={0}
      color="transparent"
      sx={{
        top: 0,
        zIndex: (theme) => theme.zIndex.drawer - 1,
        bgcolor: "rgba(12,17,26,.97)",color:'#f4f7fb',
        backdropFilter: "blur(14px)",
        borderBottom: "1px solid #293240",boxShadow:'inset 0 2px 0 #d71932',
      }}
    >
      <Toolbar sx={{ minHeight: { xs: 68, md: 76 }, gap: 1.5 }}>
        <IconButton
          onClick={onMenu}
          sx={{ color:'#dbe6f4',display: { xs: "inline-flex", lg: "none" } }}
          aria-label="Open navigation"
        >
          <MenuRoundedIcon />
        </IconButton>

        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography
            variant="h5"
            noWrap
            sx={{fontWeight: 900,  letterSpacing: -0.5 }}
          >
            {page}
          </Typography>
          <Typography variant="caption" sx={{color:'#8f9caf',letterSpacing:'.07em'}} noWrap>
            TNGOS / {role === 'admin' ? 'COMMAND' : 'WORKSPACE'}
          </Typography>
        </Box>

        <Stack
          direction="row"
          spacing={1}
          sx={{
            alignItems: "center",
          }}
        >
          <WorkspaceSearch role={role} onNavigate={onNavigate}/>
          <Tooltip title="Refresh command-center metrics">
            <IconButton onClick={onRefresh} aria-label="Refresh command-center metrics" sx={{color:'#aebdd1'}}>
              <RefreshRoundedIcon />
            </IconButton>
          </Tooltip>

          {role === "admin" && (
            <Button
              variant="outlined"
              startIcon={<SyncRoundedIcon />}
              onClick={onSync}
              disabled={syncing}
              sx={{ display: { xs: "none", md: "inline-flex" },color:'#d9e4f2',borderColor:'#394456' }}
            >
              {syncing ? "Syncing…" : "Sync Clover"}
            </Button>
          )}

          <Chip
            avatar={
              <Avatar sx={{ bgcolor: "#111", color: "white" }}>
                {initials(userName)}
              </Avatar>
            }
            label={userName || role}
            sx={{
              display: { xs: "none", sm: "flex" },
              fontWeight: 750,
              bgcolor: "#ffffff08",color:'#dbe6f4',
              border: "1px solid #303c4d",
            }}
          />

          <Tooltip title="Logout">
            <IconButton onClick={onLogout} aria-label="Logout" sx={{color:'#aebdd1'}}>
              <LogoutRoundedIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Toolbar>
    </AppBar>
  );
}
