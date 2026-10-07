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

export default function EventCompliancePage({
  mode,
  items,
  updateChecklist,
  setData,
  statusLabels,
  statusColor,
}) {
  const isMatchmaker = mode === "matchmaker";

  const title = isMatchmaker
    ? "Matchmaker Responsibilities"
    : "Promoter Responsibilities";

  const description = isMatchmaker
    ? "Bout submission, contracts, bloodwork and special fighter requirements."
    : "Track every Commission and event operations requirement.";

  return (
    <Box>
      <Typography
        variant="h5"
        fontWeight={950}
        sx={{ mb: 0.5 }}
      >
        {title}
      </Typography>

      <Typography
        color="text.secondary"
        sx={{ mb: 2 }}
      >
        {description}
      </Typography>

      <Stack spacing={1.5}>
        {(items || []).map((item) => (
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
    </Box>
  );
}
