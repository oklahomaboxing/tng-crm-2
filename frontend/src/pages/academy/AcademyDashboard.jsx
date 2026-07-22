import React, { useEffect, useMemo, useState } from "react";
import { Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Grid, Stack, TextField, Typography } from "@mui/material";
import SchoolRoundedIcon from "@mui/icons-material/SchoolRounded";
import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";
import GroupsRoundedIcon from "@mui/icons-material/GroupsRounded";
import PlayCircleRoundedIcon from "@mui/icons-material/PlayCircleRounded";
import { academyApi } from "../../services/academyApi";

function Metric({ label, value, icon }) {
  return <Card><CardContent><Stack direction="row" justifyContent="space-between" alignItems="center"><Box><Typography color="text.secondary" fontWeight={700}>{label}</Typography><Typography variant="h3" fontWeight={950}>{value ?? 0}</Typography></Box>{icon}</Stack></CardContent></Card>;
}

export default function AcademyDashboard() {
  const [data, setData] = useState(null);
  const [programs, setPrograms] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ title: "", coach_name: "", focus: "" });

  async function load() {
    setLoading(true); setError("");
    try {
      const [dashboard, programRows] = await Promise.all([academyApi.dashboard(), academyApi.programs()]);
      setData(dashboard); setPrograms(programRows);
    } catch (e) { setError(e.message); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);
  const recent = useMemo(() => data?.recent_sessions || [], [data]);

  async function startPractice() {
    if (!form.title.trim()) return setError("Enter a practice title.");
    setSaving(true); setError("");
    try {
      await academyApi.startSession({ ...form, attach_checked_in_members: true });
      setOpen(false); setForm({ title: "", coach_name: "", focus: "" }); await load();
    } catch (e) { setError(e.message); } finally { setSaving(false); }
  }

  if (loading && !data) return <Box sx={{ minHeight: 320, display: "grid", placeItems: "center" }}><CircularProgress /></Box>;

  return <Stack spacing={3}>
    <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, alignItems: { xs: "stretch", md: "center" }, flexDirection: { xs: "column", md: "row" } }}>
      <Box><Typography variant="h4" fontWeight={950}>TNG Academy</Typography><Typography color="text.secondary">Programs, classes, live practices, attendance and athlete development.</Typography></Box>
      <Button variant="contained" startIcon={<PlayCircleRoundedIcon />} onClick={() => setOpen(true)}>Start Practice</Button>
    </Box>
    {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}
    <Grid container spacing={2}>
      <Grid item xs={12} sm={6} lg={3}><Metric label="Active Programs" value={data?.active_programs} icon={<SchoolRoundedIcon color="error" sx={{ fontSize: 40 }} />} /></Grid>
      <Grid item xs={12} sm={6} lg={3}><Metric label="Active Classes" value={data?.active_classes} icon={<SportsMmaRoundedIcon color="error" sx={{ fontSize: 40 }} />} /></Grid>
      <Grid item xs={12} sm={6} lg={3}><Metric label="Sessions Today" value={data?.sessions_today} icon={<PlayCircleRoundedIcon color="error" sx={{ fontSize: 40 }} />} /></Grid>
      <Grid item xs={12} sm={6} lg={3}><Metric label="Athletes Today" value={data?.athletes_today} icon={<GroupsRoundedIcon color="error" sx={{ fontSize: 40 }} />} /></Grid>
    </Grid>
    <Grid container spacing={3}>
      <Grid item xs={12} lg={8}><Card><CardContent><Typography variant="h6" fontWeight={900} sx={{ mb: 2 }}>Recent Practices</Typography><Stack spacing={1.25}>{recent.length === 0 ? <Typography color="text.secondary">No Academy sessions have been created yet.</Typography> : recent.map((row) => <Box key={row.id} sx={{ p: 2, border: "1px solid #ececf0", borderRadius: 2.5, display: "flex", justifyContent: "space-between", gap: 2 }}><Box><Typography fontWeight={900}>{row.title}</Typography><Typography variant="body2" color="text.secondary">{row.focus || "General training"} · {row.coach_name || "Coach not assigned"}</Typography></Box><Stack alignItems="flex-end"><Chip size="small" label={row.status} color={row.status === "live" ? "error" : "default"} /><Typography variant="caption" color="text.secondary">{row.participant_count} athletes</Typography></Stack></Box>)}</Stack></CardContent></Card></Grid>
      <Grid item xs={12} lg={4}><Card><CardContent><Typography variant="h6" fontWeight={900}>Programs</Typography><Typography color="text.secondary" sx={{ mb: 2 }}>Academy pathways currently configured.</Typography><Stack spacing={1}>{programs.length === 0 ? <Alert severity="info">Program creation is available through the Academy API in this core release. The full Programs screen comes next.</Alert> : programs.map((p) => <Box key={p.id} sx={{ p: 1.5, bgcolor: "#fafafa", borderRadius: 2 }}><Typography fontWeight={850}>{p.name}</Typography><Typography variant="caption" color="text.secondary">{p.level} · {p.age_group}</Typography></Box>)}</Stack></CardContent></Card></Grid>
    </Grid>
    <Dialog open={open} onClose={() => !saving && setOpen(false)} fullWidth maxWidth="sm"><DialogTitle fontWeight={900}>Start Live Practice</DialogTitle><DialogContent><Stack spacing={2} sx={{ pt: 1 }}><TextField label="Practice title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required /><TextField label="Coach" value={form.coach_name} onChange={(e) => setForm({ ...form, coach_name: e.target.value })} /><TextField label="Training focus" value={form.focus} onChange={(e) => setForm({ ...form, focus: e.target.value })} multiline minRows={2} /><Alert severity="info">Members checked in today will automatically be attached to this practice.</Alert></Stack></DialogContent><DialogActions><Button onClick={() => setOpen(false)} disabled={saving}>Cancel</Button><Button variant="contained" onClick={startPractice} disabled={saving}>{saving ? "Starting..." : "Start Practice"}</Button></DialogActions></Dialog>
  </Stack>;
}
