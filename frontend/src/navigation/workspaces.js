export const ROLE_MENUS = {
  admin: [
    "Dashboard",
    "System Overview",
    "Renewal Reminders",
    "TNG Apparel",
    "Members",
    "TNGTrainer",
    "Promoter",
    "TNG BOXING EVENTS",
    "Fight Calendar",
    "Products",
    "Member Check-In",
    "Check-In Kiosk",
    "Event Check-In",
    "Sales",
    "Leads",
    "QR Referrals",
    "Marketing Center",
    "Clover",
    "Duplicate Review",
    "Security Center",
    "Reports",
    "Fighter Portal Videos",
    "User Management",
  ],
  staff: [
    "Member Check-In",
    "Check-In Kiosk",
    "Event Check-In",
    "TNG BOXING EVENTS",
    "Fight Calendar",
    "Members",
    "Sales",
    "Leads",
    "QR Referrals",
    "TNGTrainer",
  ],
  matchmaker: [
    "Promoter",
    "TNG BOXING EVENTS",
    "Fight Calendar",
  ],
  manager: [
    "Manager Portal",
  ],
  rep: ["My Sales"],
};

export const WORKSPACE_GROUPS = [
  { id: 'home', label: 'HOME', description: 'Daily overview and work that needs attention.', accent: '#88b8cf', pages: ['Dashboard', 'System Overview'] },
  { id: 'gym', label: 'GYM & MEMBERS', description: 'Profiles, check-in, renewals and training.', accent: '#34b6b0', pages: ['Members', 'Member Check-In', 'Check-In Kiosk', 'Renewal Reminders', 'TNGTrainer'] },
  { id: 'boxing', label: 'BOXING & EVENTS', description: 'Fighters, matchmaking, fight cards, contracts and entry.', accent: '#e43852', pages: ['TNG BOXING EVENTS', 'Promoter', 'Event Check-In', 'Fight Calendar', 'Fighter Portal Videos', 'Manager Portal'] },
  { id: 'retail', label: 'SHOP & SALES', description: 'Apparel, products, purchases and sales reporting.', accent: '#bb8d40', pages: ['TNG Apparel', 'Sales', 'Products', 'Reports', 'My Sales'] },
  { id: 'growth', label: 'MARKETING', description: 'Leads, member communication and referral links.', accent: '#8f83d8', pages: ['Marketing Center', 'Leads', 'QR Referrals'] },
  { id: 'admin', label: 'ADMINISTRATION', description: 'Connections, account security, users and contact cleanup.', accent: '#7896b3', pages: ['Clover', 'Duplicate Review', 'User Management', 'Security Center'] },
];
export const WORKSPACE_HINTS = {
  Dashboard: 'Daily membership, attendance, sales and event overview',
  'System Overview': 'Work queue, payment reconciliation and connection status',
  Members: 'Gym member profiles, account activation, memberships and renewals',
  'Member Check-In': 'Front desk member-number keypad and new-member signup QR',
  'Check-In Kiosk': 'Entrance tablet pairing, attendance and device settings',
  'Renewal Reminders': 'Membership renewal and expiration email/text notices and delivery history',
  TNGTrainer: 'Training sessions, coaches and member development',
  'TNG BOXING EVENTS': 'Open an event: fight card, tickets, contracts, printing and event operations',
  Promoter: 'Find fighters, scout opponents, manage matchups and view signed contracts',
  'Event Check-In': 'Fight-night ticket QR scanner and printed ticket activation',
  'Fight Calendar': 'Upcoming fight dates and event planning',
  'Fighter Portal Videos': 'Review fighter submissions and footage',
  'Manager Portal': 'Manager agreements and fighter representation',
  'TNG Apparel': 'Shirt designs, presales, Clover items, public shop links and pickup orders',
  Sales: 'Record purchases and review the sales ledger',
  Products: 'Membership plans, prices and merchandise inventory',
  Reports: 'Revenue, sales, commissions and business reports',
  'My Sales': 'Your sales and commissions',
  'Marketing Center': 'Email, text messages and campaigns for gym members',
  Leads: 'Prospective customers, follow-ups and contact details',
  'QR Referrals': 'Referral QR codes and signup links',
  Clover: 'Payment connection, catalog and customer synchronization',
  'Duplicate Review': 'Find and merge duplicate contacts',
  'User Management': 'Staff accounts, roles and access',
  'Security Center': 'Trusted devices, sign-ins, account protection and activity',
};
const ALIASES = {
 'Member Check-In':'front desk attendance number scanner checkin check in',
 'Event Check-In':'door scanner fight night scan tickets checkin check in',
 'TNG Apparel':'shirts tee tshirt clothing shop store preorder',
 'Promoter':'matchmaker matchmaking pro boxers scouting signed pdf download contracts',
 'TNG BOXING EVENTS':'fight night promotion signed pdf download contracts paper tickets print batch sponsors sponsorship budget expenses',
 'Marketing Center':'sms txt text email members marketing campaigns',
 'Members':'activate activation reset email resend customer profile',
 'Renewal Reminders':'sms txt text expired expiring membership reminders renew',
};
export function workspaceGroup(page) { return WORKSPACE_GROUPS.find(group=>group.pages.includes(page)); }
export function searchWorkspaces(role, query='') {
 const words=query.toLowerCase().trim().split(/\s+/).filter(Boolean);
 return (ROLE_MENUS[role]||[]).filter(page=>words.every(word=>`${page} ${WORKSPACE_HINTS[page]||''} ${ALIASES[page]||''} ${workspaceGroup(page)?.label||''}`.toLowerCase().includes(word)));
}
export function dailyWorkspaces(role) {
 const allowed=ROLE_MENUS[role]||[];
 const preferred=role==='matchmaker'?['Promoter','TNG BOXING EVENTS','Fight Calendar']:role==='staff'?['Member Check-In','Members','Event Check-In','TNG BOXING EVENTS']:['Member Check-In','Members','TNG BOXING EVENTS','Promoter','TNG Apparel','Event Check-In'];
 const chosen=preferred.filter(page=>allowed.includes(page));
 return chosen.length?chosen:allowed.slice(0,4);
}
export function workspaceSlug(page) { return page.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }
export function workspaceHash(page, target = {}) {
  const params = new URLSearchParams();
  if (page === "Members" && Number.isSafeInteger(Number(target.memberId)) && Number(target.memberId) > 0) params.set("member", String(target.memberId));
  if (page === "TNG BOXING EVENTS" && Number.isSafeInteger(Number(target.eventId)) && Number(target.eventId) > 0) params.set("event", String(target.eventId));
  return `#/${workspaceSlug(page)}${params.size ? `?${params}` : ""}`;
}
export function readWorkspace(hash, role) {
  let [slug, query = ""] = String(hash || "").replace(/^#\/?/, "").split("?");
  if (slug === 'front-desk') slug='member-check-in';
  const page = (ROLE_MENUS[role] || []).find(p => workspaceSlug(p) === slug);
  if (!page) return null;
  const params = new URLSearchParams(query), target = {};
  for (const [key, name] of [["member", "memberId"], ["event", "eventId"]]) {
    const value = Number(params.get(key));
    if (Number.isSafeInteger(value) && value > 0 && ((key === "member" && page === "Members") || (key === "event" && page === "TNG BOXING EVENTS"))) target[name] = value;
  }
  return { page, target };
}
