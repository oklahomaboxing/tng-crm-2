import React, { useEffect, useMemo, useRef, useState } from "react";

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
  Chip,
  Slider,
  LinearProgress,
} from "@mui/material";
const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const TRAINING_MODULES = {
  "Heavy Bag": {
    category: "Boxing",
    defaultRounds: 6,
    roundTime: 180,
    restTime: 60,
    focus: "Power, rhythm, punch selection, and ring control.",
  },
  Shadowboxing: {
    category: "Boxing",
    defaultRounds: 6,
    roundTime: 180,
    restTime: 45,
    focus: "Movement, balance, defense, and clean technique.",
  },
  "Defense / Reaction": {
    category: "Boxing",
    defaultRounds: 6,
    roundTime: 180,
    restTime: 45,
    focus: "Slip, roll, parry, counter, and exit safely.",
  },
  Footwork: {
    category: "Boxing",
    defaultRounds: 8,
    roundTime: 60,
    restTime: 20,
    focus: "Angles, pivots, stance control, and ring position.",
  },
  "Boxing Conditioning": {
    category: "Boxing",
    defaultRounds: 10,
    roundTime: 45,
    restTime: 15,
    focus: "High output, repeat sprint ability, and punch endurance.",
  },
  "Dynamic Warm-Up": {
    category: "Preparation",
    defaultRounds: 6,
    roundTime: 60,
    restTime: 15,
    focus: "Raise temperature, loosen joints, and prepare movement.",
  },
  Core: {
    category: "Strength",
    defaultRounds: 8,
    roundTime: 45,
    restTime: 15,
    focus: "Trunk control, bracing, rotation, and durability.",
  },
  "Fight Camp Progressive": {
    category: "Fight Camp",
    defaultRounds: 7,
    roundTime: 180,
    restTime: 45,
    focus: "Automatic round-by-round camp structure.",
  },
  "Ring IQ": {
    category: "Boxing IQ",
    defaultRounds: 6,
    roundTime: 180,
    restTime: 45,
    focus: "Situational thinking, reactions, and tactical decisions.",
  },
};

const FIGHT_CAMP_FLOW = [
  "Dynamic Warm-Up",
  "Footwork",
  "Heavy Bag",
  "Defense / Reaction",
  "Boxing Conditioning",
  "Core",
  "Ring IQ",
];

const PROMPTS = {
  orthodox: {
    beginner: {
      combo: [
        "1",
        "1, 2",
        "1, 1, 2",
        "jab, cross",
        "double jab, cross",
        "jab, cross, step right",
        "jab, cross, hook, move",
        "check hook, pivot",
      ],
      advancedAction: [
        "hands back to your face",
        "finish with your feet",
        "do not admire your work",
        "reset your stance",
      ],
    },
    intermediate: {
      combo: [
        "1, 2, 3, 2",
        "1, 1, 2, roll left",
        "2, 3, 2, roll right",
        "feint jab, 2, 3",
        "1, 2, slip, 2, 3, 2",
        "slip right, 2, 3, check hook",
        "parry jab, 2",
        "catch, 3, 2",
      ],
      advancedAction: [
        "angle out after the last shot",
        "touch the body then come upstairs",
        "change speed on the entry",
        "finish outside the center line",
      ],
    },
    advanced: {
      combo: [
        "1, 2, 3, 6, 3, 2",
        "double jab, 2, slip, 6, 3, 2",
        "1, 2, roll, 2, 3, 2",
        "feint, 1, 2, slip, roll, 3, 2",
        "pull counter 2",
        "check hook, 2, 3",
        "parry, 2, 3, move",
        "slip, counter 2, 3",
      ],
      advancedAction: [
        "set a trap before you throw",
        "draw the jab and counter",
        "cut the ring after the exchange",
        "finish with a defensive exit",
      ],
    },
  },
  southpaw: {
    beginner: {
      combo: [
        "right jab",
        "right jab, left cross",
        "double jab, cross",
        "feint jab, cross",
        "slip right, cross",
        "check hook, pivot",
      ],
      advancedAction: [
        "keep your lead foot outside",
        "reset your stance",
        "hands back high",
        "move after the cross",
      ],
    },
    intermediate: {
      combo: [
        "jab, cross, hook, cross",
        "cross, hook, cross",
        "feint jab, cross, hook",
        "slip, cross, hook",
        "pull counter cross",
      ],
      advancedAction: [
        "win the lead foot battle",
        "angle after the left hand",
        "touch the body then exit",
        "make them miss then answer",
      ],
    },
    advanced: {
      combo: [
        "jab, cross, hook, uppercut, hook, cross",
        "jab, cross, hook, uppercut, hook, cross, pivot",
        "slip, cross, hook, cross",
        "feint jab, cross, hook, cross",
        "slip, hook to the body, cross upstairs",
      ],
      advancedAction: [
        "dominate outside foot position",
        "counter over the jab",
        "turn them after the exchange",
        "finish with pressure and control",
      ],
    },
  },
};

