import React, { useMemo } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  LinearProgress,
  Stack,
  Typography,
} from "@mui/material";

function percent(done, total) {
  if (!total) return 0;
  return Math.round((done / total) * 100);
}

function isSigned(contract) {
  if (!contract) return false;

  const status = String(
    contract.status ||
    contract.docusign_status ||
    contract.adobe_status ||
    ""
  ).toLowerCase();

  return Boolean(
    contract.docusign_signed_at ||
    contract.adobe_signed_at ||
    contract.electronic_signature?.signed ||
    status === "signed" ||
    status === "completed"
  );
}

function collectContracts(bouts = []) {
  const rows = [];

  bouts.forEach((bout) => {
    if (bout.red_contract) rows.push(bout.red_contract);
    if (bout.blue_contract) rows.push(bout.blue_contract);

    if (Array.isArray(bout.contracts)) {
      rows.push(...bout.contracts);
    }
  });

  const seen = new Set();

  return rows.filter((row) => {
    if (!row) return false;

    const key =
      row.id ||
      row.contract_id ||
      `${row.fighter_id || ""}-${row.corner || ""}`;

    if (seen.has(key)) return false;

    seen.add(key);
    return true;
  });
}

export default function EventCommandCenter({
  data,
  setTab,
}) {
  const metrics = useMemo(() => {
    const event = data?.event || {};
    const bouts = (data?.bouts || []).filter(
      (bout) =>
        bout.status !== "cancelled" &&
        bout.status !== "void"
    );

    const fighters = data?.fighters || [];
    const checklist = data?.checklist || [];
    const fees = data?.fees || [];

    const contracts = collectContracts(bouts);

    const checklistDone = checklist.filter(
      (item) => item.status === "complete"
    ).length;

    const checklistAttention = checklist.filter(
      (item) => item.status === "needs_attention"
    );

    const bloodworkDone = fighters.filter(
      (fighter) =>
        String(fighter.bloodwork_status || "").toLowerCase() ===
        "verified"
    ).length;

    const bloodworkMissing = fighters.filter(
      (fighter) =>
        String(fighter.bloodwork_status || "").toLowerCase() !==
        "verified"
    );

    const paidFees = fees.filter(
      (fee) => Boolean(fee.paid)
    ).length;

    const unpaidFees = fees.filter(
      (fee) => !fee.paid
    );

    const signedContracts = contracts.filter(isSigned).length;

    const hasVenue = Boolean(
      String(event.venue || "").trim() &&
      String(event.venue_address || "").trim()
    );

    const cardScore =
      bouts.length > 0 ? 100 : 0;

    const venueScore =
      hasVenue ? 100 : 0;

    const bloodworkScore =
      fighters.length
        ? percent(bloodworkDone, fighters.length)
        : 0;

    const checklistScore =
      checklist.length
        ? percent(checklistDone, checklist.length)
        : 0;

    const feeScore =
      fees.length
        ? percent(paidFees, fees.length)
        : 100;

    const contractScore =
      contracts.length
        ? percent(signedContracts, contracts.length)
        : bouts.length
        ? 0
        : 100;

    const readiness = Math.round(
      venueScore * 0.10 +
      cardScore * 0.20 +
      contractScore * 0.25 +
      bloodworkScore * 0.20 +
      checklistScore * 0.20 +
      feeScore * 0.05
    );

    const actions = [];

    if (!hasVenue) {
      actions.push({
        severity: "warning",
        title: "Finish event venue",
        detail: "Venue name or address is missing.",
        button: "Set Venue",
        tab: 8,
      });
    }

    if (!bouts.length) {
      actions.push({
        severity: "error",
        title: "Build the fight card",
        detail: "No active bouts are assigned to this event.",
        button: "Build Fight Card",
        tab: 1,
      });
    }

    if (
      bouts.length &&
      contracts.length < bouts.length * 2
    ) {
      actions.push({
        severity: "warning",
        title: "Generate missing contracts",
        detail:
          `${contracts.length} of ${bouts.length * 2} fighter contracts are currently visible.`,
        button: "Contracts",
        tab: 2,
      });
    }

    if (
      contracts.length &&
      signedContracts < contracts.length
    ) {
      actions.push({
        severity: "warning",
        title: "Get contracts signed",
        detail:
          `${signedContracts} of ${contracts.length} contracts are signed.`,
        button: "Open Contracts",
        tab: 2,
      });
    }

    if (bloodworkMissing.length) {
      actions.push({
        severity: "warning",
        title: "Resolve fighter medicals",
        detail:
          `${bloodworkMissing.length} fighter${
            bloodworkMissing.length === 1 ? "" : "s"
          } still need verified bloodwork.`,
        button: "Bloodwork",
        tab: 5,
      });
    }

    if (checklistAttention.length) {
      actions.push({
        severity: "error",
        title: "Checklist needs attention",
        detail:
          `${checklistAttention.length} compliance item${
            checklistAttention.length === 1 ? "" : "s"
          } marked Needs Attention.`,
        button: "Promoter Checklist",
        tab: 3,
      });
    }

    if (
      checklist.length &&
      checklistDone < checklist.length &&
      !checklistAttention.length
    ) {
      actions.push({
        severity: "info",
        title: "Finish event checklist",
        detail:
          `${checklistDone} of ${checklist.length} checklist items complete.`,
        button: "Open Checklist",
        tab: 3,
      });
    }

    if (unpaidFees.length) {
      actions.push({
        severity: "info",
        title: "Outstanding event fees",
        detail:
          `${unpaidFees.length} fee${
            unpaidFees.length === 1 ? "" : "s"
          } still marked unpaid.`,
        button: "Event Fees",
        tab: 6,
      });
    }

    return {
      bouts,
      fighters,
      contracts,
      signedContracts,
      bloodworkDone,
      checklistDone,
      checklist,
      paidFees,
      fees,
      readiness,
      actions,
      hasVenue,
    };
  }, [data]);

  const stage = (label, complete, tab) => (
    <Button
      key={label}
      variant={complete ? "contained" : "outlined"}
      color={complete ? "success" : "inherit"}
      onClick={() => setTab(tab)}
      sx={{
        minWidth: 145,
        fontWeight: 900,
        py: 1.25,
      }}
    >
      {complete ? "? " : ""}
      {label}
    </Button>
  );

  const contractsComplete =
    metrics.contracts.length > 0 &&
    metrics.signedContracts === metrics.contracts.length;

  const medicalsComplete =
    metrics.fighters.length > 0 &&
    metrics.bloodworkDone === metrics.fighters.length;

  const complianceComplete =
    metrics.checklist.length > 0 &&
    metrics.checklistDone === metrics.checklist.length;

  return (
    <Stack spacing={2}>
      <Card
        sx={{
          borderRadius: 3,
          border: "1px solid",
          borderColor: "divider",
          overflow: "hidden",
        }}
      >
        <CardContent sx={{ p: { xs: 2, md: 3 } }}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            justifyContent="space-between"
            spacing={3}
          >
            <Box sx={{ flex: 1 }}>
              <Typography
                variant="overline"
                color="error"
                fontWeight={950}
                letterSpacing={1.5}
              >
                EVENT COMMAND CENTER
              </Typography>

              <Typography
                variant="h4"
                fontWeight={950}
              >
                {data?.event?.name || "Event"}
              </Typography>

              <Typography
                color="text.secondary"
                sx={{ mt: 0.5 }}
              >
                One place to build, prepare and operate the event.
              </Typography>
            </Box>

            <Box
              sx={{
                minWidth: { md: 220 },
                textAlign: { xs: "left", md: "right" },
              }}
            >
              <Typography
                variant="h2"
                fontWeight={950}
                lineHeight={1}
              >
                {metrics.readiness}%
              </Typography>

              <Typography
                color="text.secondary"
                fontWeight={800}
              >
                EVENT READY
              </Typography>
            </Box>
          </Stack>

          <LinearProgress
            variant="determinate"
            value={metrics.readiness}
            sx={{
              mt: 2.5,
              height: 12,
              borderRadius: 999,
            }}
          />

          <Grid container spacing={1.5} sx={{ mt: 1 }}>
            <Grid item xs={6} md={2.4}>
              <Chip
                label={`${metrics.bouts.length} Bouts`}
                sx={{ width: "100%", fontWeight: 900 }}
              />
            </Grid>

            <Grid item xs={6} md={2.4}>
              <Chip
                label={`${metrics.fighters.length} Fighters`}
                sx={{ width: "100%", fontWeight: 900 }}
              />
            </Grid>

            <Grid item xs={6} md={2.4}>
              <Chip
                label={`${metrics.signedContracts}/${metrics.contracts.length} Signed`}
                color={contractsComplete ? "success" : "default"}
                sx={{ width: "100%", fontWeight: 900 }}
              />
            </Grid>

            <Grid item xs={6} md={2.4}>
              <Chip
                label={`${metrics.bloodworkDone}/${metrics.fighters.length} Medicals`}
                color={medicalsComplete ? "success" : "default"}
                sx={{ width: "100%", fontWeight: 900 }}
              />
            </Grid>

            <Grid item xs={12} md={2.4}>
              <Chip
                label={`${metrics.checklistDone}/${metrics.checklist.length} Compliance`}
                color={complianceComplete ? "success" : "default"}
                sx={{ width: "100%", fontWeight: 900 }}
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography
            variant="h6"
            fontWeight={950}
            sx={{ mb: 1.5 }}
          >
            Event Workflow
          </Typography>

          <Stack
            direction="row"
            spacing={1}
            useFlexGap
            flexWrap="wrap"
          >
            {stage(
              "1. Setup",
              metrics.hasVenue,
              8
            )}

            {stage(
              "2. Fight Card",
              metrics.bouts.length > 0,
              1
            )}

            {stage(
              "3. Contracts",
              contractsComplete,
              2
            )}

            {stage(
              "4. Compliance",
              medicalsComplete && complianceComplete,
              5
            )}

            {stage(
              "5. Tickets",
              false,
              9
            )}

            {stage(
              "6. Revenue",
              false,
              7
            )}
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Stack
            direction={{ xs: "column", md: "row" }}
            justifyContent="space-between"
            alignItems={{ xs: "stretch", md: "center" }}
            spacing={1}
            sx={{ mb: 2 }}
          >
            <Box>
              <Typography
                variant="h6"
                fontWeight={950}
              >
                What Needs Attention
              </Typography>

              <Typography
                variant="body2"
                color="text.secondary"
              >
                TNGOS prioritizes the next event tasks for you.
              </Typography>
            </Box>

            <Chip
              color={
                metrics.actions.length
                  ? "warning"
                  : "success"
              }
              label={
                metrics.actions.length
                  ? `${metrics.actions.length} Action${
                      metrics.actions.length === 1 ? "" : "s"
                    }`
                  : "No Immediate Issues"
              }
            />
          </Stack>

          {!metrics.actions.length ? (
            <Alert severity="success">
              No immediate event preparation issues were detected.
            </Alert>
          ) : (
            <Stack spacing={1.25}>
              {metrics.actions.slice(0, 6).map(
                (action, index) => (
                  <Alert
                    key={`${action.title}-${index}`}
                    severity={action.severity}
                    action={
                      <Button
                        color="inherit"
                        size="small"
                        onClick={() =>
                          setTab(action.tab)
                        }
                      >
                        {action.button}
                      </Button>
                    }
                  >
                    <Typography fontWeight={900}>
                      {action.title}
                    </Typography>

                    <Typography variant="body2">
                      {action.detail}
                    </Typography>
                  </Alert>
                )
              )}
            </Stack>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography
            variant="h6"
            fontWeight={950}
            sx={{ mb: 1.5 }}
          >
            Quick Operations
          </Typography>

          <Grid container spacing={1.25}>
            {[
              ["Fight Card", 1],
              ["Contracts", 2],
              ["Bloodwork", 5],
              ["Event Fees", 6],
              ["Sponsors / Vendors", 7],
              ["Venue", 8],
              ["Ticket Sales", 9],
            ].map(([label, tab]) => (
              <Grid
                item
                xs={6}
                sm={4}
                md
                key={label}
              >
                <Button
                  fullWidth
                  variant="outlined"
                  onClick={() => setTab(tab)}
                  sx={{
                    minHeight: 52,
                    fontWeight: 900,
                  }}
                >
                  {label}
                </Button>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    </Stack>
  );
}
