import React, { useEffect, useState } from "react";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";

import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";
import ConfirmationNumberRoundedIcon from "@mui/icons-material/ConfirmationNumberRounded";

const API =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";


function formatDate(value) {
  if (!value) {
    return "Date TBD";
  }

  const parts = value.split("-");

  const date = new Date(
    Number(parts[0]),
    Number(parts[1]) - 1,
    Number(parts[2])
  );

  return date.toLocaleDateString(
    undefined,
    {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    }
  );
}


function formatTime(value) {
  if (!value) {
    return "";
  }

  const [hour, minute] =
    value.split(":");

  const date = new Date();

  date.setHours(
    Number(hour),
    Number(minute),
    0,
    0
  );

  return date.toLocaleTimeString(
    undefined,
    {
      hour: "numeric",
      minute: "2-digit",
    }
  );
}


export default function PublicFightCalendar() {
  const [events, setEvents] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");


  useEffect(() => {
    async function load() {
      try {
        const response = await fetch(
          `${API}/api/boxing/public/fight-calendar`
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
          Array.isArray(body)
            ? body
            : []
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

    load();
  }, []);


  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "#09090b",
        color: "white",
      }}
    >

      <Box
        sx={{
          borderBottom:
            "1px solid rgba(255,255,255,.1)",
          px: { xs: 2, md: 4 },
          py: 2,
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          spacing={1.5}
        >
          <SportsMmaRoundedIcon
            sx={{
              color: "#d71920",
              fontSize: 38,
            }}
          />

          <Box>
            <Typography
              variant="h5"
              fontWeight={950}
            >
              TNG BOXING
            </Typography>

            <Typography
              variant="caption"
              sx={{
                color:
                  "rgba(255,255,255,.6)",
              }}
            >
              THE NEXT GENERATION
            </Typography>
          </Box>
        </Stack>
      </Box>


      <Box
        sx={{
          width: "100%",
          maxWidth: 1100,
          mx: "auto",
          px: { xs: 2, md: 3 },
          py: { xs: 4, md: 7 },
        }}
      >
        <Box sx={{ mb: 5 }}>
          <Typography
            variant="h2"
            fontWeight={950}
            sx={{
              fontSize: {
                xs: "2.4rem",
                md: "4rem",
              },
            }}
          >
            FIGHT CALENDAR
          </Typography>

          <Typography
            sx={{
              color:
                "rgba(255,255,255,.65)",
              maxWidth: 650,
              mt: 1,
            }}
          >
            Upcoming professional boxing
            events presented by TNG Boxing.
          </Typography>
        </Box>


        {loading && (
          <CircularProgress />
        )}


        {error && (
          <Alert severity="error">
            {error}
          </Alert>
        )}


        {!loading &&
          !error &&
          events.length === 0 && (
            <Alert severity="info">
              New fight dates will be
              announced soon.
            </Alert>
          )}


        <Stack spacing={3}>
          {events.map((event) => (
            <Card
              key={event.id}
              sx={{
                bgcolor: "#18181b",
                color: "white",
                border:
                  "1px solid rgba(255,255,255,.12)",
              }}
            >
              <CardContent
                sx={{
                  p: {
                    xs: 2.5,
                    md: 4,
                  },
                }}
              >
                <Stack spacing={2}>

                  <Chip
                    label="TNG BOXING"
                    sx={{
                      alignSelf:
                        "flex-start",
                      bgcolor:
                        "#d71920",
                      color: "white",
                      fontWeight: 900,
                    }}
                  />

                  <Typography
                    variant="h4"
                    fontWeight={950}
                  >
                    {event.name}
                  </Typography>

                  <Typography
                    variant="h6"
                    fontWeight={900}
                    sx={{
                      color:
                        "#ef4444",
                    }}
                  >
                    {formatDate(
                      event.event_date
                    )}
                  </Typography>

                  <Box>
                    <Typography
                      fontWeight={900}
                    >
                      {event.venue ||
                        "Venue TBD"}
                    </Typography>

                    <Typography
                      sx={{
                        color:
                          "rgba(255,255,255,.65)",
                      }}
                    >
                      {event.venue_address}
                    </Typography>
                  </Box>


                  {(event.doors_time ||
                    event.first_bout_time) && (
                    <Stack
                      direction={{
                        xs: "column",
                        sm: "row",
                      }}
                      spacing={2}
                    >
                      {event.doors_time && (
                        <Typography>
                          <strong>
                            Doors:
                          </strong>{" "}
                          {formatTime(
                            event.doors_time
                          )}
                        </Typography>
                      )}

                      {event.first_bout_time && (
                        <Typography>
                          <strong>
                            First Bout:
                          </strong>{" "}
                          {formatTime(
                            event.first_bout_time
                          )}
                        </Typography>
                      )}
                    </Stack>
                  )}


                  {event.public_notes && (
                    <Typography
                      sx={{
                        color:
                          "rgba(255,255,255,.75)",
                      }}
                    >
                      {event.public_notes}
                    </Typography>
                  )}


                  {event.ticket_url && (
                    <Button
                      variant="contained"
                      startIcon={
                        <ConfirmationNumberRoundedIcon />
                      }
                      onClick={() =>
                        window.open(
                          event.ticket_url,
                          "_blank"
                        )
                      }
                      sx={{
                        alignSelf:
                          "flex-start",
                        bgcolor:
                          "#d71920",
                      }}
                    >
                      Tickets
                    </Button>
                  )}

                </Stack>
              </CardContent>
            </Card>
          ))}
        </Stack>
      </Box>
    </Box>
  );
}
