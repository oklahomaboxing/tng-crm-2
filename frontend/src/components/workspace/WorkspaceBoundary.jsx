import React from 'react';
import { Alert, Box, Button, CircularProgress, Stack, Typography } from '@mui/material';
export function WorkspaceLoading() {
  return <Stack spacing={2} sx={{alignItems: "center", justifyContent: "center",  minHeight: '40vh', p: 3 }} role="status"><CircularProgress color="error"/><Typography color="text.secondary">Opening your workspace…</Typography></Stack>;
}
export default class WorkspaceBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidUpdate(previous) { if (previous.workspace !== this.props.workspace && this.state.failed) this.setState({ failed: false }); }
  render() {
    if (!this.state.failed) return this.props.children;
    return <Box sx={{ p: 3 }}><Alert severity="error">This workspace could not be displayed. Your saved records are still on the server.</Alert><Typography color="text.secondary" sx={{ my: 2 }}>Choose another workspace from navigation, or reload TNGOS. Reloading may discard unsaved form changes.</Typography><Button variant="outlined" onClick={() => window.location.reload()}>Reload TNGOS</Button></Box>;
  }
}
