import React, { useEffect, useState } from "react";
import { Box, Button, Dialog, DialogContent, DialogTitle, List, ListItemButton, ListItemText, TextField, Typography } from "@mui/material";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import { ROLE_MENUS, WORKSPACE_HINTS } from "../../navigation/workspaces";
export default function WorkspaceSearch({ role, onNavigate }) {
  const [open, setOpen] = useState(false), [query, setQuery] = useState("");
  const results = (ROLE_MENUS[role] || []).filter(page => `${page} ${WORKSPACE_HINTS[page] || ""}`.toLowerCase().includes(query.toLowerCase()));
  useEffect(() => {
    function shortcut(event) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setOpen(v => !v); }
    }
    window.addEventListener("keydown", shortcut); return () => window.removeEventListener("keydown", shortcut);
  }, []);
  function choose(page) { onNavigate(page); setOpen(false); setQuery(""); }
  return <>
    <Button color="inherit" startIcon={<SearchRoundedIcon/>} onClick={() => setOpen(true)} aria-label="Search workspaces" sx={{ color: 'text.secondary', minWidth: 0 }}><Box component="span" sx={{ display: { xs: 'none', md: 'inline' } }}>Search · Ctrl K</Box></Button>
    <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
      <DialogTitle fontWeight={900}>Go to workspace</DialogTitle>
      <DialogContent>
        <TextField autoFocus fullWidth label="Search TNGOS" value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && results[0]) choose(results[0]); }} sx={{ mt: 1 }}/>
        <List>{results.map(page => <ListItemButton key={page} onClick={() => choose(page)} sx={{ borderRadius: 2 }}><ListItemText primary={page} secondary={WORKSPACE_HINTS[page]}/></ListItemButton>)}</List>
        {!results.length && <Typography color="text.secondary" sx={{ py: 3 }}>No workspaces match your search.</Typography>}
      </DialogContent>
    </Dialog>
  </>;
}
