import React from "react";
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
}) {
  return (
    <AppBar
      position="sticky"
      elevation={0}
      color="transparent"
      sx={{
        top: 0,
        zIndex: (theme) => theme.zIndex.drawer - 1,
        bgcolor: "rgba(248,249,251,.92)",
        backdropFilter: "blur(14px)",
        borderBottom: "1px solid #e7e8ec",
      }}
    >
      <Toolbar sx={{ minHeight: { xs: 68, md: 76 }, gap: 1.5 }}>
        <IconButton
          onClick={onMenu}
          sx={{ display: { xs: "inline-flex", lg: "none" } }}
          aria-label="Open navigation"
        >
          <MenuRoundedIcon />
        </IconButton>

        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography
            variant="h5"
            fontWeight={900}
            noWrap
            sx={{ letterSpacing: -0.5 }}
          >
            {page}
          </Typography>
          <Typography variant="body2" color="text.secondary" noWrap>
            TNG Boxing command center
          </Typography>
        </Box>

        <Stack direction="row" spacing={1} alignItems="center">
          <Tooltip title="Refresh page data">
            <IconButton onClick={onRefresh}>
              <RefreshRoundedIcon />
            </IconButton>
          </Tooltip>

          {role === "admin" && (
            <Button
              variant="outlined"
              startIcon={<SyncRoundedIcon />}
              onClick={onSync}
              sx={{ display: { xs: "none", md: "inline-flex" } }}
            >
              Sync
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
              bgcolor: "white",
              border: "1px solid #e2e4e8",
            }}
          />

          <Tooltip title="Logout">
            <IconButton onClick={onLogout} aria-label="Logout">
              <LogoutRoundedIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Toolbar>
    </AppBar>
  );
}
