import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  Divider,
  FormControlLabel,
  Grid,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import AutoAwesomeRoundedIcon from "@mui/icons-material/AutoAwesomeRounded";
import AddRoundedIcon from "@mui/icons-material/AddRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import SendRoundedIcon from "@mui/icons-material/SendRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";

const API = (
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

const authHeaders = (extra = {}) => ({
  Authorization: `Bearer ${localStorage.getItem("token")}`,
  ...extra,
});

function fighterName(fighter) {
  return (
    fighter?.legal_name ||
    fighter?.name ||
    fighter?.fighter_name ||
    [fighter?.first_name, fighter?.last_name]
      .filter(Boolean)
      .join(" ") ||
    `Fighter #${fighter?.id || ""}`
  );
}

function fighterRecord(fighter) {
  return (
    fighter?.pro_record ||
    fighter?.record ||
    fighter?.boxing_record ||
    "0-0"
  );
}

function money(value) {
  return `$${Number(value || 0).toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
}

function statusColor(status) {
  const value = String(status || "").toLowerCase();

  if (value === "accepted") return "success";

  if (
    value === "sent" ||
    value === "viewed"
  ) {
    return "info";
  }

  if (value === "countered") return "warning";

  if (
    value === "declined" ||
    value === "withdrawn"
  ) {
    return "error";
  }

  return "default";
}

const blankManualOffer = {
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
};

export default function EventFightCardBuilder({
  eventId,
  event,
  bouts = [],
  onRefresh,
}) {
  const [fighters, setFighters] = useState([]);
  const [offers, setOffers] = useState([]);

  const [loading, setLoading] = useState(false);
  const [working, setWorking] = useState(false);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [autoOpen, setAutoOpen] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);

  const [desiredBouts, setDesiredBouts] = useState(
    Math.max(1, 8 - bouts.length)
  );

  const [maxGap, setMaxGap] = useState(8);
  const [allowRematches, setAllowRematches] =
    useState(false);

  const [includeMale, setIncludeMale] =
    useState(true);

  const [includeFemale, setIncludeFemale] =
    useState(true);

  const [autoResult, setAutoResult] =
    useState(null);

  const [proposalTerms, setProposalTerms] =
    useState({});

  const [manual, setManual] =
    useState(blankManualOffer);

  async function request(path, options = {}) {
    const response = await fetch(
      `${API}${path}`,
      {
        ...options,
        headers: authHeaders(
          options.headers || {}
        ),
      }
    );

    const body = await response
      .json()
      .catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        body.detail ||
        body.message ||
        "Request failed"
      );
    }

    return body;
  }

  async function load() {
    setLoading(true);
    setError("");

    try {
      const [fighterData, offerData] =
        await Promise.all([
          request("/api/boxing/fighters"),
          request("/api/boxing/offers"),
        ]);

      setFighters(
        Array.isArray(fighterData)
          ? fighterData
          : fighterData?.fighters || []
      );

      setOffers(
        (Array.isArray(offerData)
          ? offerData
          : []
        ).filter(
          (offer) =>
            Number(offer.event_id) ===
            Number(eventId)
        )
      );
    } catch (err) {
      setError(
        err.message ||
        "Could not load Fight Card Builder."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [eventId]);

  useEffect(() => {
    setDesiredBouts(
      Math.max(1, 8 - bouts.length)
    );
  }, [bouts.length]);

  const activeBouts = useMemo(
    () =>
      bouts.filter(
        (bout) =>
          bout.status !== "cancelled" &&
          bout.status !== "void"
      ),
    [bouts]
  );

  const activeOffers = useMemo(
    () =>
      offers.filter((offer) =>
        [
          "draft",
          "sent",
          "viewed",
          "countered",
          "accepted",
        ].includes(
          String(offer.status || "").toLowerCase()
        )
      ),
    [offers]
  );

  const pendingOffers = activeOffers.filter(
    (offer) =>
      !offer.bout_id &&
      !offer.contract_id
  );

  const acceptedReady = pendingOffers.filter(
    (offer) =>
      offer.status === "accepted"
  );

  const countersWaiting = activeOffers.filter(
    (offer) =>
      offer.parent_offer_id &&
      offer.recipient_type === "matchmaker" &&
      ["sent", "viewed"].includes(
        offer.status
      )
  );

  const fighterMap = useMemo(() => {
    const map = {};

    fighters.forEach((fighter) => {
      map[fighter.id] = fighter;
    });

    return map;
  }, [fighters]);

  function proposalKey(proposal) {
    return (
      `${proposal.red_fighter_id}-` +
      `${proposal.blue_fighter_id}`
    );
  }

  function termsFor(proposal) {
    const key = proposalKey(proposal);

    return (
      proposalTerms[key] || {
        purse: "",
        ticket_commission_percent: "",
        rounds:
          proposal.recommended_rounds || 4,
        weight:
          proposal.proposed_weight || "",
      }
    );
  }

  function updateProposal(
    proposal,
    field,
    value
  ) {
    const key = proposalKey(proposal);

    setProposalTerms((current) => ({
      ...current,
      [key]: {
        ...termsFor(proposal),
        ...current[key],
        [field]: value,
      },
    }));
  }

  async function generateMatches() {
    setWorking(true);
    setError("");
    setMessage("");

    try {
      const result = await request(
        `/api/boxing/events/${eventId}/auto-match-proposals`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            desired_bouts:
              Number(desiredBouts),
            max_weight_difference:
              Number(maxGap),
            allow_rematches:
              allowRematches,
            include_male:
              includeMale,
            include_female:
              includeFemale,
          }),
        }
      );

      setAutoResult(result);

      setMessage(
        `${result.proposals?.length || 0} proposed matchup${
          result.proposals?.length === 1
            ? ""
            : "s"
        } generated for ${event?.name || "this event"}.`
      );
    } catch (err) {
      setError(
        err.message ||
        "Could not generate matches."
      );
    } finally {
      setWorking(false);
    }
  }

  async function sendAutoOffer(proposal) {
    const terms = termsFor(proposal);

    setWorking(true);
    setError("");
    setMessage("");

    try {
      const offer = await request(
        "/api/boxing/offers",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            event_id: Number(eventId),
            fighter_id:
              proposal.red_fighter_id,
            opponent_id:
              proposal.blue_fighter_id,
            proposed_weight:
              Number(
                terms.weight ||
                proposal.proposed_weight ||
                0
              ) || null,
            rounds:
              Number(terms.rounds || 4),
            bout_type: "pro",
            proposed_purse:
              Number(terms.purse || 0),
            ticket_commission_percent:
              Number(
                terms.ticket_commission_percent ||
                0
              ),
            match_score:
              proposal.match_score,
            message:
              `Fight offer for ${
                event?.name || "event"
              }. TNGOS match score: ${
                proposal.match_score
              }%.`,
            send: true,
          }),
        }
      );

      setMessage(
        `Offer #${offer.id} sent to ${fighterName(
          proposal.red_fighter
        )}.`
      );

      await load();
    } catch (err) {
      setError(
        err.message ||
        "Could not send fight offer."
      );
    } finally {
      setWorking(false);
    }
  }

  async function createManualOffer() {
    if (
      !manual.fighter_id ||
      !manual.opponent_id
    ) {
      setError(
        "Choose both fighters."
      );
      return;
    }

    if (
      Number(manual.fighter_id) ===
      Number(manual.opponent_id)
    ) {
      setError(
        "Choose two different fighters."
      );
      return;
    }

    setWorking(true);
    setError("");
    setMessage("");

    try {
      const offer = await request(
        "/api/boxing/offers",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            ...manual,
            event_id: Number(eventId),
            fighter_id:
              Number(manual.fighter_id),
            opponent_id:
              Number(manual.opponent_id),
            proposed_weight:
              manual.proposed_weight === ""
                ? null
                : Number(
                    manual.proposed_weight
                  ),
            rounds:
              Number(manual.rounds || 4),
            proposed_purse:
              Number(
                manual.proposed_purse || 0
              ),
            ticket_commission_percent:
              Number(
                manual.ticket_commission_percent ||
                0
              ),
            travel_expense:
              Number(
                manual.travel_expense || 0
              ),
            hotel_nights:
              Number(
                manual.hotel_nights || 0
              ),
            per_diem_daily:
              Number(
                manual.per_diem_daily || 0
              ),
            per_diem_days:
              Number(
                manual.per_diem_days || 0
              ),
            send: true,
          }),
        }
      );

      setMessage(
        `Fight offer #${offer.id} sent.`
      );

      setManual(blankManualOffer);
      setManualOpen(false);

      await load();
    } catch (err) {
      setError(
        err.message ||
        "Could not create fight offer."
      );
    } finally {
      setWorking(false);
    }
  }

  async function offerAction(
    offer,
    action
  ) {
    setWorking(true);
    setError("");
    setMessage("");

    try {
      const body =
        await request(
          `/api/boxing/offers/${offer.id}/${action}`,
          {
            method: "POST",
          }
        );

      setMessage(
        body.message ||
        `Offer #${offer.id} updated.`
      );

      await load();

      if (onRefresh) {
        await onRefresh();
      }
    } catch (err) {
      setError(
        err.message ||
        "Could not update offer."
      );
    } finally {
      setWorking(false);
    }
  }

  async function convertOffer(offer) {
    if (
      !window.confirm(
        `Create the official bout and contract from offer #${offer.id}?`
      )
    ) {
      return;
    }

    setWorking(true);
    setError("");
    setMessage("");

    try {
      const body =
        await request(
          `/api/boxing/offers/${offer.id}/convert`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              corner: "red",
            }),
          }
        );

      setMessage(
        `Bout #${
          body.bout?.id ||
          offer.bout_id ||
          ""
        } created${
          body.contract?.id
            ? ` with Contract #${body.contract.id}`
            : ""
        }.`
      );

      await load();

      if (onRefresh) {
        await onRefresh();
      }
    } catch (err) {
      setError(
        err.message ||
        "Could not convert accepted offer."
      );
    } finally {
      setWorking(false);
    }
  }

  return (
    <Stack spacing={2} sx={{ mb: 3 }}>
      <Card
        sx={{
          borderRadius: 3,
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        <CardContent>
          <Stack
            direction={{
              xs: "column",
              md: "row",
            }}
            justifyContent="space-between"
            spacing={2}
          >
            <Box>
              <Typography
                variant="overline"
                color="error"
                fontWeight={950}
                letterSpacing={1.3}
              >
                FIGHT CARD BUILDER
              </Typography>

              <Typography
                variant="h5"
                fontWeight={950}
              >
                {event?.name ||
                  "Current Event"}
              </Typography>

              <Typography
                color="text.secondary"
                sx={{ mt: 0.5 }}
              >
                Match fighters, send offers and
                turn accepted deals into official
                bouts without leaving this event.
              </Typography>
            </Box>

            <Stack
              direction="row"
              spacing={1}
              useFlexGap
              flexWrap="wrap"
            >
              <Button
                variant="outlined"
                startIcon={
                  <RefreshRoundedIcon />
                }
                onClick={load}
                disabled={loading || working}
              >
                Refresh
              </Button>

              <Button
                variant="outlined"
                startIcon={<AddRoundedIcon />}
                onClick={() =>
                  setManualOpen(
                    (current) => !current
                  )
                }
              >
                Manual Match
              </Button>

              <Button
                variant="contained"
                color="error"
                startIcon={
                  <AutoAwesomeRoundedIcon />
                }
                onClick={() =>
                  setAutoOpen(
                    (current) => !current
                  )
                }
              >
                Auto-Match
              </Button>
            </Stack>
          </Stack>

          <Grid
            container
            spacing={1.5}
            sx={{ mt: 1 }}
          >
            <Grid item xs={6} md={3}>
              <Chip
                label={`${activeBouts.length} Official Bouts`}
                color={
                  activeBouts.length
                    ? "success"
                    : "default"
                }
                sx={{
                  width: "100%",
                  fontWeight: 900,
                }}
              />
            </Grid>

            <Grid item xs={6} md={3}>
              <Chip
                label={`${pendingOffers.length} Open Offers`}
                color={
                  pendingOffers.length
                    ? "info"
                    : "default"
                }
                sx={{
                  width: "100%",
                  fontWeight: 900,
                }}
              />
            </Grid>

            <Grid item xs={6} md={3}>
              <Chip
                label={`${acceptedReady.length} Ready to Convert`}
                color={
                  acceptedReady.length
                    ? "success"
                    : "default"
                }
                sx={{
                  width: "100%",
                  fontWeight: 900,
                }}
              />
            </Grid>

            <Grid item xs={6} md={3}>
              <Chip
                label={`${countersWaiting.length} Counters Waiting`}
                color={
                  countersWaiting.length
                    ? "warning"
                    : "default"
                }
                sx={{
                  width: "100%",
                  fontWeight: 900,
                }}
              />
            </Grid>
          </Grid>

          {error && (
            <Alert
              severity="error"
              onClose={() =>
                setError("")
              }
              sx={{ mt: 2 }}
            >
              {error}
            </Alert>
          )}

          {message && (
            <Alert
              severity="success"
              onClose={() =>
                setMessage("")
              }
              sx={{ mt: 2 }}
            >
              {message}
            </Alert>
          )}
        </CardContent>
      </Card>

      <Collapse in={autoOpen}>
        <Card variant="outlined">
          <CardContent>
            <Typography
              variant="h6"
              fontWeight={950}
            >
              Auto-Match This Event
            </Typography>

            <Typography
              color="text.secondary"
              sx={{ mb: 2 }}
            >
              TNGOS will only propose fighters
              who are eligible for this event.
            </Typography>

            <Grid container spacing={2}>
              <Grid
                item
                xs={6}
                md={2}
              >
                <TextField
                  fullWidth
                  type="number"
                  label="Bouts Needed"
                  value={desiredBouts}
                  onChange={(e) =>
                    setDesiredBouts(
                      e.target.value
                    )
                  }
                />
              </Grid>

              <Grid
                item
                xs={6}
                md={2}
              >
                <TextField
                  fullWidth
                  type="number"
                  label="Max Weight Gap"
                  value={maxGap}
                  onChange={(e) =>
                    setMaxGap(
                      e.target.value
                    )
                  }
                />
              </Grid>

              <Grid
                item
                xs={12}
                md={5}
              >
                <Stack
                  direction="row"
                  spacing={1}
                  useFlexGap
                  flexWrap="wrap"
                >
                  <FormControlLabel
                    control={
                      <Switch
                        checked={
                          includeMale
                        }
                        onChange={(e) =>
                          setIncludeMale(
                            e.target.checked
                          )
                        }
                      />
                    }
                    label="Male"
                  />

                  <FormControlLabel
                    control={
                      <Switch
                        checked={
                          includeFemale
                        }
                        onChange={(e) =>
                          setIncludeFemale(
                            e.target.checked
                          )
                        }
                      />
                    }
                    label="Female"
                  />

                  <FormControlLabel
                    control={
                      <Switch
                        checked={
                          allowRematches
                        }
                        onChange={(e) =>
                          setAllowRematches(
                            e.target.checked
                          )
                        }
                      />
                    }
                    label="Allow Rematches"
                  />
                </Stack>
              </Grid>

              <Grid
                item
                xs={12}
                md={3}
              >
                <Button
                  fullWidth
                  variant="contained"
                  color="error"
                  onClick={
                    generateMatches
                  }
                  disabled={
                    working ||
                    (!includeMale &&
                      !includeFemale)
                  }
                  sx={{
                    minHeight: 56,
                    fontWeight: 900,
                  }}
                >
                  Generate Matches
                </Button>
              </Grid>
            </Grid>

            {autoResult && (
              <>
                <Divider sx={{ my: 2 }} />

                <Stack
                  direction="row"
                  spacing={1}
                  useFlexGap
                  flexWrap="wrap"
                  sx={{ mb: 2 }}
                >
                  <Chip
                    label={`${
                      autoResult.eligible_fighters ||
                      0
                    } Eligible`}
                  />

                  <Chip
                    label={`${
                      autoResult.candidate_pairs ||
                      0
                    } Candidate Pairs`}
                  />

                  <Chip
                    color="success"
                    label={`${
                      autoResult.proposals
                        ?.length || 0
                    } Proposed`}
                  />
                </Stack>

                {!autoResult.proposals
                  ?.length && (
                  <Alert severity="warning">
                    No usable matchup was found.
                    Review the exclusions below.

                    {(autoResult.exclusions ||
                      []).map((row) => (
                      <Typography
                        key={`${row.fighter_id}-${row.reason}`}
                        variant="body2"
                        sx={{ mt: 0.5 }}
                      >
                        ?{" "}
                        {row.fighter_name ||
                          `Fighter #${row.fighter_id}`}
                        : {row.reason}
                      </Typography>
                    ))}
                  </Alert>
                )}

                <Stack
                  spacing={2}
                  sx={{ mt: 2 }}
                >
                  {(autoResult.proposals ||
                    []).map(
                    (proposal) => {
                      const terms =
                        termsFor(
                          proposal
                        );

                      return (
                        <Card
                          key={
                            proposalKey(
                              proposal
                            )
                          }
                          variant="outlined"
                        >
                          <CardContent>
                            <Stack
                              direction={{
                                xs: "column",
                                md: "row",
                              }}
                              justifyContent="space-between"
                              spacing={2}
                            >
                              <Box>
                                <Stack
                                  direction="row"
                                  spacing={1}
                                  useFlexGap
                                  flexWrap="wrap"
                                >
                                  <Chip
                                    color={
                                      proposal.match_score >=
                                      85
                                        ? "success"
                                        : proposal.match_score >=
                                          70
                                        ? "warning"
                                        : "default"
                                    }
                                    label={`${proposal.match_score}% Match`}
                                  />

                                  <Chip
                                    variant="outlined"
                                    label={`${proposal.proposed_weight} lb`}
                                  />

                                  <Chip
                                    variant="outlined"
                                    label={`${proposal.weight_difference} lb gap`}
                                  />
                                </Stack>

                                <Typography
                                  variant="h6"
                                  fontWeight={950}
                                  sx={{
                                    mt: 1,
                                  }}
                                >
                                  {fighterName(
                                    proposal.red_fighter
                                  )}
                                  {" vs "}
                                  {fighterName(
                                    proposal.blue_fighter
                                  )}
                                </Typography>

                                <Typography
                                  color="text.secondary"
                                >
                                  {fighterRecord(
                                    proposal.red_fighter
                                  )}
                                  {" vs "}
                                  {fighterRecord(
                                    proposal.blue_fighter
                                  )}
                                </Typography>
                              </Box>
                            </Stack>

                            <Grid
                              container
                              spacing={1.5}
                              sx={{ mt: 1 }}
                            >
                              <Grid
                                item
                                xs={6}
                                md={3}
                              >
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Weight"
                                  value={
                                    terms.weight
                                  }
                                  onChange={(e) =>
                                    updateProposal(
                                      proposal,
                                      "weight",
                                      e.target
                                        .value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid
                                item
                                xs={6}
                                md={2}
                              >
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Rounds"
                                  value={
                                    terms.rounds
                                  }
                                  onChange={(e) =>
                                    updateProposal(
                                      proposal,
                                      "rounds",
                                      e.target
                                        .value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid
                                item
                                xs={6}
                                md={3}
                              >
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Purse"
                                  value={
                                    terms.purse
                                  }
                                  onChange={(e) =>
                                    updateProposal(
                                      proposal,
                                      "purse",
                                      e.target
                                        .value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid
                                item
                                xs={6}
                                md={2}
                              >
                                <TextField
                                  fullWidth
                                  size="small"
                                  type="number"
                                  label="Ticket %"
                                  value={
                                    terms.ticket_commission_percent
                                  }
                                  onChange={(e) =>
                                    updateProposal(
                                      proposal,
                                      "ticket_commission_percent",
                                      e.target
                                        .value
                                    )
                                  }
                                />
                              </Grid>

                              <Grid
                                item
                                xs={12}
                                md={2}
                              >
                                <Button
                                  fullWidth
                                  variant="contained"
                                  startIcon={
                                    <SendRoundedIcon />
                                  }
                                  onClick={() =>
                                    sendAutoOffer(
                                      proposal
                                    )
                                  }
                                  disabled={
                                    working
                                  }
                                  sx={{
                                    height:
                                      "100%",
                                    minHeight:
                                      40,
                                  }}
                                >
                                  Send
                                </Button>
                              </Grid>
                            </Grid>
                          </CardContent>
                        </Card>
                      );
                    }
                  )}
                </Stack>
              </>
            )}
          </CardContent>
        </Card>
      </Collapse>

      <Collapse in={manualOpen}>
        <Card variant="outlined">
          <CardContent>
            <Typography
              variant="h6"
              fontWeight={950}
            >
              Manual Match + Offer
            </Typography>

            <Typography
              color="text.secondary"
              sx={{ mb: 2 }}
            >
              Build the deal here and send it
              without leaving {event?.name || "the event"}.
            </Typography>

            <Grid container spacing={2}>
              <Grid
                item
                xs={12}
                md={6}
              >
                <TextField
                  select
                  fullWidth
                  label="Fighter Receiving Offer"
                  value={
                    manual.fighter_id
                  }
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        fighter_id:
                          e.target.value,
                      })
                    )
                  }
                >
                  {fighters.map(
                    (fighter) => (
                      <MenuItem
                        key={
                          fighter.id
                        }
                        value={
                          fighter.id
                        }
                        disabled={
                          Number(
                            fighter.id
                          ) ===
                          Number(
                            manual.opponent_id
                          )
                        }
                      >
                        {fighterName(
                          fighter
                        )}{" "}
                        ({fighterRecord(
                          fighter
                        )})
                      </MenuItem>
                    )
                  )}
                </TextField>
              </Grid>

              <Grid
                item
                xs={12}
                md={6}
              >
                <TextField
                  select
                  fullWidth
                  label="Opponent"
                  value={
                    manual.opponent_id
                  }
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        opponent_id:
                          e.target.value,
                      })
                    )
                  }
                >
                  {fighters.map(
                    (fighter) => (
                      <MenuItem
                        key={
                          fighter.id
                        }
                        value={
                          fighter.id
                        }
                        disabled={
                          Number(
                            fighter.id
                          ) ===
                          Number(
                            manual.fighter_id
                          )
                        }
                      >
                        {fighterName(
                          fighter
                        )}{" "}
                        ({fighterRecord(
                          fighter
                        )})
                      </MenuItem>
                    )
                  )}
                </TextField>
              </Grid>

              <Grid
                item
                xs={6}
                md={2}
              >
                <TextField
                  fullWidth
                  type="number"
                  label="Weight"
                  value={
                    manual.proposed_weight
                  }
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        proposed_weight:
                          e.target.value,
                      })
                    )
                  }
                />
              </Grid>

              <Grid
                item
                xs={6}
                md={2}
              >
                <TextField
                  fullWidth
                  type="number"
                  label="Rounds"
                  value={manual.rounds}
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        rounds:
                          e.target.value,
                      })
                    )
                  }
                />
              </Grid>

              <Grid
                item
                xs={6}
                md={3}
              >
                <TextField
                  fullWidth
                  type="number"
                  label="Guaranteed Purse"
                  value={
                    manual.proposed_purse
                  }
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        proposed_purse:
                          e.target.value,
                      })
                    )
                  }
                />
              </Grid>

              <Grid
                item
                xs={6}
                md={2}
              >
                <TextField
                  fullWidth
                  type="number"
                  label="Ticket %"
                  value={
                    manual.ticket_commission_percent
                  }
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        ticket_commission_percent:
                          e.target.value,
                      })
                    )
                  }
                />
              </Grid>

              <Grid
                item
                xs={12}
                md={3}
              >
                <TextField
                  select
                  fullWidth
                  label="Bout Type"
                  value={
                    manual.bout_type
                  }
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        bout_type:
                          e.target.value,
                      })
                    )
                  }
                >
                  <MenuItem value="pro">
                    Pro
                  </MenuItem>

                  <MenuItem value="amateur">
                    Amateur
                  </MenuItem>
                </TextField>
              </Grid>

              <Grid
                item
                xs={12}
                md={4}
              >
                <TextField
                  fullWidth
                  label="Travel Type"
                  value={
                    manual.travel_type
                  }
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        travel_type:
                          e.target.value,
                      })
                    )
                  }
                />
              </Grid>

              <Grid
                item
                xs={12}
                md={4}
              >
                <TextField
                  fullWidth
                  label="Travel Paid By"
                  value={
                    manual.travel_paid_by
                  }
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        travel_paid_by:
                          e.target.value,
                      })
                    )
                  }
                />
              </Grid>

              <Grid
                item
                xs={12}
                md={4}
              >
                <TextField
                  fullWidth
                  type="number"
                  label="Travel Expense"
                  value={
                    manual.travel_expense
                  }
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        travel_expense:
                          e.target.value,
                      })
                    )
                  }
                />
              </Grid>

              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={
                        manual.hotel_provided
                      }
                      onChange={(e) =>
                        setManual(
                          (current) => ({
                            ...current,
                            hotel_provided:
                              e.target
                                .checked,
                          })
                        )
                      }
                    />
                  }
                  label="Hotel provided"
                />
              </Grid>

              {manual.hotel_provided && (
                <>
                  <Grid
                    item
                    xs={12}
                    md={8}
                  >
                    <TextField
                      fullWidth
                      label="Hotel Name"
                      value={
                        manual.hotel_name
                      }
                      onChange={(e) =>
                        setManual(
                          (current) => ({
                            ...current,
                            hotel_name:
                              e.target
                                .value,
                          })
                        )
                      }
                    />
                  </Grid>

                  <Grid
                    item
                    xs={12}
                    md={4}
                  >
                    <TextField
                      fullWidth
                      type="number"
                      label="Hotel Nights"
                      value={
                        manual.hotel_nights
                      }
                      onChange={(e) =>
                        setManual(
                          (current) => ({
                            ...current,
                            hotel_nights:
                              e.target
                                .value,
                          })
                        )
                      }
                    />
                  </Grid>
                </>
              )}

              <Grid
                item
                xs={6}
                md={3}
              >
                <TextField
                  fullWidth
                  type="number"
                  label="Per Diem / Day"
                  value={
                    manual.per_diem_daily
                  }
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        per_diem_daily:
                          e.target.value,
                      })
                    )
                  }
                />
              </Grid>

              <Grid
                item
                xs={6}
                md={3}
              >
                <TextField
                  fullWidth
                  type="number"
                  label="Per Diem Days"
                  value={
                    manual.per_diem_days
                  }
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        per_diem_days:
                          e.target.value,
                      })
                    )
                  }
                />
              </Grid>

              <Grid
                item
                xs={12}
                md={6}
              >
                <TextField
                  fullWidth
                  label="Message to Fighter / Manager"
                  value={
                    manual.message
                  }
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        message:
                          e.target.value,
                      })
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
                  value={
                    manual.additional_terms
                  }
                  onChange={(e) =>
                    setManual(
                      (current) => ({
                        ...current,
                        additional_terms:
                          e.target.value,
                      })
                    )
                  }
                />
              </Grid>

              <Grid item xs={12}>
                <Button
                  variant="contained"
                  color="error"
                  size="large"
                  startIcon={
                    <SendRoundedIcon />
                  }
                  onClick={
                    createManualOffer
                  }
                  disabled={working}
                  sx={{ fontWeight: 900 }}
                >
                  Send Fight Offer
                </Button>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Collapse>

      {!!activeOffers.length && (
        <Card>
          <CardContent>
            <Typography
              variant="h6"
              fontWeight={950}
            >
              Event Offers
            </Typography>

            <Typography
              color="text.secondary"
              sx={{ mb: 2 }}
            >
              Track negotiations here. Once an
              offer is accepted, turn it into
              the official bout immediately.
            </Typography>

            <Stack spacing={1.5}>
              {activeOffers.map(
                (offer) => {
                  const fighter =
                    fighterMap[
                      offer.fighter_id
                    ];

                  const opponent =
                    fighterMap[
                      offer.opponent_id
                    ];

                  const canConvert =
                    offer.status ===
                      "accepted" &&
                    !offer.bout_id &&
                    !offer.contract_id;

                  const canAcceptCounter =
                    offer.parent_offer_id &&
                    offer.recipient_type ===
                      "matchmaker" &&
                    ["sent", "viewed"].includes(
                      offer.status
                    );

                  return (
                    <Card
                      key={offer.id}
                      variant="outlined"
                    >
                      <CardContent>
                        <Stack
                          direction={{
                            xs: "column",
                            md: "row",
                          }}
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
                              <Typography
                                fontWeight={950}
                                variant="h6"
                              >
                                {fighterName(
                                  fighter
                                )}
                                {" vs "}
                                {fighterName(
                                  opponent
                                )}
                              </Typography>

                              <Chip
                                size="small"
                                label={
                                  offer.status ||
                                  "draft"
                                }
                                color={statusColor(
                                  offer.status
                                )}
                              />

                              <Chip
                                size="small"
                                variant="outlined"
                                label={`Offer #${offer.id}`}
                              />
                            </Stack>

                            <Typography
                              variant="body2"
                              color="text.secondary"
                              sx={{ mt: 0.5 }}
                            >
                              {offer.proposed_weight ||
                                "-"}{" "}
                              lb ?{" "}
                              {offer.rounds ||
                                "-"}{" "}
                              rounds ?{" "}
                              {money(
                                offer.proposed_purse
                              )}{" "}
                              purse ?{" "}
                              {Number(
                                offer.ticket_commission_percent ||
                                  0
                              )}
                              % tickets
                            </Typography>
                          </Box>

                          <Stack
                            direction={{
                              xs: "column",
                              sm: "row",
                            }}
                            spacing={1}
                          >
                            {canAcceptCounter && (
                              <Button
                                variant="outlined"
                                color="warning"
                                disabled={working}
                                onClick={() =>
                                  offerAction(
                                    offer,
                                    "accept-counter"
                                  )
                                }
                              >
                                Accept Counter
                              </Button>
                            )}

                            {canConvert && (
                              <Button
                                variant="contained"
                                color="success"
                                startIcon={
                                  <CheckCircleRoundedIcon />
                                }
                                disabled={working}
                                onClick={() =>
                                  convertOffer(
                                    offer
                                  )
                                }
                              >
                                Create Bout +
                                Contract
                              </Button>
                            )}

                            {(offer.bout_id ||
                              offer.contract_id) && (
                              <Chip
                                color="success"
                                label={
                                  offer.bout_id
                                    ? `Bout #${offer.bout_id}`
                                    : `Contract #${offer.contract_id}`
                                }
                              />
                            )}
                          </Stack>
                        </Stack>
                      </CardContent>
                    </Card>
                  );
                }
              )}
            </Stack>
          </CardContent>
        </Card>
      )}
    </Stack>
  );
}
