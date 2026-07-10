import React, { useState } from "react";
import { Box, Drawer } from "@mui/material";
import Sidebar from "../components/Sidebar.jsx";
import TopBar from "./TopBar.jsx";

const DRAWER_WIDTH = 270;

export default function AppShell({
  role,
  page,
  setPage,
  userName,
  onRefresh,
  onSync,
  onLogout,
  children,
}) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const drawer = (
    <Sidebar
      role={role}
      page={page}
      setPage={setPage}
      onNavigate={() => setMobileOpen(false)}
    />
  );

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#f5f6f8" }}>
      <Drawer
        variant="permanent"
        open
        sx={{
          display: { xs: "none", lg: "block" },
          width: DRAWER_WIDTH,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: DRAWER_WIDTH,
            border: 0,
            boxSizing: "border-box",
          },
        }}
      >
        {drawer}
      </Drawer>

      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: "block", lg: "none" },
          "& .MuiDrawer-paper": {
            width: Math.min(DRAWER_WIDTH, 320),
            border: 0,
          },
        }}
      >
        {drawer}
      </Drawer>

      <Box
        sx={{
          ml: { xs: 0, lg: `${DRAWER_WIDTH}px` },
          minWidth: 0,
        }}
      >
        <TopBar
          page={page}
          role={role}
          userName={userName}
          onMenu={() => setMobileOpen(true)}
          onRefresh={onRefresh}
          onSync={onSync}
          onLogout={onLogout}
        />

        <Box
          component="main"
          sx={{
            width: "100%",
            maxWidth: 1600,
            mx: "auto",
            p: { xs: 1.5, sm: 2, md: 3 },
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
}