const DEFENSE_PROMPTS = [
  "slip left, counter and move",
  "slip right, answer back and reset",
  "half step back, return and move",
  "catch and counter",
  "check hook and pivot",
  "parry and respond",
  "slip, roll, and move out",
  "block, return, angle out",
];

const FOOTWORK_PROMPTS = [
  "step forward, step back",
  "step left, step right",
  "jab, step back",
  "jab, pivot left",
  "step outside and reset",
  "circle both directions",
  "angle step and reset",
  "cut the ring, do not follow",
];

const CONDITIONING_PROMPTS = [
  "straight punches nonstop",
  "body shots only",
  "fast jab cross pace",
  "hooks only",
  "uppercuts only",
  "10 second sprint flurry",
  "squat and fire 6 punches",
  "maximum output, stay clean",
];

const WARMUP_PROMPTS = [
  "arm circles forward",
  "arm circles backward",
  "hip rotations",
  "high knees",
  "butt kicks",
  "torso twists",
  "step and reach",
  "light bounce on toes",
];

const CORE_PROMPTS = [
  "plank",
  "dead bug",
  "russian twists",
  "leg raises",
  "bicycle kicks",
  "side plank",
  "mountain climbers",
  "flutter kicks",
];

const RING_IQ_PROMPTS = [
  "Opponent is backing up. Cut the ring.",
  "Opponent is rushing in. Step back and counter.",
  "Opponent keeps jabbing. Slip outside and answer.",
  "Opponent is southpaw. Win lead foot position.",
  "You are on the ropes. Pivot out now.",
  "Opponent dropped the right hand. Check hook.",
  "Opponent is covering up. Touch body then head.",
  "You landed clean. Do not admire it. Exit.",
];

async function updateLiveDisplay(extra = {}) {
  await fetch(`${API}/api/ai/live-session`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + localStorage.getItem("token"),
    },
    body: JSON.stringify({
      active: runningRef.current,
      phase,
      round: currentRound,
      total_rounds: rounds,
      time_left: timeLeft,
      module: currentModuleRef.current,
      prompt,
      sub_prompt: subPrompt,
      ...extra,
    }),
    }).catch((err) => {
    console.error("Live display update failed", err);
  });
}

