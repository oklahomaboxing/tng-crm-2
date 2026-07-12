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

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function SecurityCenter() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadSecurity() {
      try {
        const response = await fetch(`${API}/api/security/overview`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        });

        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.detail || "Could not load security data");
        }

        setData(result);
      } catch (err) {
        setError(err.message || "Could not load security data");
      }
    }

    loadSecurity();
  }, []);

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  if (!data) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", minHeight: 300 }}>
        <CircularProgress />
      </Box>
    );
  }

  const cards = [
    ["Security Score", `${data.security_score}%`],
    ["Failed Logins", data.failed_logins],
    ["Successful Logins", data.successful_logins],
    ["Locked Accounts", data.locked_accounts],
  ];

  return (
    <Box>
      <Typography variant="h4" fontWeight={900}>
        Security Center
      </Typography>

      <Typography color="text.secondary" sx={{ mt: 0.5, mb: 3 }}>
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
        {cards.map(([label, value]) => (
          <Card key={label}>
            <CardContent>
              <Typography color="text.secondary">{label}</Typography>
              <Typography variant="h3" fontWeight={900} sx={{ mt: 1 }}>
                {value}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Box>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h5" fontWeight={900} sx={{ mb: 2 }}>
            Recent Security Activity
          </Typography>

          <Stack spacing={1.5}>
            {data.recent_logs.length === 0 && (
              <Typography color="text.secondary">
                No security events recorded yet.
              </Typography>
            )}

            {data.recent_logs.map((log, index) => (
              <Box
                key={`${log.action}-${log.created_at}-${index}`}
                sx={{
                  p: 2,
                  borderRadius: 2,
                  bgcolor: log.success ? "#f6fff8" : "#fff5f5",
                  border: "1px solid #eceef2",
                }}
              >
                <Typography fontWeight={850}>{log.action}</Typography>

                <Typography>{log.description}</Typography>

                <Typography variant="body2" color="text.secondary">
                  IP: {log.ip_address || "Unknown"} ·{" "}
                  {log.created_at
                    ? new Date(log.created_at).toLocaleString()
                    : "Unknown time"}
                </Typography>
              </Box>
            ))}
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}