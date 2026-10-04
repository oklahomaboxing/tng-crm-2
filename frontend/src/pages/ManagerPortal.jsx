import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  Grid,
  MenuItem,
  Stack,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";

const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

function authHeaders(extra = {}) {
  return {
    Authorization: `Bearer ${localStorage.getItem("token")}`,
    ...extra,
  };
}

function money(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function fighterName(fighter) {
  return (
    fighter?.name ||
    fighter?.fighter_name ||
    [fighter?.first_name, fighter?.last_name].filter(Boolean).join(" ") ||
    `Fighter #${fighter?.id || ""}`
  );
}

function fighterRecord(fighter) {
  if (fighter?.record) return fighter.record;

  const wins = fighter?.wins ?? fighter?.pro_wins;
  const losses = fighter?.losses ?? fighter?.pro_losses;
  const draws = fighter?.draws ?? fighter?.pro_draws;

  if ([wins, losses, draws].some((value) => value !== undefined && value !== null)) {
    return `${wins || 0}-${losses || 0}-${draws || 0}`;
  }

  return "-";
}

function statusColor(status) {
  if (status === "accepted") return "success";
  if (status === "declined" || status === "withdrawn") return "error";
  if (status === "countered") return "warning";
  if (status === "sent" || status === "viewed") return "info";
  return "default";
}

export default function ManagerPortal() {
  const [tab, setTab] = useState(0);
  const [profile, setProfile] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [availability, setAvailability] = useState([]);
  const [offers, setOffers] = useState([]);

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [availabilityOpen, setAvailabilityOpen] = useState(false);
  const [availabilityForm, setAvailabilityForm] = useState({
    fighter_id: "",
    event_id: "",
    available: true,
    start_date: "",
    end_date: "",
    weight_min: "",
    weight_max: "",
    preferred_weight: "",
    location: "",
    travel_available: true,
    notes: "",
  });

  const [declineOffer, setDeclineOffer] = useState(null);
  const [declineReason, setDeclineReason] = useState("");

  const [counterOffer, setCounterOffer] = useState(null);
  const [counterForm, setCounterForm] = useState({
    proposed_weight: "",
    rounds: "",
    bout_type: "",
    proposed_purse: "",
    ticket_commission_percent: "",
    travel_type: "",
    travel_paid_by: "",
    travel_expense: "",
    hotel_provided: false,
    hotel_name: "",
    hotel_nights: "",
    per_diem_daily: "",
    per_diem_days: "",
    additional_terms: "",
    message: "",
  });

  const fighterMap = useMemo(() => {
    const map = {};

    assignments.forEach((assignment) => {
      if (assignment?.fighter?.id) {
        map[assignment.fighter.id] = assignment.fighter;
      }
    });

    return map;
  }, [assignments]);

  const pendingOffers = useMemo(
    () => offers.filter((offer) => ["sent", "viewed"].includes(offer.status)),
    [offers]
  );

  async function request(pathname, options = {}) {
    const response = await fetch(`${API}${pathname}`, {
      ...options,
      headers: authHeaders(options.headers || {}),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.detail || data.message || "Request failed");
    }

    return data;
  }

  async function loadPortal({ silent = false } = {}) {
    if (!silent) setLoading(true);

    setError("");

    try {
      const [profileData, fighterData, availabilityData, offerData] =
        await Promise.all([
          request("/api/boxing/manager/me"),
          request("/api/boxing/manager/me/fighters"),
          request("/api/boxing/manager/me/availability"),
          request("/api/boxing/manager/me/offers"),
        ]);

      setProfile(profileData);
      setAssignments(Array.isArray(fighterData) ? fighterData : []);
      setAvailability(Array.isArray(availabilityData) ? availabilityData : []);
      setOffers(Array.isArray(offerData) ? offerData : []);
    } catch (err) {
      setError(err.message || "Could not load manager portal");
    } finally {
      if (!silent) setLoading(false);
    }
  }

  useEffect(() => {
    loadPortal();
  }, []);

  async function markViewed(offer) {
    if (offer.status !== "sent") return;

    try {
      await request(`/api/boxing/manager/me/offers/${offer.id}/view`, {
        method: "POST",
      });

      await loadPortal({ silent: true });
    } catch (err) {
      setError(err.message || "Could not mark offer viewed");
    }
  }

  async function acceptOffer(offer) {
    if (!window.confirm("Accept this fight offer?")) return;

    setActionLoading(true);
    setError("");
    setMessage("");

    try {
      const data = await request(
        `/api/boxing/manager/me/offers/${offer.id}/accept`,
        { method: "POST" }
      );

      setMessage(data.message || "Fight offer accepted.");
      await loadPortal({ silent: true });
    } catch (err) {
      setError(err.message || "Could not accept offer");
    } finally {
      setActionLoading(false);
    }
  }

  async function submitDecline() {
    if (!declineOffer) return;

    setActionLoading(true);
    setError("");
    setMessage("");

    try {
      const data = await request(
        `/api/boxing/manager/me/offers/${declineOffer.id}/decline`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            reason: declineReason.trim(),
          }),
        }
      );

      setMessage(data.message || "Fight offer declined.");
      setDeclineOffer(null);
      setDeclineReason("");
      await loadPortal({ silent: true });
    } catch (err) {
      setError(err.message || "Could not decline offer");
    } finally {
      setActionLoading(false);
    }
  }

  function openCounter(offer) {
    setCounterOffer(offer);

    setCounterForm({
      proposed_weight: offer.proposed_weight ?? "",
      rounds: offer.rounds ?? 4,
      bout_type: offer.bout_type || "pro",
      proposed_purse: offer.proposed_purse ?? 0,
      ticket_commission_percent: offer.ticket_commission_percent ?? 0,
      travel_type: offer.travel_type || "",
      travel_paid_by: offer.travel_paid_by || "",
      travel_expense: offer.travel_expense ?? 0,
      hotel_provided: Boolean(offer.hotel_provided),
      hotel_name: offer.hotel_name || "",
      hotel_nights: offer.hotel_nights ?? 0,
      per_diem_daily: offer.per_diem_daily ?? 0,
      per_diem_days: offer.per_diem_days ?? 0,
      additional_terms: offer.additional_terms || "",
      message: "",
    });
  }

  async function submitCounter() {
    if (!counterOffer) return;

    setActionLoading(true);
    setError("");
    setMessage("");

    try {
      const data = await request(
        `/api/boxing/manager/me/offers/${counterOffer.id}/counter`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(counterForm),
        }
      );

      setMessage(data.message || "Counteroffer sent.");
      setCounterOffer(null);
      await loadPortal({ silent: true });
    } catch (err) {
      setError(err.message || "Could not send counteroffer");
    } finally {
      setActionLoading(false);
    }
  }

  function openAvailability(fighterId = "") {
    setAvailabilityForm({
      fighter_id: fighterId || "",
      event_id: "",
      available: true,
      start_date: "",
      end_date: "",
      weight_min: "",
      weight_max: "",
      preferred_weight: "",
      location: "",
      travel_available: true,
      notes: "",
    });

    setAvailabilityOpen(true);
  }

  async function saveAvailability() {
    const fighterId = Number(availabilityForm.fighter_id);

    if (!fighterId) {
      setError("Select a fighter.");
      return;
    }

    setActionLoading(true);
    setError("");
    setMessage("");

    try {
      const payload = {
        event_id: availabilityForm.event_id || null,
        available: Boolean(availabilityForm.available),
        start_date: availabilityForm.start_date,
        end_date: availabilityForm.end_date,
        weight_min: availabilityForm.weight_min,
        weight_max: availabilityForm.weight_max,
        preferred_weight: availabilityForm.preferred_weight,
        location: availabilityForm.location,
        travel_available: Boolean(availabilityForm.travel_available),
        notes: availabilityForm.notes,
      };

      const data = await request(
        `/api/boxing/manager/me/fighters/${fighterId}/availability`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );

      setMessage(data.message || "Availability saved.");
      setAvailabilityOpen(false);
      await loadPortal({ silent: true });
    } catch (err) {
      setError(err.message || "Could not save availability");
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return (
      <Box sx={{ minHeight: 300, display: "grid", placeItems: "center" }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        spacing={2}
        sx={{ mb: 3 }}
      >
        <Box>
          <Typography variant="h4" fontWeight={950}>
            Manager Portal
          </Typography>

          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
            Manage your fighters, availability, and TNG fight offers.
          </Typography>
        </Box>

        <Button
          variant="contained"
          onClick={() => openAvailability()}
          disabled={!assignments.length}
        >
          Set Fighter Availability
        </Button>
      </Stack>

      {error && (
        <Alert severity="error" onClose={() => setError("")} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {message && (
        <Alert severity="success" onClose={() => setMessage("")} sx={{ mb: 2 }}>
          {message}
        </Alert>
      )}

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                Manager
              </Typography>
              <Typography variant="h5" fontWeight={900}>
                {profile?.display_name || "Manager"}
              </Typography>
              <Typography color="text.secondary">
                {profile?.company_name || "Independent Manager"}
              </Typography>

              <Divider sx={{ my: 2 }} />

              <Typography variant="body2">
                {profile?.email || "-"}
              </Typography>
              <Typography variant="body2">
                {profile?.phone || "-"}
              </Typography>

              {(profile?.license_number || profile?.license_state) && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  License: {profile?.license_number || "-"}
                  {profile?.license_state ? ` ? ${profile.license_state}` : ""}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={4} md={2.67}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                Fighters
              </Typography>
              <Typography variant="h3" fontWeight={950}>
                {assignments.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={4} md={2.67}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                Pending Offers
              </Typography>
              <Typography variant="h3" fontWeight={950}>
                {pendingOffers.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={4} md={2.66}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                Availability Updates
              </Typography>
              <Typography variant="h3" fontWeight={950}>
                {availability.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card>
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs
            value={tab}
            onChange={(_, value) => setTab(value)}
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab label={`Fight Offers (${offers.length})`} />
            <Tab label={`My Fighters (${assignments.length})`} />
            <Tab label="Availability" />
          </Tabs>
        </Box>

        <CardContent sx={{ p: { xs: 2, md: 3 } }}>
          {tab === 0 && (
            <Stack spacing={2}>
              {!offers.length && (
                <Alert severity="info">
                  No fight offers have been sent to your fighters yet.
                </Alert>
              )}

              {offers.map((offer) => {
                const fighter = fighterMap[offer.fighter_id];
                const canRespond = ["sent", "viewed"].includes(offer.status);

                return (
                  <Card
                    key={offer.id}
                    variant="outlined"
                    onMouseEnter={() => markViewed(offer)}
                    sx={{ boxShadow: "none" }}
                  >
                    <CardContent>
                      <Stack
                        direction={{ xs: "column", md: "row" }}
                        justifyContent="space-between"
                        spacing={2}
                      >
                        <Box>
                          <Stack direction="row" spacing={1} flexWrap="wrap">
                            <Typography variant="h6" fontWeight={900}>
                              {fighterName(fighter)}
                            </Typography>

                            <Chip
                              size="small"
                              label={offer.status || "draft"}
                              color={statusColor(offer.status)}
                            />

                            {offer.version > 1 && (
                              <Chip
                                size="small"
                                variant="outlined"
                                label={`Version ${offer.version}`}
                              />
                            )}
                          </Stack>

                          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                            Event #{offer.event_id} ? Opponent #{offer.opponent_id}
                          </Typography>
                        </Box>

                        <Box sx={{ textAlign: { xs: "left", md: "right" } }}>
                          <Typography variant="h5" fontWeight={950}>
                            {money(offer.proposed_purse)}
                          </Typography>
                          <Typography color="text.secondary" variant="body2">
                            Proposed purse
                          </Typography>
                        </Box>
                      </Stack>

                      <Divider sx={{ my: 2 }} />

                      <Grid container spacing={2}>
                        <Grid item xs={6} sm={3}>
                          <Typography variant="caption" color="text.secondary">
                            Weight
                          </Typography>
                          <Typography fontWeight={800}>
                            {offer.proposed_weight
                              ? `${offer.proposed_weight} lb`
                              : "-"}
                          </Typography>
                        </Grid>

                        <Grid item xs={6} sm={3}>
                          <Typography variant="caption" color="text.secondary">
                            Rounds
                          </Typography>
                          <Typography fontWeight={800}>
                            {offer.rounds || "-"}
                          </Typography>
                        </Grid>

                        <Grid item xs={6} sm={3}>
                          <Typography variant="caption" color="text.secondary">
                            Ticket Commission
                          </Typography>
                          <Typography fontWeight={800}>
                            {Number(offer.ticket_commission_percent || 0)}%
                          </Typography>
                        </Grid>

                        <Grid item xs={6} sm={3}>
                          <Typography variant="caption" color="text.secondary">
                            Bout Type
                          </Typography>
                          <Typography fontWeight={800}>
                            {offer.bout_type || "-"}
                          </Typography>
                        </Grid>
                      </Grid>

                      {(offer.travel_expense ||
                        offer.hotel_provided ||
                        offer.per_diem_total) && (
                        <>
                          <Divider sx={{ my: 2 }} />

                          <Stack
                            direction={{ xs: "column", sm: "row" }}
                            spacing={2}
                          >
                            {Number(offer.travel_expense || 0) > 0 && (
                              <Chip
                                variant="outlined"
                                label={`Travel ${money(offer.travel_expense)}`}
                              />
                            )}

                            {offer.hotel_provided && (
                              <Chip
                                variant="outlined"
                                label={`Hotel${
                                  offer.hotel_nights
                                    ? ` ? ${offer.hotel_nights} nights`
                                    : ""
                                }`}
                              />
                            )}

                            {Number(offer.per_diem_total || 0) > 0 && (
                              <Chip
                                variant="outlined"
                                label={`Per Diem ${money(offer.per_diem_total)}`}
                              />
                            )}
                          </Stack>
                        </>
                      )}

                      {offer.additional_terms && (
                        <Box sx={{ mt: 2 }}>
                          <Typography variant="caption" color="text.secondary">
                            Additional Terms
                          </Typography>
                          <Typography>{offer.additional_terms}</Typography>
                        </Box>
                      )}

                      {offer.message && (
                        <Box sx={{ mt: 2 }}>
                          <Typography variant="caption" color="text.secondary">
                            Message
                          </Typography>
                          <Typography>{offer.message}</Typography>
                        </Box>
                      )}

                      {canRespond && (
                        <Stack
                          direction={{ xs: "column", sm: "row" }}
                          spacing={1}
                          sx={{ mt: 3 }}
                        >
                          <Button
                            variant="contained"
                            color="success"
                            disabled={actionLoading}
                            onClick={() => acceptOffer(offer)}
                          >
                            Accept Offer
                          </Button>

                          <Button
                            variant="outlined"
                            disabled={actionLoading}
                            onClick={() => openCounter(offer)}
                          >
                            Counter
                          </Button>

                          <Button
                            variant="outlined"
                            color="error"
                            disabled={actionLoading}
                            onClick={() => {
                              setDeclineOffer(offer);
                              setDeclineReason("");
                            }}
                          >
                            Decline
                          </Button>
                        </Stack>
                      )}

                      {offer.contract_id && (
                        <Alert severity="success" sx={{ mt: 2 }}>
                          Contract #{offer.contract_id} has been created.
                        </Alert>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </Stack>
          )}

          {tab === 1 && (
            <Grid container spacing={2}>
              {!assignments.length && (
                <Grid item xs={12}>
                  <Alert severity="info">
                    No fighters are currently assigned to this manager account.
                  </Alert>
                </Grid>
              )}

              {assignments.map((assignment) => {
                const fighter = assignment.fighter;

                return (
                  <Grid item xs={12} md={6} lg={4} key={assignment.assignment_id}>
                    <Card variant="outlined" sx={{ height: "100%", boxShadow: "none" }}>
                      <CardContent>
                        <Typography variant="h6" fontWeight={900}>
                          {fighterName(fighter)}
                        </Typography>

                        <Typography color="text.secondary">
                          Record: {fighterRecord(fighter)}
                        </Typography>

                        {(fighter?.weight || fighter?.weight_class) && (
                          <Typography sx={{ mt: 1 }}>
                            Weight: {fighter.weight || fighter.weight_class}
                          </Typography>
                        )}

                        {(fighter?.city || fighter?.state) && (
                          <Typography>
                            {[fighter.city, fighter.state].filter(Boolean).join(", ")}
                          </Typography>
                        )}

                        <Button
                          sx={{ mt: 2 }}
                          variant="outlined"
                          onClick={() => openAvailability(fighter.id)}
                        >
                          Set Availability
                        </Button>
                      </CardContent>
                    </Card>
                  </Grid>
                );
              })}
            </Grid>
          )}

          {tab === 2 && (
            <Stack spacing={2}>
              {!availability.length && (
                <Alert severity="info">
                  No fighter availability has been entered yet.
                </Alert>
              )}

              {availability.map((row) => {
                const fighter = fighterMap[row.fighter_id];

                return (
                  <Card key={row.id} variant="outlined" sx={{ boxShadow: "none" }}>
                    <CardContent>
                      <Stack
                        direction={{ xs: "column", sm: "row" }}
                        justifyContent="space-between"
                        spacing={2}
                      >
                        <Box>
                          <Typography variant="h6" fontWeight={900}>
                            {fighterName(fighter)}
                          </Typography>

                          <Typography color="text.secondary">
                            {row.start_date || "Open"}
                            {row.end_date ? ` ? ${row.end_date}` : ""}
                          </Typography>
                        </Box>

                        <Stack direction="row" spacing={1}>
                          <Chip
                            label={row.available ? "Available" : "Unavailable"}
                            color={row.available ? "success" : "default"}
                          />

                          {row.travel_available && (
                            <Chip label="Can Travel" variant="outlined" />
                          )}
                        </Stack>
                      </Stack>

                      <Grid container spacing={2} sx={{ mt: 0.5 }}>
                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" color="text.secondary">
                            Minimum
                          </Typography>
                          <Typography fontWeight={800}>
                            {row.weight_min ? `${row.weight_min} lb` : "-"}
                          </Typography>
                        </Grid>

                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" color="text.secondary">
                            Preferred
                          </Typography>
                          <Typography fontWeight={800}>
                            {row.preferred_weight
                              ? `${row.preferred_weight} lb`
                              : "-"}
                          </Typography>
                        </Grid>

                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" color="text.secondary">
                            Maximum
                          </Typography>
                          <Typography fontWeight={800}>
                            {row.weight_max ? `${row.weight_max} lb` : "-"}
                          </Typography>
                        </Grid>

                        <Grid item xs={6} md={3}>
                          <Typography variant="caption" color="text.secondary">
                            Location
                          </Typography>
                          <Typography fontWeight={800}>
                            {row.location || "-"}
                          </Typography>
                        </Grid>
                      </Grid>

                      {row.notes && (
                        <Typography sx={{ mt: 2 }}>
                          {row.notes}
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </Stack>
          )}
        </CardContent>
      </Card>

      <Dialog
        open={availabilityOpen}
        onClose={() => setAvailabilityOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Set Fighter Availability</DialogTitle>

        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              select
              label="Fighter"
              value={availabilityForm.fighter_id}
              onChange={(event) =>
                setAvailabilityForm({
                  ...availabilityForm,
                  fighter_id: event.target.value,
                })
              }
              required
            >
              {assignments.map((assignment) => (
                <MenuItem
                  key={assignment.assignment_id}
                  value={assignment.fighter.id}
                >
                  {fighterName(assignment.fighter)}
                </MenuItem>
              ))}
            </TextField>

            <FormControlLabel
              control={
                <Switch
                  checked={availabilityForm.available}
                  onChange={(event) =>
                    setAvailabilityForm({
                      ...availabilityForm,
                      available: event.target.checked,
                    })
                  }
                />
              }
              label="Available to fight"
            />

            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Start Date"
                  type="date"
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                  value={availabilityForm.start_date}
                  onChange={(event) =>
                    setAvailabilityForm({
                      ...availabilityForm,
                      start_date: event.target.value,
                    })
                  }
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  label="End Date"
                  type="date"
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                  value={availabilityForm.end_date}
                  onChange={(event) =>
                    setAvailabilityForm({
                      ...availabilityForm,
                      end_date: event.target.value,
                    })
                  }
                />
              </Grid>
            </Grid>

            <Grid container spacing={2}>
              <Grid item xs={4}>
                <TextField
                  label="Min Weight"
                  type="number"
                  fullWidth
                  value={availabilityForm.weight_min}
                  onChange={(event) =>
                    setAvailabilityForm({
                      ...availabilityForm,
                      weight_min: event.target.value,
                    })
                  }
                />
              </Grid>

              <Grid item xs={4}>
                <TextField
                  label="Preferred"
                  type="number"
                  fullWidth
                  value={availabilityForm.preferred_weight}
                  onChange={(event) =>
                    setAvailabilityForm({
                      ...availabilityForm,
                      preferred_weight: event.target.value,
                    })
                  }
                />
              </Grid>

              <Grid item xs={4}>
                <TextField
                  label="Max Weight"
                  type="number"
                  fullWidth
                  value={availabilityForm.weight_max}
                  onChange={(event) =>
                    setAvailabilityForm({
                      ...availabilityForm,
                      weight_max: event.target.value,
                    })
                  }
                />
              </Grid>
            </Grid>

            <TextField
              label="Location"
              value={availabilityForm.location}
              onChange={(event) =>
                setAvailabilityForm({
                  ...availabilityForm,
                  location: event.target.value,
                })
              }
            />

            <FormControlLabel
              control={
                <Switch
                  checked={availabilityForm.travel_available}
                  onChange={(event) =>
                    setAvailabilityForm({
                      ...availabilityForm,
                      travel_available: event.target.checked,
                    })
                  }
                />
              }
              label="Available to travel"
            />

            <TextField
              label="Notes"
              multiline
              minRows={3}
              value={availabilityForm.notes}
              onChange={(event) =>
                setAvailabilityForm({
                  ...availabilityForm,
                  notes: event.target.value,
                })
              }
            />
          </Stack>
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setAvailabilityOpen(false)}>
            Cancel
          </Button>

          <Button
            variant="contained"
            disabled={actionLoading}
            onClick={saveAvailability}
          >
            Save Availability
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={Boolean(declineOffer)}
        onClose={() => setDeclineOffer(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Decline Fight Offer</DialogTitle>

        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            multiline
            minRows={3}
            label="Reason or message"
            value={declineReason}
            onChange={(event) => setDeclineReason(event.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setDeclineOffer(null)}>
            Cancel
          </Button>

          <Button
            color="error"
            variant="contained"
            disabled={actionLoading}
            onClick={submitDecline}
          >
            Decline Offer
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={Boolean(counterOffer)}
        onClose={() => setCounterOffer(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>Counter Fight Offer</DialogTitle>

        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 0 }}>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Weight"
                value={counterForm.proposed_weight}
                onChange={(event) =>
                  setCounterForm({
                    ...counterForm,
                    proposed_weight: event.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Rounds"
                value={counterForm.rounds}
                onChange={(event) =>
                  setCounterForm({
                    ...counterForm,
                    rounds: event.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Bout Type"
                value={counterForm.bout_type}
                onChange={(event) =>
                  setCounterForm({
                    ...counterForm,
                    bout_type: event.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Purse"
                value={counterForm.proposed_purse}
                onChange={(event) =>
                  setCounterForm({
                    ...counterForm,
                    proposed_purse: event.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Ticket Commission %"
                value={counterForm.ticket_commission_percent}
                onChange={(event) =>
                  setCounterForm({
                    ...counterForm,
                    ticket_commission_percent: event.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Travel Type"
                value={counterForm.travel_type}
                onChange={(event) =>
                  setCounterForm({
                    ...counterForm,
                    travel_type: event.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Travel Paid By"
                value={counterForm.travel_paid_by}
                onChange={(event) =>
                  setCounterForm({
                    ...counterForm,
                    travel_paid_by: event.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Travel Expense"
                value={counterForm.travel_expense}
                onChange={(event) =>
                  setCounterForm({
                    ...counterForm,
                    travel_expense: event.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={counterForm.hotel_provided}
                    onChange={(event) =>
                      setCounterForm({
                        ...counterForm,
                        hotel_provided: event.target.checked,
                      })
                    }
                  />
                }
                label="Hotel provided"
              />
            </Grid>

            {counterForm.hotel_provided && (
              <>
                <Grid item xs={12} sm={8}>
                  <TextField
                    fullWidth
                    label="Hotel Name"
                    value={counterForm.hotel_name}
                    onChange={(event) =>
                      setCounterForm({
                        ...counterForm,
                        hotel_name: event.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Hotel Nights"
                    value={counterForm.hotel_nights}
                    onChange={(event) =>
                      setCounterForm({
                        ...counterForm,
                        hotel_nights: event.target.value,
                      })
                    }
                  />
                </Grid>
              </>
            )}

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Per Diem / Day"
                value={counterForm.per_diem_daily}
                onChange={(event) =>
                  setCounterForm({
                    ...counterForm,
                    per_diem_daily: event.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Per Diem Days"
                value={counterForm.per_diem_days}
                onChange={(event) =>
                  setCounterForm({
                    ...counterForm,
                    per_diem_days: event.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                minRows={2}
                label="Additional Terms"
                value={counterForm.additional_terms}
                onChange={(event) =>
                  setCounterForm({
                    ...counterForm,
                    additional_terms: event.target.value,
                  })
                }
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                minRows={2}
                label="Message to Matchmaker"
                value={counterForm.message}
                onChange={(event) =>
                  setCounterForm({
                    ...counterForm,
                    message: event.target.value,
                  })
                }
              />
            </Grid>
          </Grid>
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setCounterOffer(null)}>
            Cancel
          </Button>

          <Button
            variant="contained"
            disabled={actionLoading}
            onClick={submitCounter}
          >
            Send Counteroffer
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
