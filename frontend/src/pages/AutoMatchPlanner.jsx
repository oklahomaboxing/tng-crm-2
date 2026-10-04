import React, { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
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
import SendRoundedIcon from "@mui/icons-material/SendRounded";

const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const authHeaders = (extra = {}) => ({
  Authorization: `Bearer ${localStorage.getItem("token")}`,
  ...extra,
});

function fighterName(fighter) {
  return (
    fighter?.legal_name ||
    fighter?.name ||
    fighter?.fighter_name ||
    `Fighter #${fighter?.id || ""}`
  );
}

export default function AutoMatchPlanner({
  events = [],
}) {
  const [eventId, setEventId] = useState("");
  const [desiredBouts, setDesiredBouts] = useState(6);
  const [maxGap, setMaxGap] = useState(8);
  const [allowRematches, setAllowRematches] = useState(false);
  const [includeMale, setIncludeMale] = useState(true);
  const [includeFemale, setIncludeFemale] = useState(true);
  const [result, setResult] = useState(null);
  const [working, setWorking] = useState(false);
  const [sent, setSent] = useState({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

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

    const data = await response
      .json()
      .catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail ||
        data.message ||
        "Request failed"
      );
    }

    return data;
  }

  async function generate() {
    if (!eventId) {
      setError("Choose an event.");
      return;
    }

    setWorking(true);
    setError("");
    setMessage("");
    setSent({});

    try {
      const data = await request(
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

      setResult(data);

      setMessage(
        `${data.proposals?.length || 0} proposed bouts generated.`
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setWorking(false);
    }
  }

  async function sendOffer(proposal) {
    const key =
      `${proposal.red_fighter_id}-${proposal.blue_fighter_id}`;

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
            event_id:
              Number(eventId),
            fighter_id:
              proposal.red_fighter_id,
            opponent_id:
              proposal.blue_fighter_id,
            proposed_weight:
              proposal.proposed_weight,
            rounds:
              proposal.recommended_rounds,
            bout_type: "pro",
            proposed_purse: 0,
            ticket_commission_percent: 0,
            match_score:
              proposal.match_score,
            message:
              `TNG Auto-Match recommendation (${proposal.match_score}% match).`,
            send: true,
          }),
        }
      );

      setSent((current) => ({
        ...current,
        [key]:
          offer.id || true,
      }));

      setMessage(
        `Fight offer #${offer.id} sent.`
      );
    } catch (err) {
      setError(err.message);
    }
  }

  return (
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
          direction="row"
          spacing={1}
          alignItems="center"
        >
          <AutoAwesomeRoundedIcon
            color="error"
          />

          <Typography
            variant="h5"
            fontWeight={950}
          >
            2027 Auto-Match
          </Typography>
        </Stack>

        <Typography
          color="text.secondary"
          sx={{ mt: 0.5 }}
        >
          Generate the strongest proposed fight card from available fighters.
        </Typography>

        <Divider sx={{ my: 2 }} />

        {error && (
          <Alert
            severity="error"
            sx={{ mb: 2 }}
          >
            {error}
          </Alert>
        )}

        {message && (
          <Alert
            severity="success"
            sx={{ mb: 2 }}
          >
            {message}
          </Alert>
        )}

        <Grid container spacing={2}>
          <Grid item xs={12} md={5}>
            <TextField
              select
              fullWidth
              label="Event"
              value={eventId}
              onChange={(event) =>
                setEventId(
                  event.target.value
                )
              }
            >
              {events.map((event) => (
                <MenuItem
                  key={event.id}
                  value={event.id}
                >
                  {event.name ||
                    `Event #${event.id}`}
                  {event.event_date
                    ? ` ? ${event.event_date}`
                    : ""}
                </MenuItem>
              ))}
            </TextField>
          </Grid>

          <Grid item xs={6} md={2}>
            <TextField
              fullWidth
              type="number"
              label="Target Bouts"
              value={desiredBouts}
              onChange={(event) =>
                setDesiredBouts(
                  event.target.value
                )
              }
            />
          </Grid>

          <Grid item xs={6} md={2}>
            <TextField
              fullWidth
              type="number"
              label="Max Weight Gap"
              value={maxGap}
              onChange={(event) =>
                setMaxGap(
                  event.target.value
                )
              }
            />
          </Grid>

          <Grid
            item
            xs={12}
            md={3}
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
                    checked={includeMale}
                    onChange={(event) =>
                      setIncludeMale(
                        event.target.checked
                      )
                    }
                  />
                }
                label="Male"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={includeFemale}
                    onChange={(event) =>
                      setIncludeFemale(
                        event.target.checked
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
                  onChange={(event) =>
                    setAllowRematches(
                      event.target.checked
                    )
                  }
                />
              }
              label="Allow Rematches"
              />
            </Stack>
          </Grid>
        </Grid>

        <Button
          variant="contained"
          color="error"
          size="large"
          startIcon={
            <AutoAwesomeRoundedIcon />
          }
          onClick={generate}
          disabled={
            working ||
            !eventId ||
            (!includeMale && !includeFemale)
          }
          sx={{
            mt: 2,
            fontWeight: 900,
            px: 4,
            py: 1.4,
          }}
        >
          {working
            ? "Generating..."
            : "AUTO-GENERATE MATCHES"}
        </Button>

        {result && (
          <>
            <Divider sx={{ my: 3 }} />

            <Stack
              direction="row"
              spacing={1}
              useFlexGap
              flexWrap="wrap"
              sx={{ mb: 2 }}
            >
              <Chip
                label={`${result.eligible_fighters || 0} Eligible Fighters`}
              />

              <Chip
                label={`${result.candidate_pairs || 0} Candidate Pairs`}
              />

              <Chip
                color="success"
                label={`${result.proposals?.length || 0} Proposed Bouts`}
              />
            </Stack>

            <Stack spacing={2}>
              {result.proposals?.map(
                (proposal) => {
                  const key =
                    `${proposal.red_fighter_id}-${proposal.blue_fighter_id}`;

                  return (
                    <Card
                      key={key}
                      variant="outlined"
                      sx={{
                        borderRadius: 3,
                      }}
                    >
                      <CardContent>
                        <Stack
                          direction={{
                            xs: "column",
                            md: "row",
                          }}
                          spacing={2}
                          justifyContent="space-between"
                        >
                          <Box>
                            <Stack
                              direction="row"
                              spacing={1}
                              useFlexGap
                              flexWrap="wrap"
                              sx={{ mb: 1 }}
                            >
                              <Chip
                                color={
                                  proposal.match_score >= 85
                                    ? "success"
                                    : proposal.match_score >= 70
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
                                label={`${proposal.weight_difference} lb Gap`}
                              />
                            </Stack>

                            <Typography
                              variant="h6"
                              fontWeight={950}
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
                              Record: {proposal.red_fighter?.pro_record || "0-0"}
                              {" vs "}
                              {proposal.blue_fighter?.pro_record || "0-0"}
                            </Typography>

                            <Typography
                              color="text.secondary"
                            >
                              {proposal.red_fighter?.sex === "female" ? "Female" : "Male"}
                              {" ? "}
                              {proposal.red_weight?.preferred} lb
                              {" vs "}
                              {proposal.blue_weight?.preferred} lb
                              {" ? "}
                              {proposal.recommended_rounds} rounds
                            </Typography>
                          </Box>

                          {sent[key] ? (
                            <Chip
                              color="success"
                              label={`Offer #${sent[key]} Sent`}
                            />
                          ) : (
                            <Button
                              variant="contained"
                              startIcon={
                                <SendRoundedIcon />
                              }
                              onClick={() =>
                                sendOffer(
                                  proposal
                                )
                              }
                            >
                              Send Offer
                            </Button>
                          )}
                        </Stack>
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
  );
}
