import React, { useEffect, useRef, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  TextField,
  Select,
  MenuItem,
  Stack,
  Divider,
} from "@mui/material";

const combos = {
  beginner: ["1", "1, 2", "1, 1, 2", "jab, cross", "double jab, cross"],
  intermediate: ["1, 2, 3, 2", "1, 1, 2, roll", "2, 3, 2", "feint jab, 2, 3"],
  advanced: ["1, 2, 3, 6, 3, 2", "double jab, 2, slip, 3, 2", "pull counter 2"],
};

const modes = {
  boxing: ["Heavy Bag", "Shadowboxing", "Defense", "Footwork", "Conditioning"],
  sports: ["Agility", "Balance", "Strength", "Explosive Power"],
  health: ["Warm Up", "Core", "Mobility", "Recovery"],
};

export default function AITrainer() {
  const [category, setCategory] = useState("boxing");
  const [mode, setMode] = useState("Heavy Bag");
  const [level, setLevel] = useState("intermediate");
  const [rounds, setRounds] = useState(6);
  const [roundTime, setRoundTime] = useState(180);
  const [restTime, setRestTime] = useState(60);
  const [currentRound, setCurrentRound] = useState(0);
  const [phase, setPhase] = useState("Ready");
  const [timeLeft, setTimeLeft] = useState(0);
  const [prompt, setPrompt] = useState("Press Start");
  const [running, setRunning] = useState(false);
  const [paused, setPaused] = useState(false);
  const timerRef = useRef(null);
  const promptRef = useRef(null);

  function speak(text) {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
  }

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }

  function nextPrompt() {
    const pool = combos[level] || combos.intermediate;
    const text = pool[Math.floor(Math.random() * pool.length)];
    setPrompt(text);
    speak(text);
  }

  function clearTimers() {
    if (timerRef.current) clearInterval(timerRef.current);
    if (promptRef.current) clearInterval(promptRef.current);
  }

  function startRound(roundNumber) {
    setCurrentRound(roundNumber);
    setPhase("Fight");
    setTimeLeft(Number(roundTime));
    setPrompt(`Round ${roundNumber} - ${mode}`);
    speak(`Round ${roundNumber}, ${mode}, begin`);

    promptRef.current = setInterval(() => {
      if (!paused) nextPrompt();
    }, 10000);

    timerRef.current = setInterval(() => {
      setTimeLeft((old) => {
        if (paused) return old;

        if (old <= 1) {
          clearTimers();

          if (roundNumber >= Number(rounds)) {
            setPhase("Complete");
            setRunning(false);
            setPrompt("Workout Complete");
            speak("Workout complete");
            return 0;
          }

          startRest(roundNumber);
          return 0;
        }

        if (old === 10) speak("10 seconds");

        return old - 1;
      });
    }, 1000);
  }

  function startRest(roundNumber) {
    setPhase("Rest");
    setTimeLeft(Number(restTime));
    setPrompt("Rest");
    speak("Rest");

    timerRef.current = setInterval(() => {
      setTimeLeft((old) => {
        if (paused) return old;

        if (old <= 1) {
          clearTimers();
          startRound(roundNumber + 1);
          return 0;
        }

        if (old === 10) speak("10 seconds");

        return old - 1;
      });
    }, 1000);
  }

  function startSession() {
    clearTimers();
    setRunning(true);
    setPaused(false);
    startRound(1);
  }

  function pauseSession() {
    setPaused(true);
    setPhase("Paused");
    window.speechSynthesis?.cancel();
  }

  function resumeSession() {
    setPaused(false);
    setPhase("Fight");
    speak("Resume");
  }

  function resetSession() {
    clearTimers();
    setRunning(false);
    setPaused(false);
    setCurrentRound(0);
    setPhase("Ready");
    setTimeLeft(0);
    setPrompt("Press Start");
    window.speechSynthesis?.cancel();
  }

  useEffect(() => {
    setMode(modes[category][0]);
  }, [category]);

  useEffect(() => {
    return () => clearTimers();
  }, []);

  return (
    <Box>
      <Typography variant="h4" fontWeight="bold" sx={{ mb: 2 }}>
        🤖 TNG AI Trainer
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
          <Card sx={{ borderRadius: 3 }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold">
                Coach Controls
              </Typography>
              <Divider sx={{ my: 2 }} />

              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography>Category</Typography>
                  <Select fullWidth value={category} onChange={(e) => setCategory(e.target.value)}>
                    <MenuItem value="boxing">Boxing</MenuItem>
                    <MenuItem value="sports">Sports Performance</MenuItem>
                    <MenuItem value="health">General Health</MenuItem>
                  </Select>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography>Mode</Typography>
                  <Select fullWidth value={mode} onChange={(e) => setMode(e.target.value)}>
                    {modes[category].map((m) => (
                      <MenuItem key={m} value={m}>{m}</MenuItem>
                    ))}
                  </Select>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography>Skill Level</Typography>
                  <Select fullWidth value={level} onChange={(e) => setLevel(e.target.value)}>
                    <MenuItem value="beginner">Beginner</MenuItem>
                    <MenuItem value="intermediate">Intermediate</MenuItem>
                    <MenuItem value="advanced">Advanced</MenuItem>
                  </Select>
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField fullWidth label="Rounds" type="number" value={rounds} onChange={(e) => setRounds(e.target.value)} />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField fullWidth label="Round Time Seconds" type="number" value={roundTime} onChange={(e) => setRoundTime(e.target.value)} />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField fullWidth label="Rest Time Seconds" type="number" value={restTime} onChange={(e) => setRestTime(e.target.value)} />
                </Grid>
              </Grid>

              <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mt: 3 }}>
                <Button variant="contained" color="error" onClick={startSession}>
                  Start Session
                </Button>
                <Button variant="outlined" color="error" onClick={pauseSession}>
                  Pause
                </Button>
                <Button variant="outlined" color="success" onClick={resumeSession}>
                  Resume
                </Button>
                <Button variant="outlined" color="warning" onClick={resetSession}>
                  Reset
                </Button>
                <Button variant="contained" color="success" onClick={nextPrompt} disabled={!running}>
                  Next Prompt
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={5}>
          <Card sx={{ borderRadius: 3, background: "#111", color: "white" }}>
            <CardContent sx={{ textAlign: "center", p: 4 }}>
              <Typography variant="h6">
                ROUND {currentRound} / {rounds}
              </Typography>

              <Typography variant="h5" sx={{ mt: 2 }}>
                {phase}
              </Typography>

              <Typography variant="h1" fontWeight="bold" sx={{ my: 3 }}>
                {formatTime(timeLeft)}
              </Typography>

              <Box
                sx={{
                  background: "#222",
                  p: 3,
                  borderRadius: 3,
                  minHeight: 120,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Typography variant="h4" fontWeight="bold">
                  {prompt}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}