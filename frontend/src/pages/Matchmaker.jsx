import React, { useEffect, useMemo, useState } from "react";
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress,
  FormControl, InputLabel, MenuItem, Select, Stack,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography
} from "@mui/material";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const headers = (extra = {}) => ({
  Authorization: `Bearer ${localStorage.getItem("token")}`,
  ...extra,
});

export default function Matchmaker() {
  const [fighters, setFighters] = useState([]);
  const [events, setEvents] = useState([]);
  const [fighterId, setFighterId] = useState("");
  const [eventId, setEventId] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  async function load() {
    setLoading(true);
    try {
      const [fr, er] = await Promise.all([
        fetch(`${API}/api/boxing/fighters`, { headers: headers() }),
        fetch(`${API}/api/boxing/events`, { headers: headers() }),
      ]);
      const fd = await fr.json();
      const ed = await er.json();
      if (!fr.ok) throw new Error(fd.detail || "Could not load fighters");
      if (!er.ok) throw new Error(ed.detail || "Could not load events");
      setFighters(fd);
      setEvents(ed);
    } catch (e) {
      setMsg(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function findMatches() {
    const q = eventId ? `?event_id=${eventId}` : "";
    const r = await fetch(`${API}/api/boxing/match/${fighterId}${q}`, { headers: headers() });
    const d = await r.json();
    if (!r.ok) {
      setMsg(d.detail || "Matchmaking failed");
      return;
    }
    setResult(d);
  }

  async function buildBout(match) {
    if (!eventId) {
      setMsg("Choose an event before building a bout.");
      return;
    }

    const payload = {
      event_id: Number(eventId),
      red_fighter_id: Number(fighterId),
      blue_fighter_id: match.fighter.id,
      weight_agreed: result.fighter.fight_weight || match.fighter.fight_weight,
      rounds: 4,
      bout_type: "pro",
      red_purse: 0,
      blue_purse: 0,
      match_score: match.score,
      notes: `TNG Matchmaker ${match.score}% recommendation`,
    };

    const r = await fetch(`${API}/api/boxing/bouts`, {
      method: "POST",
      headers: headers({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    const d = await r.json();
    setMsg(r.ok ? `Bout #${d.id} created as draft.` : (d.detail || "Could not build bout"));
    if (r.ok) await findMatches();
  }

  const eligible = useMemo(() => fighters.filter(f => f.eligible).length, [fighters]);

  if (loading) {
    return <Box sx={{ p: 3 }}><CircularProgress /></Box>;
  }

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <Stack spacing={2}>
        <Box>
          <Typography variant="h4" fontWeight={950}>TNG Matchmaker</Typography>
          <Typography color="text.secondary">
            Rank opponents using weight, experience, record, age, dimensions, eligibility,
            availability, gym, travel, prior bouts, and event conflicts.
          </Typography>
        </Box>

        {msg && <Alert severity={msg.includes("created") ? "success" : "info"}>{msg}</Alert>}

        <Card>
          <CardContent>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <FormControl fullWidth>
                <InputLabel>Fighter to Match</InputLabel>
                <Select
                  value={fighterId}
                  label="Fighter to Match"
                  onChange={e => { setFighterId(e.target.value); setResult(null); }}
                >
                  {fighters.map(f => (
                    <MenuItem key={f.id} value={f.id}>
                      {f.legal_name} — {f.fight_weight || "?"} lb — {f.pro_record || "record N/A"}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel>Event</InputLabel>
                <Select value={eventId} label="Event" onChange={e => setEventId(e.target.value)}>
                  <MenuItem value="">Any / not assigned</MenuItem>
                  {events.map(e => (
                    <MenuItem key={e.id} value={e.id}>
                      {e.event_date} — {e.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button
                variant="contained"
                disabled={!fighterId}
                onClick={findMatches}
                sx={{ minWidth: 180, bgcolor: "#e31b23" }}
              >
                Find Opponents
              </Button>
            </Stack>
          </CardContent>
        </Card>

        {!result && (
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight={900}>Fighter Pool</Typography>
              <Typography color="text.secondary">
                {fighters.length} fighters • {eligible} eligible
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
                    {fighters.map(f => (
                      <TableRow
                        hover
                        key={f.id}
                        onClick={() => setFighterId(f.id)}
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
                {result.matches.map((m, i) => (
                  <TableRow key={m.fighter.id}>
                    <TableCell>#{i + 1}</TableCell>
                    <TableCell>
                      <Typography variant="h5" fontWeight={950}>{m.score}%</Typography>
                      <Typography variant="caption">{m.tier}</Typography>
                    </TableCell>
                    <TableCell>
                      <b>{m.fighter.legal_name}</b>
                      <Typography display="block" variant="caption">
                        {[m.fighter.gym, m.fighter.city, m.fighter.state].filter(Boolean).join(" • ")}
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
                        {m.reasons.slice(0, 4).map(x => <Chip key={x} size="small" label={x} />)}
                        {m.warnings.map(x => <Chip key={x} size="small" variant="outlined" label={`Review: ${x}`} />)}
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Button
                        size="small"
                        variant="contained"
                        disabled={!eventId}
                        onClick={() => buildBout(m)}
                        sx={{ bgcolor: "#e31b23" }}
                      >
                        Build Bout
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Stack>
    </Box>
  );
}
