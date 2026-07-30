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
    defaultRounds: 8,
    roundTime: 45,
    restTime: 10,
    focus: "Ordered mobility, running mechanics, lateral movement, and jump preparation.",
  },
  "Coordination Drills": {
    category: "Coordination",
    defaultRounds: 6,
    roundTime: 90,
    restTime: 20,
    focus: "Coordinate opposite arms and legs, punches, shoulder turns, slips, and direction changes.",
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
    defaultRounds: 8,
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
  "Coordination Drills",
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


const FUNDAMENTAL_PUNCHES = {
  1: "Jab",
  2: "Cross",
  3: "Lead Hook",
  4: "Rear Hook",
  5: "Lead Uppercut",
  6: "Rear Uppercut",
};

const MODE_ENGINES = {
  "Heavy Bag": {
    actions: {
      beginner: [
        [1], [1, 2], [1, 1, 2], [1, 2, 3], [2, 3, 2],
      ],
      intermediate: [
        [1, 2, 3, 2], [1, 1, 2, 3], [1, 2, 5, 2], [2, 3, 6, 3, 2], [1, 6, 3, 2],
      ],
      advanced: [
        [1, 2, 3, 6, 3, 2], [1, 1, 2, 5, 2, 3], [2, 3, 2, 5, 2, 3], [1, 2, 5, 6, 3, 2],
      ],
    },
    cues: [
      "Drive through the bag, recover both hands, and keep your feet under you.",
      "Change the rhythm: touch, touch, then sit down on the final punch.",
      "Picture the bag as an opponent. Create the opening before throwing power.",
      "Finish the combination, take an angle, and do not stand directly in front.",
    ],
    triggers: [
      "The opponent raises a high guard and leaves the body available.",
      "The opponent backs toward the ropes and gives up space.",
      "The jab makes the opponent freeze and opens the rear side.",
    ],
    exits: ["Step out at an angle.", "Roll under and reset.", "Take one step back with both hands high."],
    objective: "Power, punch placement, rhythm, and controlled pressure",
  },
  Shadowboxing: {
    actions: {
      beginner: [
        "1, 2, step left", "double 1, 2, step right", "1, 2, 3, pivot", "1, slip, 2, move",
      ],
      intermediate: [
        "feint 1, 2, 3, pivot", "1, 2, slip right, 2, 3, exit", "double 1, 2, roll left, 3, 2", "1 to body, 2 upstairs, move",
      ],
      advanced: [
        "feint 1, draw the counter, slip, 2, 3, 2, pivot", "1, 2, roll, 5, 2, angle out", "pull, 2, 3, 6, 3, exit", "double 1, step outside, 2, 3, 2, reset",
      ],
    },
    cues: [
      "See a real opponent in front of you and react to what they throw back.",
      "Move before and after the punches. Never shadowbox from one fixed spot.",
      "Stay relaxed, breathe with each punch, and make every defensive move believable.",
      "Visualize distance: enter safely, score, and leave before the return fire.",
    ],
    triggers: [
      "The opponent reaches with the jab.", "The opponent gives ground after your entry.", "The opponent fires back after your cross.",
    ],
    exits: ["Pivot away from the imagined power hand.", "Slide out behind the jab.", "Roll and change direction."],
    objective: "Visualization, fluid movement, balance, and realistic transitions",
  },
  "Defense / Reaction": {
    actions: {
      beginner: [
        "slip left, 2", "slip right, 2", "catch the jab, 2", "step back, 1, 2", "block the hook, 3, 2",
      ],
      intermediate: [
        "parry the jab, 2, 3, exit", "slip outside, 2, 3, 2", "roll under the hook, 3, 2", "pull the cross, return 2, 3", "catch, 3, 2, pivot",
      ],
      advanced: [
        "draw the jab, slip outside, 2, 3, 6, exit", "catch the 1, roll the 3, return 3, 2", "half-step back, 2, 5, 2, pivot", "parry, shoulder roll, 2, 3, 2",
      ],
    },
    cues: [
      "Defense comes first. See the punch, make it miss, answer, then leave safely.",
      "Keep your eyes open and your stance underneath you while defending.",
      "Use the smallest movement possible, then counter immediately.",
      "Do not admire the counter. Finish with a defensive exit.",
    ],
    triggers: ["The opponent shoots a jab.", "The opponent commits to the rear hand.", "The opponent throws a wide lead hook."],
    exits: ["Pivot after the counter.", "Roll under the return hook.", "Step outside the opponent's lead foot."],
    objective: "Recognition, defensive reaction, immediate counters, and safe exits",
  },
  Footwork: {
    actions: {
      beginner: ["forward and back", "left and right", "circle left", "circle right", "step in with 1, step out"],
      intermediate: ["1, 2, pivot left", "step outside, 2, exit", "L-step, reset", "double 1 while cutting the ring", "angle step, 1, 2, angle out"],
      advanced: ["cut the ring with two short steps, 1, 2", "pendulum step, 1, 2, pivot", "shift right, 2, 3, exit left", "draw the lead, step outside, 2, turn the opponent"],
    },
    cues: [
      "Move your feet first and keep the stance width consistent.",
      "Use short steps. Do not cross your feet or bring them together.",
      "Imagine cutting off an opponent instead of following them around.",
      "Finish every movement balanced enough to punch or defend immediately.",
    ],
    triggers: ["The opponent circles toward your lead side.", "The opponent retreats in a straight line.", "The opponent tries to escape the corner."],
    exits: ["Reset in stance.", "Pivot to face the opponent.", "Take the angle and hold ring position."],
    objective: "Stance integrity, angles, pivots, ring cutting, and distance control",
  },
  "Boxing Conditioning": {
    actions: {
      beginner: ["1, 2 nonstop", "1, 2, 3 repeat", "straight punches for ten seconds", "body punches for ten seconds"],
      intermediate: ["1, 2, 3, 2 repeat at pace", "six straight punches, sprawl, reset", "hooks and uppercuts for ten seconds", "1, 2 sprint, move, repeat"],
      advanced: ["ten-second maximum-output 1 through 6", "1, 2, 3, 6, 3, 2 nonstop", "body-head flurry, move, repeat", "power burst, speed burst, defensive exit"],
    },
    cues: [
      "Work fast but keep the punches technically clean.",
      "Breathe on every punch and keep your hands returning to guard.",
      "Hold your stance when fatigue arrives. Do not reach or fall forward.",
      "The goal is repeatable output, not one wild burst.",
    ],
    triggers: ["The coach calls sprint.", "The opponent covers up and gives you an output window.", "You have ten seconds to steal the round."],
    exits: ["Hands high and keep moving.", "Reset your breathing without stopping your feet.", "Return to controlled boxing pace."],
    objective: "Punch endurance, repeat sprint ability, breathing, and form under fatigue",
  },
  "Dynamic Warm-Up": {
    ordered: true,
    actions: {
      beginner: [
        "walk straight and turn your shoulders",
        "comb the hair motions",
        "arm circles forward",
        "arm circles backward",
        "reach back then reach forward and touch the ground",
        "lateral shuffle",
        "butt kicks",
        "high knees",
        "two-foot pogo jumps",
        "forward and backward line jumps",
      ],
      intermediate: [
        "walk straight and turn your shoulders",
        "comb the hair motions",
        "large arm circles with controlled shoulder rotation",
        "reach back then reach forward and touch the ground",
        "lateral shuffle with direction change",
        "butt kicks with active arm drive",
        "high knees with controlled rhythm",
        "two-foot pogo jumps",
        "lateral line jumps",
        "skater jumps and stick the landing",
      ],
      advanced: [
        "walk straight with fast shoulder turns",
        "comb the hair motions while walking",
        "alternating arm circles with torso rotation",
        "reach back then reach forward and touch the ground",
        "reactive lateral shuffle",
        "fast butt kicks with sprint arms",
        "high knees with acceleration",
        "pogo jumps into quarter turns",
        "forward backward lateral line-jump pattern",
        "skater jump to boxing stance",
      ],
    },
    cues: [
      "Build speed gradually.",
      "Stay tall and land softly.",
      "Move with control.",
    ],
    triggers: ["The body is progressing from mobility to movement and then to elastic jump preparation."],
    exits: ["Finish balanced in an athletic boxing stance."],
    objective: "Ordered mobility, running mechanics, lateral preparation, and safe jump progression",
  },
  "Coordination Drills": {
    ordered: true,
    actions: {
      beginner: [
        "walk and coordinate opposite arm and leg",
        "walk and throw alternating straight punches",
        "step with the right leg while throwing the left arm",
        "walk forward while turning the shoulders into slips",
        "1 punch, 2 slips",
        "2 punches, 1 slip",
      ],
      intermediate: [
        "walk and throw alternating straight punches",
        "step with the right leg while throwing the left arm",
        "walk while turning the shoulders into left and right slips",
        "1 punch, 2 slips",
        "2 punches, 1 slip",
        "3 punches, 2 slips",
        "4 punches, 1 slip",
      ],
      advanced: [
        "walk and throw alternating straight punches with rhythm changes",
        "step with the right leg while throwing the left arm, then switch sides",
        "walk while slipping and keeping the eyes forward",
        "1 punch, 2 slips",
        "2 punches, 1 slip",
        "3 punches, 2 slips",
        "4 punches, 1 slip",
        "5 punches, 2 slips",
      ],
    },
    cues: [
      "Match the arms and legs.",
      "Keep your eyes forward.",
      "Stay balanced while traveling.",
    ],
    triggers: [
      "Imagine a straight line on the floor and an opponent directly in front of you.",
      "The coach changes the punch-and-slip pattern while you continue traveling.",
    ],
    exits: ["Finish in stance, hands high, eyes forward, and reverse direction when instructed."],
    objective: "Opposite-side coordination, traveling punches, shoulder-led slips, rhythm, and forward-backward control",
  },
  Core: {
    actions: {
      beginner: ["front plank", "dead bug", "bird dog", "glute bridge", "slow mountain climbers"],
      intermediate: ["side plank reach", "russian twists", "leg raises", "plank shoulder taps", "bicycle kicks"],
      advanced: ["plank punch-outs", "V-ups", "hollow-body rocks", "side plank rotation", "fast mountain climbers with control"],
    },
    cues: ["Brace the trunk and breathe behind the brace.", "Keep the neck relaxed and the spine controlled.", "Move from the hips and trunk without losing position.", "Quality repetitions matter more than speed."],
    triggers: ["Maintain control as fatigue builds."],
    exits: ["Reset slowly and protect the lower back."],
    objective: "Bracing, rotation control, posture, and force transfer",
  },
  "Ring IQ": {
    actions: {
      beginner: [
        "Opponent backs up: double 1 and cut the ring", "Opponent rushes: step back, 2", "Opponent jabs: slip outside, 2", "On the ropes: pivot out",
      ],
      intermediate: [
        "Opponent shells up: 1, 2 to body, 3 upstairs", "Opponent circles right: step across and stop the exit", "Opponent reaches: pull, 2, 3", "Opponent southpaw: win outside foot, 2",
      ],
      advanced: [
        "Show the jab, draw the parry, hook around the guard", "Give ground, set the trap, counter 2, 3, pivot", "Pressure without punching, force the escape, intercept with 2", "Bank the round: score clean, deny exchanges, control center",
      ],
    },
    cues: [
      "Read the situation before choosing the action.",
      "Visualize the opponent's position, guard, momentum, and likely response.",
      "Choose the safest high-percentage answer instead of throwing randomly.",
      "After scoring, control position and prepare for the next decision.",
    ],
    triggers: ["The opponent changes rhythm.", "The opponent gives a predictable reaction.", "The ring position creates a tactical opportunity."],
    exits: ["Take center ring.", "Turn the opponent and control the angle.", "Score and deny the return exchange."],
    objective: "Decision-making, opponent reads, ring position, traps, and tactical control",
  },
};

function pickByIndex(list, roundNumber, commandNumber) {
  return list[(roundNumber * 3 + commandNumber) % list.length];
}

function actionToPrompt(action) {
  return Array.isArray(action) ? action.join(", ") : action;
}

function actionToNames(action) {
  if (!Array.isArray(action)) return action;
  return action.map((number) => FUNDAMENTAL_PUNCHES[number]).join(" — ");
}


const LEVEL_GUIDANCE = {
  beginner: {
    label: "Beginner",
    description: "Build stance, balance, punch mechanics, and simple reactions. Commands stay short and controlled.",
  },
  intermediate: {
    label: "Intermediate",
    description: "Connect combinations with defense, body-head changes, pivots, and controlled changes of rhythm.",
  },
  advanced: {
    label: "Advanced",
    description: "Use feints, traps, layered counters, angle changes, and tactical decisions under pressure.",
  },
};

const EXERCISE_INSTRUCTIONS = {
  "walk straight and turn your shoulders": "Walk forward with short natural steps. Keep your eyes forward and rotate one shoulder toward the center line at a time, as if slipping a straight punch without bending at the waist.",
  "walk straight with fast shoulder turns": "Walk forward under control while alternating sharper shoulder turns. Keep the chin tucked, hips mostly square, and head moving just outside the imagined punch line.",
  "comb the hair motions": "Lift each hand near the side of your head and sweep it backward as if combing your hair. Alternate arms while walking, opening the shoulders without arching the lower back.",
  "comb the hair motions while walking": "Walk tall while alternating the comb-the-hair shoulder motion. Reach the elbow up and back, keep the ribs controlled, and maintain an even walking rhythm.",
  "arm circles forward": "Walk or stand tall with both arms extended. Circle forward from small to large while keeping the shoulders down and relaxed.",
  "arm circles backward": "Walk or stand tall with both arms extended. Circle backward from small to large without shrugging or forcing the shoulder joint.",
  "large arm circles with controlled shoulder rotation": "Make large smooth arm circles while allowing a small controlled torso turn. Keep the ribs down and avoid throwing the arms loosely.",
  "alternating arm circles with torso rotation": "Circle one arm at a time while rotating the upper torso toward the moving arm. Keep the hips stable and the movement smooth.",
  "reach back then reach forward and touch the ground": "Step forward, reach both arms behind you to open the chest, then hinge at the hips and reach toward the ground in front of the lead foot. Keep the knees soft and back long.",
  "lateral shuffle with direction change": "Shuffle sideways with short quick steps. On the cue, plant under control and push back the opposite direction without crossing your feet.",
  "reactive lateral shuffle": "Stay low and shuffle laterally. React immediately to the direction cue while keeping the feet apart, chest up, and weight centered.",
  "butt kicks": "Jog forward or in place and bring each heel toward the glute. Stay tall, land softly, and keep the knees pointing down.",
  "butt kicks with active arm drive": "Perform butt kicks while pumping the arms from cheek to hip. Keep the shoulders relaxed and match the arm rhythm to the legs.",
  "fast butt kicks with sprint arms": "Increase the cadence of the butt kicks while driving the arms quickly. Stay tall and avoid leaning forward excessively.",
  "high knees with controlled rhythm": "Drive each knee toward hip height with a steady rhythm. Land under the hips and coordinate opposite arm and leg.",
  "high knees with acceleration": "Begin controlled, then gradually increase knee and arm speed while maintaining posture and soft landings.",
  "two-foot pogo jumps": "Keep the knees slightly bent and make small quick jumps from the ankles. Land softly on both feet and keep the body tall.",
  "forward and backward line jumps": "Jump with both feet together over an imaginary line forward and backward. Keep the jumps small, quick, and quiet.",
  "lateral line jumps": "Jump side to side over an imaginary line with both feet together. Keep the hips level and land softly.",
  "skater jumps and stick the landing": "Push sideways from one leg to the other. Land on one foot, hold balance briefly, then jump back in the opposite direction.",
  "pogo jumps into quarter turns": "Perform quick pogo jumps and add a controlled quarter turn on the cue. Land with both feet aligned and regain athletic posture.",
  "forward backward lateral line-jump pattern": "Jump forward, backward, left, and right over an imaginary cross. Keep the pattern quick but stop if the feet lose control.",
  "skater jump to boxing stance": "Jump laterally from one leg, land softly, then place the other foot down and settle immediately into a balanced boxing stance.",
  "walk and coordinate opposite arm and leg": "Walk naturally while driving the right arm with the left leg and the left arm with the right leg. Keep the rhythm smooth and shoulders relaxed.",
  "walk and throw alternating straight punches": "Walk on a straight line and extend one straight punch with each opposite step. Return every hand to the face before the next punch.",
  "walk and throw alternating straight punches with rhythm changes": "Travel on a straight line while alternating jabs and crosses. Change between smooth and quick rhythms without losing opposite arm-leg coordination.",
  "step with the right leg while throwing the left arm": "Step forward with the right leg as the left arm punches straight. Keep the torso balanced, return the hand to guard, then repeat slowly before increasing speed.",
  "step with the right leg while throwing the left arm, then switch sides": "Step with the right leg and punch the left arm, then step with the left leg and punch the right arm. Alternate without allowing the upper and lower body to move together on the same side.",
  "walk forward while turning the shoulders into slips": "Walk forward with short steps. Turn the left shoulder forward to slip one direction, then the right shoulder forward to slip the other. Keep the eyes ahead and avoid leaning at the waist.",
  "walk while turning the shoulders into left and right slips": "Continue traveling while alternating shoulder-led slips. Bend the knees slightly, rotate through the ribs, and move the head only a few inches off center.",
  "walk while slipping and keeping the eyes forward": "Travel forward or backward while slipping left and right. Keep the chin tucked, eyes on the imagined opponent, and feet underneath the body.",
  "1 punch, 2 slips": "Throw one straight punch, return it to guard, then slip left and slip right while continuing to travel. Keep the slips compact and shoulder-led.",
  "2 punches, 1 slip": "Throw a jab-cross, return both hands, then make one clean slip before taking the next traveling step.",
  "3 punches, 2 slips": "Throw three straight or fundamental punches, recover the guard, then slip once to each side while maintaining forward or backward movement.",
  "4 punches, 1 slip": "Throw four controlled punches with full hand recovery, then make one compact slip and continue traveling in stance.",
  "5 punches, 2 slips": "Throw five clean punches without rushing, recover both hands, then slip left and right before reversing or continuing direction.",
  "arm circles": "Stand tall with your arms extended. Make small controlled circles, gradually increasing the size without shrugging your shoulders.",
  "hip rotations": "Keep your feet shoulder-width apart. Circle your hips slowly while keeping your chest tall and knees soft.",
  "high knees": "Run lightly in place and lift each knee toward hip height. Stay tall, land softly, and pump your arms.",
  "torso twists": "Stand in your boxing stance with relaxed knees. Rotate your ribs left and right while keeping your hips controlled.",
  "light bounce and reach": "Bounce lightly on the balls of your feet and alternate relaxed reaches without locking your elbows.",
  "inchworm to push-up": "Hinge forward, walk your hands into a plank, perform one controlled push-up, then walk your feet toward your hands.",
  "walking lunge with rotation": "Step into a lunge, keep the front knee aligned over the foot, and rotate your torso toward the front leg.",
  "lateral shuffle": "Stay low in stance and push from the outside leg. Keep your feet apart and never cross them.",
  "knee pull to calf raise": "Pull one knee toward your chest while standing tall, release it, then rise onto the ball of the supporting foot.",
  "shadowbox at fifty percent": "Move lightly and throw clean punches at half speed. Focus on balance, breathing, and returning your hands to guard.",
  "world's greatest stretch": "Step into a long lunge, place one hand inside the lead foot, rotate the other arm toward the ceiling, then switch sides.",
  "fast-feet reaction steps": "Take rapid, short steps while staying in stance. Keep your weight centered so you can change direction immediately.",
  "sprawl to stance": "Place your hands down, kick your legs back into a plank, return your feet underneath you, and finish in boxing stance.",
  "dynamic lunge and pivot": "Step into a controlled lunge, push back to stance, then pivot on the lead foot without crossing your legs.",
  "technical shadowboxing build-up": "Begin slowly, then increase speed while keeping every punch, defensive move, and step technically clean.",
  "front plank": "Place your elbows under your shoulders, squeeze your glutes, brace your stomach, and keep a straight line from head to heels.",
  "dead bug": "Lie on your back with hips and knees at ninety degrees. Press your lower back down and slowly extend the opposite arm and leg.",
  "bird dog": "Start on hands and knees. Brace your core and extend the opposite arm and leg without rotating your hips.",
  "glute bridge": "Lie on your back with knees bent. Drive through your heels and squeeze your glutes without arching your lower back.",
  "slow mountain climbers": "Hold a strong plank and slowly drive one knee toward your chest at a time without letting your hips twist.",
  "side plank reach": "Hold a side plank with your elbow under your shoulder. Reach the top arm underneath your body, then rotate it back upward.",
  "russian twists": "Sit tall with knees bent, brace your core, and rotate your ribs from side to side without swinging your arms.",
  "leg raises": "Lie flat, press your lower back down, raise both legs with control, and stop before your back arches.",
  "plank shoulder taps": "Hold a wide-foot plank and touch the opposite shoulder while keeping your hips as still as possible.",
  "bicycle kicks": "Keep your lower back pressed down and rotate one shoulder toward the opposite knee while extending the other leg.",
  "plank punch-outs": "From a strong plank, punch one arm forward at a time while resisting rotation through the hips and shoulders.",
  "V-ups": "Lie long, brace your core, and lift your legs and torso together to reach toward your feet without jerking your neck.",
  "hollow-body rocks": "Press your lower back into the floor, lift your shoulders and legs, and rock gently while keeping the hollow position.",
  "side plank rotation": "Hold a side plank, rotate the top arm under your ribs, then open your chest without dropping your hips.",
  "fast mountain climbers with control": "Drive the knees quickly from a stable plank while keeping your shoulders above your hands and hips level.",
};

function describePunchSequence(action) {
  if (!Array.isArray(action)) return "";
  const names = action.map((number) => FUNDAMENTAL_PUNCHES[number]).join(", ");
  return `Throw ${names}. Rotate from the floor through the hips and shoulders, exhale on each punch, return each hand to guard, and finish balanced.`;
}

function explainExercise(moduleName, action, levelName) {
  const text = actionToPrompt(action);
  const lower = String(text).toLowerCase();

  if (Array.isArray(action)) return describePunchSequence(action);

  // Keep warm-up coaching short so athletes can begin moving immediately.
  if (moduleName === "Dynamic Warm-Up") {
    const shortWarmUpInstructions = {
      "walk straight and turn your shoulders": "Walk forward and rotate your shoulders side to side.",
      "walk straight with fast shoulder turns": "Walk forward and turn your shoulders quickly with control.",
      "comb the hair motions": "Circle each hand over the shoulder like combing your hair.",
      "comb the hair motions while walking": "Walk while circling each hand over the shoulder.",
      "arm circles forward": "Make controlled forward arm circles.",
      "arm circles backward": "Make controlled backward arm circles.",
      "large arm circles with controlled shoulder rotation": "Make large circles and rotate the shoulders gently.",
      "alternating arm circles with torso rotation": "Alternate arm circles while turning the torso.",
      "reach back then reach forward and touch the ground": "Reach back, fold forward, and touch the ground.",
      "lateral shuffle": "Shuffle sideways without crossing your feet.",
      "lateral shuffle with direction change": "Shuffle sideways and change direction on command.",
      "reactive lateral shuffle": "React to the call and shuffle in that direction.",
      "butt kicks": "Jog lightly and bring your heels toward your glutes.",
      "butt kicks with active arm drive": "Do butt kicks while driving the arms.",
      "fast butt kicks with sprint arms": "Move fast with butt kicks and sprinting arms.",
      "high knees": "Drive your knees up while staying tall.",
      "high knees with controlled rhythm": "Lift the knees with a steady rhythm.",
      "high knees with acceleration": "Start controlled, then increase the pace.",
      "two-foot pogo jumps": "Make small quick jumps from both feet.",
      "forward and backward line jumps": "Jump forward and backward over the line.",
      "lateral line jumps": "Jump side to side over the line.",
      "skater jumps and stick the landing": "Jump side to side and hold each landing.",
      "pogo jumps into quarter turns": "Pogo jump and add a small quarter turn.",
      "forward backward lateral line-jump pattern": "Jump forward, backward, then side to side.",
      "skater jump to boxing stance": "Skater jump and land in boxing stance.",
    };

    return shortWarmUpInstructions[lower] || `Perform ${text} with control.`;
  }

  // Keep coordination instructions direct and easy to follow while traveling.
  if (moduleName === "Coordination Drills") {
    if (lower.includes("1 punch, 2 slips")) return "Throw one punch, then slip left and right.";
    if (lower.includes("2 punches, 1 slip")) return "Throw two punches, then make one slip.";
    if (lower.includes("3 punches, 2 slips")) return "Throw three punches, then slip twice.";
    if (lower.includes("4 punches, 1 slip")) return "Throw four punches, then make one slip.";
    if (lower.includes("5 punches, 2 slips")) return "Throw five punches, then slip twice.";
    if (lower.includes("opposite arm and leg")) return "Step with the opposite arm and leg.";
    if (lower.includes("alternating straight punches")) return "Walk and alternate straight punches.";
    if (lower.includes("right leg") && lower.includes("left arm")) return "Step right while punching with the left arm.";
    if (lower.includes("turning the shoulders") || lower.includes("slipping")) return "Walk and turn the shoulders into each slip.";
    return `Perform ${text} while staying balanced.`;
  }

  if (EXERCISE_INSTRUCTIONS[lower]) return EXERCISE_INSTRUCTIONS[lower];

  if (moduleName === "Shadowboxing") {
    return `Visualize a real opponent at proper distance. Perform ${text}. Move your head and feet naturally, keep your guard responsible, and finish where the opponent cannot immediately return.`;
  }
  if (moduleName === "Defense / Reaction") {
    return `Imagine the incoming punch first. Perform ${text} with the smallest defensive movement possible, counter immediately, then recover your stance and exit safely.`;
  }
  if (moduleName === "Footwork") {
    return `Perform ${text} using short steps. Move the foot nearest the direction first, keep your stance width, avoid crossing your feet, and finish ready to punch or defend.`;
  }
  if (moduleName === "Boxing Conditioning") {
    return `Perform ${text} at the assigned pace. Exhale continuously, return your hands to guard, keep your feet underneath you, and reduce speed before sacrificing technique.`;
  }
  if (moduleName === "Ring IQ") {
    return `Read the situation before moving. ${text}. Picture the opponent's position and reaction, choose the safest opening, score cleanly, and control the position afterward.`;
  }
  if (moduleName === "Coordination Drills") {
    return `Perform ${text} while traveling in the assigned direction. Coordinate opposite arms and legs, keep your eyes forward, and maintain balance before increasing speed.`;
  }

  return `Perform ${text} with controlled posture, steady breathing, and clean technique appropriate for the ${LEVEL_GUIDANCE[levelName]?.label || levelName} level.`;
}

function getLevelSpecificCue(levelName) {
  return LEVEL_GUIDANCE[levelName]?.description || LEVEL_GUIDANCE.intermediate.description;
}

function createModuleCommand(moduleName, levelName, roundNumber, commandNumber) {
  const engine = MODE_ENGINES[moduleName] || MODE_ENGINES["Heavy Bag"];
  const levelPool = engine.actions[levelName] || engine.actions.intermediate;
  const action = engine.ordered
    ? levelPool[(roundNumber - 1) % levelPool.length]
    : pickByIndex(levelPool, roundNumber, commandNumber);
  const cue = pickByIndex(engine.cues, roundNumber + 1, commandNumber);
  const trigger = pickByIndex(engine.triggers, roundNumber + 2, commandNumber);
  const exit = pickByIndex(engine.exits, roundNumber + 3, commandNumber);
  const names = actionToNames(action);

  const exerciseExplanation = explainExercise(moduleName, action, levelName);
  const travelDirection = moduleName === "Coordination Drills"
    ? (roundNumber % 2 === 1 ? "FORWARD" : "BACKWARD")
    : "";
  const promptText = travelDirection
    ? `${travelDirection}: ${actionToPrompt(action)}`
    : actionToPrompt(action);
  const directionCue = travelDirection
    ? `Travel ${travelDirection.toLowerCase()} for this round. Reverse direction next round. `
    : "";

  return {
    prompt: promptText,
    coaching_cue: `${directionCue}${exerciseExplanation} ${cue}`,
    level_guidance: getLevelSpecificCue(levelName),
    objective: engine.objective,
    opponent_trigger: trigger,
    correct_exit: exit,
  };
}

function createInstantModePlan({ rounds, level, selectedModule }) {
  const roundCount = Math.max(1, Number(rounds) || 1);
  const commandsPerRound = level === "beginner" ? 8 : level === "advanced" ? 12 : 10;

  return {
    source: "instant-mode-specific",
    rounds: Array.from({ length: roundCount }, (_, roundIndex) => {
      const moduleName = selectedModule === "Fight Camp Progressive"
        ? FIGHT_CAMP_FLOW[roundIndex % FIGHT_CAMP_FLOW.length]
        : selectedModule;
      const engine = MODE_ENGINES[moduleName] || MODE_ENGINES["Heavy Bag"];

      return {
        round_number: roundIndex + 1,
        module: moduleName,
        objective: engine.objective,
        commands: Array.from({ length: commandsPerRound }, (_, commandIndex) =>
          createModuleCommand(moduleName, level, roundIndex + 1, commandIndex)
        ),
      };
    }),
  };
}

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


const REST_COACHING = {
  "Heavy Bag": [
    "Walk slowly and control your breathing. Relax your shoulders and loosen your hands.",
    "Breathe in through your nose and out through your mouth. Review the last combination and prepare to repeat it cleanly.",
    "Stay on your feet, shake out your arms, and keep your eyes on the bag. Power comes after you recover your balance.",
  ],
  Shadowboxing: [
    "Keep moving lightly. Reset your stance, relax your shoulders, and picture the opponent in front of you.",
    "Control your breathing and review your foot position. Start the next round balanced and ready to move.",
    "Walk, breathe, and stay loose. Think about clean technique instead of speed.",
  ],
  "Defense / Reaction": [
    "Breathe and review the defensive movement from the last round. Keep your eyes forward and your hands ready.",
    "Relax your upper body. Think defense first, then the counter, then a safe exit.",
    "Reset your stance and visualize the opponent's next attack. Make them miss before you answer.",
  ],
  Footwork: [
    "Keep walking and breathe steadily. Reset your feet underneath your shoulders and stay off your heels.",
    "Shake out your legs and recover. Think small controlled steps, strong stance, and no crossing your feet.",
    "Stay light on your feet. Prepare to move with balance before adding speed.",
  ],
  "Boxing Conditioning": [
    "Keep moving. Take deep controlled breaths and bring your heart rate down without sitting down.",
    "Walk slowly, loosen your arms, and recover your breathing. The next round starts with clean form.",
    "Breathe, stay upright, and prepare to work again. Do not hold your breath when the pace increases.",
  ],
  "Dynamic Warm-Up": [
    "Stay loose and keep moving. Breathe naturally and prepare the next movement with control.",
    "Use the rest to check your posture and range of motion. Nothing should feel forced.",
  ],
  "Coordination Drills": [
    "Walk slowly and reset your rhythm. Think opposite arm and leg, eyes forward, and relaxed shoulders.",
    "Recover your breathing and prepare to reverse direction in the next round.",
    "Shake out your arms and legs. The next round continues the progression with clean coordination before speed.",
  ],
  Core: [
    "Breathe deeply and relax your neck and shoulders. Brace only when the next exercise begins.",
    "Reset your position and control your breathing. Quality repetitions matter more than rushing.",
    "Loosen your hips and lower back. Prepare to brace your core without holding your breath.",
  ],
  "Ring IQ": [
    "Breathe and replay the last situation. Identify the opponent's action, your response, and your safest exit.",
    "Stay mentally engaged. Decide what you will look for first when the next round begins.",
    "Recover physically while thinking tactically. See the opening before you throw.",
  ],
  default: [
    "Walk slowly, control your breathing, and relax your shoulders. Listen for the next instruction.",
    "Breathe in through your nose and out through your mouth. Stay loose and prepare for the next round.",
    "Shake out your arms, reset your stance, and focus on clean technique when the bell sounds.",
  ],
};

const PREFERRED_VOICE_NAMES = [
  "Microsoft Guy Online",
  "Microsoft Aria Online",
  "Microsoft Jenny Online",
  "Microsoft Davis Online",
  "Google US English",
  "Samantha",
  "Daniel",
];



function randomFrom(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function formatTime(seconds) {
  const safe = Math.max(0, Number(seconds) || 0);
  const mins = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

const SAVED_PROGRAMS = {
  custom: { label: "Custom Workout" },
  beginnerFundamentals: {
    label: "Beginner Boxing Fundamentals",
    module: "Shadowboxing",
    level: "beginner",
    rounds: 6,
    roundTime: 120,
    restTime: 30,
    paceSeconds: 40,
  },
  youthCoordination: {
    label: "Youth Coordination",
    module: "Coordination Drills",
    level: "beginner",
    rounds: 6,
    roundTime: 90,
    restTime: 25,
    paceSeconds: 30,
  },
  competitionWarmup: {
    label: "Competition Team Warm-Up",
    module: "Dynamic Warm-Up",
    level: "intermediate",
    rounds: 10,
    roundTime: 45,
    restTime: 10,
    paceSeconds: 30,
  },
  footworkDevelopment: {
    label: "Footwork Development",
    module: "Footwork",
    level: "intermediate",
    rounds: 8,
    roundTime: 90,
    restTime: 25,
    paceSeconds: 35,
  },
  defenseReaction: {
    label: "Defense and Reaction",
    module: "Defense / Reaction",
    level: "intermediate",
    rounds: 6,
    roundTime: 180,
    restTime: 45,
    paceSeconds: 35,
  },
  fightCamp: {
    label: "Fight Camp Conditioning",
    module: "Fight Camp Progressive",
    level: "advanced",
    rounds: 8,
    roundTime: 180,
    restTime: 45,
    paceSeconds: 30,
  },
};

export default function AITrainer() {
  const [selectedModule, setSelectedModule] = useState("Heavy Bag");
  const [stance, setStance] = useState("orthodox");
  const [level, setLevel] = useState("intermediate");
  const [rounds, setRounds] = useState(TRAINING_MODULES["Heavy Bag"].defaultRounds);
  const [roundTime, setRoundTime] = useState(TRAINING_MODULES["Heavy Bag"].roundTime);
  const [restTime, setRestTime] = useState(TRAINING_MODULES["Heavy Bag"].restTime);
  const [paceSeconds, setPaceSeconds] = useState(45);
  const [availableVoices, setAvailableVoices] = useState([]);
  const [selectedVoiceURI, setSelectedVoiceURI] = useState("");
  const [voiceRate, setVoiceRate] = useState(0.92);
  const [selectedProgram, setSelectedProgram] = useState("custom");
  const [blockTimeLeft, setBlockTimeLeft] = useState(0);
  const [currentDrillNumber, setCurrentDrillNumber] = useState(0);
  const [nextDrill, setNextDrill] = useState("Waiting for round to begin");
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [sessionResults, setSessionResults] = useState(null);

  const [currentRound, setCurrentRound] = useState(0);
  const [phase, setPhase] = useState("Ready");
  const [timeLeft, setTimeLeft] = useState(0);
  const [prompt, setPrompt] = useState("Select a module and press Start");
  const [subPrompt, setSubPrompt] = useState("TNG Coach AI is ready.");
  const [running, setRunning] = useState(false);
  const [paused, setPaused] = useState(false);
  const [promptLog, setPromptLog] = useState([]);
  const [aiPlan, setAiPlan] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState("");
  const [commandIndex, setCommandIndex] = useState(0);
  const [aiDetails, setAiDetails] = useState({
    objective: "",
    opponentTrigger: "",
    correctExit: "",
  });

  const timerRef = useRef(null);
  const promptRef = useRef(null);
  const pausedRef = useRef(false);
  const runningRef = useRef(false);
  const currentModuleRef = useRef(selectedModule);
  const aiPlanRef = useRef(null);
  const commandIndexRef = useRef(0);
  const currentRoundRef = useRef(0);
  const phaseRef = useRef("Ready");
  const voiceRateRef = useRef(voiceRate);
  const selectedVoiceURIRef = useRef(selectedVoiceURI);
  const lastSpokenRef = useRef({ text: "", at: 0 });
  const currentSpokenRef = useRef("");
  const moduleConfig = TRAINING_MODULES[selectedModule];

  async function generateAIPlanInBackground() {
    const token = localStorage.getItem("token");

    if (!token) {
      setAiError("Instant fundamentals mode is active. Sign in to enable AI enhancement.");
      return null;
    }

    setAiLoading(true);
    setAiError("");

    try {
      const response = await fetch(`${API}/api/ai/training-plan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          module: selectedModule,
          level,
          stance,
          rounds: Number(rounds),
          round_time: Number(roundTime),
          pace_seconds: Number(paceSeconds),
          punch_system: "1-6 boxing fundamentals",
          visualization_method: true,
        }),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const errorMessage =
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail || data);
        throw new Error(errorMessage || `AI enhancement failed with status ${response.status}`);
      }

      // Keep the instant 1-6 fundamentals plan active so outside AI wording
      // cannot introduce non-standard combinations during the workout.
      return data;
    } catch (error) {
      console.warn("AI enhancement unavailable. Continuing with instant fundamentals plan.", error);
      setAiError("Instant fundamentals mode is running. AI enhancement was unavailable.");
      return null;
    } finally {
      setAiLoading(false);
    }
  }

  function getAIRound(roundNumber) {
    return aiPlanRef.current?.rounds?.find(
      (item) => Number(item.round_number) === Number(roundNumber)
    );
  }

  function getNextAICommand(roundNumber) {
    const activeRound = getAIRound(roundNumber);
    const commands = activeRound?.commands || [];

    if (commands.length === 0) {
      return null;
    }

    const index = commandIndexRef.current % commands.length;
    const command = commands[index];
    const nextIndex = index + 1;

    commandIndexRef.current = nextIndex;
    setCommandIndex(nextIndex);

    return command;
  }

  async function updateLiveDisplay(extra = {}) {
    const token = localStorage.getItem("token");

    if (!token) {
      console.warn("No token found. Live display update skipped.");
      return;
    }

    await fetch(`${API}/api/ai/live-session`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + token,
      },
      body: JSON.stringify({
        active: runningRef.current,
        phase,
        round: currentRound,
        total_rounds: Number(rounds),
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

  const progress = useMemo(() => {
    const total = phase === "Rest" ? restTime : roundTime;
    if (!total || !timeLeft) return 0;
    return Math.max(0, Math.min(100, ((total - timeLeft) / total) * 100));
  }, [phase, restTime, roundTime, timeLeft]);

  function choosePreferredVoice(voices) {
    if (!voices?.length) return null;

    const selected = voices.find(
      (voice) => voice.voiceURI === selectedVoiceURIRef.current
    );

    if (selected) return selected;

    for (const preferredName of PREFERRED_VOICE_NAMES) {
      const match = voices.find((voice) =>
        voice.name.toLowerCase().includes(preferredName.toLowerCase())
      );

      if (match) return match;
    }

    return (
      voices.find(
        (voice) => voice.lang === "en-US" && voice.localService
      ) ||
      voices.find((voice) => voice.lang?.startsWith("en")) ||
      voices[0]
    );
  }

  function speak(text, options = {}) {
    if (!voiceEnabled) return;
    if (!text || !("speechSynthesis" in window)) return;

    const normalizedText = String(text).trim();
    const now = Date.now();

    if (
      lastSpokenRef.current.text === normalizedText &&
      now - lastSpokenRef.current.at < 750
    ) {
      return;
    }

    lastSpokenRef.current = {
      text: normalizedText,
      at: now,
    };

    try {
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(normalizedText);
      const voices = window.speechSynthesis.getVoices();
      const preferredVoice = choosePreferredVoice(voices);

      if (preferredVoice) {
        utterance.voice = preferredVoice;
        utterance.lang = preferredVoice.lang || "en-US";
      } else {
        utterance.lang = "en-US";
      }

      utterance.rate = options.rate ?? voiceRateRef.current;
      utterance.pitch = options.pitch ?? 0.96;
      utterance.volume = options.volume ?? 1;

      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.log("Voice failed", err);
    }
  }

  function getRestInstruction(activeModule, roundNumber) {
    const instructions =
      REST_COACHING[activeModule] || REST_COACHING.default;

    const index = Math.max(0, Number(roundNumber) - 1) % instructions.length;
    return instructions[index];
  }

  function getNextRoundPreview(roundNumber) {
    const nextRoundNumber = Number(roundNumber) + 1;
    const nextModule = resolveActiveModule(nextRoundNumber);
    const nextAIRound = getAIRound(nextRoundNumber);
    const nextAICommand = nextAIRound?.commands?.[0];

    return {
      module: nextModule,
      prompt:
        nextAICommand?.prompt ||
        `Round ${nextRoundNumber}: ${nextModule}`,
    };
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

  function getCommandPreview(roundNumber = currentRoundRef.current || 1) {
    const activeRound = getAIRound(roundNumber);
    const commands = activeRound?.commands || [];

    if (commands.length > 0) {
      return commands[commandIndexRef.current % commands.length]?.prompt || "Next drill";
    }

    const preview = createModuleCommand(
      currentModuleRef.current,
      level,
      roundNumber,
      commandIndexRef.current
    );
    return preview?.prompt || "Next drill";
  }

  function applySavedProgram(programKey) {
    setSelectedProgram(programKey);
    const program = SAVED_PROGRAMS[programKey];
    if (!program || programKey === "custom") return;

    setSelectedModule(program.module);
    setLevel(program.level);
    setRounds(program.rounds);
    setRoundTime(program.roundTime);
    setRestTime(program.restTime);
    setPaceSeconds(program.paceSeconds);
    setPrompt(`${program.label} loaded`);
    setSubPrompt("Review the settings, then press Start Instantly.");
  }

  function repeatCurrentDrill() {
    if (!runningRef.current || phaseRef.current !== "Fight") return;
    setBlockTimeLeft(Number(paceSeconds));
    speak(`${prompt}. ${subPrompt}`, { force: true });
  }

  function skipCurrentDrill() {
    if (!runningRef.current || phaseRef.current !== "Fight") return;
    callPrompt(true);
  }

  function addDrillTime(seconds = 15) {
    if (!runningRef.current || phaseRef.current !== "Fight") return;
    setBlockTimeLeft((old) => {
      const next = old + seconds;
      startPromptLoop(next);
      return next;
    });
    speak(`${seconds} seconds added`, { force: true });
  }

  function changePromptPace(delta) {
    setPaceSeconds((old) => {
      const next = Math.max(10, Math.min(120, Number(old) + delta));
      if (runningRef.current && phaseRef.current === "Fight") {
        setBlockTimeLeft(next);
        startPromptLoop(next);
      }
      return next;
    });
  }

  function generatePrompt(activeModule) {
    const command = createModuleCommand(
      activeModule,
      level,
      currentRoundRef.current || 1,
      commandIndexRef.current
    );

    commandIndexRef.current += 1;
    setCommandIndex(commandIndexRef.current);
    return command;
  }

  function callPrompt(manual = false, introText = "") {
    if (!runningRef.current || phaseRef.current === "Rest") return;

    const activeModule = currentModuleRef.current;
    const activeRoundNumber = currentRoundRef.current || 1;
    const aiCommand = getNextAICommand(activeRoundNumber);
    const command = aiCommand || generatePrompt(activeModule);

    const next = command?.prompt || "1, 2";
    const coachingCue =
      command?.coaching_cue ||
      (manual ? "Manual coach command." : moduleConfig.focus);

    setPrompt(next);
    setSubPrompt(coachingCue);
    setBlockTimeLeft(Number(paceSeconds));
    setCurrentDrillNumber(commandIndexRef.current);
    const upcoming = getCommandPreview(activeRoundNumber);
    setNextDrill(upcoming === next ? "Repeat with cleaner technique" : upcoming);
    currentSpokenRef.current = `${next}. ${coachingCue}`;

    setAiDetails({
      objective: command?.objective || "Clean boxing fundamentals",
      opponentTrigger:
        command?.opponent_trigger ||
        "Visualize the opponent reacting and identify the next opening.",
      correctExit:
        command?.correct_exit ||
        "Hands home, balanced stance, and move off the center line.",
    });

    logPrompt(next);
    const spokenIntro = introText ? `${introText} ` : "";
    speak(`${spokenIntro}${next}. ${coachingCue}`);
  }

  function startPromptLoop(delaySeconds = paceSeconds) {
    if (promptRef.current) clearTimeout(promptRef.current);

    promptRef.current = setTimeout(() => {
      if (!runningRef.current || phaseRef.current === "Rest") return;
      if (pausedRef.current) {
        startPromptLoop(1);
        return;
      }
      callPrompt(false);
      startPromptLoop(Number(paceSeconds));
    }, Number(delaySeconds) * 1000);
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
    setNextDrill("Session complete");
    setBlockTimeLeft(0);
    setSessionResults({
      program: SAVED_PROGRAMS[selectedProgram]?.label || "Custom Workout",
      module: selectedModule,
      level: LEVEL_GUIDANCE[level]?.label || level,
      roundsCompleted: Number(rounds),
      promptsCompleted: promptLog.length + 1,
      completedAt: new Date().toLocaleString(),
    });
    speak("Workout complete");

    updateLiveDisplay({
      active: false,
      phase: "Complete",
      round: currentRound,
      total_rounds: Number(rounds),
      time_left: 0,
      module: currentModuleRef.current,
      prompt: "Workout Complete",
      sub_prompt: "Good work. Recover, hydrate, and log your notes.",
    });
  }

  function startRest(roundNumber) {
    clearTimers();

    const activeModule = currentModuleRef.current;
    const restInstruction = getRestInstruction(activeModule, roundNumber);
    const nextRound = getNextRoundPreview(roundNumber);
    const restPrompt = "Breathe and Recover";
    const restSubPrompt = `${restInstruction} Up next: ${nextRound.prompt}.`;

    phaseRef.current = "Rest";
    setPhase("Rest");
    setTimeLeft(Number(restTime));
    setPrompt(restPrompt);
    setSubPrompt(restSubPrompt);

    speak(`Rest. ${restInstruction}`, {
      rate: Math.max(0.78, voiceRateRef.current - 0.04),
      pitch: 0.94,
    });

    updateLiveDisplay({
      active: true,
      phase: "Rest",
      round: roundNumber,
      total_rounds: Number(rounds),
      time_left: Number(restTime),
      module: activeModule,
      prompt: restPrompt,
      sub_prompt: restSubPrompt,
      next_prompt: nextRound.prompt,
      next_combination: nextRound.prompt,
    });

    timerRef.current = setInterval(() => {
      setBlockTimeLeft((old) => {
        if (pausedRef.current || phaseRef.current !== "Fight") return old;
        return Math.max(0, old - 1);
      });
      setTimeLeft((old) => {
        if (pausedRef.current) return old;

        if (old <= 1) {
          clearTimers();
          startRound(roundNumber + 1);
          return 0;
        }

        if (old === 11) {
          speak(
            "Ten seconds. Return to your stance, bring your hands up, and prepare for the next round.",
            { rate: voiceRateRef.current, pitch: 0.96 }
          );
        }

        if (old === 4) {
          speak("Three, two, one.", {
            rate: Math.max(0.8, voiceRateRef.current - 0.05),
            pitch: 0.98,
          });
        }

        const next = old - 1;

        updateLiveDisplay({
          active: true,
          phase: "Rest",
          round: roundNumber,
          total_rounds: Number(rounds),
          time_left: next,
          module: activeModule,
          prompt: restPrompt,
          sub_prompt: restSubPrompt,
          next_prompt: nextRound.prompt,
          next_combination: nextRound.prompt,
        });

        return next;
      });
    }, 1000);
  }


  function startRound(roundNumber) {
    console.log("6. startRound called", {
      roundNumber,
      plan: aiPlanRef.current,
      running: runningRef.current,
    });

    clearTimers();

    commandIndexRef.current = 0;
    setCommandIndex(0);

    setAiDetails({
      objective: "",
      opponentTrigger: "",
      correctExit: "",
    });

    const activeModule = resolveActiveModule(roundNumber);
    currentModuleRef.current = activeModule;

    const roundPrompt = `Round ${roundNumber}: ${activeModule}`;
    const roundSubPrompt =
      TRAINING_MODULES[activeModule]?.focus || "Boxing round active.";

    currentRoundRef.current = roundNumber;
    phaseRef.current = "Fight";
    setCurrentRound(roundNumber);
    setPhase("Fight");
    setTimeLeft(Number(roundTime));
    setPrompt(roundPrompt);
    setSubPrompt(roundSubPrompt);

    updateLiveDisplay({
      active: true,
      phase: "Fight",
      round: roundNumber,
      total_rounds: Number(rounds),
      time_left: Number(roundTime),
      module: activeModule,
      prompt: roundPrompt,
      sub_prompt: roundSubPrompt,
    });

    // Issue the first exercise immediately instead of waiting for the first pace interval.
    callPrompt(false, `Round ${roundNumber}. ${activeModule}. Begin.`);
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

        const next = old - 1;

        updateLiveDisplay({
          active: true,
          phase: "Fight",
          round: roundNumber,
          total_rounds: Number(rounds),
          time_left: next,
          module: activeModule,
          prompt,
          sub_prompt: subPrompt,
        });

        return next;
      });
    }, 1000);
  }

  function startSession() {
    console.log("Starting instant boxing-fundamentals workout");

    clearTimers();

    runningRef.current = true;
    pausedRef.current = false;

    setPromptLog([]);
    setSessionResults(null);
    setAiError("");

    const instantPlan = createInstantModePlan({
      rounds: Number(rounds),
      level,
      selectedModule,
    });

    aiPlanRef.current = instantPlan;
    setAiPlan(instantPlan);

    setCommandIndex(0);
    commandIndexRef.current = 0;

    setAiDetails({
      objective: "Build clean 1-6 boxing fundamentals",
      opponentTrigger: "Visualize a live opponent reacting to every punch.",
      correctExit: "Return to stance and move safely after every exchange.",
    });

    setRunning(true);
    setPaused(false);
    setCurrentRound(1);

    // Start immediately. The network AI no longer blocks the workout.
    startRound(1);

    // Optional enhancement runs after the workout has already begun.
    generateAIPlanInBackground();
  }

  function pauseSession() {
    if (!runningRef.current) return;

    pausedRef.current = true;
    setPaused(true);
    phaseRef.current = "Paused";
    setPhase("Paused");

    updateLiveDisplay({
      active: true,
      phase: "Paused",
      round: currentRound,
      total_rounds: Number(rounds),
      time_left: timeLeft,
      module: currentModuleRef.current,
      prompt,
      sub_prompt: "Timer paused.",
    });

    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }

  function resumeSession() {
    if (!runningRef.current) return;

    pausedRef.current = false;
    setPaused(false);
    phaseRef.current = "Fight";
    setPhase("Fight");
    speak("Resume");

    updateLiveDisplay({
      active: true,
      phase: "Fight",
      round: currentRound,
      total_rounds: Number(rounds),
      time_left: timeLeft,
      module: currentModuleRef.current,
      prompt,
      sub_prompt: "Timer resumed.",
    });
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
    setBlockTimeLeft(0);
    setCurrentDrillNumber(0);
    setNextDrill("Waiting for round to begin");
    setSessionResults(null);

    updateLiveDisplay({
      active: false,
      phase: "Ready",
      round: 0,
      total_rounds: Number(rounds),
      time_left: 0,
      module: selectedModule,
      prompt: "Waiting for coach to start session",
      sub_prompt: "Open this screen on every TV in the gym.",
    });

    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }

  useEffect(() => {
    if (!("speechSynthesis" in window)) return undefined;

    const loadVoices = () => {
      const voices = window.speechSynthesis
        .getVoices()
        .filter((voice) => voice.lang?.toLowerCase().startsWith("en"));

      setAvailableVoices(voices);

      if (!selectedVoiceURIRef.current && voices.length > 0) {
        const preferred = choosePreferredVoice(voices);

        if (preferred) {
          selectedVoiceURIRef.current = preferred.voiceURI;
          setSelectedVoiceURI(preferred.voiceURI);
        }
      }
    };

    loadVoices();
    window.speechSynthesis.addEventListener("voiceschanged", loadVoices);

    return () => {
      window.speechSynthesis.removeEventListener("voiceschanged", loadVoices);
    };
  }, []);

  useEffect(() => {
    voiceRateRef.current = voiceRate;
  }, [voiceRate]);

  useEffect(() => {
    selectedVoiceURIRef.current = selectedVoiceURI;
  }, [selectedVoiceURI]);

  useEffect(() => {
    const config = TRAINING_MODULES[selectedModule];

    const orderedRounds = MODE_ENGINES[selectedModule]?.ordered
      ? MODE_ENGINES[selectedModule]?.actions?.[level]?.length
      : null;

    setRounds(orderedRounds || config.defaultRounds);
    setRoundTime(config.roundTime);
    setRestTime(config.restTime);
    setPrompt(`${selectedModule} selected`);
    setSubPrompt(config.focus);

    currentModuleRef.current = selectedModule;
  }, [selectedModule, level]);

  useEffect(() => {
    aiPlanRef.current = aiPlan;
  }, [aiPlan]);

  useEffect(() => {
    commandIndexRef.current = commandIndex;
  }, [commandIndex]);

  useEffect(() => {
    currentRoundRef.current = currentRound;
  }, [currentRound]);

  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);

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
      total_rounds: Number(rounds),
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
          <Chip label="Coordination" />
          <Chip label="Conditioning" />
          <Chip label={aiLoading ? "AI Enhancing…" : "Instant Start"} color={aiLoading ? "warning" : "success"} />
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
                  <Typography fontWeight="bold">Saved Program</Typography>
                  <Select
                    fullWidth
                    value={selectedProgram}
                    onChange={(e) => applySavedProgram(e.target.value)}
                  >
                    {Object.entries(SAVED_PROGRAMS).map(([key, program]) => (
                      <MenuItem key={key} value={key}>{program.label}</MenuItem>
                    ))}
                  </Select>
                </Box>

                <Box>
                  <Typography fontWeight="bold">Training Module</Typography>
                  <Select
                    fullWidth
                    value={selectedModule}
                    onChange={(e) => { setSelectedModule(e.target.value); setSelectedProgram("custom"); }}
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
                      onChange={(e) => { setLevel(e.target.value); setSelectedProgram("custom"); }}
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
                    min={10}
                    max={120}
                    step={5}
                    onChange={(e, value) => setPaceSeconds(value)}
                  />
                </Box>

                <Box>
                  <Typography fontWeight="bold">Coach Voice</Typography>
                  <Select
                    fullWidth
                    value={selectedVoiceURI}
                    onChange={(e) => setSelectedVoiceURI(e.target.value)}
                    displayEmpty
                  >
                    {availableVoices.length === 0 && (
                      <MenuItem value="">
                        Default browser voice
                      </MenuItem>
                    )}

                    {availableVoices.map((voice) => (
                      <MenuItem key={voice.voiceURI} value={voice.voiceURI}>
                        {voice.name} ({voice.lang})
                      </MenuItem>
                    ))}
                  </Select>
                </Box>

                <Box>
                  <Typography fontWeight="bold">
                    Voice Speed: {voiceRate.toFixed(2)}x
                  </Typography>
                  <Slider
                    value={voiceRate}
                    min={0.75}
                    max={1.15}
                    step={0.01}
                    onChange={(e, value) => setVoiceRate(Number(value))}
                  />
                </Box>

                <Button
                  type="button"
                  variant="outlined"
                  onClick={() =>
                    speak(
                      "TNG Coach is ready. Stay relaxed, listen carefully, and work with clean technique.",
                      { rate: voiceRate }
                    )
                  }
                >
                  Test Coach Voice
                </Button>

                <Stack direction="row" spacing={1} flexWrap="wrap">
                  <Button
                    type="button"
                    variant="contained"
                    color="error"
                    onClick={startSession}
                    disabled={running}
                  >
                    {running ? "Running" : "Start Instantly"}
                  </Button>

                  <Button
                    type="button"
                    variant="outlined"
                    color="error"
                    onClick={pauseSession}
                  >
                    Pause
                  </Button>

                  <Button
                    type="button"
                    variant="outlined"
                    color="success"
                    onClick={resumeSession}
                  >
                    Resume
                  </Button>

                  <Button
                    type="button"
                    variant="outlined"
                    color="warning"
                    onClick={resetSession}
                  >
                    Reset
                  </Button>

                  <Button
                    type="button"
                    variant="contained"
                    color="success"
                    onClick={() => callPrompt(true)}
                    disabled={!running}
                  >
                    Next Prompt
                  </Button>

                  <Button type="button" variant="outlined" onClick={repeatCurrentDrill} disabled={!running}>
                    Repeat Drill
                  </Button>
                  <Button type="button" variant="outlined" onClick={skipCurrentDrill} disabled={!running}>
                    Skip Drill
                  </Button>
                  <Button type="button" variant="outlined" onClick={() => addDrillTime(15)} disabled={!running}>
                    +15 Seconds
                  </Button>
                  <Button type="button" variant="outlined" onClick={() => changePromptPace(5)}>
                    Slower Prompts
                  </Button>
                  <Button type="button" variant="outlined" onClick={() => changePromptPace(-5)}>
                    Faster Prompts
                  </Button>
                  <Button type="button" variant="outlined" onClick={() => setVoiceEnabled((old) => !old)}>
                    {voiceEnabled ? "Mute Voice" : "Enable Voice"}
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

              <Typography sx={{ color: "#bdbdbd", mb: 2 }}>
                {subPrompt}
              </Typography>

              {phase === "Fight" && (
                <Grid container spacing={2} sx={{ mb: 2, textAlign: "left" }}>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ background: "#171820", borderRadius: 2, p: 1.5, height: "100%" }}>
                      <Typography variant="caption" sx={{ color: "#ef5350", fontWeight: "bold" }}>
                        CURRENT DRILL
                      </Typography>
                      <Typography fontWeight="bold">Drill {Math.max(1, currentDrillNumber)}</Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ background: "#171820", borderRadius: 2, p: 1.5, height: "100%" }}>
                      <Typography variant="caption" sx={{ color: "#ffb74d", fontWeight: "bold" }}>
                        DRILL TIME LEFT
                      </Typography>
                      <Typography fontWeight="bold" fontSize={24}>{formatTime(blockTimeLeft)}</Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Box sx={{ background: "#171820", borderRadius: 2, p: 1.5, height: "100%" }}>
                      <Typography variant="caption" sx={{ color: "#66bb6a", fontWeight: "bold" }}>
                        NEXT DRILL
                      </Typography>
                      <Typography fontWeight="bold">{nextDrill}</Typography>
                    </Box>
                  </Grid>
                </Grid>
              )}

              {(aiDetails.objective ||
                aiDetails.opponentTrigger ||
                aiDetails.correctExit) && (
                <Stack spacing={1} sx={{ textAlign: "left", mt: 2 }}>
                  {aiDetails.opponentTrigger && (
                    <Box
                      sx={{
                        background: "#171820",
                        borderRadius: 2,
                        p: 1.5,
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{ color: "#ef5350", fontWeight: "bold" }}
                      >
                        OPPONENT TRIGGER
                      </Typography>

                      <Typography>
                        {aiDetails.opponentTrigger}
                      </Typography>
                    </Box>
                  )}

                  {aiDetails.objective && (
                    <Box
                      sx={{
                        background: "#171820",
                        borderRadius: 2,
                        p: 1.5,
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{ color: "#ffb74d", fontWeight: "bold" }}
                      >
                        OBJECTIVE
                      </Typography>

                      <Typography>
                        {aiDetails.objective}
                      </Typography>
                    </Box>
                  )}

                  {aiDetails.correctExit && (
                    <Box
                      sx={{
                        background: "#171820",
                        borderRadius: 2,
                        p: 1.5,
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{ color: "#66bb6a", fontWeight: "bold" }}
                      >
                        CORRECT EXIT
                      </Typography>

                      <Typography>
                        {aiDetails.correctExit}
                      </Typography>
                    </Box>
                  )}
                </Stack>
              )}
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
                <b>Level:</b> {LEVEL_GUIDANCE[level]?.label || level}
              </Typography>
              <Typography sx={{ mt: 0.5, color: "text.secondary" }}>
                {LEVEL_GUIDANCE[level]?.description}
              </Typography>
              <Typography sx={{ mt: 1 }}>
                <b>Focus:</b> {moduleConfig.focus}
              </Typography>

              {sessionResults && (
                <Box sx={{ mt: 2, p: 2, background: "#f5f5f5", borderRadius: 2 }}>
                  <Typography fontWeight="bold">Workout Result</Typography>
                  <Typography variant="body2">{sessionResults.program}</Typography>
                  <Typography variant="body2">{sessionResults.roundsCompleted} rounds completed</Typography>
                  <Typography variant="body2">{sessionResults.level} · {sessionResults.module}</Typography>
                  <Typography variant="caption" color="text.secondary">{sessionResults.completedAt}</Typography>
                </Box>
              )}

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