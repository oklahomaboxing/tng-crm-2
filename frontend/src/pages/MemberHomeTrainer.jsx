import { useEffect, useRef, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  FormControl,
  Grid,
  MenuItem,
  Select,
  Stack,
  Switch,
  Typography,
} from "@mui/material";

import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import PauseRoundedIcon from "@mui/icons-material/PauseRounded";
import StopRoundedIcon from "@mui/icons-material/StopRounded";
import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";

const COMBOS = {
  beginner: [
    [1, 2],
    [1, 1, 2],
    [1, 3, 2],
    [2, 3, 2],
  ],
  intermediate: [
    [1, 2, 3, 2],
    [1, 2, 5, 2],
    [1, 3, 2],
    [2, 3, 2],
    [6, 3, 2],
    [1, 1, 2, 3, 2],
  ],
  advanced: [
    [1, 2, 3, 2],
    [1, 2, 5, 2],
    [6, 3, 2],
    [1, 1, 2, 5, 2],
    [2, 3, 6, 3, 2],
    [1, 2, 3, 6, 3, 2],
  ],
};

const FOOTWORK = [
  "Step forward, step back",
  "Step left, step right",
  "Pivot left",
  "Pivot right",
  "Circle left",
  "Circle right",
  "Step right and reset",
  "Step left and reset",
];

const CONDITIONING = [
  "1, 2 nonstop",
  "1, 2, 3, 2 repeat",
  "Straight punches",
  "Body shots",
  "Hooks",
  "Uppercuts",
  "Fast 1, 2",
  "Six punch burst",
];

function movementAfter(lastPunch, index) {
  if (index % 5 === 4) {
    return "bob";
  }

  const direction =
    [2, 4, 6].includes(Number(lastPunch))
      ? "right"
      : "left";

  const movement =
    ["roll", "slip", "step"][index % 3];

  return `${movement} ${direction}`;
}

function counterAfter(lastPunch) {
  return [2, 4, 6].includes(Number(lastPunch))
    ? "2, 3"
    : "3, 2";
}

function boxingPrompt(level, index) {
  const pool = COMBOS[level] || COMBOS.intermediate;
  const combo = pool[index % pool.length];
  const comboText = combo.join(", ");

  if (index % 2 === 0) {
    return comboText;
  }

  const lastPunch = combo[combo.length - 1];

  return `${comboText}, ${movementAfter(
    lastPunch,
    index
  )}, ${counterAfter(lastPunch)}`;
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = String(seconds % 60).padStart(2, "0");
  return `${mins}:${secs}`;
}

