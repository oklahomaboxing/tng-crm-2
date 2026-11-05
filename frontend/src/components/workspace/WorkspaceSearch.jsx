import React, { useEffect, useState } from "react";
import { Box, Button, Dialog, DialogContent, DialogTitle, List, ListItemButton, ListItemText, TextField, Typography } from "@mui/material";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import { WORKSPACE_GROUPS, WORKSPACE_HINTS, searchWorkspaces } from "../../navigation/workspaces";
export default function WorkspaceSearch({ role, onNavigate }) {
  const [open, setOpen] = useState(false), [query, setQuery] = useState("");
  const results = searchWorkspaces(role,query);
  useEffect(() => {
    function shortcut(event) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setOpen(v => !v); }
    }
    window.addEventListener("keydown", shortcut); return () => window.removeEventListener("keydown", shortcut);
  }, []);
  function choose(page) { onNavigate(page); setOpen(false); setQuery(""); }
  return <>
    <Button color="inherit" startIcon={<SearchRoundedIcon/>} onClick={() => setOpen(true)} aria-label="Search workspaces" sx={{ color: 'inherit',opacity:.8,border:'1px solid #ffffff20', minWidth: 0 }}><Box component="span" sx={{ display: { xs: 'none', md: 'inline' } }}>Search <Box component="kbd" sx={{ml:2,fontSize:11,opacity:.65}}>⌘ / Ctrl K</Box></Box></Button>
    <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
      <DialogTitle fontWeight={900}>Go to workspace</DialogTitle>
      <DialogContent>
        <TextField autoFocus fullWidth label="Search TNGOS" value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && results[0]) {const first=WORKSPACE_GROUPS.flatMap(g=>g.pages).find(p=>results.includes(p));if(first)choose(first);} }} sx={{ mt: 1 }}/>
        <List>{WORKSPACE_GROUPS.map(group=>{const pages=group.pages.filter(p=>results.includes(p));if(!pages.length)return null;return <Box key={group.id}><Typography sx={{fontSize:10,fontWeight:850,letterSpacing:1,color:'text.secondary',pt:2,pb:.5,px:2}}>{group.label}</Typography>{pages.map(page=><ListItemButton key={page} onClick={()=>choose(page)} sx={{borderRadius:2}}><ListItemText primary={page} secondary={WORKSPACE_HINTS[page]}/></ListItemButton>)}</Box>;})}</List>
        {!results.length && <Typography color="text.secondary" sx={{ py: 3 }}>No workspaces match your search.</Typography>}
      </DialogContent>
    </Dialog>
  </>;
}
