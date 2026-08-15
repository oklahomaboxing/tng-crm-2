import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert, Autocomplete, Box, Button, Card, CardContent, Chip, CircularProgress, Dialog,
  DialogActions, DialogContent, DialogTitle, Divider, FormControl,
  Grid, InputLabel, MenuItem, Select, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TextField, Typography
} from "@mui/material";
import AddRoundedIcon from "@mui/icons-material/AddRounded";
import EventRoundedIcon from "@mui/icons-material/EventRounded";
import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";
import EventWorkspace from "./EventWorkspace.jsx";

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
  const [eventWorkspaceId, setEventWorkspaceId] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [boxrecSearching, setBoxrecSearching] = useState(false);
  const [boxrecSearchText, setBoxrecSearchText] = useState("");
  const [existingFighterId, setExistingFighterId] = useState("");
  const [msg, setMsg] = useState("");
  const [msgType, setMsgType] = useState("info");

  const [socialOpen, setSocialOpen] = useState(false);
  const [socialLoading, setSocialLoading] = useState(false);
  const [socialResults, setSocialResults] = useState([]);
  const [socialFighter, setSocialFighter] = useState(null);
  const [socialError, setSocialError] = useState("");


  const [fighterOpen, setFighterOpen] = useState(false);
  const [eventOpen, setEventOpen] = useState(false);

  const boxrecWindowRef = useRef(null);
  const [fighterForm, setFighterForm] = useState(emptyFighter);

  const [editFighterOpen, setEditFighterOpen] = useState(false);
  const [editFighterId, setEditFighterId] = useState("");
  const [editFighterForm, setEditFighterForm] = useState(emptyFighter);
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

  function openBoxRecProfile(searchValue = null) {
    const query = String(
      searchValue ??
      boxrecSearchText ??
      fighterForm.boxrec_id ??
      ""
    ).trim();

    if (!query) {
      setMsgType("warning");
      setMsg("Enter a fighter name or BoxRec ID.");
      return;
    }

    const isBoxRecId = /^\d+$/.test(query);

    const url = isBoxRecId
      ? `https://boxrec.com/en/box-pro/${encodeURIComponent(query)}`
      : `https://boxrec.com/en/search?search%5Bquery%5D=${encodeURIComponent(query)}`;

    try {
      if (
        boxrecWindowRef.current &&
        !boxrecWindowRef.current.closed
      ) {
        boxrecWindowRef.current.location.href = url;
        boxrecWindowRef.current.focus();
        return;
      }

      boxrecWindowRef.current = window.open(
        url,
        "tngBoxRecProfile",
        "popup=yes,width=1100,height=820,resizable=yes,scrollbars=yes"
      );

      if (!boxrecWindowRef.current) {
        window.open(
          url,
          "_blank",
          "noopener,noreferrer"
        );
      }
    } catch {
      window.open(
        url,
        "_blank",
        "noopener,noreferrer"
      );
    }
  }


  function closeBoxRecProfile() {
    try {
      if (
        boxrecWindowRef.current &&
        !boxrecWindowRef.current.closed
      ) {
        boxrecWindowRef.current.close();
      }
    } catch {
      // Ignore cross-window browser restrictions.
    }

    boxrecWindowRef.current = null;
  }


  async function lookupBoxRec() {
    const query = String(
      boxrecSearchText ||
      fighterForm.boxrec_id ||
      ""
    ).trim();

    if (!query) {
      setMsgType("warning");
      setMsg("Enter a fighter name or BoxRec ID first.");
      return;
    }

    const isBoxRecId = /^\d+$/.test(query);

    // Name search: open BoxRec search only.
    if (!isBoxRecId) {
      openBoxRecProfile(query);

      setMsgType("info");
      setMsg(
        `Searching BoxRec for "${query}". Once you find the correct fighter, enter their BoxRec ID to link them to TNG.`
      );

      return;
    }

    // ID search: direct profile + check TNG database.
    setFighterForm({
      ...fighterForm,
      boxrec_id: query,
    });

    openBoxRecProfile(query);

    setBoxrecSearching(true);
    setExistingFighterId("");
    setMsg("");

    try {
      const r = await fetch(
        `${API}/api/boxing/fighters/by-boxrec/${encodeURIComponent(query)}`,
        { headers: authHeaders() }
      );

      const d = await readJson(r);

      if (r.status === 404) {
        setMsgType("info");
        setMsg(
          `BoxRec ID ${query} is not in TNG yet. Verify the fighter on BoxRec, complete the fighter information below, then click Add Fighter.`
        );
        return;
      }

      if (!r.ok) {
        throw new Error(
          d.detail || "Could not search BoxRec ID"
        );
      }

      setFighterForm({
        ...emptyFighter,
        ...d,
        boxrec_id: query,
        available: d.available ?? true,
      });

      setBoxrecSearchText(query);
      setExistingFighterId(d.id || "");

      setMsgType("success");
      setMsg(
        `${d.legal_name || "Fighter"} already exists in TNG. Their saved information has been loaded.`
      );

    } catch (e) {
      setMsgType("error");
      setMsg(
        e.message || "Could not search BoxRec ID"
      );
    } finally {
      setBoxrecSearching(false);
    }
  }


  async function createFighter(findAfterSave = false) {
    if (existingFighterId) {
      setFighterId(existingFighterId);
      setFighterOpen(false);

      if (findAfterSave) {
        await findMatches(existingFighterId);
      } else {
        setMsgType("success");
        setMsg("Existing fighter selected for matchmaking.");
      }

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
      closeBoxRecProfile();
      setMsgType("success");
      setMsg(`${d.legal_name || payload.legal_name} added to the fighter pool.`);

      await load();

      if (d.id) {
        setFighterId(d.id);

        if (findAfterSave) {
          await findMatches(d.id);
        }
      }
    } catch (e) {
      setMsgType("error");
      setMsg(e.message || "Could not add fighter");
    } finally {
      setWorking(false);
    }
  }

  function openEditFighter(fighter) {
    setEditFighterId(fighter.id);

    setEditFighterForm({
      ...emptyFighter,
      ...fighter,

      boxrec_id: fighter.boxrec_id || "",

      fight_weight:
        fighter.fight_weight ?? "",

      walk_weight:
        fighter.walk_weight ?? "",

      height_in:
        fighter.height_in ?? "",

      reach_in:
        fighter.reach_in ?? "",

      available_weight_min:
        fighter.available_weight_min ?? "",

      available_weight_max:
        fighter.available_weight_max ?? "",
    });

    setEditFighterOpen(true);
  }

  async function saveFighterEdits() {
    if (!editFighterId) return;

    if (!editFighterForm.legal_name?.trim()) {
      setMsgType("warning");
      setMsg("Fighter name is required.");
      return;
    }

    setWorking(true);

    try {
      const payload = {
        ...editFighterForm,

        legal_name:
          editFighterForm.legal_name.trim(),

        boxrec_id:
          (editFighterForm.boxrec_id || "").trim(),

        height_in:
          numberOrNull(editFighterForm.height_in),

        reach_in:
          numberOrNull(editFighterForm.reach_in),

        walk_weight:
          numberOrNull(editFighterForm.walk_weight),

        fight_weight:
          numberOrNull(editFighterForm.fight_weight),

        available_weight_min:
          numberOrNull(
            editFighterForm.available_weight_min
          ),

        available_weight_max:
          numberOrNull(
            editFighterForm.available_weight_max
          ),
      };

      const response = await fetch(
        `${API}/api/boxing/fighters/${editFighterId}`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(payload),
        }
      );

      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          data.detail || "Could not update fighter"
        );
      }

      setEditFighterOpen(false);
      setEditFighterId("");
      setEditFighterForm(emptyFighter);

      setMsgType("success");
      setMsg(
        `${data.legal_name || payload.legal_name} updated.`
      );

      await load();

      if (
        fighterId &&
        Number(fighterId) === Number(data.id)
      ) {
        setResult(null);
      }
    } catch (error) {
      setMsgType("error");
      setMsg(
        error.message || "Could not update fighter"
      );
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

  async function findSocials() {
    if (!fighterId) {
      setMsgType("warning");
      setMsg("Select a fighter first.");
      return;
    }

    const fighter = fighters.find(
      (row) => Number(row.id) === Number(fighterId)
    );

    setSocialFighter(fighter || null);
    setSocialResults([]);
    setSocialError("");
    setSocialOpen(true);
    setSocialLoading(true);

    try {
      const response = await fetch(
        `${API}/api/boxing/fighters/${fighterId}/find-socials`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
        }
      );

      const responseText = await response.text();

      let body = {};

      try {
        body = responseText
          ? JSON.parse(responseText)
          : {};
      } catch {
        throw new Error(
          `Social search returned HTTP ${response.status} instead of JSON. ` +
          `Response: ${responseText.slice(0, 180)}`
        );
      }

      if (!response.ok) {
        throw new Error(
          body.detail ||
          `Social search failed with HTTP ${response.status}`
        );
      }

      setSocialFighter(body.fighter || fighter);

      setSocialResults(
        Array.isArray(body.candidates)
          ? body.candidates
          : []
      );

    } catch (error) {
      const message =
        error.message ||
        "Could not search fighter social media";

      setSocialError(message);
      setMsgType("error");
      setMsg(message);
    } finally {
      setSocialLoading(false);
    }
  }


  async function saveSocialCandidate(candidate) {
    if (!socialFighter?.id) return;

    try {
      const response = await fetch(
        `${API}/api/boxing/fighters/${socialFighter.id}/socials`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({
            [candidate.platform]: candidate.url,
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not save social profile"
        );
      }

      setFighters((old) =>
        old.map((row) =>
          Number(row.id) === Number(body.id)
            ? { ...row, ...body }
            : row
        )
      );

      setSocialFighter(body);

      setMsgType("success");
      setMsg(
        `${candidate.platform} saved for ${body.legal_name}.`
      );

    } catch (error) {
      setMsgType("error");
      setMsg(
        error.message || "Could not save social profile"
      );
    }
  }


  async function findMatches(targetFighterId = fighterId) {
    // React onClick can pass a MouseEvent when a function is used directly.
    // Only accept a numeric/string fighter ID here.
    if (
      targetFighterId &&
      typeof targetFighterId === "object"
    ) {
      targetFighterId = fighterId;
    }

    if (!targetFighterId) {
      // Instead of warning that the fighter must already exist,
      // immediately open Add Fighter.
      setFighterOpen(true);
      return;
    }

    setWorking(true);
    setMsg("");
    try {
      const resolvedFighterId = Number(targetFighterId);

      if (!Number.isInteger(resolvedFighterId) || resolvedFighterId <= 0) {
        throw new Error("A valid fighter must be selected before finding opponents.");
      }

      const q = eventId ? `?event_id=${eventId}` : "";
      const r = await fetch(`${API}/api/boxing/match/${resolvedFighterId}${q}`, {
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

  if (eventWorkspaceId) {
    return (
      <EventWorkspace
        eventId={eventWorkspaceId}
        onBack={() => setEventWorkspaceId("")}
      />
    );
  }

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
              <Autocomplete
                fullWidth
                options={fighters}
                value={
                  fighters.find(
                    (f) =>
                      Number(f.id) === Number(fighterId)
                  ) || null
                }
                getOptionLabel={(f) =>
                  `${f.legal_name || ""} — ${
                    f.fight_weight || "?"
                  } lb — ${
                    f.pro_record || "record N/A"
                  }`
                }
                isOptionEqualToValue={(option, value) =>
                  Number(option.id) === Number(value.id)
                }
                onChange={(event, value) => {
                  setFighterId(value ? value.id : "");
                  setResult(null);
                }}
                filterOptions={(options, state) => {
                  const search =
                    state.inputValue
                      .toLowerCase()
                      .trim();

                  if (!search) return options;

                  return options.filter((f) =>
                    [
                      f.legal_name,
                      f.pro_record,
                      f.gym,
                      f.city,
                      f.state,
                      f.boxrec_id,
                    ]
                      .filter(Boolean)
                      .join(" ")
                      .toLowerCase()
                      .includes(search)
                  );
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Search Fighter"
                    placeholder="Type fighter name..."
                  />
                )}
              />

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
                variant="outlined"
                disabled={!eventId}
                onClick={() => setEventWorkspaceId(eventId)}
                sx={{ minWidth: 130 }}
              >
                Open Event
              </Button>

                            <Button
                variant="outlined"
                disabled={!fighterId || working}
                onClick={findSocials}
                sx={{ minWidth: 150 }}
              >
                Find Socials
              </Button>

<Button
                variant="contained"
                startIcon={<SportsMmaRoundedIcon />}
                disabled={!fighterId || working}
                onClick={() => findMatches()}
                sx={{ minWidth: 190, bgcolor: "#e31b23" }}
              >
                Find Opponents
              </Button>
            </Stack>

            {socialOpen && (
              <Card
                variant="outlined"
                sx={{
                  mt: 2,
                  borderColor: "divider",
                }}
              >
                <CardContent>
                  <Stack spacing={2}>

                    <Box>
                      <Typography
                        variant="h6"
                        fontWeight={950}
                      >
                        Fighter Social Media Results
                      </Typography>

                      <Typography
                        variant="body2"
                        color="text.secondary"
                      >
                        {socialFighter?.legal_name ||
                          "Selected fighter"}
                      </Typography>
                    </Box>

                    {socialError && (
                      <Alert severity="error">
                        {socialError}
                      </Alert>
                    )}

                    {socialLoading && (
                      <Stack
                        direction="row"
                        spacing={2}
                        alignItems="center"
                        sx={{ py: 2 }}
                      >
                        <CircularProgress size={26} />

                        <Typography>
                          Searching public social media profiles...
                        </Typography>
                      </Stack>
                    )}

                    {!socialLoading &&
                      !socialError &&
                      socialResults.length === 0 && (
                        <Alert severity="info">
                          No strong public social media matches
                          were found for this fighter.
                        </Alert>
                      )}

                    {!socialLoading &&
                      socialResults.map(
                        (candidate, index) => (
                          <Card
                            key={`${candidate.platform}-${candidate.url}-${index}`}
                            variant="outlined"
                          >
                            <CardContent>
                              <Stack spacing={1.5}>
                                <Stack
                                  direction={{
                                    xs: "column",
                                    sm: "row",
                                  }}
                                  spacing={1}
                                  justifyContent="space-between"
                                  alignItems={{
                                    xs: "flex-start",
                                    sm: "center",
                                  }}
                                >
                                  <Box>
                                    <Typography
                                      fontWeight={950}
                                      sx={{
                                        textTransform:
                                          "capitalize",
                                      }}
                                    >
                                      {candidate.platform}
                                    </Typography>

                                    <Typography>
                                      {candidate.handle ||
                                        candidate.url}
                                    </Typography>
                                  </Box>

                                  <Chip
                                    label={`${
                                      candidate.confidence || 0
                                    }% confidence`}
                                    color={
                                      Number(
                                        candidate.confidence
                                      ) >= 85
                                        ? "success"
                                        : Number(
                                            candidate.confidence
                                          ) >= 65
                                        ? "warning"
                                        : "default"
                                    }
                                  />
                                </Stack>

                                {candidate.reason && (
                                  <Typography
                                    variant="body2"
                                    color="text.secondary"
                                  >
                                    {candidate.reason}
                                  </Typography>
                                )}

                                <Typography
                                  variant="caption"
                                  sx={{
                                    overflowWrap: "anywhere",
                                  }}
                                >
                                  {candidate.url}
                                </Typography>

                                <Stack
                                  direction={{
                                    xs: "column",
                                    sm: "row",
                                  }}
                                  spacing={1}
                                >
                                  <Button
                                    variant="outlined"
                                    onClick={() =>
                                      window.open(
                                        candidate.url,
                                        "_blank",
                                        "noopener,noreferrer"
                                      )
                                    }
                                  >
                                    View Profile
                                  </Button>

                                  <Button
                                    variant="contained"
                                    onClick={() =>
                                      saveSocialCandidate(
                                        candidate
                                      )
                                    }
                                  >
                                    Confirm & Save
                                  </Button>
                                </Stack>
                              </Stack>
                            </CardContent>
                          </Card>
                        )
                      )}

                    {!socialLoading && (
                      <Stack
                        direction="row"
                        spacing={1}
                      >
                        <Button
                          variant="text"
                          onClick={findSocials}
                        >
                          Search Again
                        </Button>

                        <Button
                          variant="text"
                          onClick={() => {
                            setSocialOpen(false);
                            setSocialResults([]);
                            setSocialError("");
                          }}
                        >
                          Close Results
                        </Button>
                      </Stack>
                    )}

                  </Stack>
                </CardContent>
              </Card>
            )}

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

                        <TableCell align="right">
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={(e) => {
                              e.stopPropagation();
                              openEditFighter(f);
                            }}
                          >
                            Edit
                          </Button>
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

      <Dialog
        open={fighterOpen}
        onClose={() => !working && setFighterOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          <Typography variant="h5" fontWeight={950}>
            Add Fighter
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Add only what you need for matchmaking. More details can be completed later.
          </Typography>
        </DialogTitle>

        <DialogContent>
          <Stack spacing={2.5} sx={{ pt: 1 }}>

            {/* BOXREC LOOKUP */}
            <Box>
              <Typography
                variant="subtitle2"
                fontWeight={900}
                sx={{ mb: 1 }}
              >
                BoxRec
              </Typography>

              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={1}
              >
                <TextField
                  fullWidth
                  label="Find Fighter on BoxRec"
                  placeholder="Type fighter name or BoxRec ID"
                  value={boxrecSearchText}
                  onChange={(e) => {
                    const value = e.target.value;

                    setExistingFighterId("");
                    setBoxrecSearchText(value);

                    if (/^\d*$/.test(value)) {
                      setFighterForm({
                        ...fighterForm,
                        boxrec_id: value,
                      });
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      lookupBoxRec();
                    }
                  }}
                />

                <Button
                  variant="outlined"
                  disabled={boxrecSearching || !boxrecSearchText.trim()}
                  onClick={lookupBoxRec}
                  sx={{
                    minWidth: 120,
                    minHeight: 56,
                    fontWeight: 900,
                  }}
                >
                  {boxrecSearching ? "Checking..." : "Find Fighter"}
                </Button>

                <Button
                  variant="text"
                  onClick={closeBoxRecProfile}
                  disabled={!boxrecSearchText.trim()}
                  sx={{
                    minHeight: 56,
                    whiteSpace: "nowrap",
                  }}
                >
                  Close BoxRec
                </Button>
              </Stack>

              {existingFighterId && (
                <Alert severity="success" sx={{ mt: 1 }}>
                  Fighter already exists in TNG. Saved information has been loaded.
                </Alert>
              )}
            </Box>

            <Divider />

            {/* FIGHTER */}
            <Box>
              <Typography
                variant="subtitle2"
                fontWeight={900}
                sx={{ mb: 1.5 }}
              >
                Fighter
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    required
                    autoFocus={!fighterForm.boxrec_id}
                    label="Fighter Name"
                    placeholder="First and last name"
                    value={fighterForm.legal_name}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        legal_name: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Pro Record"
                    placeholder="5-1-0"
                    value={fighterForm.pro_record}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        pro_record: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Fight Weight"
                    placeholder="140"
                    value={fighterForm.fight_weight}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        fight_weight: e.target.value,
                      })
                    }
                    InputProps={{
                      endAdornment: (
                        <Typography color="text.secondary">
                          lb
                        </Typography>
                      ),
                    }}
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Stance</InputLabel>
                    <Select
                      value={fighterForm.stance}
                      label="Stance"
                      onChange={(e) =>
                        setFighterForm({
                          ...fighterForm,
                          stance: e.target.value,
                        })
                      }
                    >
                      <MenuItem value="">Unknown</MenuItem>
                      <MenuItem value="orthodox">Orthodox</MenuItem>
                      <MenuItem value="southpaw">Southpaw</MenuItem>
                      <MenuItem value="switch">Switch</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Gym"
                    value={fighterForm.gym}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        gym: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider />

            {/* LOCATION */}
            <Box>
              <Typography
                variant="subtitle2"
                fontWeight={900}
                sx={{ mb: 1.5 }}
              >
                Location
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="City"
                    value={fighterForm.city}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        city: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={6} sm={3}>
                  <TextField
                    fullWidth
                    label="State"
                    value={fighterForm.state}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        state: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={6} sm={3}>
                  <TextField
                    fullWidth
                    label="Country"
                    value={fighterForm.country}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        country: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider />

            {/* AVAILABLE WEIGHT */}
            <Box>
              <Typography
                variant="subtitle2"
                fontWeight={900}
                sx={{ mb: 0.5 }}
              >
                Available Weight Range
              </Typography>

              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mb: 1.5 }}
              >
                Optional — useful when searching for opponents.
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Minimum"
                    placeholder="138"
                    value={fighterForm.available_weight_min}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        available_weight_min: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Maximum"
                    placeholder="143"
                    value={fighterForm.available_weight_max}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        available_weight_max: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

          </Stack>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            disabled={working}
            onClick={() => {
              setFighterOpen(false);
              setExistingFighterId("");
              closeBoxRecProfile();
            }}
          >
            Cancel
          </Button>

          <Button
            variant="outlined"
            disabled={working || !fighterForm.legal_name.trim()}
            onClick={() => createFighter(false)}
            sx={{
              fontWeight: 900,
            }}
          >
            {working
              ? "Saving..."
              : existingFighterId
                ? "Use Fighter"
                : "Save Fighter"}
          </Button>

          <Button
            variant="contained"
            disabled={
              working ||
              !fighterForm.legal_name.trim() ||
              (
                !fighterForm.fight_weight &&
                !fighterForm.available_weight_min &&
                !fighterForm.available_weight_max
              )
            }
            onClick={() => createFighter(true)}
            sx={{
              bgcolor: "#e31b23",
              fontWeight: 950,
              px: 3,
            }}
          >
            {working
              ? "Finding..."
              : "Save & Find Opponents"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={editFighterOpen}
        onClose={() => !working && setEditFighterOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          <Typography variant="h5" fontWeight={950}>
            Edit Fighter
          </Typography>

          <Typography variant="body2" color="text.secondary">
            Update the information used for matchmaking and event operations.
          </Typography>
        </DialogTitle>

        <DialogContent>
          <Stack spacing={3} sx={{ pt: 1 }}>

            <Box>
              <Typography variant="subtitle2" fontWeight={900} sx={{ mb: 1.5 }}>
                Fighter
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} md={8}>
                  <TextField
                    fullWidth
                    required
                    label="Fighter Name"
                    value={editFighterForm.legal_name || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        legal_name: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="BoxRec ID"
                    value={editFighterForm.boxrec_id || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        boxrec_id:
                          e.target.value.replace(/[^0-9]/g, ""),
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Pro Record"
                    placeholder="8-2-0"
                    value={editFighterForm.pro_record || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        pro_record: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Stance</InputLabel>

                    <Select
                      label="Stance"
                      value={editFighterForm.stance || ""}
                      onChange={(e) =>
                        setEditFighterForm({
                          ...editFighterForm,
                          stance: e.target.value,
                        })
                      }
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
                    label="Gym"
                    value={editFighterForm.gym || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        gym: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider />

            <Box>
              <Typography variant="subtitle2" fontWeight={900} sx={{ mb: 1.5 }}>
                Matchmaking Weight
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={6} md={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Low Weight"
                    value={editFighterForm.available_weight_min ?? ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        available_weight_min: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={6} md={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="High Weight"
                    value={editFighterForm.available_weight_max ?? ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        available_weight_max: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Preferred Fight Weight"
                    value={editFighterForm.fight_weight ?? ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        fight_weight: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider />

            <Box>
              <Typography variant="subtitle2" fontWeight={900} sx={{ mb: 1.5 }}>
                Contact
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Phone"
                    value={editFighterForm.phone || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        phone: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    type="email"
                    label="Email"
                    value={editFighterForm.email || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        email: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Instagram"
                    value={editFighterForm.instagram || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        instagram: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Facebook"
                    value={editFighterForm.facebook || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        facebook: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="TikTok"
                    value={editFighterForm.tiktok || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        tiktok: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider />

            <Box>
              <Typography variant="subtitle2" fontWeight={900} sx={{ mb: 1.5 }}>
                Location
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} md={5}>
                  <TextField
                    fullWidth
                    label="City"
                    value={editFighterForm.city || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        city: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={6} md={3}>
                  <TextField
                    fullWidth
                    label="State"
                    value={editFighterForm.state || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        state: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={6} md={4}>
                  <TextField
                    fullWidth
                    label="Country"
                    value={editFighterForm.country || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        country: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider />

            <Box>
              <Typography variant="subtitle2" fontWeight={900} sx={{ mb: 1.5 }}>
                Commission / Medical
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Bloodwork</InputLabel>

                    <Select
                      label="Bloodwork"
                      value={editFighterForm.bloodwork_status || "missing"}
                      onChange={(e) =>
                        setEditFighterForm({
                          ...editFighterForm,
                          bloodwork_status: e.target.value,
                        })
                      }
                    >
                      <MenuItem value="missing">Missing</MenuItem>
                      <MenuItem value="verified">Verified</MenuItem>
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
                    value={editFighterForm.bloodwork_expires || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        bloodwork_expires: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Suspension</InputLabel>

                    <Select
                      label="Suspension"
                      value={
                        editFighterForm.suspension_status ||
                        "needs_review"
                      }
                      onChange={(e) =>
                        setEditFighterForm({
                          ...editFighterForm,
                          suspension_status: e.target.value,
                        })
                      }
                    >
                      <MenuItem value="needs_review">
                        Needs Review
                      </MenuItem>

                      <MenuItem value="verified_clear">
                        Verified Clear
                      </MenuItem>

                      <MenuItem value="suspended">
                        Suspended
                      </MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            </Box>

          </Stack>
        </DialogContent>

        <DialogActions>
          <Button
            disabled={working}
            onClick={() => setEditFighterOpen(false)}
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            disabled={
              working ||
              !editFighterForm.legal_name?.trim()
            }
            onClick={saveFighterEdits}
            sx={{
              bgcolor: "#e31b23",
              fontWeight: 900,
            }}
          >
            {working ? "Saving..." : "Save Changes"}
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
