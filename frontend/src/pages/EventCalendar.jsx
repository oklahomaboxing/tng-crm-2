import React, { useEffect, useMemo, useState } from "react";

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
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import ArrowBackIosNewRoundedIcon from "@mui/icons-material/ArrowBackIosNewRounded";
import ArrowForwardIosRoundedIcon from "@mui/icons-material/ArrowForwardIosRounded";
import EventRoundedIcon from "@mui/icons-material/EventRounded";
import LaunchRoundedIcon from "@mui/icons-material/LaunchRounded";

import EventWorkspace from "./EventWorkspace.jsx";

const API =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const authHeaders = (extra = {}) => ({
  Authorization:
    `Bearer ${localStorage.getItem("token")}`,
  ...extra,
});


function parseEventDate(value) {
  if (!value) return null;

  const parts = value.split("-");

  if (parts.length !== 3) {
    return null;
  }

  const year = Number(parts[0]);
  const month = Number(parts[1]);
  const day = Number(parts[2]);

  if (!year || !month || !day) {
    return null;
  }

  return new Date(
    year,
    month - 1,
    day
  );
}


function formatDate(value) {
  const date = parseEventDate(value);

  if (!date) {
    return "Date TBD";
  }

  return date.toLocaleDateString(
    undefined,
    {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    }
  );
}


