import React, { useEffect, useMemo, useState } from "react";
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Dialog,
  DialogActions, DialogContent, DialogTitle, Divider, FormControl,
  Grid, InputLabel, MenuItem, Select, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TextField, Typography
} from "@mui/material";
import AddRoundedIcon from "@mui/icons-material/AddRounded";
import EventRoundedIcon from "@mui/icons-material/EventRounded";
import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const authHeaders = (extra = {}) => ({
  Authorization: `Bearer ${localStorage.getItem("token")}`,
  ...extra,
});

const emptyFighter = {
  legal_name: "",
  dob: "",
  phone: "",
  email: "",
  city: "",
  state: "OK",
  country: "USA",
  stance: "",
  gym: "",
  coach: "",
  height_in: "",
  reach_in: "",
  walk_weight: "",
  fight_weight: "",
  pro_record: "",
  amateur_record: "",
  boxrec_id: "",
  boxrec_url: "",
  manager_name: "",
  manager_phone: "",
  manager_email: "",
  ok_license_status: "unknown",
  federal_id_status: "unknown",
  suspension_status: "needs_review",
  bloodwork_status: "missing",
  bloodwork_expires: "",
  available: true,
  available_weight_min: "",
  available_weight_max: "",
  last_fight_date: "",
};

const emptyEvent = {
  name: "",
  slug: "",
  venue: "",
  venue_address: "",
  event_date: "",
};

