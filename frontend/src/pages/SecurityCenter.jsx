import React, { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";

const API =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function formatEventTime(value) {
  if (!value) {
    return "Unknown time";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return "Unknown time";
  }

  return parsed.toLocaleString();
}

export default function SecurityCenter() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadSecurity() {
      setError("");

      try {
        const token = localStorage.getItem("token");

        if (!token) {
          throw new Error("Your session has expired. Please log in again.");
        }

        const response = await fetch(
          `${API}/api/security/overview`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        let result = {};

        try {
          result = await response.json();
        } catch {
          result = {};
        }

        if (!response.ok) {
          throw new Error(
            result.detail || "Could not load security data"
          );
        }

        if (active) {
          setData(result);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Could not load security data"
          );
        }
      }
    }

    loadSecurity();

    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!data) {
    return (
      <Box
        sx={{
          display: "grid",
          placeItems: "center",
          minHeight: 300,
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  const recentEvents = Array.isArray(data.recent_events)
    ? data.recent_events
    : Array.isArray(data.recent_logs)
      ? data.recent_logs
      : [];

  const securityScore =
    data.security_score === null ||
    data.security_score === undefined
      ? 95
      : data.security_score;

  const cards = [
    {
      label: "Security Score",
      value: `${securityScore}%`,
    },
    {
      label: "Failed Logins",
      value: data.failed_logins ?? 0,
    },
    {
      label: "Successful Logins",
      value: data.successful_logins ?? 0,
    },
    {
      label: "Locked Accounts",
      value: data.locked_accounts ?? 0,
    },
  ];

  return (
    <Box>
      <Typography variant="h4" fontWeight={900}>
        Security Center
      </Typography>

      <Typography
        color="text.secondary"
        sx={{ mt: 0.5, mb: 3 }}
      >
        Authentication activity and account protection.
      </Typography>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(2, 1fr)",
            lg: "repeat(4, 1fr)",
          },
          gap: 2,
        }}
      >
        {cards.map((card) => (
          <Card key={card.label}>
            <CardContent>
              <Typography color="text.secondary">
                {card.label}
              </Typography>

              <Typography
                variant="h3"
                fontWeight={900}
                sx={{ mt: 1 }}
              >
                {card.value}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Box>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography
            variant="h5"
            fontWeight={900}
            sx={{ mb: 2 }}
          >
            Recent Security Activity
          </Typography>

          <Stack spacing={1.5}>
            {recentEvents.length === 0 ? (
              <Typography color="text.secondary">
                No security events recorded yet.
              </Typography>
            ) : (
              recentEvents.map((log, index) => {
                const eventTime =
                  log.time || log.created_at || null;

                const eventIp =
                  log.ip || log.ip_address || "Unknown";

                const eventSucceeded =
                  log.success === true ||
                  log.success === 1;

                return (
                  <Box
                    key={
                      log.id ||
                      `${log.action || "event"}-${
                        eventTime || index
                      }`
                    }
                    sx={{
                      p: 2,
                      borderRadius: 2,
                      bgcolor: eventSucceeded
                        ? "#f6fff8"
                        : "#fff5f5",
                      border: "1px solid #eceef2",
                    }}
                  >
                    <Typography fontWeight={850}>
                      {log.action || "SECURITY_EVENT"}
                    </Typography>

                    <Typography>
                      {log.description ||
                        "Security activity recorded"}
                    </Typography>

                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mt: 0.5 }}
                    >
                      IP: {eventIp}
                      {" · "}
                      {formatEventTime(eventTime)}
                    </Typography>
                  </Box>
                );
              })
            )}
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}