export default function MemberHomeTrainer() {
  const [workout, setWorkout] = useState("Shadowboxing");
  const [level, setLevel] = useState("beginner");
  const [rounds, setRounds] = useState(3);
  const [roundMinutes, setRoundMinutes] = useState(2);
  const [voiceEnabled, setVoiceEnabled] = useState(true);

  const [running, setRunning] = useState(false);
  const [paused, setPaused] = useState(false);
  const [phase, setPhase] = useState("Ready");
  const [currentRound, setCurrentRound] = useState(0);
  const [timeLeft, setTimeLeft] = useState(0);
  const [prompt, setPrompt] = useState("Ready to train");
  const [nextPrompt, setNextPrompt] = useState("");
  const [commandIndex, setCommandIndex] = useState(0);

  const timerRef = useRef(null);
  const promptRef = useRef(null);
  const commandIndexRef = useRef(0);
  const stateRef = useRef({
    running: false,
    paused: false,
    phase: "Ready",
    round: 0,
  });

  function speak(text) {
    if (!voiceEnabled) return;
    if (!("speechSynthesis" in window)) return;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.9;
    utterance.pitch = 0.95;
    utterance.volume = 1;

    window.speechSynthesis.speak(utterance);
  }

  function getPrompt(index) {
    if (workout === "Footwork") {
      return FOOTWORK[index % FOOTWORK.length];
    }

    if (workout === "Boxing Conditioning") {
      return CONDITIONING[index % CONDITIONING.length];
    }

    return boxingPrompt(level, index);
  }

  function callNextPrompt() {
    const index = commandIndexRef.current;
    const next = getPrompt(index);
    const upcoming = getPrompt(index + 1);

    setPrompt(next);
    setNextPrompt(upcoming);

    commandIndexRef.current = index + 1;
    setCommandIndex(index + 1);

    speak(next);
  }

  function clearTimers() {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    if (promptRef.current) {
      clearInterval(promptRef.current);
      promptRef.current = null;
    }
  }

  function stopWorkout() {
    clearTimers();

    stateRef.current = {
      running: false,
      paused: false,
      phase: "Ready",
      round: 0,
    };

    setRunning(false);
    setPaused(false);
    setPhase("Ready");
    setCurrentRound(0);
    setTimeLeft(0);
    commandIndexRef.current = 0;
    setCommandIndex(0);
    setPrompt("Ready to train");
    setNextPrompt("");

    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }

  function startRound(roundNumber) {
    const seconds = Number(roundMinutes) * 60;

    stateRef.current.phase = "Work";
    stateRef.current.round = roundNumber;

    setPhase("Work");
    setCurrentRound(roundNumber);
    setTimeLeft(seconds);

    commandIndexRef.current = 0;
    setCommandIndex(0);

    speak(`Round ${roundNumber}. Begin.`);

    setTimeout(() => {
      if (stateRef.current.running) {
        callNextPrompt();
      }
    }, 900);

    promptRef.current = setInterval(() => {
      if (
        stateRef.current.running &&
        !stateRef.current.paused &&
        stateRef.current.phase === "Work"
      ) {
        callNextPrompt();
      }
    }, 12000);
  }

  function startRest(roundNumber) {
    if (promptRef.current) {
      clearInterval(promptRef.current);
      promptRef.current = null;
    }

    stateRef.current.phase = "Rest";

    setPhase("Rest");
    setTimeLeft(30);
    setPrompt("Rest");
    setNextPrompt(
      roundNumber < Number(rounds)
        ? `Round ${roundNumber + 1}`
        : "Workout complete"
    );

    speak("Rest. Breathe and reset.");
  }

  function startWorkout() {
    clearTimers();

    stateRef.current.running = true;
    stateRef.current.paused = false;

    setRunning(true);
    setPaused(false);

    startRound(1);

    timerRef.current = setInterval(() => {
      if (
        !stateRef.current.running ||
        stateRef.current.paused
      ) {
        return;
      }

      setTimeLeft((old) => {
        if (old > 1) {
          return old - 1;
        }

        const roundNumber = stateRef.current.round;

        if (stateRef.current.phase === "Work") {
          startRest(roundNumber);
          return 30;
        }

        if (roundNumber >= Number(rounds)) {
          setTimeout(() => {
            speak("Workout complete. Good work.");
            stopWorkout();
          }, 50);

          return 0;
        }

        setTimeout(() => {
          startRound(roundNumber + 1);
        }, 50);

        return Number(roundMinutes) * 60;
      });
    }, 1000);
  }

  function togglePause() {
    const nextPaused = !paused;

    stateRef.current.paused = nextPaused;
    setPaused(nextPaused);

    if (nextPaused) {
      speak("Pause");
    } else {
      speak("Resume");
    }
  }

  useEffect(() => {
    stateRef.current.running = running;
    stateRef.current.paused = paused;
    stateRef.current.phase = phase;
    stateRef.current.round = currentRound;
  }, [running, paused, phase, currentRound]);

  useEffect(() => {
    return () => clearTimers();
  }, []);

  return (
    <Card
      sx={{
        borderRadius: 4,
        bgcolor: "#09090b",
        color: "white",
      }}
    >
      <CardContent sx={{ p: { xs: 2.5, md: 4 } }}>
        <Stack spacing={3}>
          <Box>
            <Stack
              direction="row"
              spacing={1.5}
              alignItems="center"
            >
              <SportsMmaRoundedIcon color="error" />
              <Typography variant="h4" fontWeight={950}>
                TNGTrainer Home
              </Typography>
            </Stack>

            <Typography sx={{ color: "grey.400", mt: 1 }}>
              Train anywhere with TNG Boxing combinations,
              movement and voice coaching.
            </Typography>
          </Box>

          {!running && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Typography
                  variant="caption"
                  sx={{ color: "grey.400" }}
                >
                  Workout
                </Typography>

                <FormControl fullWidth>
                  <Select
                    value={workout}
                    onChange={(e) =>
                      setWorkout(e.target.value)
                    }
                    sx={{
                      bgcolor: "white",
                      mt: 0.5,
                    }}
                  >
                    <MenuItem value="Shadowboxing">
                      Shadowboxing
                    </MenuItem>

                    <MenuItem value="Boxing Conditioning">
                      Boxing Conditioning
                    </MenuItem>

                    <MenuItem value="Footwork">
                      Footwork
                    </MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} sm={6}>
                <Typography
                  variant="caption"
                  sx={{ color: "grey.400" }}
                >
                  Level
                </Typography>

                <FormControl fullWidth>
                  <Select
                    value={level}
                    onChange={(e) =>
                      setLevel(e.target.value)
                    }
                    sx={{
                      bgcolor: "white",
                      mt: 0.5,
                    }}
                  >
                    <MenuItem value="beginner">
                      Beginner
                    </MenuItem>

                    <MenuItem value="intermediate">
                      Intermediate
                    </MenuItem>

                    <MenuItem value="advanced">
                      Advanced
                    </MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={6}>
                <Typography
                  variant="caption"
                  sx={{ color: "grey.400" }}
                >
                  Rounds
                </Typography>

                <FormControl fullWidth>
                  <Select
                    value={rounds}
                    onChange={(e) =>
                      setRounds(Number(e.target.value))
                    }
                    sx={{
                      bgcolor: "white",
                      mt: 0.5,
                    }}
                  >
                    {[3, 6, 8, 10].map((value) => (
                      <MenuItem key={value} value={value}>
                        {value}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={6}>
                <Typography
                  variant="caption"
                  sx={{ color: "grey.400" }}
                >
                  Round Time
                </Typography>

                <FormControl fullWidth>
                  <Select
                    value={roundMinutes}
                    onChange={(e) =>
                      setRoundMinutes(
                        Number(e.target.value)
                      )
                    }
                    sx={{
                      bgcolor: "white",
                      mt: 0.5,
                    }}
                  >
                    {[1, 2, 3].map((value) => (
                      <MenuItem key={value} value={value}>
                        {value} min
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <Stack
                  direction="row"
                  alignItems="center"
                  justifyContent="space-between"
                  sx={{
                    bgcolor: "rgba(255,255,255,.06)",
                    borderRadius: 2,
                    px: 2,
                    py: 1,
                  }}
                >
                  <Typography fontWeight={800}>
                    Voice Coach
                  </Typography>

                  <Switch
                    checked={voiceEnabled}
                    onChange={(e) =>
                      setVoiceEnabled(e.target.checked)
                    }
                    color="error"
                  />
                </Stack>
              </Grid>
            </Grid>
          )}

          {running && (
            <Stack
              spacing={2}
              alignItems="center"
              textAlign="center"
              sx={{
                py: 3,
                borderRadius: 3,
                bgcolor: "rgba(255,255,255,.05)",
              }}
            >
              <Stack
                direction="row"
                spacing={1}
                flexWrap="wrap"
                justifyContent="center"
              >
                <Chip
                  label={`ROUND ${currentRound}/${rounds}`}
                  color="error"
                />

                <Chip
                  label={phase.toUpperCase()}
                  sx={{
                    bgcolor:
                      phase === "Rest"
                        ? "#f59e0b"
                        : "white",
                    color: "black",
                    fontWeight: 900,
                  }}
                />
              </Stack>

              <Typography
                sx={{
                  fontSize: {
                    xs: "3.8rem",
                    md: "5rem",
                  },
                  fontWeight: 950,
                  lineHeight: 1,
                }}
              >
                {formatTime(timeLeft)}
              </Typography>

              <Typography
                sx={{
                  fontSize: {
                    xs: "1.8rem",
                    md: "2.6rem",
                  },
                  fontWeight: 950,
                  minHeight: 70,
                }}
              >
                {prompt}
              </Typography>

              {nextPrompt && (
                <Typography sx={{ color: "grey.400" }}>
                  Next: {nextPrompt}
                </Typography>
              )}
            </Stack>
          )}

          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1.5}
          >
            {!running ? (
              <Button
                fullWidth
                size="large"
                variant="contained"
                color="error"
                startIcon={<PlayArrowRoundedIcon />}
                onClick={startWorkout}
                sx={{
                  py: 1.5,
                  fontWeight: 900,
                }}
              >
                Start Workout
              </Button>
            ) : (
              <>
                <Button
                  fullWidth
                  size="large"
                  variant="contained"
                  onClick={togglePause}
                  startIcon={
                    paused
                      ? <PlayArrowRoundedIcon />
                      : <PauseRoundedIcon />
                  }
                  sx={{
                    py: 1.5,
                    fontWeight: 900,
                  }}
                >
                  {paused ? "Resume" : "Pause"}
                </Button>

                <Button
                  fullWidth
                  size="large"
                  variant="outlined"
                  color="error"
                  onClick={stopWorkout}
                  startIcon={<StopRoundedIcon />}
                  sx={{
                    py: 1.5,
                    fontWeight: 900,
                  }}
                >
                  Stop
                </Button>
              </>
            )}
          </Stack>

          <Typography
            variant="caption"
            sx={{ color: "grey.500" }}
          >
            Train in a clear area with enough room to move safely.
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}
