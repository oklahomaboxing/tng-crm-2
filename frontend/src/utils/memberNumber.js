export function simpleMemberNumber(value) {
  const original = String(value || '').trim();
  const match = original.match(/^(?:TNG[- ]?)?(\d+)$/i);
  return match ? match[1].replace(/^0+(?=\d)/, '') : original;
}