export default function EventCalendar() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const [selectedEventId, setSelectedEventId] =
    useState("");

  const [monthDate, setMonthDate] =
    useState(() => {
      const today = new Date();

      return new Date(
        today.getFullYear(),
        today.getMonth(),
        1
      );
    });


  async function loadCalendar() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        `${API}/api/boxing/calendar`,
        {
          headers: authHeaders(),
        }
      );

      const body =
        await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not load fight calendar"
        );
      }

      setEvents(
        Array.isArray(body) ? body : []
      );

    } catch (err) {
      setError(
        err.message ||
        "Could not load fight calendar"
      );
    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    loadCalendar();
  }, []);


  async function updateEvent(
    event,
    changes
  ) {
    setEvents((old) =>
      old.map((row) =>
        row.id === event.id
          ? {
              ...row,
              ...changes,
            }
          : row
      )
    );

    try {
      const response = await fetch(
        `${API}/api/boxing/calendar/${event.id}`,
        {
          method: "PATCH",

          headers: authHeaders({
            "Content-Type":
              "application/json",
          }),

          body:
            JSON.stringify(changes),
        }
      );

      const body =
        await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not save calendar event"
        );
      }

      setEvents((old) =>
        old.map((row) =>
          row.id === event.id
            ? {
                ...row,
                ...body,
              }
            : row
        )
      );

    } catch (err) {
      setError(
        err.message ||
        "Could not save event"
      );

      await loadCalendar();
    }
  }


  const upcoming = useMemo(() => {
    const today = new Date();

    today.setHours(0, 0, 0, 0);

    return [...events]
      .filter((event) => {
        const date =
          parseEventDate(
            event.event_date
          );

        return date && date >= today;
      })
      .sort((a, b) =>
        String(a.event_date).localeCompare(
          String(b.event_date)
        )
      );
  }, [events]);


  if (selectedEventId) {
    return (
      <EventWorkspace
        eventId={selectedEventId}
        onBack={() =>
          setSelectedEventId("")
        }
      />
    );
  }


  const year =
    monthDate.getFullYear();

  const month =
    monthDate.getMonth();

  const firstDay =
    new Date(year, month, 1);

  const daysInMonth =
    new Date(
      year,
      month + 1,
      0
    ).getDate();

  const startOffset =
    firstDay.getDay();

  const cells = [];

  for (
    let i = 0;
    i < startOffset;
    i += 1
  ) {
    cells.push(null);
  }

  for (
    let day = 1;
    day <= daysInMonth;
    day += 1
  ) {
    cells.push(day);
  }


  return (
    <Stack spacing={3}>

      <Stack
        direction={{
          xs: "column",
          md: "row",
        }}
        justifyContent="space-between"
        spacing={1}
      >
        <Box>
          <Typography
            variant="h4"
            fontWeight={950}
          >
            Fight Calendar
          </Typography>

          <Typography
            color="text.secondary"
          >
            Plan TNG events and control
            which dates appear on the
            public fight calendar.
          </Typography>
        </Box>

        <Button
          variant="outlined"
          startIcon={
            <LaunchRoundedIcon />
          }
          onClick={() =>
            window.open(
              "/fight-calendar",
              "_blank"
            )
          }
        >
          View Public Calendar
        </Button>
      </Stack>


      {error && (
        <Alert severity="error">
          {error}
        </Alert>
      )}


      <Card>
        <CardContent>
          <Stack spacing={2}>

            <Stack
              direction="row"
              alignItems="center"
              justifyContent="space-between"
            >
              <Button
                onClick={() =>
                  setMonthDate(
                    new Date(
                      year,
                      month - 1,
                      1
                    )
                  )
                }
              >
                <ArrowBackIosNewRoundedIcon />
              </Button>

              <Typography
                variant="h5"
                fontWeight={950}
              >
                {monthDate.toLocaleDateString(
                  undefined,
                  {
                    month: "long",
                    year: "numeric",
                  }
                )}
              </Typography>

              <Button
                onClick={() =>
                  setMonthDate(
                    new Date(
                      year,
                      month + 1,
                      1
                    )
                  )
                }
              >
                <ArrowForwardIosRoundedIcon />
              </Button>
            </Stack>


            <Box
              sx={{
                display: "grid",
                gridTemplateColumns:
                  "repeat(7, minmax(0, 1fr))",
                gap: 1,
              }}
            >
              {[
                "Sun",
                "Mon",
                "Tue",
                "Wed",
                "Thu",
                "Fri",
                "Sat",
              ].map((day) => (
                <Typography
                  key={day}
                  align="center"
                  variant="caption"
                  fontWeight={900}
                  color="text.secondary"
                >
                  {day}
                </Typography>
              ))}


              {cells.map(
                (day, index) => {
                  if (!day) {
                    return (
                      <Box
                        key={`blank-${index}`}
                        sx={{
                          minHeight: 105,
                        }}
                      />
                    );
                  }

                  const dateKey =
                    `${year}-${String(
                      month + 1
                    ).padStart(
                      2,
                      "0"
                    )}-${String(day).padStart(
                      2,
                      "0"
                    )}`;

                  const dayEvents =
                    events.filter(
                      (event) =>
                        event.event_date ===
                        dateKey
                    );

                  return (
                    <Box
                      key={dateKey}
                      sx={{
                        minHeight: 105,
                        p: 1,
                        border:
                          "1px solid",
                        borderColor:
                          "divider",
                        borderRadius: 2,
                        bgcolor:
                          dayEvents.length
                            ? "#fff"
                            : "#fafafa",
                      }}
                    >
                      <Typography
                        fontWeight={900}
                        variant="body2"
                      >
                        {day}
                      </Typography>

                      <Stack
                        spacing={0.5}
                        sx={{ mt: 0.5 }}
                      >
                        {dayEvents.map(
                          (event) => (
                            <Box
                              key={event.id}
                              onClick={() =>
                                setSelectedEventId(
                                  event.id
                                )
                              }
                              sx={{
                                p: 0.75,
                                bgcolor:
                                  event.published
                                    ? "#d71920"
                                    : "#27272a",
                                color:
                                  "white",
                                borderRadius: 1.5,
                                cursor:
                                  "pointer",
                              }}
                            >
                              <Typography
                                variant="caption"
                                fontWeight={900}
                              >
                                {event.name}
                              </Typography>
                            </Box>
                          )
                        )}
                      </Stack>
                    </Box>
                  );
                }
              )}
            </Box>

          </Stack>
        </CardContent>
      </Card>


      <Box>
        <Typography
          variant="h5"
          fontWeight={950}
          sx={{ mb: 2 }}
        >
          Upcoming Events
        </Typography>

        {loading && (
          <Typography>
            Loading events...
          </Typography>
        )}

        {!loading &&
          !upcoming.length && (
            <Alert severity="info">
              No upcoming events are
              currently scheduled.
            </Alert>
          )}

        <Stack spacing={2}>
          {upcoming.map((event) => (
            <Card key={event.id}>
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
                      <Typography
                        variant="h6"
                        fontWeight={950}
                      >
                        {event.name}
                      </Typography>

                      <Typography
                        fontWeight={800}
                      >
                        {formatDate(
                          event.event_date
                        )}
                      </Typography>

                      <Typography
                        variant="body2"
                        color="text.secondary"
                      >
                        {event.venue ||
                          "Venue TBD"}
                      </Typography>

                      <Typography
                        variant="body2"
                        color="text.secondary"
                      >
                        {event.venue_address}
                      </Typography>
                    </Box>

                    <Stack
                      direction="row"
                      spacing={1}
                      alignItems="center"
                    >
                      <Chip
                        label={
                          event.published
                            ? "PUBLIC"
                            : "PRIVATE"
                        }
                        color={
                          event.published
                            ? "success"
                            : "default"
                        }
                      />

                      <Typography
                        variant="body2"
                        fontWeight={900}
                      >
                        Publish
                      </Typography>

                      <Switch
                        checked={
                          Boolean(
                            event.published
                          )
                        }
                        onChange={(e) =>
                          updateEvent(
                            event,
                            {
                              published:
                                e.target.checked,
                            }
                          )
                        }
                      />
                    </Stack>
                  </Stack>


                  <Divider />


                  <Grid
                    container
                    spacing={2}
                  >
                    <Grid
                      item
                      xs={12}
                      md={3}
                    >
                      <TextField
                        fullWidth
                        label="Public Title"
                        value={
                          event.public_title ||
                          ""
                        }
                        onChange={(e) => {
                          const value =
                            e.target.value;

                          setEvents((old) =>
                            old.map((row) =>
                              row.id === event.id
                                ? {
                                    ...row,
                                    public_title:
                                      value,
                                  }
                                : row
                            )
                          );
                        }}
                        onBlur={(e) =>
                          updateEvent(
                            event,
                            {
                              public_title:
                                e.target.value,
                            }
                          )
                        }
                      />
                    </Grid>

                    <Grid
                      item
                      xs={6}
                      md={2}
                    >
                      <TextField
                        fullWidth
                        type="time"
                        label="Doors"
                        InputLabelProps={{
                          shrink: true,
                        }}
                        value={
                          event.doors_time ||
                          ""
                        }
                        onChange={(e) => {
                          const value =
                            e.target.value;

                          setEvents((old) =>
                            old.map((row) =>
                              row.id === event.id
                                ? {
                                    ...row,
                                    doors_time:
                                      value,
                                  }
                                : row
                            )
                          );
                        }}
                        onBlur={(e) =>
                          updateEvent(
                            event,
                            {
                              doors_time:
                                e.target.value,
                            }
                          )
                        }
                      />
                    </Grid>

                    <Grid
                      item
                      xs={6}
                      md={2}
                    >
                      <TextField
                        fullWidth
                        type="time"
                        label="First Bout"
                        InputLabelProps={{
                          shrink: true,
                        }}
                        value={
                          event.first_bout_time ||
                          ""
                        }
                        onChange={(e) => {
                          const value =
                            e.target.value;

                          setEvents((old) =>
                            old.map((row) =>
                              row.id === event.id
                                ? {
                                    ...row,
                                    first_bout_time:
                                      value,
                                  }
                                : row
                            )
                          );
                        }}
                        onBlur={(e) =>
                          updateEvent(
                            event,
                            {
                              first_bout_time:
                                e.target.value,
                            }
                          )
                        }
                      />
                    </Grid>

                    <Grid
                      item
                      xs={12}
                      md={5}
                    >
                      <TextField
                        fullWidth
                        label="Ticket URL"
                        value={
                          event.ticket_url ||
                          ""
                        }
                        onChange={(e) => {
                          const value =
                            e.target.value;

                          setEvents((old) =>
                            old.map((row) =>
                              row.id === event.id
                                ? {
                                    ...row,
                                    ticket_url:
                                      value,
                                  }
                                : row
                            )
                          );
                        }}
                        onBlur={(e) =>
                          updateEvent(
                            event,
                            {
                              ticket_url:
                                e.target.value,
                            }
                          )
                        }
                      />
                    </Grid>

                    <Grid
                      item
                      xs={12}
                    >
                      <TextField
                        fullWidth
                        multiline
                        minRows={2}
                        label="Public Notes"
                        value={
                          event.public_notes ||
                          ""
                        }
                        onChange={(e) => {
                          const value =
                            e.target.value;

                          setEvents((old) =>
                            old.map((row) =>
                              row.id === event.id
                                ? {
                                    ...row,
                                    public_notes:
                                      value,
                                  }
                                : row
                            )
                          );
                        }}
                        onBlur={(e) =>
                          updateEvent(
                            event,
                            {
                              public_notes:
                                e.target.value,
                            }
                          )
                        }
                      />
                    </Grid>
                  </Grid>


                  <Button
                    variant="outlined"
                    startIcon={
                      <EventRoundedIcon />
                    }
                    onClick={() =>
                      setSelectedEventId(
                        event.id
                      )
                    }
                  >
                    Open Event Workspace
                  </Button>

                </Stack>
              </CardContent>
            </Card>
          ))}
        </Stack>
      </Box>

    </Stack>
  );
}
