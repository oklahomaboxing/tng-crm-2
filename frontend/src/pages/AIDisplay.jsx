import React, { useEffect, useState } from "react";
import { Box, Typography, Chip, LinearProgress } from "@mui/material";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function formatTime(seconds) {
  const safe = Math.max(0, Number(seconds) || 0);
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export default function AIDisplay() {
  const [session, setSession] = useState(null);

  async function loadSession() {
    try {
      const res = await fetch(`${API}/api/ai/live-session`);
      const data = await res.json();
      setSession(data);
    } catch (err) {
      console.log(err);
    }
  }

  useEffect(() => {
    loadSession();
    const interval = setInterval(loadSession, 1000);
    return () => clearInterval(interval);
  }, []);

  const timeLeft = session?.time_left || 0;
  const totalRounds = session?.total_rounds || 0;
  const currentRound = session?.round || 0;

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background: "radial-gradient(circle at top, #2a0000, #050506 55%)",
        color: "white",
        p: 5,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        textAlign: "center",
      }}
    >
      <Typography
        sx={{
          fontSize: 42,
          fontWeight: 900,
          letterSpacing: 2,
          mb: 2,
        }}
      >
        TNG COACH AI
      </Typography>

      <Chip
        label={session?.module || "Waiting"}
        color="error"
        sx={{
          mx: "auto",
          fontSize: 24,
          height: 48,
          px: 3,
          mb: 3,
        }}
      />

      <Typography sx={{ fontSize: 36, fontWeight: 800 }}>
        ROUND {currentRound} / {totalRounds}
      </Typography>

      <Typography sx={{ fontSize: 40, fontWeight: 800, color: "#ff4b4b", mt: 1 }}>
        {session?.phase || "Ready"}
      </Typography>

      <Typography
        sx={{
          fontSize: { xs: 90, md: 160 },
          fontWeight: 1000,
          lineHeight: 1,
          my: 4,
        }}
      >
        {formatTime(timeLeft)}
      </Typography>

      <LinearProgress
        variant="determinate"
        value={0}
        color="error"
        sx={{
          height: 12,
          borderRadius: 999,
          background: "#333",
          maxWidth: 900,
          width: "100%",
          mx: "auto",
          mb: 4,
        }}
      />

      <Box
        sx={{
          border: "3px solid #d71920",
          background: "rgba(0,0,0,.55)",
          borderRadius: 5,
          p: 5,
          maxWidth: 1200,
          mx: "auto",
          minHeight: 220,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Typography
          sx={{
            fontSize: { xs: 44, md: 76 },
            fontWeight: 1000,
            lineHeight: 1.1,
          }}
        >
          {session?.prompt || "Waiting for coach"}
        </Typography>
      </Box>

      <Typography
        sx={{
          fontSize: 28,
          color: "#cfcfcf",
          mt: 3,
        }}
      >
        {session?.sub_prompt || "Open this page on every gym TV."}
      </Typography>
    </Box>
  );
}