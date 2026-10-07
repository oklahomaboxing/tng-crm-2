import React from "react";
import {
  Button,
  Card,
  CardContent,
  Grid,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

export default function EventSettingsPage({
  venueName,
  setVenueName,
  venueAddress,
  setVenueAddress,
  saveVenue,
  venueSaving,
}) {
  return (
          <Stack spacing={2}>
            <Card>
              <CardContent>
                <Typography
                  variant="h6"
                  fontWeight={900}
                  sx={{ mb: 2 }}
                >
                  Event Venue
                </Typography>

                <Grid container spacing={2}>
                  <Grid item xs={12} md={5}>
                    <TextField
                      fullWidth
                      label="Venue Name"
                      value={venueName}
                      onChange={(e) =>
                        setVenueName(e.target.value)
                      }
                    />
                  </Grid>

                  <Grid item xs={12} md={5}>
                    <TextField
                      fullWidth
                      label="Venue Address"
                      value={venueAddress}
                      onChange={(e) =>
                        setVenueAddress(e.target.value)
                      }
                    />
                  </Grid>

                  <Grid item xs={12} md={2}>
                    <Button
                      fullWidth
                      variant="contained"
                      color="error"
                      onClick={saveVenue}
                      disabled={venueSaving}
                      sx={{ height: "100%", minHeight: 56 }}
                    >
                      {venueSaving
                        ? "Saving..."
                        : "Save Venue"}
                    </Button>
                  </Grid>
                </Grid>

                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: "block", mt: 1.5 }}
                >
                  Updating the venue also updates all unsigned
                  contracts for this event. Electronically signed
                  contracts remain unchanged.
                </Typography>
              </CardContent>
            </Card>
          </Stack>
  );
}
