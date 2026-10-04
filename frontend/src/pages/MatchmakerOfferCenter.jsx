import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
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
  TextField,
  Typography,
} from "@mui/material";

const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const authHeaders = (extra = {}) => ({
  Authorization: `Bearer ${localStorage.getItem("token")}`,
  ...extra,
});

const emptyOffer = {
  event_id: "",
  fighter_id: "",
  opponent_id: "",
  proposed_weight: "",
  rounds: 4,
  bout_type: "pro",
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
  send: true,
};

function fighterName(fighter) {
  return (
    fighter?.legal_name ||
    fighter?.name ||
    fighter?.fighter_name ||
    [fighter?.first_name, fighter?.last_name].filter(Boolean).join(" ") ||
    `Fighter #${fighter?.id || ""}`
  );
}

function money(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function statusColor(status) {
  if (status === "accepted") return "success";
  if (status === "sent" || status === "viewed") return "info";
  if (status === "countered") return "warning";
  if (status === "declined" || status === "withdrawn") return "error";
  return "default";
}

export default function MatchmakerOfferCenter({
  fighters = [],
  events = [],
}) {
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [working, setWorking] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [form, setForm] = useState(emptyOffer);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const fighterMap = useMemo(() => {
    const map = {};
    fighters.forEach((fighter) => {
      if (fighter?.id) map[fighter.id] = fighter;
    });
    return map;
  }, [fighters]);

  const eventMap = useMemo(() => {
    const map = {};
    events.forEach((event) => {
      if (event?.id) map[event.id] = event;
    });
    return map;
  }, [events]);

  const activeOffers = useMemo(
    () =>
      offers.filter((offer) =>
        ["draft", "sent", "viewed", "countered", "accepted"].includes(
          offer.status
        )
      ),
    [offers]
  );

  const counters = useMemo(
    () => offers.filter((offer) => offer.parent_offer_id),
    [offers]
  );

  const historyOffers = useMemo(
    () =>
      offers.filter((offer) =>
        ["declined", "withdrawn"].includes(offer.status)
      ),
    [offers]
  );

  async function request(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers: authHeaders(options.headers || {}),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail ||
        data.message ||
        "Request failed"
      );
    }

    return data;
  }

  async function loadOffers({ silent = false } = {}) {
    if (!silent) setLoading(true);
    setError("");

    try {
      const data = await request("/api/boxing/offers");
      setOffers(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || "Could not load fight offers");
    } finally {
      if (!silent) setLoading(false);
    }
  }

  useEffect(() => {
    loadOffers();
  }, []);

  function setField(name, value) {
    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function createOffer() {
    if (!form.event_id || !form.fighter_id || !form.opponent_id) {
      setError("Choose an event, fighter, and opponent.");
      return;
    }

    if (Number(form.fighter_id) === Number(form.opponent_id)) {
      setError("Choose two different fighters.");
      return;
    }

    setWorking(true);
    setError("");
    setMessage("");

    try {
      const payload = {
        ...form,
        event_id: Number(form.event_id),
        fighter_id: Number(form.fighter_id),
        opponent_id: Number(form.opponent_id),
      };

      const data = await request("/api/boxing/offers", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      setMessage(
        form.send
          ? `Fight offer #${data.id} sent.`
          : `Fight offer #${data.id} saved as draft.`
      );

      setForm(emptyOffer);
      setFormOpen(false);
      await loadOffers({ silent: true });
    } catch (err) {
      setError(err.message || "Could not create fight offer");
    } finally {
      setWorking(false);
    }
  }

  async function action(offer, actionName, body = null) {
    setWorking(true);
    setError("");
    setMessage("");

    try {
      const options = {
        method: "POST",
      };

      if (body !== null) {
        options.headers = {
          "Content-Type": "application/json",
        };
        options.body = JSON.stringify(body);
      }

      const data = await request(
        `/api/boxing/offers/${offer.id}/${actionName}`,
        options
      );

      setMessage(
        data.message ||
        `Offer #${offer.id} updated successfully.`
      );

      await loadOffers({ silent: true });
    } catch (err) {
      setError(
        err.message ||
        `Could not ${actionName.replace("-", " ")} offer`
      );
    } finally {
      setWorking(false);
    }
  }

  async function convertOffer(offer) {
    if (
      !window.confirm(
        `Convert accepted offer #${offer.id} into a bout and contract?`
      )
    ) {
      return;
    }

    setWorking(true);
    setError("");
    setMessage("");

    try {
      const data = await request(
        `/api/boxing/offers/${offer.id}/convert`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            corner: "red",
          }),
        }
      );

      setMessage(
        `Offer converted. Bout #${data.bout?.id || offer.bout_id || ""}` +
        `${data.contract?.id ? ` ? Contract #${data.contract.id}` : ""}`
      );

      await loadOffers({ silent: true });
    } catch (err) {
      setError(err.message || "Could not convert accepted offer");
    } finally {
      setWorking(false);
    }
  }

  function offerCard(offer) {
    const fighter = fighterMap[offer.fighter_id];
    const opponent = fighterMap[offer.opponent_id];
    const event = eventMap[offer.event_id];

    const isCounter =
      Boolean(offer.parent_offer_id) &&
      offer.recipient_type === "matchmaker";

    const canAcceptCounter =
      isCounter &&
      ["sent", "viewed"].includes(offer.status);

    const canWithdraw =
      !offer.parent_offer_id &&
      ["draft", "sent", "viewed"].includes(offer.status);

    const canSend =
      offer.status === "draft";

    const canConvert =
      offer.status === "accepted" &&
      !offer.bout_id &&
      !offer.contract_id;

    return (
      <Card
        key={offer.id}
        variant="outlined"
        sx={{
          boxShadow: "none",
          borderRadius: 3,
        }}
      >
        <CardContent>
          <Stack
            direction={{ xs: "column", md: "row" }}
            justifyContent="space-between"
            spacing={2}
          >
            <Box>
              <Stack
                direction="row"
                spacing={1}
                useFlexGap
                flexWrap="wrap"
                alignItems="center"
              >
                <Typography variant="h6" fontWeight={950}>
                  {fighterName(fighter)}
                  {" vs "}
                  {fighterName(opponent)}
                </Typography>

                <Chip
                  size="small"
                  label={offer.status || "draft"}
                  color={statusColor(offer.status)}
                />

                {offer.parent_offer_id && (
                  <Chip
                    size="small"
                    variant="outlined"
                    label={`Counter v${offer.version || 1}`}
                  />
                )}
              </Stack>

              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.5 }}
              >
                {event?.name || `Event #${offer.event_id}`}
                {event?.event_date
                  ? ` ? ${event.event_date}`
                  : ""}
                {" ? "}
                Offer #{offer.id}
              </Typography>
            </Box>

            <Box
              sx={{
                textAlign: { xs: "left", md: "right" },
              }}
            >
              <Typography variant="h5" fontWeight={950}>
                {money(offer.proposed_purse)}
              </Typography>

              <Typography
                variant="caption"
                color="text.secondary"
              >
                Proposed purse
              </Typography>
            </Box>
          </Stack>

          <Divider sx={{ my: 2 }} />

          <Grid container spacing={2}>
            <Grid item xs={6} sm={3}>
              <Typography
                variant="caption"
                color="text.secondary"
              >
                Weight
              </Typography>

              <Typography fontWeight={850}>
                {offer.proposed_weight
                  ? `${offer.proposed_weight} lb`
                  : "-"}
              </Typography>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Typography
                variant="caption"
                color="text.secondary"
              >
                Rounds
              </Typography>

              <Typography fontWeight={850}>
                {offer.rounds || "-"}
              </Typography>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Typography
                variant="caption"
                color="text.secondary"
              >
                Ticket Commission
              </Typography>

              <Typography fontWeight={850}>
                {Number(
                  offer.ticket_commission_percent || 0
                )}%
              </Typography>
            </Grid>

            <Grid item xs={6} sm={3}>
              <Typography
                variant="caption"
                color="text.secondary"
              >
                Match Score
              </Typography>

              <Typography fontWeight={850}>
                {offer.match_score !== null &&
                offer.match_score !== undefined
                  ? `${offer.match_score}%`
                  : "-"}
              </Typography>
            </Grid>
          </Grid>

          {(Number(offer.travel_expense || 0) > 0 ||
            offer.hotel_provided ||
            Number(offer.per_diem_total || 0) > 0) && (
            <>
              <Divider sx={{ my: 2 }} />

              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={1}
                useFlexGap
                flexWrap="wrap"
              >
                {Number(offer.travel_expense || 0) > 0 && (
                  <Chip
                    variant="outlined"
                    label={`Travel ${money(
                      offer.travel_expense
                    )}`}
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
                    label={`Per Diem ${money(
                      offer.per_diem_total
                    )}`}
                  />
                )}
              </Stack>
            </>
          )}

          {offer.additional_terms && (
            <Box sx={{ mt: 2 }}>
              <Typography
                variant="caption"
                color="text.secondary"
              >
                Additional Terms
              </Typography>

              <Typography>
                {offer.additional_terms}
              </Typography>
            </Box>
          )}

          {offer.message && (
            <Box sx={{ mt: 2 }}>
              <Typography
                variant="caption"
                color="text.secondary"
              >
                Message
              </Typography>

              <Typography>{offer.message}</Typography>
            </Box>
          )}

          {(offer.bout_id || offer.contract_id) && (
            <Alert severity="success" sx={{ mt: 2 }}>
              {offer.bout_id
                ? `Bout #${offer.bout_id}`
                : ""}
              {offer.bout_id && offer.contract_id
                ? " ? "
                : ""}
              {offer.contract_id
                ? `Contract #${offer.contract_id}`
                : ""}
            </Alert>
          )}

          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1}
            sx={{ mt: 3 }}
          >
            {canSend && (
              <Button
                variant="contained"
                disabled={working}
                onClick={() =>
                  action(offer, "send")
                }
              >
                Send Offer
              </Button>
            )}

            {canAcceptCounter && (
              <Button
                variant="contained"
                color="success"
                disabled={working}
                onClick={() =>
                  action(offer, "accept-counter")
                }
              >
                Accept Counter
              </Button>
            )}

            {canConvert && (
              <Button
                variant="contained"
                color="success"
                disabled={working}
                onClick={() => convertOffer(offer)}
              >
                Create Bout + Contract
              </Button>
            )}

            {canWithdraw && (
              <Button
                variant="outlined"
                color="error"
                disabled={working}
                onClick={() => {
                  if (
                    window.confirm(
                      `Withdraw offer #${offer.id}?`
                    )
                  ) {
                    action(offer, "withdraw");
                  }
                }}
              >
                Withdraw
              </Button>
            )}
          </Stack>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card
        sx={{
          mb: 3,
          borderRadius: 3,
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        <CardContent>
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={2}
            justifyContent="space-between"
            alignItems={{ xs: "stretch", md: "center" }}
          >
            <Box>
              <Typography
                variant="h5"
                fontWeight={950}
              >
                Fight Offer Center
              </Typography>

              <Typography color="text.secondary">
                Send offers, review manager counters, and
                convert accepted deals into bouts and contracts.
              </Typography>
            </Box>

            <Button
              variant="contained"
              onClick={() => setFormOpen(true)}
              disabled={
                fighters.length < 2 ||
                events.length < 1
              }
            >
              New Fight Offer
            </Button>
          </Stack>

          {error && (
            <Alert
              severity="error"
              onClose={() => setError("")}
              sx={{ mt: 2 }}
            >
              {error}
            </Alert>
          )}

          {message && (
            <Alert
              severity="success"
              onClose={() => setMessage("")}
              sx={{ mt: 2 }}
            >
              {message}
            </Alert>
          )}

          <Stack
            direction="row"
            spacing={1}
            useFlexGap
            flexWrap="wrap"
            sx={{ mt: 2 }}
          >
            <Chip
              label={`${activeOffers.length} Active`}
              color="primary"
            />

            <Chip
              label={`${counters.length} Counters`}
              color={
                counters.some((offer) =>
                  ["sent", "viewed"].includes(
                    offer.status
                  )
                )
                  ? "warning"
                  : "default"
              }
            />

            <Chip
              label={`${
                offers.filter(
                  (offer) =>
                    offer.status === "accepted"
                ).length
              } Accepted`}
              color="success"
            />
          </Stack>

          <Divider sx={{ my: 2 }} />

          {loading ? (
            <Typography color="text.secondary">
              Loading fight offers...
            </Typography>
          ) : !activeOffers.length ? (
            <Alert severity="info">
              No active fight offers yet.
            </Alert>
          ) : (
            <Stack spacing={2}>
              {activeOffers.map(offerCard)}
            </Stack>
          )}

          {!!historyOffers.length && (
            <Box sx={{ mt: 2 }}>
              <Button
                variant="text"
                onClick={() =>
                  setShowHistory((current) => !current)
                }
              >
                {showHistory
                  ? "Hide Offer History"
                  : `Show Offer History (${historyOffers.length})`}
              </Button>

              <Collapse in={showHistory}>
                <Stack spacing={2} sx={{ mt: 1 }}>
                  {historyOffers.map(offerCard)}
                </Stack>
              </Collapse>
            </Box>
          )}
        </CardContent>
      </Card>

      <Dialog
        open={formOpen}
        onClose={() => setFormOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>New Fight Offer</DialogTitle>

        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 0 }}>
            <Grid item xs={12}>
              <TextField
                select
                fullWidth
                label="Event"
                value={form.event_id}
                onChange={(event) =>
                  setField(
                    "event_id",
                    event.target.value
                  )
                }
              >
                {events.map((event) => (
                  <MenuItem
                    key={event.id}
                    value={event.id}
                  >
                    {event.name || `Event #${event.id}`}
                    {event.event_date
                      ? ` ? ${event.event_date}`
                      : ""}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                select
                fullWidth
                label="Fighter Receiving Offer"
                value={form.fighter_id}
                onChange={(event) =>
                  setField(
                    "fighter_id",
                    event.target.value
                  )
                }
              >
                {fighters.map((fighter) => (
                  <MenuItem
                    key={fighter.id}
                    value={fighter.id}
                    disabled={
                      Number(fighter.id) ===
                      Number(form.opponent_id)
                    }
                  >
                    {fighterName(fighter)}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                select
                fullWidth
                label="Opponent"
                value={form.opponent_id}
                onChange={(event) =>
                  setField(
                    "opponent_id",
                    event.target.value
                  )
                }
              >
                {fighters.map((fighter) => (
                  <MenuItem
                    key={fighter.id}
                    value={fighter.id}
                    disabled={
                      Number(fighter.id) ===
                      Number(form.fighter_id)
                    }
                  >
                    {fighterName(fighter)}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Contract Weight"
                value={form.proposed_weight}
                onChange={(event) =>
                  setField(
                    "proposed_weight",
                    event.target.value
                  )
                }
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Rounds"
                value={form.rounds}
                onChange={(event) =>
                  setField(
                    "rounds",
                    event.target.value
                  )
                }
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                select
                fullWidth
                label="Bout Type"
                value={form.bout_type}
                onChange={(event) =>
                  setField(
                    "bout_type",
                    event.target.value
                  )
                }
              >
                <MenuItem value="pro">Pro</MenuItem>
                <MenuItem value="amateur">
                  Amateur
                </MenuItem>
              </TextField>
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Guaranteed Purse"
                value={form.proposed_purse}
                onChange={(event) =>
                  setField(
                    "proposed_purse",
                    event.target.value
                  )
                }
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Ticket Commission %"
                value={
                  form.ticket_commission_percent
                }
                onChange={(event) =>
                  setField(
                    "ticket_commission_percent",
                    event.target.value
                  )
                }
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Travel Type"
                placeholder="Flight, mileage, etc."
                value={form.travel_type}
                onChange={(event) =>
                  setField(
                    "travel_type",
                    event.target.value
                  )
                }
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Travel Paid By"
                value={form.travel_paid_by}
                onChange={(event) =>
                  setField(
                    "travel_paid_by",
                    event.target.value
                  )
                }
              />
            </Grid>

            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Travel Expense"
                value={form.travel_expense}
                onChange={(event) =>
                  setField(
                    "travel_expense",
                    event.target.value
                  )
                }
              />
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={form.hotel_provided}
                    onChange={(event) =>
                      setField(
                        "hotel_provided",
                        event.target.checked
                      )
                    }
                  />
                }
                label="Hotel provided"
              />
            </Grid>

            {form.hotel_provided && (
              <>
                <Grid item xs={12} sm={8}>
                  <TextField
                    fullWidth
                    label="Hotel Name"
                    value={form.hotel_name}
                    onChange={(event) =>
                      setField(
                        "hotel_name",
                        event.target.value
                      )
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Hotel Nights"
                    value={form.hotel_nights}
                    onChange={(event) =>
                      setField(
                        "hotel_nights",
                        event.target.value
                      )
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
                value={form.per_diem_daily}
                onChange={(event) =>
                  setField(
                    "per_diem_daily",
                    event.target.value
                  )
                }
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                label="Per Diem Days"
                value={form.per_diem_days}
                onChange={(event) =>
                  setField(
                    "per_diem_days",
                    event.target.value
                  )
                }
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                minRows={2}
                label="Additional Terms"
                value={form.additional_terms}
                onChange={(event) =>
                  setField(
                    "additional_terms",
                    event.target.value
                  )
                }
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                minRows={2}
                label="Message to Fighter / Manager"
                value={form.message}
                onChange={(event) =>
                  setField(
                    "message",
                    event.target.value
                  )
                }
              />
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={form.send}
                    onChange={(event) =>
                      setField(
                        "send",
                        event.target.checked
                      )
                    }
                  />
                }
                label={
                  form.send
                    ? "Send immediately"
                    : "Save as draft"
                }
              />
            </Grid>
          </Grid>
        </DialogContent>

        <DialogActions>
          <Button
            onClick={() => setFormOpen(false)}
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            disabled={working}
            onClick={createOffer}
          >
            {form.send
              ? "Send Fight Offer"
              : "Save Draft"}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