function randomFrom(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function formatTime(seconds) {
  const safe = Math.max(0, Number(seconds) || 0);
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export default function AITrainer() {
  const [selectedModule, setSelectedModule] = useState("Heavy Bag");
  const [stance, setStance] = useState("orthodox");
  const [level, setLevel] = useState("intermediate");
  const [rounds, setRounds] = useState(TRAINING_MODULES["Heavy Bag"].defaultRounds);
  const [roundTime, setRoundTime] = useState(TRAINING_MODULES["Heavy Bag"].roundTime);
  const [restTime, setRestTime] = useState(TRAINING_MODULES["Heavy Bag"].restTime);
  const [paceSeconds, setPaceSeconds] = useState(10);

  const [currentRound, setCurrentRound] = useState(0);
  const [phase, setPhase] = useState("Ready");
  const [timeLeft, setTimeLeft] = useState(0);
  const [prompt, setPrompt] = useState("Select a module and press Start");
  const [subPrompt, setSubPrompt] = useState("TNG Coach AI is ready.");
  const [running, setRunning] = useState(false);
  const [paused, setPaused] = useState(false);
  const [promptLog, setPromptLog] = useState([]);

  const timerRef = useRef(null);
  const promptRef = useRef(null);
  const pausedRef = useRef(false);
  const runningRef = useRef(false);
  const currentModuleRef = useRef(selectedModule);

  const moduleConfig = TRAINING_MODULES[selectedModule];

  const progress = useMemo(() => {
    const total = phase === "Rest" ? restTime : roundTime;
    if (!total || !timeLeft) return 0;
    return Math.max(0, Math.min(100, ((total - timeLeft) / total) * 100));
  }, [phase, restTime, roundTime, timeLeft]);

  function speak(text) {
    if (!("speechSynthesis" in window)) return;

    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1;
      utterance.pitch = 1;
      utterance.volume = 1;
      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.log("Voice failed", err);
    }
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

  function logPrompt(text) {
    setPromptLog((old) => [
      {
        time: new Date().toLocaleTimeString(),
        text,
      },
      ...old.slice(0, 24),
    ]);
  }

  function resolveActiveModule(roundNumber) {
    if (selectedModule === "Fight Camp Progressive") {
      return FIGHT_CAMP_FLOW[(roundNumber - 1) % FIGHT_CAMP_FLOW.length];
    }

    return selectedModule;
  }

  function generatePrompt(activeModule) {
    if (activeModule === "Defense / Reaction") {
      return randomFrom(DEFENSE_PROMPTS);
    }

    if (activeModule === "Footwork") {
      return randomFrom(FOOTWORK_PROMPTS);
    }

    if (activeModule === "Boxing Conditioning") {
      return randomFrom(CONDITIONING_PROMPTS);
    }

    if (activeModule === "Dynamic Warm-Up") {
      return randomFrom(WARMUP_PROMPTS);
    }

    if (activeModule === "Core") {
      return randomFrom(CORE_PROMPTS);
    }

    if (activeModule === "Ring IQ") {
      return randomFrom(RING_IQ_PROMPTS);
    }

    const combo = randomFrom(PROMPTS[stance][level].combo);
    const coaching = randomFrom(PROMPTS[stance][level].advancedAction);

    if (activeModule === "Shadowboxing") {
      return `${combo}, move, ${coaching}`;
    }

    return `${combo}, ${coaching}`;
  }

  function callPrompt(manual = false) {
    if (!runningRef.current) return;

    const activeModule = currentModuleRef.current;
    const next = generatePrompt(activeModule);

    setPrompt(next);
    setSubPrompt(manual ? "Manual coach command." : moduleConfig.focus);
    logPrompt(next);
    speak(next);
  }

  function startPromptLoop() {
    if (promptRef.current) clearInterval(promptRef.current);

    promptRef.current = setInterval(() => {
      if (!runningRef.current || pausedRef.current || phase === "Rest") return;
      callPrompt(false);
    }, Number(paceSeconds) * 1000);
  }

  function finishSession() {
    clearTimers();
    runningRef.current = false;
    pausedRef.current = false;

    setRunning(false);
    setPaused(false);
    setPhase("Complete");
    setTimeLeft(0);
    setPrompt("Workout Complete");
    setSubPrompt("Good work. Recover, hydrate, and log your notes.");
    speak("Workout complete");
  }

  function startRest(roundNumber) {
    clearTimers();

    setPhase("Rest");
    setTimeLeft(Number(restTime));
    setPrompt("Rest");
    setSubPrompt("Breathe, recover, and get ready for the next round.");
    speak("Rest");

    timerRef.current = setInterval(() => {
      setTimeLeft((old) => {
        if (pausedRef.current) return old;

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

  function startRound(roundNumber) {
    clearTimers();

    const activeModule = resolveActiveModule(roundNumber);
    currentModuleRef.current = activeModule;

    setCurrentRound(roundNumber);
    setPhase("Fight");
    setTimeLeft(Number(roundTime));
    setPrompt(`Round ${roundNumber}: ${activeModule}`);
    setSubPrompt(TRAINING_MODULES[activeModule]?.focus || "Boxing round active.");

    speak(`Round ${roundNumber}. ${activeModule}. Begin.`);
    startPromptLoop();

    timerRef.current = setInterval(() => {
      setTimeLeft((old) => {
        if (pausedRef.current) return old;

        if (old <= 1) {
          clearTimers();

          if (roundNumber >= Number(rounds)) {
            finishSession();
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

  function startSession() {
    clearTimers();

    runningRef.current = true;
    pausedRef.current = false;

    setPromptLog([]);
    setRunning(true);
    setPaused(false);
    setCurrentRound(1);

    startRound(1);
  }

  function pauseSession() {
    if (!runningRef.current) return;

    pausedRef.current = true;
    setPaused(true);
    setPhase("Paused");

    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }

  function resumeSession() {
    if (!runningRef.current) return;

    pausedRef.current = false;
    setPaused(false);
    setPhase("Fight");
    speak("Resume");
  }

  function resetSession() {
    clearTimers();

    runningRef.current = false;
    pausedRef.current = false;

    setRunning(false);
    setPaused(false);
    setCurrentRound(0);
    setPhase("Ready");
    setTimeLeft(0);
    setPrompt("Select a module and press Start");
    setSubPrompt("TNG Coach AI is ready.");
    setPromptLog([]);

    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }

  useEffect(() => {
    const config = TRAINING_MODULES[selectedModule];

    setRounds(config.defaultRounds);
    setRoundTime(config.roundTime);
    setRestTime(config.restTime);
    setPrompt(`${selectedModule} selected`);
    setSubPrompt(config.focus);

    currentModuleRef.current = selectedModule;
  }, [selectedModule]);

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  useEffect(() => {
    runningRef.current = running;
  }, [running]);

  useEffect(() => {
    return () => clearTimers();
  }, []);
useEffect(() => {
  updateLiveDisplay({
    active: running,
    phase,
    round: currentRound,
    total_rounds: rounds,
    time_left: timeLeft,
    module: currentModuleRef.current,
    prompt,
    sub_prompt: subPrompt,
  });
}, [running, phase, currentRound, rounds, timeLeft, prompt, subPrompt]);
  return (
    <Box>
      <Box
        sx={{
          background: "linear-gradient(135deg, #0b0b0f, #1a1a22)",
          color: "white",
          p: 3,
          borderRadius: 4,
          mb: 3,
          border: "1px solid #2a2a35",
        }}
      >
        <Typography variant="h4" fontWeight="bold">
          🤖 TNG Coach AI
        </Typography>

        <Typography sx={{ color: "#cfcfcf", mt: 1 }}>
          Advanced boxing training engine for TNG athletes, members, and fight camp development.
        </Typography>

        <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 2 }}>
          <Chip label="Boxing IQ" color="error" />
          <Chip label="Fight Camp" />
          <Chip label="Defense" />
          <Chip label="Footwork" />
          <Chip label="Conditioning" />
        </Stack>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} lg={4}>
          <Card sx={{ borderRadius: 4, height: "100%" }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold">
                Coach Controls
              </Typography>

              <Divider sx={{ my: 2 }} />

              <Stack spacing={2}>
                <Box>
                  <Typography fontWeight="bold">Training Module</Typography>
                  <Select
                    fullWidth
                    value={selectedModule}
                    onChange={(e) => setSelectedModule(e.target.value)}
                  >
                    {Object.keys(TRAINING_MODULES).map((module) => (
                      <MenuItem key={module} value={module}>
                        {module}
                      </MenuItem>
                    ))}
                  </Select>
                </Box>

                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography fontWeight="bold">Stance</Typography>
                    <Select
                      fullWidth
                      value={stance}
                      onChange={(e) => setStance(e.target.value)}
                    >
                      <MenuItem value="orthodox">Orthodox</MenuItem>
                      <MenuItem value="southpaw">Southpaw</MenuItem>
                    </Select>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Typography fontWeight="bold">Level</Typography>
                    <Select
                      fullWidth
                      value={level}
                      onChange={(e) => setLevel(e.target.value)}
                    >
                      <MenuItem value="beginner">Beginner</MenuItem>
                      <MenuItem value="intermediate">Intermediate</MenuItem>
                      <MenuItem value="advanced">Advanced</MenuItem>
                    </Select>
                  </Grid>
                </Grid>

                <Grid container spacing={2}>
                  <Grid item xs={12} md={4}>
                    <TextField
                      fullWidth
                      label="Rounds"
                      type="number"
                      value={rounds}
                      onChange={(e) => setRounds(e.target.value)}
                    />
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <TextField
                      fullWidth
                      label="Round Sec"
                      type="number"
                      value={roundTime}
                      onChange={(e) => setRoundTime(e.target.value)}
                    />
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <TextField
                      fullWidth
                      label="Rest Sec"
                      type="number"
                      value={restTime}
                      onChange={(e) => setRestTime(e.target.value)}
                    />
                  </Grid>
                </Grid>

                <Box>
                  <Typography fontWeight="bold">
                    Prompt Pace: {paceSeconds}s
                  </Typography>
                  <Slider
                    value={paceSeconds}
                    min={5}
                    max={30}
                    step={1}
                    onChange={(e, value) => setPaceSeconds(value)}
                  />
                </Box>

                <Stack direction="row" spacing={1} flexWrap="wrap">
                  <Button
                    variant="contained"
                    color="error"
                    onClick={startSession}
                  >
                    Start
                  </Button>

                  <Button
                    variant="outlined"
                    color="error"
                    onClick={pauseSession}
                  >
                    Pause
                  </Button>

                  <Button
                    variant="outlined"
                    color="success"
                    onClick={resumeSession}
                  >
                    Resume
                  </Button>

                  <Button
                    variant="outlined"
                    color="warning"
                    onClick={resetSession}
                  >
                    Reset
                  </Button>

                  <Button
                    variant="contained"
                    color="success"
                    onClick={() => callPrompt(true)}
                    disabled={!running}
                  >
                    Next Prompt
                  </Button>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} lg={5}>
          <Card
            sx={{
              borderRadius: 4,
              background: "#0b0b0f",
              color: "white",
              border: "1px solid #2a2a35",
              minHeight: 560,
            }}
          >
            <CardContent sx={{ textAlign: "center", p: 4 }}>
              <Stack direction="row" justifyContent="center" spacing={1} sx={{ mb: 2 }}>
                <Chip
                  label={`ROUND ${currentRound} / ${rounds}`}
                  color="error"
                />
                <Chip label={currentModuleRef.current} />
              </Stack>

              <Typography variant="h5" fontWeight="bold">
                {phase}
              </Typography>

              <Typography
                sx={{
                  fontSize: { xs: 64, md: 96 },
                  fontWeight: 900,
                  lineHeight: 1,
                  my: 3,
                  letterSpacing: 2,
                }}
              >
                {formatTime(timeLeft)}
              </Typography>

              <LinearProgress
                variant="determinate"
                value={progress}
                sx={{
                  height: 10,
                  borderRadius: 999,
                  mb: 3,
                  background: "#333",
                }}
                color="error"
              />

              <Box
                sx={{
                  background: "linear-gradient(135deg, #1a1b25, #111218)",
                  border: "1px solid #2f3342",
                  borderRadius: 4,
                  p: 3,
                  minHeight: 165,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  mb: 2,
                }}
              >
                <Typography
                  sx={{
                    fontSize: { xs: 26, md: 34 },
                    fontWeight: 900,
                    lineHeight: 1.2,
                  }}
                >
                  {prompt}
                </Typography>
              </Box>

              <Typography sx={{ color: "#bdbdbd" }}>
                {subPrompt}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} lg={3}>
          <Card sx={{ borderRadius: 4, height: "100%" }}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold">
                Session Intelligence
              </Typography>

              <Divider sx={{ my: 2 }} />

              <Typography>
                <b>Module:</b> {selectedModule}
              </Typography>
              <Typography>
                <b>Category:</b> {moduleConfig.category}
              </Typography>
              <Typography>
                <b>Stance:</b> {stance}
              </Typography>
              <Typography>
                <b>Level:</b> {level}
              </Typography>
              <Typography>
                <b>Focus:</b> {moduleConfig.focus}
              </Typography>

              <Divider sx={{ my: 2 }} />

              <Typography variant="h6" fontWeight="bold">
                Prompt Log
              </Typography>

              <Stack spacing={1} sx={{ mt: 1, maxHeight: 320, overflow: "auto" }}>
                {promptLog.length === 0 ? (
                  <Typography color="text.secondary">
                    Prompts will appear here during the session.
                  </Typography>
                ) : (
                  promptLog.map((item, index) => (
                    <Card key={index} sx={{ p: 1.5, borderRadius: 2 }}>
                      <Typography fontWeight="bold">{item.text}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {item.time}
                      </Typography>
                    </Card>
                  ))
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}