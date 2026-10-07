import React from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  Stack,
  Typography,
} from "@mui/material";

export default function EventFightNightPage({
  activeBouts,
  fighters,
  checklist,
}) {
  const bouts = [...(activeBouts || [])].sort(
    (a, b) =>
      Number(a.bout_order || 999) -
      Number(b.bout_order || 999)
  );

  const roster = fighters || [];
  const compliance = checklist || [];

  const medicalFlags = roster.filter(
    (fighter) => fighter.bloodwork_status !== "verified"
  );

  const checklistFlags = compliance.filter(
    (item) => item.status === "needs_attention"
  );

  const totalFlags =
    medicalFlags.length + checklistFlags.length;

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h5" fontWeight={950}>
          Fight Night
        </Typography>

        <Typography color="text.secondary">
          Bout order, fighter readiness and event-day operations.
        </Typography>
      </Box>

      <Grid container spacing={2}>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography
                variant="body2"
                color="text.secondary"
                fontWeight={800}
              >
                ACTIVE BOUTS
              </Typography>

              <Typography variant="h4" fontWeight={950}>
                {bouts.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography
                variant="body2"
                color="text.secondary"
                fontWeight={800}
              >
                FIGHTERS
              </Typography>

              <Typography variant="h4" fontWeight={950}>
                {roster.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography
                variant="body2"
                color="text.secondary"
                fontWeight={800}
              >
                ATTENTION FLAGS
              </Typography>

              <Typography variant="h4" fontWeight={950}>
                {totalFlags}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {totalFlags === 0 ? (
        <Alert severity="success">
          No current fighter medical or compliance attention flags.
        </Alert>
      ) : (
        <Stack spacing={1}>
          {medicalFlags.map((fighter) => (
            <Alert severity="warning" key={`medical-${fighter.id}`}>
              {fighter.legal_name}: bloodwork{" "}
              {fighter.bloodwork_status || "missing"}
            </Alert>
          ))}

          {checklistFlags.map((item) => (
            <Alert severity="error" key={`check-${item.id}`}>
              {item.label}
            </Alert>
          ))}
        </Stack>
      )}

      <Card>
        <CardContent>
          <Typography variant="h6" fontWeight={950}>
            Fight Night Bout Order
          </Typography>

          <Divider sx={{ my: 2 }} />

          {!bouts.length && (
            <Typography color="text.secondary">
              No active bouts have been built for this event yet.
            </Typography>
          )}

          <Stack spacing={1.5}>
            {bouts.map((bout, index) => (
              <Box
                key={bout.id}
                sx={{
                  p: 2,
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 2,
                }}
              >
                <Stack
                  direction={{ xs: "column", md: "row" }}
                  justifyContent="space-between"
                  spacing={1.5}
                >
                  <Box>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      fontWeight={800}
                    >
                      BOUT {bout.bout_order || index + 1}
                    </Typography>

                    <Typography fontWeight={950}>
                      {bout.red?.legal_name || "Red Corner"}
                      {" vs "}
                      {bout.blue?.legal_name || "Blue Corner"}
                    </Typography>

                    <Typography
                      variant="body2"
                      color="text.secondary"
                    >
                      {bout.weight_agreed
                        ? `${bout.weight_agreed} lb`
                        : "Weight TBD"}
                      {" ? "}
                      {bout.rounds || "TBD"} rounds
                    </Typography>
                  </Box>

                  <Chip
                    size="small"
                    label={bout.status || "scheduled"}
                    color={
                      bout.status === "cancelled" ||
                      bout.status === "void"
                        ? "error"
                        : "success"
                    }
                    sx={{ alignSelf: { xs: "flex-start", md: "center" } }}
                  />
                </Stack>
              </Box>
            ))}
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
