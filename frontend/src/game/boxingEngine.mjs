export const MOVES = {
  '1': { name: 'Jab', key: '1', button: 'A / Cross' },
  '2': { name: 'Cross', key: '2', button: 'B / Circle' },
  '3': { name: 'Lead hook', key: '3', button: 'X / Square' },
  '4': { name: 'Rear hook', key: '4', button: 'Y / Triangle' },
  '5': { name: 'Lead uppercut', key: '5', button: 'LB / L1' },
  '6': { name: 'Rear uppercut', key: '6', button: 'RB / R1' },
  slip: { name: 'Slip either side', key: 'A / D', button: 'LT / RT or left stick' },
  slipLeft: { name: 'Slip left', key: 'A / ←', button: 'LT / L2' },
  slipRight: { name: 'Slip right', key: 'D / →', button: 'RT / R2' },
  roll: { name: 'Roll', key: 'S / ↓', button: 'D-pad down' },
  block: { name: 'Block', key: 'Space / ↑', button: 'D-pad up' },
};
export const DRILLS = [
  { id: 'signature', name: 'TNG signature', moves: ['1', 'slip', '5', '2', '3', '2'] },
  { id: 'fundamentals', name: 'Fundamentals', moves: ['1', '2', '3', '2'] },
  { id: 'counter', name: 'Slip & counter', moves: ['1', 'slipRight', '2', '3', '2'] },
  { id: 'body', name: 'Inside work', moves: ['3', 'roll', '5', '6', '3', '2'] },
  { id: 'defense', name: 'Defend & return', moves: ['block', '1', '2', 'slipLeft', '3', '2'] },
];
export function parseCombo(text) {
  const aliases = { 'slip left': 'slipLeft', 'slip right': 'slipRight', slipleft: 'slipLeft', slipright: 'slipRight' };
  const moves = text.split(/[,;→]+/).map(x => x.trim().toLowerCase()).filter(Boolean).map(x => aliases[x] || x);
  if (moves.length < 2 || moves.length > 16 || moves.some(x => !MOVES[x])) throw Error('Use 2–16 moves separated by commas: 1–6, slip, slip left, slip right, roll or block.');
  return moves;
}
export function matches(expected, actual) { return expected === actual || (expected === 'slip' && ['slipLeft', 'slipRight'].includes(actual)); }
export function newRound(now, duration = 120) {
  return { startedAt: now, endsAt: now + duration * 1000, duration, index: 0, points: 0, combos: 0, hits: 0, attempts: 0, misses: 0, streak: 0, bestStreak: 0, deadline: null, lastInput: -Infinity, feedback: 'Ready. Throw the first move.', result: 'ready' };
}
export function tickRound(state, now) {
  if (now >= state.endsAt) return { ...state, result: 'finished', deadline: null };
  if (state.deadline !== null && now > state.deadline) return { ...state, index: 0, streak: 0, misses: state.misses + 1, deadline: null, feedback: 'Timing missed. Reset and start the combination again.', result: 'timeout' };
  return state;
}
export function playMove(state, move, combo, now, windowMs = 1400) {
  if (state.result === 'finished' || now >= state.endsAt) return tickRound(state, now);
  if (!MOVES[move] || now - state.lastInput < 100) return state;
  const s = tickRound(state, now);
  const correct = matches(combo[s.index], move);
  if (!correct) return { ...s, attempts: s.attempts + 1, misses: s.misses + 1, streak: 0, index: 0, deadline: null, lastInput: now, feedback: `${MOVES[move].name}. Expected ${MOVES[combo[s.index]].name}. Start again.`, result: 'wrong' };
  const complete = s.index === combo.length - 1;
  const streak = s.streak + 1;
  return { ...s, index: complete ? 0 : s.index + 1, points: s.points + 100 + (complete ? 250 : 0), combos: s.combos + Number(complete), hits: s.hits + 1, attempts: s.attempts + 1, streak, bestStreak: Math.max(streak, s.bestStreak), deadline: complete ? null : now + windowMs, lastInput: now, feedback: complete ? 'Combination complete! Reset your guard and go again.' : `${MOVES[move].name} · Clean!`, result: complete ? 'combo' : 'correct' };
}
export function resumeRound(state, pausedAt, now) {
  const elapsed = Math.max(0, now - pausedAt);
  return { ...state, endsAt: state.endsAt + elapsed, deadline: state.deadline === null ? null : state.deadline + elapsed };
}
export function keyboardMove(key) {
  return ({ a: 'slipLeft', ArrowLeft: 'slipLeft', d: 'slipRight', ArrowRight: 'slipRight', s: 'roll', ArrowDown: 'roll', ' ': 'block', ArrowUp: 'block' })[key] || (/^[1-6]$/.test(key) ? key : null);
}
export function gamepadEdges(pad, previous = {}) {
  if (!pad || pad.mapping !== 'standard') return { moves: [], pause: false, state: {} };
  const pressed = i => !!pad.buttons?.[i]?.pressed || (pad.buttons?.[i]?.value || 0) > .6;
  const state = Object.fromEntries([0,1,2,3,4,5,6,7,9,12,13,14,15].map(i => [i, pressed(i)]));
  state.left = (pad.axes?.[0] || 0) < -.65; state.right = (pad.axes?.[0] || 0) > .65;
  const map = { 0:'1',1:'2',2:'3',3:'4',4:'5',5:'6',6:'slipLeft',7:'slipRight',12:'block',13:'roll',14:'slipLeft',15:'slipRight',left:'slipLeft',right:'slipRight' };
  return { state, pause: state[9] && !previous[9], moves: [...new Set(Object.keys(map).filter(k => state[k] && !previous[k]).map(k => map[k]))] };
}
