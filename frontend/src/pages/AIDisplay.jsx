import React, { useEffect, useState } from "react";
import {
  Box,
  Button,
  Chip,
  LinearProgress,
  Typography,
} from "@mui/material";
import FullscreenRoundedIcon from "@mui/icons-material/FullscreenRounded";
import FullscreenExitRoundedIcon from "@mui/icons-material/FullscreenExitRounded";

const API =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

function formatTime(seconds) {
  const safe = Math.max(
    0,
    Math.floor(Number(seconds) || 0)
  );

  const minutes = Math.floor(safe / 60);
  const remainingSeconds = safe % 60;

  return `${String(minutes).padStart(
    2,
    "0"
  )}:${String(remainingSeconds).padStart(2, "0")}`;
}

export default function AIDisplay() {
  const [session, setSession] = useState(null);
  const [isFullscreen, setIsFullscreen] =
    useState(false);
  const [error, setError] = useState("");

  async function loadSession() {
    try {
      const response = await fetch(
        `${API}/api/ai/live-session`
      );

      if (!response.ok) {
        throw new Error(
          `Unable to load live session: ${response.status}`
        );
      }

      const data = await response.json();

      setSession(data);
      setError("");
    } catch (err) {
      console.error(err);
      setError("Waiting for the AI Trainer connection.");
    }
  }

  async function toggleFullscreen() {
    try {
      const display =
        document.getElementById("tng-tv-display");

      if (!display) {
        return;
      }

      if (!document.fullscreenElement) {
        await display.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch (err) {
      console.error("Fullscreen failed:", err);
    }
  }

  useEffect(() => {
    loadSession();

    const interval = window.setInterval(
      loadSession,
      1000
    );

    return () => {
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    function handleFullscreenChange() {
      setIsFullscreen(
        Boolean(document.fullscreenElement)
      );
    }

    document.addEventListener(
      "fullscreenchange",
      handleFullscreenChange
    );

    return () => {
      document.removeEventListener(
        "fullscreenchange",
        handleFullscreenChange
      );
    };
  }, []);

  useEffect(() => {
    function handleKeyDown(event) {
      const key = event.key.toLowerCase();

      if (
        (key === "f" || event.key === "F11") &&
        !event.repeat
      ) {
        event.preventDefault();
        toggleFullscreen();
      }
    }

    window.addEventListener(
      "keydown",
      handleKeyDown
    );

    return () => {
      window.removeEventListener(
        "keydown",
        handleKeyDown
      );
    };
  }, []);

  const timeLeft =
    Number(session?.time_left) || 0;

  const totalRounds =
    Number(session?.total_rounds) || 0;

  const currentRound =
    Number(session?.round) || 0;

  const phase =
    session?.phase || "Ready";

  const prompt =
    session?.prompt || "Waiting for coach";

  const subPrompt =
    session?.sub_prompt ||
    "Start the AI Trainer to begin the workout.";

  const moduleName =
    session?.module || "Waiting";

  const progress =
    Number(session?.progress) || 0;

  return (
    <Box
      id="tng-tv-display"
      sx={{
        width: "100%",
        height: isFullscreen
          ? "100vh"
          : "calc(100vh - 140px)",
        minHeight: 620,
        background:
          "radial-gradient(circle at top, #2a0000 0%, #050506 55%, #000000 100%)",
        color: "white",
        position: "relative",
        overflowY: "auto",
        overflowX: "hidden",
        boxSizing: "border-box",
      }}
    >
      <Box
        sx={{
          width: "100%",
          minHeight: "100%",
          px: {
            xs: 2,
            sm: 3,
            md: 5,
          },
          py: {
            xs: 2,
            md: 3,
          },
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "flex-start",
          textAlign: "center",
          boxSizing: "border-box",
        }}
      >
        <Box
          sx={{
            width: "100%",
            display: "flex",
            justifyContent: "flex-end",
            mb: {
              xs: 1,
              md: 0,
            },
          }}
        >
          <Button
            variant="contained"
            color="error"
            size="large"
            startIcon={
              isFullscreen ? (
                <FullscreenExitRoundedIcon />
              ) : (
                <FullscreenRoundedIcon />
              )
            }
            onClick={toggleFullscreen}
            sx={{
              minWidth: {
                xs: 150,
                md: 190,
              },
              minHeight: {
                xs: 44,
                md: 52,
              },
              fontSize: {
                xs: "0.8rem",
                md: "0.95rem",
              },
              fontWeight: 900,
              borderRadius: 2.5,
            }}
          >
            {isFullscreen
              ? "Exit Fullscreen"
              : "Fullscreen TV"}
          </Button>
        </Box>

        <Typography
          sx={{
            fontSize:
              "clamp(26px, 3vw, 46px)",
            fontWeight: 950,
            letterSpacing:
              "clamp(1px, 0.2vw, 3px)",
            lineHeight: 1,
            mb: 1.5,
          }}
        >
          TNG COACH AI
        </Typography>

        <Chip
          label={moduleName}
          color="error"
          sx={{
            mx: "auto",
            fontSize:
              "clamp(14px, 1.4vw, 22px)",
            fontWeight: 900,
            height:
              "clamp(36px, 4vw, 48px)",
            px: 2,
            mb: 1.5,
          }}
        />

        <Typography
          sx={{
            fontSize:
              "clamp(22px, 2.5vw, 38px)",
            fontWeight: 900,
            lineHeight: 1.1,
          }}
        >
          ROUND {currentRound} / {totalRounds}
        </Typography>

        <Typography
          sx={{
            fontSize:
              "clamp(26px, 3vw, 44px)",
            fontWeight: 950,
            color: "#ff4b4b",
            mt: 0.5,
            lineHeight: 1.1,
            textTransform: "uppercase",
          }}
        >
          {phase}
        </Typography>

        <Typography
          sx={{
            fontSize:
              "clamp(78px, 13vh, 170px)",
            fontWeight: 1000,
            lineHeight: 0.9,
            my: {
              xs: 2,
              md: 2.5,
            },
            fontVariantNumeric: "tabular-nums",
            textShadow:
              "0 8px 30px rgba(0,0,0,.65)",
          }}
        >
          {formatTime(timeLeft)}
        </Typography>

        <LinearProgress
          variant="determinate"
          value={Math.min(
            100,
            Math.max(0, progress)
          )}
          color="error"
          sx={{
            height: {
              xs: 8,
              md: 12,
            },
            borderRadius: 999,
            backgroundColor: "#333333",
            maxWidth: 1100,
            width: "100%",
            mb: {
              xs: 2,
              md: 2.5,
            },
          }}
        />

        <Box
          sx={{
            border: {
              xs: "2px solid #d71920",
              md: "4px solid #d71920",
            },
            background:
              "rgba(0,0,0,0.62)",
            borderRadius: {
              xs: 3,
              md: 5,
            },
            px: {
              xs: 2,
              sm: 4,
              md: 5,
            },
            py: {
              xs: 2,
              md: 3,
            },
            maxWidth: 1300,
            width: "100%",
            minHeight: {
              xs: 130,
              md: 160,
            },
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxSizing: "border-box",
            boxShadow:
              "0 16px 40px rgba(0,0,0,.5)",
          }}
        >
          <Typography
            sx={{
              fontSize:
                "clamp(32px, 5vw, 78px)",
              fontWeight: 1000,
              lineHeight: 1.05,
              textTransform: "uppercase",
              overflowWrap: "anywhere",
            }}
          >
            {prompt}
          </Typography>
        </Box>

        <Typography
          sx={{
            fontSize:
              "clamp(16px, 2vw, 28px)",
            color: "#d5d5d5",
            mt: {
              xs: 1.5,
              md: 2,
            },
            mb: 1,
            fontWeight: 700,
            lineHeight: 1.25,
            maxWidth: 1200,
            px: 2,
          }}
        >
          {subPrompt}
        </Typography>

        {error && (
          <Typography
            sx={{
              color: "#ff8a8a",
              fontSize:
                "clamp(13px, 1.2vw, 17px)",
              mt: 1,
            }}
          >
            {error}
          </Typography>
        )}

        <Typography
          sx={{
            color: "rgba(255,255,255,.45)",
            fontSize: 12,
            mt: "auto",
            pt: 1,
          }}
        >
          Press F or F11 for fullscreen
        </Typography>
      </Box>
    </Box>
  );
}