export function memberDate(value) {
  if (!value) return null;
  const raw = String(value);
  const normalized = raw.includes('T') && !/(Z|[+-]\d{2}:?\d{2})$/i.test(raw) ? `${raw}Z` : raw;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}
export function membershipCategory(member, now = Date.now()) {
  if (member.membership_category) return member.membership_category;
  // Fallback while rolling deployments finish. The server is authoritative.
  if (!`${member.first_name||''} ${member.last_name||''}`.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((member.email||'').trim())) return 'contact';
  if (member.member_type === 'CUSTOMER' || !member.membership_start) return 'contact';
  const end = memberDate(member.membership_end);
  if (end && end.getTime() <= now) return 'expired';
  if (member.membership_status === 'active') return end && end.getTime() <= now + 7*86400000 ? 'expiring' : 'active';
  return member.membership_status === 'pending' ? 'contact' : 'inactive';
}
export function rosterTotals(members) {
  const counts={active:0,expiring:0,expired:0,inactive:0,contact:0,review:0,all:0,profiles:members.length};
  for (const member of members) counts[membershipCategory(member)]++;
  counts.active+=counts.expiring;
  counts.all=counts.active+counts.expired+counts.inactive+counts.review;
  return counts;
}
