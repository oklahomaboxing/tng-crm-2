import {ThemeProvider} from '@mui/material';
import standardTheme from '../theme/tngTheme';
import commandTheme from '../theme/commandTheme';
import {readDisplayMode,saveDisplayMode} from '../services/displayMode';
import CommandCenter from '../components/workspace/CommandCenter';
import {CommissionReportAlerts} from '../components/tickets/CommissionReports.jsx';
import React, { Suspense, useEffect, useMemo, useState } from "react";
import { Alert, Box, Drawer, createTheme } from "@mui/material";
import Sidebar from "../components/Sidebar.jsx";
import TopBar from "./TopBar.jsx";
import WorkspaceBoundary, { WorkspaceLoading } from "../components/workspace/WorkspaceBoundary";
import './command.css';
import ModuleCenter from '../components/workspace/ModuleCenter';
import WorkspaceGuide from '../components/workspace/WorkspaceGuide';
import {readWorkspacePreferences,saveWorkspacePreferences,visitWorkspace,togglePinnedWorkspace} from '../services/workspacePreferences';

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
  const [briefingOpen,setBriefingOpen]=useState(false);
  const [modulesOpen,setModulesOpen]=useState(false);
  const [preferenceState,setPreferenceState]=useState(()=>({role,value:readWorkspacePreferences(role)}));
  const preferences=preferenceState.role===role?preferenceState.value:readWorkspacePreferences(role);
  const [offline,setOffline]=useState(()=>navigator.onLine===false);
  useEffect(()=>{const changed=()=>setOffline(navigator.onLine===false);window.addEventListener('online',changed);window.addEventListener('offline',changed);return()=>{window.removeEventListener('online',changed);window.removeEventListener('offline',changed);};},[]);
  useEffect(()=>{setPreferenceState(state=>({role,value:saveWorkspacePreferences(role,visitWorkspace(role,state.role===role?state.value:readWorkspacePreferences(role),page))}));},[role,page]);
  function updatePreferences(next){setPreferenceState({role,value:saveWorkspacePreferences(role,next)});}
  function pin(page){updatePreferences(togglePinnedWorkspace(role,preferences,page));}
  const [mode,setMode]=useState(readDisplayMode);
  function changeMode(value){setMode(saveDisplayMode(value));}
  const theme=useMemo(()=>createTheme(mode==='command'?commandTheme:standardTheme,preferences.density==='compact'?{components:{MuiTableCell:{styleOverrides:{root:{padding:'9px 12px'}}},MuiButton:{styleOverrides:{root:{minHeight:36}}},MuiOutlinedInput:{styleOverrides:{input:{paddingTop:9,paddingBottom:9}}}}}:{}),[mode,preferences.density]);

  const drawer = (
    <Sidebar
      role={role}
      pinned={preferences.pinned}
      onModules={() => setModulesOpen(true)}
      page={page}
      setPage={setPage}
      onNavigate={() => setMobileOpen(false)}
    />
  );

  return (
    <ThemeProvider theme={theme}><Box className={`tng-shell ${mode==='command'?'tng-command':''}`} data-display-mode={mode} data-density={preferences.density} sx={{ minHeight: "100vh" }}>
      <Box component="a" href="#tng-workspace-content" className="tng-skip-link" onClick={e=>{e.preventDefault();document.getElementById('tng-workspace-content')?.focus();}}>Skip to workspace</Box>
      <ModuleCenter open={modulesOpen} onClose={()=>setModulesOpen(false)} role={role} page={page} onNavigate={setPage} preferences={preferences} onPreferences={updatePreferences} onPin={pin}/>
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
          onModules={() => setModulesOpen(true)}
          moduleCenterOpen={modulesOpen}
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
          id="tng-workspace-content"
          tabIndex={-1}
          className="tng-main"
          sx={{
            width: "100%",
            maxWidth: 1600,
            mx: "auto",
            p: { xs: 1.5, sm: 2.5, md: 3.5 },
            pb: { xs: 12, md: 9 },
          }}
        >
          {offline&&<Alert severity="warning" sx={{mb:2}}>This browser is offline. Reconnect before saving or checking in. TNGOS cannot confirm changes while offline.</Alert>}
          {role==='admin'&&<CommissionReportAlerts/>}
          {role==='admin'&&['Dashboard','System Overview'].includes(page)&&mode==='command'&&<Box component="details" onToggle={e=>setBriefingOpen(e.currentTarget.open)} sx={{mb:2}}><Box component="summary" sx={{cursor:'pointer',fontWeight:700,p:1}}>Command briefing</Box>{briefingOpen&&<CommandCenter onNavigate={setPage}/>}</Box>}
          {!preferences.focus&&<WorkspaceGuide key={`guide-${page}`} role={role} page={page} onNavigate={setPage} pinned={preferences.pinned.includes(page)} onPin={pin} onModules={()=>setModulesOpen(true)}/>}
          <Box key={page} className={`tng-module-surface ${mode==='command'?'tng-command-page':''}`}><WorkspaceBoundary workspace={page}><Suspense fallback={<WorkspaceLoading/>}>{children}</Suspense></WorkspaceBoundary></Box>
        </Box>
      </Box>
    </Box></ThemeProvider>
  );
}
