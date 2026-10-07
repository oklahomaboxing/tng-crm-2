import React from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

const REQUEST_A_TEST_URL =
  "https://requestatest.com/combative";

export default function EventMedicalsPage({
  fighters,
  updateBloodwork,
}) {
  return (
          <Stack spacing={2}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              justifyContent="space-between"
              spacing={1}
            >
              <Box>
                <Typography variant="h5" fontWeight={950}>
                  Fighter Bloodwork
                </Typography>

                <Typography color="text.secondary">
                  Update bloodwork status for each fighter on this card.
                </Typography>
              </Box>

              <Button
                variant="outlined"
                startIcon={<BloodtypeRoundedIcon />}
                onClick={() =>
                  window.open(
                    REQUEST_A_TEST_URL,
                    "_blank",
                    "noopener,noreferrer"
                  )
                }
              >
                Open Request A Test
              </Button>
            </Stack>

            {fighters.map((fighter) => (
              <Card key={fighter.id}>
                <CardContent>
                  <Stack spacing={2}>
                    <Box>
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
                        {fighter.pro_record || "Record N/A"}
                        {" | "}
                        {fighter.fight_weight
                          ? `${fighter.fight_weight} lb`
                          : "Weight N/A"}
                      </Typography>
                    </Box>

                    <Grid container spacing={2}>
                      <Grid item xs={12} md={3}>
                        <Select
                          fullWidth
                          value={
                            fighter.bloodwork_status ||
                            "missing"
                          }
                          onChange={(e) =>
                            updateBloodwork(fighter, {
                              bloodwork_status:
                                e.target.value,
                            })
                          }
                        >
                          <MenuItem value="missing">
                            Missing
                          </MenuItem>

                          <MenuItem value="requested">
                            Requested
                          </MenuItem>

                          <MenuItem value="pending">
                            Pending
                          </MenuItem>

                          <MenuItem value="verified">
                            Verified
                          </MenuItem>

                          <MenuItem value="expired">
                            Expired
                          </MenuItem>
                        </Select>
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <TextField
                          fullWidth
                          label="Provider"
                          defaultValue={
                            fighter.bloodwork_provider || ""
                          }
                          onBlur={(e) =>
                            updateBloodwork(fighter, {
                              bloodwork_provider:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <TextField
                          fullWidth
                          type="date"
                          label="Requested"
                          InputLabelProps={{
                            shrink: true,
                          }}
                          defaultValue={
                            fighter.bloodwork_requested_date ||
                            ""
                          }
                          onBlur={(e) =>
                            updateBloodwork(fighter, {
                              bloodwork_requested_date:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <TextField
                          fullWidth
                          type="date"
                          label="Completed"
                          InputLabelProps={{
                            shrink: true,
                          }}
                          defaultValue={
                            fighter.bloodwork_completed_date ||
                            ""
                          }
                          onBlur={(e) =>
                            updateBloodwork(fighter, {
                              bloodwork_completed_date:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={3}>
                        <TextField
                          fullWidth
                          type="date"
                          label="Expires"
                          InputLabelProps={{
                            shrink: true,
                          }}
                          defaultValue={
                            fighter.bloodwork_expires || ""
                          }
                          onBlur={(e) =>
                            updateBloodwork(fighter, {
                              bloodwork_expires:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={7}>
                        <TextField
                          fullWidth
                          label="Notes"
                          defaultValue={
                            fighter.bloodwork_notes || ""
                          }
                          onBlur={(e) =>
                            updateBloodwork(fighter, {
                              bloodwork_notes:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={2}>
                        <Button
                          fullWidth
                          variant="outlined"
                          sx={{ minHeight: 56 }}
                          onClick={() =>
                            window.open(
                              REQUEST_A_TEST_URL,
                              "_blank",
                              "noopener,noreferrer"
                            )
                          }
                        >
                          Request Test
                        </Button>
                      </Grid>
                    </Grid>
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Stack>
  );
}
