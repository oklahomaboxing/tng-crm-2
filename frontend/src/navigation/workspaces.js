export const ROLE_MENUS = {
  admin: [
    "Dashboard",
    "System Overview",
    "Call Center",
    "Renewal Reminders",
    "TNG Apparel",
    "Members",
    "TNGTrainer",
    "TNG Boxing Game",
    "Promoter",
    "Amateur Matchmaker",
    "Announcer & DJ",
    "TNG BOXING EVENTS",
    "Chef & Concessions",
    "Venue & Event Bookings",
    "Fight Calendar",
    "Products",
    "Member Check-In",
    "Check-In Kiosk",
    "Event Check-In",
    "Sales",
    "Leads",
    "Text Inbox",
    "Club Inbox",
    "Venue Inbox",
    "Officials Inbox",
    "QR Referrals",
    "Marketing Center",
    "Clover",
    "Duplicate Review",
    "Security Center",
    "Reports",
    "Fighter Portal Videos",
    "User Management",
    "Investor Center",
    "Fight Recap",
    "USA Boxing Officials",
    "Oklahoma Boxing Clubs",
  ],
  staff: [
    "Amateur Matchmaker",
    "Announcer & DJ",
    "Member Check-In",
    "Check-In Kiosk",
    "Event Check-In",
    "TNG BOXING EVENTS",
    "Fight Calendar",
    "Members",
    "Sales",
    "Leads",
    "Text Inbox",
    "Club Inbox",
    "Venue Inbox",
    "Officials Inbox",
    "QR Referrals",
    "TNGTrainer",
    "Fight Recap",
    "USA Boxing Officials",
    "Oklahoma Boxing Clubs",
  ],
  matchmaker: [
    "Promoter",
    "Amateur Matchmaker",
    "TNG BOXING EVENTS",
    "Fight Calendar",
  ],
  manager: [
    "Manager Portal",
  ],
  rep: ["My Sales"],
  investor: ["Investor Portal"],
  sponsor: ["Sponsor Portal"],
  concessions: ["Chef & Concessions"],
  event_coordinator: ["Venue & Event Bookings"],
  announcer: ["Announcer & DJ"],
  dj: ["Announcer & DJ"],
};

