import React from "react";
import {
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

export default function EventExpensesPage({
  fees,
  updateFee,
}) {
  return (
          <Stack spacing={2}>
            <Box>
              <Typography variant="h5" fontWeight={950}>
                Event Fees & Assessments
              </Typography>

              <Typography color="text.secondary">
                Track estimated and actual costs for this event.
              </Typography>
            </Box>

            {(fees || []).map((fee) => (
              <Card key={fee.id}>
                <CardContent>
                  <Stack spacing={2}>
                    <Stack
                      direction={{
                        xs: "column",
                        md: "row",
                      }}
                      justifyContent="space-between"
                      spacing={1}
                    >
                      <Box>
                        <Typography fontWeight={950}>
                          {fee.name}
                        </Typography>

                        <Typography
                          variant="body2"
                          color="text.secondary"
                        >
                          Estimate: {fee.estimate}
                        </Typography>
                      </Box>

                      <Chip
                        label={
                          fee.paid ? "Paid" : "Unpaid"
                        }
                        color={
                          fee.paid
                            ? "success"
                            : "warning"
                        }
                      />
                    </Stack>

                    <Grid container spacing={2}>
                      <Grid item xs={12} md={3}>
                        <TextField
                          fullWidth
                          type="number"
                          label="Actual Amount"
                          defaultValue={
                            fee.actual_amount ?? ""
                          }
                          onBlur={(e) =>
                            updateFee(fee, {
                              actual_amount:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={2}>
                        <Select
                          fullWidth
                          value={
                            fee.paid ? "paid" : "unpaid"
                          }
                          onChange={(e) =>
                            updateFee(fee, {
                              paid:
                                e.target.value === "paid",
                            })
                          }
                        >
                          <MenuItem value="unpaid">
                            Unpaid
                          </MenuItem>

                          <MenuItem value="paid">
                            Paid
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
                          defaultValue={
                            fee.due_date || ""
                          }
                          onBlur={(e) =>
                            updateFee(fee, {
                              due_date:
                                e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12} md={4}>
                        <TextField
                          fullWidth
                          label="Payee"
                          defaultValue={
                            fee.payee || ""
                          }
                          onBlur={(e) =>
                            updateFee(fee, {
                              payee: e.target.value,
                            })
                          }
                        />
                      </Grid>

                      <Grid item xs={12}>
                        <TextField
                          fullWidth
                          multiline
                          minRows={2}
                          label="Notes"
                          defaultValue={
                            fee.notes || ""
                          }
                          onBlur={(e) =>
                            updateFee(fee, {
                              notes: e.target.value,
                            })
                          }
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
