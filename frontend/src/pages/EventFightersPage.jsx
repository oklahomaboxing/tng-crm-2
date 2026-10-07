import React from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  Stack,
  Typography,
} from "@mui/material";

function bloodworkColor(status) {
  if (status === "verified") return "success";
  if (status === "pending" || status === "requested") return "warning";
  return "error";
}

export default function EventFightersPage({
  fighters,
}) {
  const roster = fighters || [];
  const readyCount = roster.filter(
    (fighter) => fighter.bloodwork_status === "verified"
  ).length;

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h5" fontWeight={950}>
          Event Fighters
        </Typography>

        <Typography color="text.secondary">
          Event roster, fighter readiness and medical status.
        </Typography>
      </Box>

      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography
                variant="body2"
                color="text.secondary"
                fontWeight={800}
              >
                EVENT ROSTER
              </Typography>

              <Typography variant="h4" fontWeight={950}>
                {roster.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography
                variant="body2"
                color="text.secondary"
                fontWeight={800}
              >
                BLOODWORK VERIFIED
              </Typography>

              <Typography variant="h4" fontWeight={950}>
                {readyCount}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography
                variant="body2"
                color="text.secondary"
                fontWeight={800}
              >
                NEEDS ATTENTION
              </Typography>

              <Typography variant="h4" fontWeight={950}>
                {roster.length - readyCount}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {!roster.length && (
        <Alert severity="info">
          No fighters are assigned to this event yet.
        </Alert>
      )}

      <Grid container spacing={2}>
        {roster.map((fighter) => (
          <Grid item xs={12} md={6} key={fighter.id}>
            <Card>
              <CardContent>
                <Stack spacing={1.5}>
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    justifyContent="space-between"
                    spacing={1}
                  >
                    <Box>
                      <Typography fontWeight={950}>
                        {fighter.legal_name || "Unnamed Fighter"}
                      </Typography>

                      {fighter.nickname && (
                        <Typography
                          variant="body2"
                          color="text.secondary"
                        >
                          "{fighter.nickname}"
                        </Typography>
                      )}
                    </Box>

                    <Chip
                      size="small"
                      label={
                        fighter.bloodwork_status === "verified"
                          ? "Medical Ready"
                          : `Bloodwork: ${
                              fighter.bloodwork_status || "missing"
                            }`
                      }
                      color={bloodworkColor(
                        fighter.bloodwork_status
                      )}
                    />
                  </Stack>

                  {fighter.boxrec_id && (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                    >
                      BoxRec ID: {fighter.boxrec_id}
                    </Typography>
                  )}

                  {fighter.bloodwork_expires && (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                    >
                      Bloodwork expires: {fighter.bloodwork_expires}
                    </Typography>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Stack>
  );
}
