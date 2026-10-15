import React, { useEffect, useState } from "react";
import { Alert, Box, Button, Card, Chip, CircularProgress, FormControl, InputLabel, MenuItem, Select, Stack, TextField, Typography } from "@mui/material";
import { Search, ExternalLink, BookmarkPlus, MapPin, Phone, Mail } from "lucide-react";
const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const states = { OK: "Oklahoma", TX: "Texas", KS: "Kansas", AR: "Arkansas", MO: "Missouri", CO: "Colorado", NM: "New Mexico" };
const stages = { not_contacted: "Not contacted", contacted: "Contacted", interested: "Interested", negotiating: "Negotiating", declined: "Declined" };
async function request(path, options = {}) {
  const response = await fetch(`${API}/api/boxing/discovery${path}`, { ...options, headers: { Authorization: `Bearer ${localStorage.getItem("token")}`, "Content-Type": "application/json" }, signal: AbortSignal.timeout(70000) });
  const data = await response.json();
  if (!response.ok) throw Error(typeof data.detail === "string" ? data.detail : "Could not complete the request.");
  return data;
}
function LeadCard({ lead, onSave, onUpdate, saved, busy }) {
  const [stage, setStage] = useState(lead.outreach_status || "not_contacted");
  const [availability, setAvailability] = useState(lead.availability || "unknown");
  const [notes, setNotes] = useState(lead.notes || "");
  return <Card sx={{ p: 2.5, minWidth: 0 }}>
    <Stack direction="row" justifyContent="space-between" spacing={2}><Box><Typography variant="h6">{lead.name}</Typography><Typography variant="body2" color="text.secondary"><MapPin size={13} /> {[lead.city, states[lead.state]].filter(Boolean).join(", ")}</Typography></Box><Chip size="small" label={lead.kind} sx={{ textTransform: "capitalize" }} /></Stack>
    <Stack direction="row" useFlexGap flexWrap="wrap" gap={1} sx={{ my: 2 }}><Chip size="small" variant="outlined" label={lead.id && lead.availability !== "unknown" ? `Staff confirmed: ${lead.availability}` : "Availability unknown"} />{lead.record && <Chip size="small" label={`Reported record: ${lead.record}`} />}{lead.weight && <Chip size="small" label={lead.weight} />}</Stack>
    {lead.last_bout_date && <Typography variant="body2" sx={{ mb: 1 }}>Last bout reported by source: {lead.last_bout_date}</Typography>}
    {lead.gym_or_manager && <Typography variant="body2" sx={{ mb: 1 }}>Gym / manager: {lead.gym_or_manager}</Typography>}
    <Typography variant="body2" color="text.secondary">{lead.last_activity ? `Reported activity: ${lead.last_activity}` : "Recent activity not established from this source."}</Typography>
    <Box sx={{ p: 1.5, my: 2, bgcolor: "#f6f8fa", borderRadius: 2 }}><Typography variant="caption" fontWeight={800}>SOURCE EVIDENCE · VERIFY BEFORE USE</Typography><Typography variant="body2" sx={{ mt: .5, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{lead.evidence || "Open the source to review this lead."}</Typography><Button component="a" href={lead.source_url} target="_blank" rel="noopener noreferrer" size="small" endIcon={<ExternalLink size={13} />}>Review original source</Button></Box>
    <Stack direction="row" useFlexGap flexWrap="wrap" gap={1}>
      {lead.business_phone && <Button component="a" href={`tel:${lead.business_phone.replace(/[^+0-9]/g, "")}`} startIcon={<Phone size={14} />}>{lead.business_phone}</Button>}
      {lead.business_email && <Button component="a" href={`mailto:${encodeURIComponent(lead.business_email)}`} startIcon={<Mail size={14} />} sx={{ overflowWrap: "anywhere" }}>{lead.business_email}</Button>}
    </Stack>
    {!lead.business_phone && !lead.business_email && <Typography variant="body2" color="text.secondary">No supported business contact found. Check the source's contact page or associated gym.</Typography>}
    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>Researched {new Date(lead.researched_at).toLocaleDateString()}. Records, contacts and activity are unverified research leads.</Typography>
    {lead.id ? <Box sx={{ mt: 2, pt: 2, borderTop: "1px solid", borderColor: "divider" }}>
      <Stack direction={{ xs: "column", sm: "row" }} gap={1.5}>
        <TextField select label="Outreach stage" value={stage} onChange={e => setStage(e.target.value)} fullWidth>{Object.entries(stages).map(([v,l]) => <MenuItem key={v} value={v}>{l}</MenuItem>)}</TextField>
        <TextField select label="Availability" value={availability} onChange={e => setAvailability(e.target.value)} fullWidth>{["unknown", "available", "unavailable"].map(v => <MenuItem key={v} value={v}>{v === "unknown" ? "Not confirmed" : `Confirmed ${v}`}</MenuItem>)}</TextField>
      </Stack>
      <TextField label="Contact attempts, availability date, bout and follow-up notes" multiline minRows={2} fullWidth value={notes} onChange={e => setNotes(e.target.value)} slotProps={{ htmlInput: { maxLength: 4000 } }} sx={{ mt: 2 }} />
      {lead.availability_checked_at && <Typography variant="caption" display="block">Availability checked: {new Date(lead.availability_checked_at + (lead.availability_checked_at.endsWith("Z") ? "" : "Z")).toLocaleString()}</Typography>}
      <Button variant="outlined" disabled={busy} sx={{ mt: 1.5 }} onClick={() => onUpdate(lead.id, { outreach_status: stage, availability, notes })}>Save follow-up</Button>
    </Box> : <Button variant="outlined" startIcon={<BookmarkPlus size={16} />} sx={{ mt: 2 }} disabled={saved || busy} onClick={() => onSave(lead)}>{saved ? "Saved to leads" : "Save research lead"}</Button>}
  </Card>;
}
export default function RegionalFinder() {
  const [kind, setKind] = useState("fighter"), [region, setRegion] = useState(Object.keys(states));
  const [activeSince, setActiveSince] = useState(""), [query, setQuery] = useState(""), [weightMin, setWeightMin] = useState(""), [weightMax, setWeightMax] = useState("");
  const [results, setResults] = useState([]), [leads, setLeads] = useState([]), [view, setView] = useState("search");
  const [searching, setSearching] = useState(false), [busy, setBusy] = useState(false), [searched, setSearched] = useState(false), [error, setError] = useState("");
  useEffect(() => { let active = true; request("/leads").then(x => { if (active) setLeads(x); }).catch(e => { if (active) setError(e.message); }); return () => { active = false; }; }, []);
  async function search(e) {
    e.preventDefault(); setSearching(true); setError(""); setSearched(false); setResults([]);
    try { const data = await request("/search", { method: "POST", body: JSON.stringify({ query, kind, states: region, weight_min: kind === "fighter" && weightMin ? Number(weightMin) : null, weight_max: kind === "fighter" && weightMax ? Number(weightMax) : null, active_since: kind === "fighter" ? activeSince : "" }) }); setResults(data.leads); setSearched(true); }
    catch (e) { setError(e.name === "TimeoutError" ? "Search timed out. Try a specific city or name." : e.message); }
    finally { setSearching(false); }
  }
  async function save(lead) { setBusy(true); setError(""); try { const row = await request("/leads", { method: "POST", body: JSON.stringify(lead) }); setLeads(old => [row, ...old.filter(x => x.id !== row.id)]); } catch(e) {setError(e.message);} finally {setBusy(false);} }
  async function update(id, body) { setBusy(true); setError(""); try { const row = await request(`/leads/${id}`, { method: "PATCH", body: JSON.stringify(body) }); setLeads(old => old.map(x => x.id === id ? row : x)); } catch(e) {setError(e.message);} finally {setBusy(false);} }
  const researchQuery = `${query} professional boxing ${kind} ${region.map(s => states[s]).join(" ")}`;
  return <Stack spacing={2.5}>
    <Box><Typography className="promotion-eyebrow" color="text.secondary">OKLAHOMA + SURROUNDING STATES</Typography><Typography component="h1" variant="h4" sx={{ mt: 1 }}>Find your next connection.</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>Locate pro boxers, gyms and managers. Keep the source, save the lead, track the conversation.</Typography></Box>
    <Alert severity="info">Recent activity does not confirm availability. Verify records, licensing, suspensions and contact details before booking. Searches never send outreach messages.</Alert>
    {error && <Alert severity="error" onClose={() => setError("")}>{error}</Alert>}
    <Stack direction="row" gap={1}><Button variant={view === "search" ? "contained" : "outlined"} onClick={() => setView("search")}>Search public web</Button><Button variant={view === "saved" ? "contained" : "outlined"} onClick={() => setView("saved")}>Saved leads ({leads.length})</Button></Stack>
    {view === "search" && <Card component="form" onSubmit={search} sx={{ p: 2.5 }}>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "180px minmax(0,1fr) minmax(220px,1fr)" }, gap: 2 }}>
        <TextField select label="Find" value={kind} onChange={e => setKind(e.target.value)}>{[["fighter","Pro boxers"],["gym","Boxing gyms"],["manager","Managers"]].map(([v,l]) => <MenuItem value={v} key={v}>{l}</MenuItem>)}</TextField>
        <TextField label="Name, city, gym or manager" placeholder="e.g. Tulsa, Dallas, heavyweight" value={query} onChange={e => setQuery(e.target.value)} slotProps={{ htmlInput: { maxLength: 300 } }} />
        <FormControl><InputLabel id="region-label">States</InputLabel><Select labelId="region-label" multiple label="States" value={region} onChange={e => setRegion(e.target.value)} renderValue={x => x.join(", ")}>{Object.entries(states).map(([v,l]) => <MenuItem key={v} value={v}>{region.includes(v) ? "✓ " : ""}{l}</MenuItem>)}</Select></FormControl>
      </Box>
      <Stack direction={{ xs: "column", sm: "row" }} gap={2} sx={{ mt: 2 }} alignItems="center">{kind === "fighter" && <><TextField type="number" label="Minimum weight (lb)" value={weightMin} onChange={e => setWeightMin(e.target.value)} slotProps={{ htmlInput: { min: 50, max: 500 } }} /><TextField type="number" label="Maximum weight (lb)" value={weightMax} onChange={e => setWeightMax(e.target.value)} slotProps={{ htmlInput: { min: 50, max: 500 } }} /></>}{kind === "fighter" && <TextField type="date" label="Require a bout on / after" value={activeSince} onChange={e => setActiveSince(e.target.value)} slotProps={{ inputLabel: { shrink: true } }} />}<Button type="submit" variant="contained" disabled={searching || !region.length} startIcon={searching ? <CircularProgress size={16} color="inherit" /> : <Search size={17} />}>{searching ? "Researching public sources…" : "Find regional leads"}</Button></Stack>
      <Stack direction="row" gap={1} useFlexGap flexWrap="wrap" sx={{ mt: 2 }}><Button component="a" href={`https://www.google.com/search?q=${encodeURIComponent(researchQuery)}`} target="_blank" rel="noopener noreferrer" endIcon={<ExternalLink size={13} />}>Search sources yourself</Button><Button component="a" href={`https://www.google.com/maps/search/${encodeURIComponent(`${query} boxing gym ${region.map(s => states[s]).join(" ")}`)}`} target="_blank" rel="noopener noreferrer" endIcon={<ExternalLink size={13} />}>Locate gyms on Maps</Button><Button component="a" href="https://fightfax.com" target="_blank" rel="noopener noreferrer">Fight Fax</Button><Button component="a" href="https://boxrec.com" target="_blank" rel="noopener noreferrer">BoxRec</Button></Stack>
      <Typography variant="caption" color="text.secondary">Fight Fax / BoxRec open their own sites; account access may be required. TNGOS does not have a licensed records feed.</Typography>
    </Card>}
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0,1fr)", lg: "repeat(2,minmax(0,1fr))" }, gap: 2 }}>
      {(view === "saved" ? leads : results).map(lead => <LeadCard key={lead.id || `${lead.name}-${lead.source_url}`} lead={lead} onSave={save} onUpdate={update} busy={busy} saved={leads.some(x => x.source_url === lead.source_url && x.name.toLowerCase() === lead.name.toLowerCase())} />)}
    </Box>
    {view === "search" && searched && !results.length && <Alert severity="info">No sufficiently sourced leads matched this search. Try one state and a specific city, or use the direct research links.</Alert>}
    {view === "saved" && !leads.length && <Card sx={{ p: 4, textAlign: "center" }}><Typography variant="h6">Build your regional contact book.</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>Search public sources, review a candidate, then save the lead here to track outreach and confirmed availability.</Typography></Card>}
  </Stack>;
}
