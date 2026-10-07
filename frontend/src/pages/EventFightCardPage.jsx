import React from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

function fighterLocation(fighter) {
  return [
    fighter?.city,
    fighter?.state,
    fighter?.country,
  ]
    .filter(Boolean)
    .join(", ");
}

export default function EventFightCardPage({
  activeBouts,
  cancelledBouts,
  setData,
  updateBoutOrder,
  setCancelBout,
  setCancelBoutNotes,
  setCancelBoutOpen,
}) {
  return (
    <Stack spacing={2}>
      {activeBouts.map((bout, index) => (
        <Card
          key={bout.id}
          sx={{
            borderRadius: 4,
            overflow: "hidden",
            border: "1px solid",
            borderColor: "divider",
            boxShadow: "0 14px 38px rgba(15,23,42,.10)",
            mb: 3,
          }}
        >
          <CardContent
            sx={{
              p: { xs: 2, md: 3 },
              "&:last-child": {
                pb: { xs: 2, md: 3 },
              },
            }}
          >
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
                <Typography fontWeight={950}>
                  RED: {bout.red?.legal_name}
                </Typography>

                <Typography variant="body2">
                  {bout.red?.pro_record || "Record N/A"}
                </Typography>

                {bout.red_series &&
                  bout.red_series.status !== "released" && (
                    <Chip
                      size="small"
                      color="primary"
                      sx={{ mt: 0.75 }}
                      label={
                        bout.red_series.status === "graduated"
                          ? "FIRST 5 FIGHTS SERIES - GRADUATED"
                          : `FIRST 5 FIGHTS SERIES - FIGHT ${bout.red_series.next_fight_number} OF ${bout.red_series.target_fights}`
                      }
                    />
                  )}

                <Typography
                  variant="caption"
                  color="text.secondary"
                >
                  {fighterLocation(bout.red)}
                </Typography>
              </Grid>

              <Grid item xs={12} md={4}>
                <Typography fontWeight={950}>
                  BLUE: {bout.blue?.legal_name}
                </Typography>

                <Typography variant="body2">
                  {bout.blue?.pro_record || "Record N/A"}
                </Typography>

                {bout.blue_series &&
                  bout.blue_series.status !== "released" && (
                    <Chip
                      size="small"
                      color="primary"
                      sx={{ mt: 0.75 }}
                      label={
                        bout.blue_series.status === "graduated"
                          ? "FIRST 5 FIGHTS SERIES - GRADUATED"
                          : `FIRST 5 FIGHTS SERIES - FIGHT ${bout.blue_series.next_fight_number} OF ${bout.blue_series.target_fights}`
                      }
                    />
                  )}

                <Typography
                  variant="caption"
                  color="text.secondary"
                >
                  {fighterLocation(bout.blue)}
                </Typography>
              </Grid>

              <Grid item xs={12} md={2}>
                <TextField
                  fullWidth
                  type="number"
                  size="small"
                  label="Bout Order"
                  value={bout.bout_order ?? ""}
                  inputProps={{ min: 1 }}
                  onChange={(e) => {
                    const value = e.target.value;

                    setData((old) => ({
                      ...old,
                      bouts: old.bouts.map((row) =>
                        row.id === bout.id
                          ? {
                              ...row,
                              bout_order: value,
                            }
                          : row
                      ),
                    }));
                  }}
                  onBlur={(e) =>
                    updateBoutOrder(
                      bout,
                      e.target.value
                    )
                  }
                  sx={{ mb: 1 }}
                />

                <Typography fontWeight={850}>
                  {bout.weight_agreed
                    ? `${bout.weight_agreed} lb`
                    : "TBD"}
                </Typography>

                <Typography variant="body2">
                  {bout.rounds} rounds
                </Typography>

                {bout.status !== "cancelled" ? (
                  <Button
                    size="small"
                    color="error"
                    variant="outlined"
                    sx={{ mt: 1 }}
                    onClick={() => {
                      setCancelBout(bout);
                      setCancelBoutNotes("");
                      setCancelBoutOpen(true);
                    }}
                  >
                    Remove Bout
                  </Button>
                ) : (
                  <Chip
                    size="small"
                    color="default"
                    label="Removed / Cancelled"
                    sx={{ mt: 1 }}
                  />
                )}
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      ))}

      {!activeBouts.length && (
        <Alert severity="info">
          No active bouts are currently assigned to this event.
        </Alert>
      )}

      {cancelledBouts.length > 0 && (
        <>
          <Divider sx={{ my: 2 }} />

          <Typography
            variant="h6"
            fontWeight={950}
          >
            Cancelled Bout History
          </Typography>

          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ mb: 1 }}
          >
            These bouts remain in TNGOS for records but are no longer
            part of the active fight card.
          </Typography>

          <Stack spacing={1}>
            {cancelledBouts.map((bout) => (
              <Card
                key={bout.id}
                variant="outlined"
                sx={{
                  opacity: 0.78,
                  borderStyle: "dashed",
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
                        {" - "}
                        {bout.rounds} rounds
                      </Typography>

                      {bout.notes && (
                        <Typography
                          variant="body2"
                          sx={{
                            mt: 1,
                            whiteSpace: "pre-line",
                          }}
                        >
                          {bout.notes}
                        </Typography>
                      )}
                    </Box>

                    <Chip
                      label={
                        bout.status === "void"
                          ? "Void"
                          : "Cancelled"
                      }
                    />
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Stack>
        </>
      )}
    </Stack>
  );
}