function numberOrNull(value) {
  if (value === "" || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function slugify(value) {
  return (value || "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export default function Matchmaker() {
  const [fighters, setFighters] = useState([]);
  const [events, setEvents] = useState([]);
  const [fighterId, setFighterId] = useState("");
  const [eventId, setEventId] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [boxrecSearching, setBoxrecSearching] = useState(false);
  const [existingFighterId, setExistingFighterId] = useState("");
  const [msg, setMsg] = useState("");
  const [msgType, setMsgType] = useState("info");

  const [fighterOpen, setFighterOpen] = useState(false);
  const [eventOpen, setEventOpen] = useState(false);
  const [fighterForm, setFighterForm] = useState(emptyFighter);
  const [eventForm, setEventForm] = useState(emptyEvent);

  async function readJson(response) {
    try {
      return await response.json();
    } catch {
      return {};
    }
  }

  async function load() {
    setLoading(true);
    setMsg("");
    try {
      const [fr, er] = await Promise.all([
        fetch(`${API}/api/boxing/fighters`, { headers: authHeaders() }),
        fetch(`${API}/api/boxing/events`, { headers: authHeaders() }),
      ]);

      const fd = await readJson(fr);
      const ed = await readJson(er);

      if (!fr.ok) throw new Error(fd.detail || "Could not load fighters");
      if (!er.ok) throw new Error(ed.detail || "Could not load events");

      setFighters(Array.isArray(fd) ? fd : []);
      setEvents(Array.isArray(ed) ? ed : []);
    } catch (e) {
      setMsgType("error");
      setMsg(e.message || "Could not load Matchmaker data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function lookupBoxRec() {
    const boxrecId = (fighterForm.boxrec_id || "").trim();

    if (!boxrecId) {
      setMsgType("warning");
      setMsg("Enter a BoxRec ID first.");
      return;
    }

    setBoxrecSearching(true);
    setExistingFighterId("");
    setMsg("");

    try {
      const r = await fetch(
        `${API}/api/boxing/fighters/by-boxrec/${encodeURIComponent(boxrecId)}`,
        { headers: authHeaders() }
      );

      const d = await readJson(r);

      if (r.status === 404) {
        setMsgType("info");
        setMsg(
          `BoxRec ID ${boxrecId} is not in TNG yet. Enter or verify the fighter information below, then click Add Fighter.`
        );
        return;
      }

      if (!r.ok) {
        throw new Error(d.detail || "Could not search BoxRec ID");
      }

      setFighterForm({
        ...emptyFighter,
        ...d,
        boxrec_id: boxrecId,
        available: d.available ?? true,
      });

      setExistingFighterId(d.id || "");

      setMsgType("success");
      setMsg(
        `${d.legal_name || "Fighter"} already exists in TNG. Their information has been loaded.`
      );
    } catch (e) {
      setMsgType("error");
      setMsg(e.message || "Could not search BoxRec ID");
    } finally {
      setBoxrecSearching(false);
    }
  }

  async function createFighter() {
    if (existingFighterId) {
      setFighterId(existingFighterId);
      setFighterOpen(false);
      setMsgType("success");
      setMsg("Existing fighter selected for matchmaking.");
      return;
    }

    if (!fighterForm.legal_name.trim()) {
      setMsgType("warning");
      setMsg("Fighter name is required.");
      return;
    }

    setWorking(true);
    try {
      const payload = {
        ...fighterForm,
        legal_name: fighterForm.legal_name.trim(),
        height_in: numberOrNull(fighterForm.height_in),
        reach_in: numberOrNull(fighterForm.reach_in),
        walk_weight: numberOrNull(fighterForm.walk_weight),
        fight_weight: numberOrNull(fighterForm.fight_weight),
        available_weight_min: numberOrNull(fighterForm.available_weight_min),
        available_weight_max: numberOrNull(fighterForm.available_weight_max),
      };

      const r = await fetch(`${API}/api/boxing/fighters`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      });
      const d = await readJson(r);

      if (!r.ok) throw new Error(d.detail || "Could not add fighter");

      setFighterForm(emptyFighter);
      setExistingFighterId("");
      setFighterOpen(false);
      setMsgType("success");
      setMsg(`${d.legal_name || payload.legal_name} added to the fighter pool.`);
      await load();
      if (d.id) setFighterId(d.id);
    } catch (e) {
      setMsgType("error");
      setMsg(e.message || "Could not add fighter");
    } finally {
      setWorking(false);
    }
  }

  async function createEvent() {
    if (!eventForm.name.trim()) {
      setMsgType("warning");
      setMsg("Event name is required.");
      return;
    }

    setWorking(true);
    try {
      const payload = {
        ...eventForm,
        name: eventForm.name.trim(),
        slug: (eventForm.slug || slugify(eventForm.name)).trim(),
      };

      const r = await fetch(`${API}/api/boxing/events`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      });
      const d = await readJson(r);

      if (!r.ok) throw new Error(d.detail || "Could not add event");

      setEventForm(emptyEvent);
      setEventOpen(false);
      setMsgType("success");
      setMsg(`${payload.name} added.`);
      await load();
      if (d.id) setEventId(d.id);
    } catch (e) {
      setMsgType("error");
      setMsg(e.message || "Could not add event");
    } finally {
      setWorking(false);
    }
  }

  async function findMatches() {
    if (!fighterId) {
      setMsgType("warning");
      setMsg("Choose a fighter first.");
      return;
    }

    setWorking(true);
    setMsg("");
    try {
      const q = eventId ? `?event_id=${eventId}` : "";
      const r = await fetch(`${API}/api/boxing/match/${fighterId}${q}`, {
        headers: authHeaders(),
      });
      const d = await readJson(r);

      if (!r.ok) throw new Error(d.detail || "Matchmaking failed");

      setResult(d);
      setMsgType("success");
      setMsg(`Found ${d.matches?.length || 0} ranked opponent options.`);
    } catch (e) {
      setMsgType("error");
      setMsg(e.message || "Matchmaking failed");
    } finally {
      setWorking(false);
    }
  }

  async function buildBout(match) {
    if (!eventId) {
      setMsgType("warning");
      setMsg("Choose an event before building a bout.");
      return;
    }

    setWorking(true);
    try {
      const payload = {
        event_id: Number(eventId),
        red_fighter_id: Number(fighterId),
        blue_fighter_id: match.fighter.id,
        weight_agreed: result?.fighter?.fight_weight || match.fighter.fight_weight || null,
        rounds: 4,
        bout_type: "pro",
        red_purse: 0,
        blue_purse: 0,
        match_score: match.score,
        notes: `TNG Matchmaker ${match.score}% recommendation`,
      };

      const r = await fetch(`${API}/api/boxing/bouts`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      });
      const d = await readJson(r);

      if (!r.ok) throw new Error(d.detail || "Could not build bout");

      setMsgType("success");
      setMsg(`Bout #${d.id} created as a draft.`);
      await findMatches();
    } catch (e) {
      setMsgType("error");
      setMsg(e.message || "Could not build bout");
    } finally {
      setWorking(false);
    }
  }

  const eligible = useMemo(
    () => fighters.filter((f) => f.eligible).length,
    [fighters]
  );

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <Stack spacing={2}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={2}
          justifyContent="space-between"
          alignItems={{ xs: "stretch", md: "center" }}
        >
          <Box>
            <Typography variant="h4" fontWeight={950}>
              TNG Matchmaker
            </Typography>
            <Typography color="text.secondary">
              Build the fighter pool, create events, rank opponents, and build bout drafts.
            </Typography>
          </Box>

          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <Button
              variant="outlined"
              startIcon={<EventRoundedIcon />}
              onClick={() => setEventOpen(true)}
            >
              Add Event
            </Button>
            <Button
              variant="contained"
              startIcon={<AddRoundedIcon />}
              onClick={() => setFighterOpen(true)}
              sx={{ bgcolor: "#e31b23" }}
            >
              Add Fighter
            </Button>
          </Stack>
        </Stack>

        {msg && <Alert severity={msgType}>{msg}</Alert>}

        <Grid container spacing={2}>
          <Grid item xs={12} sm={4}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">Fighters</Typography>
                <Typography variant="h4" fontWeight={950}>{fighters.length}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">Eligible</Typography>
                <Typography variant="h4" fontWeight={950}>{eligible}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">Events</Typography>
                <Typography variant="h4" fontWeight={950}>{events.length}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Card>
          <CardContent>
            <Typography variant="h6" fontWeight={900} sx={{ mb: 2 }}>
              Find a Match
            </Typography>

            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <FormControl fullWidth>
                <InputLabel>Fighter to Match</InputLabel>
                <Select
                  value={fighterId}
                  label="Fighter to Match"
                  onChange={(e) => {
                    setFighterId(e.target.value);
                    setResult(null);
                  }}
                >
                  {fighters.map((f) => (
                    <MenuItem key={f.id} value={f.id}>
                      {f.legal_name} — {f.fight_weight || "?"} lb — {f.pro_record || "record N/A"}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel>Event</InputLabel>
                <Select
                  value={eventId}
                  label="Event"
                  onChange={(e) => setEventId(e.target.value)}
                >
                  <MenuItem value="">Any / not assigned</MenuItem>
                  {events.map((e) => (
                    <MenuItem key={e.id} value={e.id}>
                      {e.event_date || "No date"} — {e.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button
                variant="contained"
                startIcon={<SportsMmaRoundedIcon />}
                disabled={!fighterId || working}
                onClick={findMatches}
                sx={{ minWidth: 190, bgcolor: "#e31b23" }}
              >
                Find Opponents
              </Button>
            </Stack>
          </CardContent>
        </Card>

        {!fighters.length && (
          <Card>
            <CardContent sx={{ textAlign: "center", py: 5 }}>
              <SportsMmaRoundedIcon sx={{ fontSize: 54, mb: 1 }} />
              <Typography variant="h5" fontWeight={900}>No fighters yet</Typography>
              <Typography color="text.secondary" sx={{ mb: 2 }}>
                Add your first fighter to start using the Matchmaker.
              </Typography>
              <Button
                variant="contained"
                startIcon={<AddRoundedIcon />}
                onClick={() => setFighterOpen(true)}
                sx={{ bgcolor: "#e31b23" }}
              >
                Add Fighter
              </Button>
            </CardContent>
          </Card>
        )}

        {!!fighters.length && !result && (
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight={900}>Fighter Pool</Typography>
              <Typography color="text.secondary">
                Click a fighter to select them for matchmaking.
              </Typography>

              <TableContainer sx={{ mt: 2 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>Weight</TableCell>
                      <TableCell>Record</TableCell>
                      <TableCell>Gym</TableCell>
                      <TableCell>Eligibility</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {fighters.map((f) => (
                      <TableRow
                        hover
                        key={f.id}
                        selected={Number(fighterId) === Number(f.id)}
                        onClick={() => {
                          setFighterId(f.id);
                          setResult(null);
                        }}
                        sx={{ cursor: "pointer" }}
                      >
                        <TableCell><b>{f.legal_name}</b></TableCell>
                        <TableCell>{f.fight_weight || "—"}</TableCell>
                        <TableCell>{f.pro_record || "—"}</TableCell>
                        <TableCell>{f.gym || "—"}</TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={f.eligible ? "Eligible" : "Needs review"}
                            color={f.eligible ? "success" : "default"}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        )}

        {result && (
          <>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="h6" fontWeight={900}>
                  Ranked Opponents for {result.fighter?.legal_name}
                </Typography>
                <Typography color="text.secondary">
                  Higher scores indicate closer competitive matches.
                </Typography>
              </Box>
              <Button onClick={() => setResult(null)}>Back to Fighter Pool</Button>
            </Stack>

            <TableContainer component={Card}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Rank</TableCell>
                    <TableCell>Match</TableCell>
                    <TableCell>Opponent</TableCell>
                    <TableCell>Weight</TableCell>
                    <TableCell>Record</TableCell>
                    <TableCell>Why</TableCell>
                    <TableCell>Action</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(result.matches || []).map((m, i) => (
                    <TableRow key={m.fighter.id}>
                      <TableCell>#{i + 1}</TableCell>
                      <TableCell>
                        <Typography variant="h5" fontWeight={950}>{m.score}%</Typography>
                        <Typography variant="caption">{m.tier}</Typography>
                      </TableCell>
                      <TableCell>
                        <b>{m.fighter.legal_name}</b>
                        <Typography display="block" variant="caption">
                          {[m.fighter.gym, m.fighter.city, m.fighter.state]
                            .filter(Boolean)
                            .join(" • ")}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {m.fighter.fight_weight || "?"} lb
                        <br />
                        <Typography variant="caption">Δ {m.weight_diff} lb</Typography>
                      </TableCell>
                      <TableCell>{m.fighter.pro_record || "N/A"}</TableCell>
                      <TableCell>
                        <Stack direction="row" useFlexGap flexWrap="wrap" spacing={0.5}>
                          {(m.reasons || []).slice(0, 4).map((x) => (
                            <Chip key={x} size="small" label={x} />
                          ))}
                          {(m.warnings || []).map((x) => (
                            <Chip key={x} size="small" variant="outlined" label={`Review: ${x}`} />
                          ))}
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          variant="contained"
                          disabled={!eventId || working}
                          onClick={() => buildBout(m)}
                          sx={{ bgcolor: "#e31b23" }}
                        >
                          Build Bout
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}

                  {!result.matches?.length && (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        No eligible opponent matches found. Add more fighters or review eligibility.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
      </Stack>

      <Dialog open={fighterOpen} onClose={() => !working && setFighterOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>Add Fighter</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Typography variant="subtitle2" fontWeight={900}>
              BoxRec Fighter Lookup
            </Typography>

            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} md={8}>
                <TextField
                  fullWidth
                  label="BoxRec ID"
                  placeholder="Example: 123456"
                  helperText="Enter the fighter's BoxRec ID. TNG will first check whether this fighter is already in your database."
                  value={fighterForm.boxrec_id}
                  onChange={(e) => {
                    setExistingFighterId("");
                    setFighterForm({
                      ...fighterForm,
                      boxrec_id: e.target.value.replace(/[^0-9]/g, ""),
                    });
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      lookupBoxRec();
                    }
                  }}
                />
              </Grid>

              <Grid item xs={12} md={4}>
                <Button
                  fullWidth
                  variant="contained"
                  disabled={boxrecSearching || !fighterForm.boxrec_id}
                  onClick={lookupBoxRec}
                  sx={{
                    bgcolor: "#111",
                    minHeight: 56,
                    "&:hover": { bgcolor: "#222" },
                  }}
                >
                  {boxrecSearching ? "Searching..." : "Find Fighter"}
                </Button>
              </Grid>
            </Grid>

            {existingFighterId && (
              <Alert severity="success">
                Fighter found in TNG. The information below was populated from the saved fighter record.
              </Alert>
            )}

            <Divider />

            <Typography variant="subtitle2" fontWeight={900}>Basic Information</Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  required
                  label="Legal Name"
                  value={fighterForm.legal_name}
                  onChange={(e) => setFighterForm({ ...fighterForm, legal_name: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField
                  fullWidth
                  type="date"
                  label="Date of Birth"
                  InputLabelProps={{ shrink: true }}
                  value={fighterForm.dob}
                  onChange={(e) => setFighterForm({ ...fighterForm, dob: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <FormControl fullWidth>
                  <InputLabel>Stance</InputLabel>
                  <Select
                    value={fighterForm.stance}
                    label="Stance"
                    onChange={(e) => setFighterForm({ ...fighterForm, stance: e.target.value })}
                  >
                    <MenuItem value="">Unknown</MenuItem>
                    <MenuItem value="orthodox">Orthodox</MenuItem>
                    <MenuItem value="southpaw">Southpaw</MenuItem>
                    <MenuItem value="switch">Switch</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Phone"
                  value={fighterForm.phone}
                  onChange={(e) => setFighterForm({ ...fighterForm, phone: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Email"
                  value={fighterForm.email}
                  onChange={(e) => setFighterForm({ ...fighterForm, email: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Gym"
                  value={fighterForm.gym}
                  onChange={(e) => setFighterForm({ ...fighterForm, gym: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Coach"
                  value={fighterForm.coach}
                  onChange={(e) => setFighterForm({ ...fighterForm, coach: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="City"
                  value={fighterForm.city}
                  onChange={(e) => setFighterForm({ ...fighterForm, city: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={2}>
                <TextField
                  fullWidth
                  label="State"
                  value={fighterForm.state}
                  onChange={(e) => setFighterForm({ ...fighterForm, state: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={2}>
                <TextField
                  fullWidth
                  label="Country"
                  value={fighterForm.country}
                  onChange={(e) => setFighterForm({ ...fighterForm, country: e.target.value })}
                />
              </Grid>
            </Grid>

            <Divider />
            <Typography variant="subtitle2" fontWeight={900}>Boxing Profile</Typography>

            <Grid container spacing={2}>
              <Grid item xs={6} md={3}>
                <TextField
                  fullWidth
                  type="number"
                  label="Fight Weight"
                  value={fighterForm.fight_weight}
                  onChange={(e) => setFighterForm({ ...fighterForm, fight_weight: e.target.value })}
                />
              </Grid>
              <Grid item xs={6} md={3}>
                <TextField
                  fullWidth
                  type="number"
                  label="Walk Weight"
                  value={fighterForm.walk_weight}
                  onChange={(e) => setFighterForm({ ...fighterForm, walk_weight: e.target.value })}
                />
              </Grid>
              <Grid item xs={6} md={3}>
                <TextField
                  fullWidth
                  type="number"
                  label="Height (in)"
                  value={fighterForm.height_in}
                  onChange={(e) => setFighterForm({ ...fighterForm, height_in: e.target.value })}
                />
              </Grid>
              <Grid item xs={6} md={3}>
                <TextField
                  fullWidth
                  type="number"
                  label="Reach (in)"
                  value={fighterForm.reach_in}
                  onChange={(e) => setFighterForm({ ...fighterForm, reach_in: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Pro Record (W-L-D)"
                  placeholder="5-1-0"
                  value={fighterForm.pro_record}
                  onChange={(e) => setFighterForm({ ...fighterForm, pro_record: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Amateur Record"
                  value={fighterForm.amateur_record}
                  onChange={(e) => setFighterForm({ ...fighterForm, amateur_record: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="BoxRec URL"
                  value={fighterForm.boxrec_url}
                  onChange={(e) => setFighterForm({ ...fighterForm, boxrec_url: e.target.value })}
                />
              </Grid>
              <Grid item xs={6} md={3}>
                <TextField
                  fullWidth
                  type="number"
                  label="Available Min Weight"
                  value={fighterForm.available_weight_min}
                  onChange={(e) => setFighterForm({ ...fighterForm, available_weight_min: e.target.value })}
                />
              </Grid>
              <Grid item xs={6} md={3}>
                <TextField
                  fullWidth
                  type="number"
                  label="Available Max Weight"
                  value={fighterForm.available_weight_max}
                  onChange={(e) => setFighterForm({ ...fighterForm, available_weight_max: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <TextField
                  fullWidth
                  type="date"
                  label="Last Fight"
                  InputLabelProps={{ shrink: true }}
                  value={fighterForm.last_fight_date}
                  onChange={(e) => setFighterForm({ ...fighterForm, last_fight_date: e.target.value })}
                />
              </Grid>
            </Grid>

            <Divider />
            <Typography variant="subtitle2" fontWeight={900}>Eligibility / Commission Status</Typography>

            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel>Suspension</InputLabel>
                  <Select
                    value={fighterForm.suspension_status}
                    label="Suspension"
                    onChange={(e) => setFighterForm({ ...fighterForm, suspension_status: e.target.value })}
                  >
                    <MenuItem value="verified_clear">Verified Clear</MenuItem>
                    <MenuItem value="needs_review">Needs Review</MenuItem>
                    <MenuItem value="suspended">Suspended</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel>Bloodwork</InputLabel>
                  <Select
                    value={fighterForm.bloodwork_status}
                    label="Bloodwork"
                    onChange={(e) => setFighterForm({ ...fighterForm, bloodwork_status: e.target.value })}
                  >
                    <MenuItem value="verified">Verified</MenuItem>
                    <MenuItem value="missing">Missing</MenuItem>
                    <MenuItem value="expired">Expired</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel>OK License</InputLabel>
                  <Select
                    value={fighterForm.ok_license_status}
                    label="OK License"
                    onChange={(e) => setFighterForm({ ...fighterForm, ok_license_status: e.target.value })}
                  >
                    <MenuItem value="active">Active</MenuItem>
                    <MenuItem value="pending">Pending</MenuItem>
                    <MenuItem value="unknown">Unknown</MenuItem>
                    <MenuItem value="expired">Expired</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel>Federal ID</InputLabel>
                  <Select
                    value={fighterForm.federal_id_status}
                    label="Federal ID"
                    onChange={(e) => setFighterForm({ ...fighterForm, federal_id_status: e.target.value })}
                  >
                    <MenuItem value="active">Active</MenuItem>
                    <MenuItem value="pending">Pending</MenuItem>
                    <MenuItem value="unknown">Unknown</MenuItem>
                    <MenuItem value="expired">Expired</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  type="date"
                  label="Bloodwork Expires"
                  InputLabelProps={{ shrink: true }}
                  value={fighterForm.bloodwork_expires}
                  onChange={(e) => setFighterForm({ ...fighterForm, bloodwork_expires: e.target.value })}
                />
              </Grid>
            </Grid>

            <Divider />
            <Typography variant="subtitle2" fontWeight={900}>Manager</Typography>

            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Manager Name"
                  value={fighterForm.manager_name}
                  onChange={(e) => setFighterForm({ ...fighterForm, manager_name: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Manager Phone"
                  value={fighterForm.manager_phone}
                  onChange={(e) => setFighterForm({ ...fighterForm, manager_phone: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Manager Email"
                  value={fighterForm.manager_email}
                  onChange={(e) => setFighterForm({ ...fighterForm, manager_email: e.target.value })}
                />
              </Grid>
            </Grid>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button disabled={working} onClick={() => setFighterOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={working}
            onClick={createFighter}
            sx={{ bgcolor: "#e31b23" }}
          >
            {working
              ? "Saving..."
              : existingFighterId
                ? "Use Existing Fighter"
                : "Add Fighter"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={eventOpen} onClose={() => !working && setEventOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Add Boxing Event</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField
              fullWidth
              required
              label="Event Name"
              value={eventForm.name}
              onChange={(e) => {
                const name = e.target.value;
                setEventForm({
                  ...eventForm,
                  name,
                  slug: eventForm.slug || slugify(name),
                });
              }}
            />
            <TextField
              fullWidth
              label="Event Slug"
              helperText="Used internally. Example: fall-brawl-6"
              value={eventForm.slug}
              onChange={(e) => setEventForm({ ...eventForm, slug: slugify(e.target.value) })}
            />
            <TextField
              fullWidth
              type="date"
              label="Event Date"
              InputLabelProps={{ shrink: true }}
              value={eventForm.event_date}
              onChange={(e) => setEventForm({ ...eventForm, event_date: e.target.value })}
            />
            <TextField
              fullWidth
              label="Venue"
              value={eventForm.venue}
              onChange={(e) => setEventForm({ ...eventForm, venue: e.target.value })}
            />
            <TextField
              fullWidth
              label="Venue Address"
              value={eventForm.venue_address}
              onChange={(e) => setEventForm({ ...eventForm, venue_address: e.target.value })}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button disabled={working} onClick={() => setEventOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={working}
            onClick={createEvent}
            sx={{ bgcolor: "#e31b23" }}
          >
            {working ? "Saving..." : "Add Event"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
