import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";

import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import BloodtypeRoundedIcon from "@mui/icons-material/BloodtypeRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";

const API =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const authHeaders = (extra = {}) => ({
  Authorization: `Bearer ${localStorage.getItem("token")}`,
  ...extra,
});

const REQUEST_A_TEST_URL =
  "https://requestatest.com/combative";

const statusLabels = {
  not_started: "Not Started",
  in_progress: "In Progress",
  submitted: "Submitted",
  complete: "Complete",
  needs_attention: "Needs Attention",
};

function statusColor(status) {
  if (status === "complete") return "success";
  if (status === "needs_attention") return "error";
  if (status === "submitted") return "info";
  if (status === "in_progress") return "warning";
  return "default";
}

function fighterLocation(fighter) {
  return [
    fighter?.city,
    fighter?.state,
    fighter?.country,
  ]
    .filter(Boolean)
    .join(", ");
}

export default function EventWorkspace({
  eventId,
  onBack,
}) {
  const [data, setData] = useState(null);
  const [tab, setTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  async function load() {
    setLoading(true);

    try {
      const response = await fetch(
        `${API}/api/boxing/events/${eventId}/workspace`,
        {
          headers: authHeaders(),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not load event workspace"
        );
      }

      setData(body);
    } catch (error) {
      setMessage(
        error.message ||
          "Could not load event workspace"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [eventId]);

  async function updateChecklist(item, changes) {
    const response = await fetch(
      `${API}/api/boxing/events/${eventId}/checklist/${item.id}`,
      {
        method: "PATCH",
        headers: authHeaders({
          "Content-Type": "application/json",
        }),
        body: JSON.stringify(changes),
      }
    );

    const body = await response.json();

    if (!response.ok) {
      setMessage(
        body.detail || "Could not update checklist"
      );
      return;
    }

    setData((old) => ({
      ...old,
      checklist: old.checklist.map((row) =>
        row.id === item.id
          ? { ...row, ...body }
          : row
      ),
    }));
  }

  const promoterItems = useMemo(
    () =>
      (data?.checklist || []).filter(
        (x) => x.section === "promoter"
      ),
    [data]
  );

  const matchmakerItems = useMemo(
    () =>
      (data?.checklist || []).filter(
        (x) => x.section === "matchmaker"
      ),
    [data]
  );

  const completed = useMemo(
    () =>
      (data?.checklist || []).filter(
        (x) => x.status === "complete"
      ).length,
    [data]
  );

  const bloodworkVerified = useMemo(
    () =>
      (data?.fighters || []).filter(
        (x) => x.bloodwork_status === "verified"
      ).length,
    [data]
  );

  if (loading) {
    return (
      <Box sx={{ p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!data) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          {message || "Event could not be loaded."}
        </Alert>

        <Button
          sx={{ mt: 2 }}
          onClick={onBack}
        >
          Back
        </Button>
      </Box>
    );
  }

  const event = data.event;
  const bouts = data.bouts || [];
  const fighters = data.fighters || [];
  const totalChecklist =
    data.checklist?.length || 0;

  function ChecklistSection({ items }) {
    return (
      <Stack spacing={1.5}>
        {items.map((item) => (
          <Card key={item.id}>
            <CardContent>
              <Stack spacing={1.5}>
                <Stack
                  direction={{
                    xs: "column",
                    md: "row",
                  }}
                  spacing={1}
                  justifyContent="space-between"
                >
                  <Typography fontWeight={850}>
                    {item.label}
                  </Typography>

                  <Chip
                    size="small"
                    label={
                      statusLabels[item.status] ||
                      item.status
                    }
                    color={statusColor(item.status)}
                  />
                </Stack>

                <Grid container spacing={1.5}>
                  <Grid item xs={12} md={3}>
                    <Select
                      fullWidth
                      size="small"
                      value={item.status}
                      onChange={(e) =>
                        updateChecklist(item, {
                          status: e.target.value,
                        })
                      }
                    >
                      <MenuItem value="not_started">
                        Not Started
                      </MenuItem>

                      <MenuItem value="in_progress">
                        In Progress
                      </MenuItem>

                      <MenuItem value="submitted">
                        Submitted
                      </MenuItem>

                      <MenuItem value="complete">
                        Complete
                      </MenuItem>

                      <MenuItem value="needs_attention">
                        Needs Attention
                      </MenuItem>
                    </Select>
                  </Grid>

                  <Grid item xs={12} md={3}>
                    <TextField
                      fullWidth
                      type="date"
                      label="Due Date"
                      InputLabelProps={{
                        shrink: true,
                      }}
                      value={item.due_date || ""}
                      onChange={(e) =>
                        updateChecklist(item, {
                          due_date: e.target.value,
                        })
                      }
                    />
                  </Grid>

                  <Grid item xs={12} md={3}>
                    <TextField
                      fullWidth
                      label="Assigned To"
                      value={item.assigned_to || ""}
                      onBlur={(e) =>
                        updateChecklist(item, {
                          assigned_to:
                            e.target.value,
                        })
                      }
                      onChange={(e) => {
                        const value =
                          e.target.value;

                        setData((old) => ({
                          ...old,
                          checklist:
                            old.checklist.map(
                              (row) =>
                                row.id === item.id
                                  ? {
                                      ...row,
                                      assigned_to:
                                        value,
                                    }
                                  : row
                            ),
                        }));
                      }}
                    />
                  </Grid>

                  <Grid item xs={12} md={3}>
                    <TextField
                      fullWidth
                      label="Notes"
                      value={item.notes || ""}
                      onBlur={(e) =>
                        updateChecklist(item, {
                          notes: e.target.value,
                        })
                      }
                      onChange={(e) => {
                        const value =
                          e.target.value;

                        setData((old) => ({
                          ...old,
                          checklist:
                            old.checklist.map(
                              (row) =>
                                row.id === item.id
                                  ? {
                                      ...row,
                                      notes: value,
                                    }
                                  : row
                            ),
                        }));
                      }}
                    />
                  </Grid>
                </Grid>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>
    );
  }

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <Stack spacing={2.5}>
        <Stack
          direction={{
            xs: "column",
            md: "row",
          }}
          spacing={2}
          justifyContent="space-between"
        >
          <Box>
            <Button
              startIcon={<ArrowBackRoundedIcon />}
              onClick={onBack}
              sx={{ mb: 1 }}
            >
              Back to Matchmaker
            </Button>

            <Typography
              variant="h4"
              fontWeight={950}
            >
              {event.name}
            </Typography>

            <Typography color="text.secondary">
              {event.event_date || "No date"}
              {event.venue
                ? ` • ${event.venue}`
                : ""}
            </Typography>

            {event.venue_address && (
              <Typography
                variant="body2"
                color="text.secondary"
              >
                {event.venue_address}
              </Typography>
            )}
          </Box>

          <Chip
            label={event.status || "planning"}
            sx={{
              alignSelf: {
                xs: "flex-start",
                md: "center",
              },
            }}
          />
        </Stack>

        {message && (
          <Alert
            severity="info"
            onClose={() => setMessage("")}
          >
            {message}
          </Alert>
        )}

        <Grid container spacing={2}>
          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">
                  Bouts
                </Typography>

                <Typography
                  variant="h4"
                  fontWeight={950}
                >
                  {bouts.length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">
                  Fighters
                </Typography>

                <Typography
                  variant="h4"
                  fontWeight={950}
                >
                  {fighters.length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">
                  Bloodwork
                </Typography>

                <Typography
                  variant="h4"
                  fontWeight={950}
                >
                  {bloodworkVerified}/{fighters.length}
                </Typography>

                <Typography variant="caption">
                  verified
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary">
                  Checklist
                </Typography>

                <Typography
                  variant="h4"
                  fontWeight={950}
                >
                  {completed}/{totalChecklist}
                </Typography>

                <Typography variant="caption">
                  complete
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Card>
          <Tabs
            value={tab}
            onChange={(_, value) =>
              setTab(value)
            }
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab label="Overview" />
            <Tab label="Fight Card" />
            <Tab label="Bout Sheets" />
            <Tab label="Promoter Checklist" />
            <Tab label="Matchmaker Checklist" />
            <Tab label="Bloodwork" />
            <Tab label="Fees" />
          </Tabs>
        </Card>

        {/* OVERVIEW */}
        {tab === 0 && (
          <Grid container spacing={2}>
            <Grid item xs={12} md={7}>
              <Card>
                <CardContent>
                  <Typography
                    variant="h6"
                    fontWeight={900}
                  >
                    Fight Card
                  </Typography>

                  <Divider sx={{ my: 1.5 }} />

                  {!bouts.length && (
                    <Typography color="text.secondary">
                      No bouts have been built for
                      this event yet.
                    </Typography>
                  )}

                  <Stack spacing={1}>
                    {bouts.map((bout, index) => (
                      <Box
                        key={bout.id}
                        sx={{
                          p: 1.5,
                          borderRadius: 2,
                          bgcolor: "#fafafa",
                        }}
                      >
                        <Typography
                          fontWeight={900}
                        >
                          Bout {index + 1}
                        </Typography>

                        <Typography>
                          {bout.red?.legal_name}
                          {" vs "}
                          {bout.blue?.legal_name}
                        </Typography>

                        <Typography
                          variant="caption"
                          color="text.secondary"
                        >
                          {bout.weight_agreed
                            ? `${bout.weight_agreed} lb`
                            : "Weight TBD"}
                          {" • "}
                          {bout.rounds} rounds
                          {" • "}
                          {bout.status}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={5}>
              <Card>
                <CardContent>
                  <Typography
                    variant="h6"
                    fontWeight={900}
                  >
                    Needs Attention
                  </Typography>

                  <Divider sx={{ my: 1.5 }} />

                  <Stack spacing={1}>
                    {fighters
                      .filter(
                        (fighter) =>
                          fighter.bloodwork_status !==
                          "verified"
                      )
                      .map((fighter) => (
                        <Alert
                          severity="warning"
                          key={fighter.id}
                        >
                          {fighter.legal_name}: bloodwork{" "}
                          {fighter.bloodwork_status ||
                            "missing"}
                        </Alert>
                      ))}

                    {data.checklist
                      .filter(
                        (item) =>
                          item.status ===
                          "needs_attention"
                      )
                      .map((item) => (
                        <Alert
                          severity="error"
                          key={item.id}
                        >
                          {item.label}
                        </Alert>
                      ))}

                    {!fighters.some(
                      (f) =>
                        f.bloodwork_status !==
                        "verified"
                    ) &&
                      !data.checklist.some(
                        (x) =>
                          x.status ===
                          "needs_attention"
                      ) && (
                        <Alert severity="success">
                          No current attention flags.
                        </Alert>
                      )}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* FIGHT CARD */}
        {tab === 1 && (
          <Stack spacing={2}>
            {bouts.map((bout, index) => (
              <Card key={bout.id}>
                <CardContent>
                  <Grid
                    container
                    spacing={2}
                    alignItems="center"
                  >
                    <Grid item xs={12} md={2}>
                      <Typography
                        variant="h6"
                        fontWeight={950}
                      >
                        Bout {index + 1}
                      </Typography>

                      <Chip
                        size="small"
                        label={bout.status}
                      />
                    </Grid>

                    <Grid item xs={12} md={4}>
                      <Typography
                        fontWeight={950}
                      >
                        RED:{" "}
                        {bout.red?.legal_name}
                      </Typography>

                      <Typography variant="body2">
                        {bout.red?.pro_record ||
                          "Record N/A"}
                      </Typography>

                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        {fighterLocation(
                          bout.red
                        )}
                      </Typography>
                    </Grid>

                    <Grid item xs={12} md={4}>
                      <Typography
                        fontWeight={950}
                      >
                        BLUE:{" "}
                        {bout.blue?.legal_name}
                      </Typography>

                      <Typography variant="body2">
                        {bout.blue?.pro_record ||
                          "Record N/A"}
                      </Typography>

                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        {fighterLocation(
                          bout.blue
                        )}
                      </Typography>
                    </Grid>

                    <Grid item xs={12} md={2}>
                      <Typography fontWeight={850}>
                        {bout.weight_agreed
                          ? `${bout.weight_agreed} lb`
                          : "TBD"}
                      </Typography>

                      <Typography variant="body2">
                        {bout.rounds} rounds
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            ))}

            {!bouts.length && (
              <Alert severity="info">
                Build bouts in Matchmaker and assign
                them to this event.
              </Alert>
            )}
          </Stack>
        )}

        {/* BOUT SHEETS */}
        {tab === 2 && (
          <Stack spacing={2}>
            {bouts.map((bout, index) => (
              <Card key={bout.id}>
                <CardContent>
                  <Typography
                    variant="h5"
                    fontWeight={950}
                  >
                    Bout Sheet #{index + 1}
                  </Typography>

                  <Divider sx={{ my: 2 }} />

                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Typography
                        color="error"
                        fontWeight={900}
                      >
                        RED CORNER
                      </Typography>

                      <Typography
                        variant="h6"
                        fontWeight={950}
                      >
                        {bout.red?.legal_name}
                      </Typography>

                      <Typography>
                        {bout.red?.pro_record ||
                          "Record N/A"}
                      </Typography>

                      <Typography>
                        BoxRec #
                        {bout.red?.boxrec_id || "—"}
                      </Typography>

                      <Typography>
                        Phone:{" "}
                        {bout.red?.phone || "—"}
                      </Typography>

                      <Typography>
                        Email:{" "}
                        {bout.red?.email || "—"}
                      </Typography>

                      <Typography>
                        Manager:{" "}
                        {bout.red?.manager_name ||
                          "—"}
                      </Typography>
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <Typography
                        fontWeight={900}
                      >
                        BLUE CORNER
                      </Typography>

                      <Typography
                        variant="h6"
                        fontWeight={950}
                      >
                        {bout.blue?.legal_name}
                      </Typography>

                      <Typography>
                        {bout.blue?.pro_record ||
                          "Record N/A"}
                      </Typography>

                      <Typography>
                        BoxRec #
                        {bout.blue?.boxrec_id ||
                          "—"}
                      </Typography>

                      <Typography>
                        Phone:{" "}
                        {bout.blue?.phone || "—"}
                      </Typography>

                      <Typography>
                        Email:{" "}
                        {bout.blue?.email || "—"}
                      </Typography>

                      <Typography>
                        Manager:{" "}
                        {bout.blue?.manager_name ||
                          "—"}
                      </Typography>
                    </Grid>
                  </Grid>

                  <Divider sx={{ my: 2 }} />

                  <Grid container spacing={2}>
                    <Grid item xs={6} md={3}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        WEIGHT
                      </Typography>

                      <Typography
                        fontWeight={900}
                      >
                        {bout.weight_agreed
                          ? `${bout.weight_agreed} lb`
                          : "TBD"}
                      </Typography>
                    </Grid>

                    <Grid item xs={6} md={3}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        ROUNDS
                      </Typography>

                      <Typography
                        fontWeight={900}
                      >
                        {bout.rounds}
                      </Typography>
                    </Grid>

                    <Grid item xs={6} md={3}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        RED PURSE
                      </Typography>

                      <Typography
                        fontWeight={900}
                      >
                        ${Number(
                          bout.red_purse || 0
                        ).toFixed(2)}
                      </Typography>
                    </Grid>

                    <Grid item xs={6} md={3}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        BLUE PURSE
                      </Typography>

                      <Typography
                        fontWeight={900}
                      >
                        ${Number(
                          bout.blue_purse || 0
                        ).toFixed(2)}
                      </Typography>
                    </Grid>
                  </Grid>

                  {bout.notes && (
                    <>
                      <Divider sx={{ my: 2 }} />

                      <Typography
                        fontWeight={850}
                      >
                        Notes
                      </Typography>

                      <Typography>
                        {bout.notes}
                      </Typography>
                    </>
                  )}
                </CardContent>
              </Card>
            ))}
          </Stack>
        )}

        {/* PROMOTER */}
        {tab === 3 && (
          <Box>
            <Typography
              variant="h5"
              fontWeight={950}
              sx={{ mb: 0.5 }}
            >
              Promoter Responsibilities
            </Typography>

            <Typography
              color="text.secondary"
              sx={{ mb: 2 }}
            >
              Track every Commission and event
              operations requirement.
            </Typography>

            <ChecklistSection
              items={promoterItems}
            />
          </Box>
        )}

        {/* MATCHMAKER */}
        {tab === 4 && (
          <Box>
            <Typography
              variant="h5"
              fontWeight={950}
              sx={{ mb: 0.5 }}
            >
              Matchmaker Responsibilities
            </Typography>

            <Typography
              color="text.secondary"
              sx={{ mb: 2 }}
            >
              Bout submission, contracts, bloodwork
              and special fighter requirements.
            </Typography>

            <ChecklistSection
              items={matchmakerItems}
            />
          </Box>
        )}

        {/* BLOODWORK */}
        {tab === 5 && (
          <Stack spacing={2}>
            <Stack
              direction={{
                xs: "column",
                sm: "row",
              }}
              justifyContent="space-between"
              spacing={1}
            >
              <Box>
                <Typography
                  variant="h5"
                  fontWeight={950}
                >
                  Fighter Bloodwork
                </Typography>

                <Typography color="text.secondary">
                  Track readiness for every fighter
                  on this card.
                </Typography>
              </Box>

              <Button
                variant="outlined"
                startIcon={
                  <BloodtypeRoundedIcon />
                }
                onClick={() =>
                  window.open(
                    REQUEST_A_TEST_URL,
                    "_blank",
                    "noopener,noreferrer"
                  )
                }
              >
                Request A Test
              </Button>
            </Stack>

            {fighters.map((fighter) => {
              const verified =
                fighter.bloodwork_status ===
                "verified";

              return (
                <Card key={fighter.id}>
                  <CardContent>
                    <Grid
                      container
                      spacing={2}
                      alignItems="center"
                    >
                      <Grid item xs={12} md={4}>
                        <Typography
                          variant="h6"
                          fontWeight={950}
                        >
                          {fighter.legal_name}
                        </Typography>

                        <Typography
                          variant="body2"
                          color="text.secondary"
                        >
                          {fighter.pro_record ||
                            "Record N/A"}
                          {" • "}
                          {fighter.fight_weight
                            ? `${fighter.fight_weight} lb`
                            : "Weight N/A"}
                        </Typography>
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <Chip
                          icon={
                            verified ? (
                              <CheckCircleRoundedIcon />
                            ) : undefined
                          }
                          label={
                            verified
                              ? "Verified"
                              : fighter.bloodwork_status ||
                                "Missing"
                          }
                          color={
                            verified
                              ? "success"
                              : "warning"
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                        >
                          EXPIRES
                        </Typography>

                        <Typography>
                          {fighter.bloodwork_expires ||
                            "—"}
                        </Typography>
                      </Grid>

                      <Grid item xs={12} md={2}>
                        <Button
                          fullWidth
                          variant="outlined"
                          onClick={() =>
                            window.open(
                              REQUEST_A_TEST_URL,
                              "_blank",
                              "noopener,noreferrer"
                            )
                          }
                        >
                          Request
                        </Button>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              );
            })}

            {!fighters.length && (
              <Alert severity="info">
                Fighters will appear here after bouts
                are assigned to this event.
              </Alert>
            )}
          </Stack>
        )}

        {/* FEES */}
        {tab === 6 && (
          <Stack spacing={2}>
            <Typography
              variant="h5"
              fontWeight={950}
            >
              Estimated Fees & Assessments
            </Typography>

            <Alert severity="info">
              These figures are based on the promoter /
              matchmaker checklist supplied for this
              workspace. Confirm final amounts with the
              Commission for each event.
            </Alert>

            {(data.fees || []).map(
              (fee) => (
                <Card key={fee.name}>
                  <CardContent>
                    <Stack
                      direction={{
                        xs: "column",
                        sm: "row",
                      }}
                      justifyContent="space-between"
                      spacing={1}
                    >
                      <Typography
                        fontWeight={900}
                      >
                        {fee.name}
                      </Typography>

                      <Typography>
                        {fee.amount}
                      </Typography>
                    </Stack>
                  </CardContent>
                </Card>
              )
            )}
          </Stack>
        )}
      </Stack>
    </Box>
  );
}
