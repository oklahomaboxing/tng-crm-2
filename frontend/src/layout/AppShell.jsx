import {ThemeProvider} from '@mui/material';
import standardTheme from '../theme/tngTheme';
import commandTheme from '../theme/commandTheme';
import {readDisplayMode,saveDisplayMode} from '../services/displayMode';
import CommandCenter from '../components/workspace/CommandCenter';
import {CommissionReportAlerts} from '../components/tickets/CommissionReports.jsx';
import React, { Suspense, useState } from "react";
import { Box, Drawer } from "@mui/material";
import Sidebar from "../components/Sidebar.jsx";
import TopBar from "./TopBar.jsx";
import WorkspaceBoundary, { WorkspaceLoading } from "../components/workspace/WorkspaceBoundary";
import './command.css';

const DRAWER_WIDTH = 270;

export default function AppShell({
  role,
  page,
  setPage,
  userName,
  onRefresh,
  onSync,
  onLogout,
  syncing,
  children,
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mode,setMode]=useState(readDisplayMode);
  function changeMode(value){setMode(saveDisplayMode(value));}

  const drawer = (
    <Sidebar
      role={role}
      page={page}
      setPage={setPage}
      onNavigate={() => setMobileOpen(false)}
    />
  );

  return (
    <ThemeProvider theme={mode==='command'?commandTheme:standardTheme}><Box className={`tng-shell ${mode==='command'?'tng-command':''}`} data-display-mode={mode} sx={{ minHeight: "100vh" }}>
      <Drawer
        variant="permanent"
        open
        sx={{
          display: { xs: "none", lg: "block" },
          width: DRAWER_WIDTH,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: DRAWER_WIDTH,
            border: 0,borderRight:'1px solid #ffffff08',
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
          mode={mode}
          onModeChange={changeMode}
          page={page}
          role={role}
          userName={userName}
          onMenu={() => setMobileOpen(true)}
          onRefresh={onRefresh}
          onSync={onSync}
          onLogout={onLogout}
          onNavigate={setPage}
          syncing={syncing}
        />

        <Box
          component="main"
          className="tng-main"
          sx={{
            width: "100%",
            maxWidth: 1600,
            mx: "auto",
            p: { xs: 1.5, sm: 2.5, md: 3.5 },
            pb: { xs: 12, md: 9 },
          }}
        >
          {role==='admin'&&<CommissionReportAlerts/>}
          {role==='admin'&&mode==='command'&&<CommandCenter onNavigate={setPage}/>}
          <Box key={page} className={mode==='command'?'tng-command-page':undefined}><WorkspaceBoundary workspace={page}><Suspense fallback={<WorkspaceLoading/>}>{children}</Suspense></WorkspaceBoundary></Box>
        </Box>
      </Box>
    </Box></ThemeProvider>
  );
}