export const WORKSPACE_GROUPS = [
  { id: 'home', label: 'HOME', description: 'Daily overview and work that needs attention.', accent: '#88b8cf', pages: ['Dashboard', 'System Overview', 'Investor Portal', 'Sponsor Portal', 'Concessions Portal'] },
  { id: 'gym', label: 'GYM & MEMBERS', description: 'Profiles, check-in, renewals and training.', accent: '#34b6b0', pages: ['Members', 'Member Check-In', 'Check-In Kiosk', 'Renewal Reminders', 'TNGTrainer', 'TNG Boxing Game'] },
  { id: 'boxing', label: 'TNG PROMOTIONS', description: 'Fighters, matchmaking, fight cards, contracts and entry.', accent: '#e43852', pages: ['Announcer & DJ', 'Amateur Matchmaker', 'TNG BOXING EVENTS', 'Fight Recap', 'USA Boxing Officials', 'Oklahoma Boxing Clubs', 'Club Inbox', 'Officials Inbox', 'Promoter', 'Event Check-In', 'Fight Calendar', 'Fighter Portal Videos', 'Manager Portal'] },
  { id: 'operations', label: 'VENUE & OPERATIONS', description: 'Facility bookings, venue messages and event concessions.', accent: '#487e93', pages: ['Venue & Event Bookings', 'Venue Inbox', 'Chef & Concessions'] },
  { id: 'retail', label: 'SHOP & SALES', description: 'Apparel, products, purchases and sales reporting.', accent: '#bb8d40', pages: ['TNG Apparel', 'Sales', 'Products', 'Reports', 'My Sales'] },
  { id: 'growth', label: 'MARKETING', description: 'Leads, member communication and referral links.', accent: '#8f83d8', pages: ['Text Inbox', 'Call Center', 'Marketing Center', 'Leads', 'QR Referrals'] },
  { id: 'admin', label: 'ADMINISTRATION', description: 'Connections, account security, users and contact cleanup.', accent: '#7896b3', pages: ['Investor Center', 'Clover', 'Duplicate Review', 'User Management', 'Security Center'] },
];
export const WORKSPACE_HINTS = {
 'Oklahoma Boxing Clubs':'Oklahoma boxing gyms clubs coaches contact person phone email directory',
 'USA Boxing Officials':'Oklahoma LBC 27 USA Boxing official contacts work texts SMS permission messages conversations',
 'Fight Recap':'Compare event revenue costs fighter purses commissions expenses profit loss side by side',
  "Announcer & DJ": "Event run of show, fighter introductions, walkout songs, announcer profile, sponsor promotions and concessions sales announcements",
  "TNG Boxing Game": "Play boxing combinations with keyboard or controller: punches, slips, defense and timed drills",
  "Investor Center": "Investor business access, membership revenue, event and fighter ticket sales, expenses and published updates",
  "Amateur Matchmaker": "Upload amateur boxing rosters, review ages weights and experience, USA Boxing Appendix F proposals",
  "Venue & Event Bookings": "Facility rentals, coordinator calendar, public booking requests, holds and reservations",
  "Investor Portal": "Your assigned event updates and approved business summaries",
  "Chef & Concessions": "Event kitchen: menu pricing, food costs, shopping lists, prep, AI drafts and printable menus",
  "Concessions Portal": "Your assigned event concessions details and updates",
  "Sponsor Portal": "Your assigned sponsorship events and TNG updates",
  Dashboard: 'Daily membership, attendance, sales and event overview',
  'Club Inbox': 'Oklahoma club SMS conversations and replies',
  'Venue Inbox': 'Venue booking SMS conversations and replies',
  'Officials Inbox': 'Official work texts, replies and unread conversations',
  'Text Inbox': 'Incoming SMS, unread conversations and customer service replies',
  'Call Center': 'Inbound phone calls, marketing transfers, callbacks and ticket checkout texts',
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
 'TNG BOXING EVENTS':'boxing events tng promotions fight night promotion signed pdf download contracts paper tickets print batch sponsors sponsorship budget forecast planning break even itemized expenses concessions bar recap paid purses payouts deductions profit loss commission results scorecards judges winners knockout',
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
export const EVENT_SECTIONS={overview:0,'fight-card':1,contracts:2,compliance:3,checklist:4,medicals:5,expenses:6,sponsors:7,settings:8,tickets:9,matchmaking:10,fighters:11,'fight-night':12,recap:13,offers:14,'matchmaker-desk':15,concessions:16,budget:17};
export function workspaceSlug(page) { return page.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }
export function workspaceHash(page, target = {}) {
  const params = new URLSearchParams();
  if (page === "Members" && Number.isSafeInteger(Number(target.memberId)) && Number(target.memberId) > 0) params.set("member", String(target.memberId));
  if (["TNG BOXING EVENTS","Announcer & DJ"].includes(page) && Number.isSafeInteger(Number(target.eventId)) && Number(target.eventId) > 0) params.set("event", String(target.eventId));
  if(page==='TNG BOXING EVENTS'&&Object.prototype.hasOwnProperty.call(EVENT_SECTIONS,target.eventSection))params.set('section',target.eventSection);
  return `#/${workspaceSlug(page)}${params.size ? `?${params}` : ""}`;
}
export function readWorkspace(hash, role) {
  let [slug, query = ""] = String(hash || "").replace(/^#\/?/, "").split("?");
  if (slug === 'concessions-portal') slug='chef-concessions';
  if (slug === 'front-desk') slug='member-check-in';
  const page = (ROLE_MENUS[role] || []).find(p => workspaceSlug(p) === slug);
  if (!page) return null;
  const params = new URLSearchParams(query), target = {};
  for (const [key, name] of [["member", "memberId"], ["event", "eventId"]]) {
    const value = Number(params.get(key));
    if (Number.isSafeInteger(value) && value > 0 && ((key === "member" && page === "Members") || (key === "event" && ["TNG BOXING EVENTS","Announcer & DJ"].includes(page)))) target[name] = value;
  }
  const section=params.get('section');
  if(page==='TNG BOXING EVENTS'&&Object.prototype.hasOwnProperty.call(EVENT_SECTIONS,section)&&(!['recap','concessions','budget'].includes(section)||['admin','staff'].includes(role)))target.eventSection=section;
  return { page, target };
}
