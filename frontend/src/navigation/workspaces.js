export const ROLE_MENUS = {
  admin: [
    "Dashboard",
    "System Overview",
    "Members",
    "TNGTrainer",
    "Promoter",
    "TNG BOXING EVENTS",
    "Fight Calendar",
    "Products",
    "Front Desk",
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
    "Front Desk",
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
  { label: "COMMAND", pages: ["Dashboard", "System Overview"] },
  { label: "GYM OPERATIONS", pages: ["Members", "Front Desk", "Sales", "Products", "TNGTrainer"] },
  { label: "TNG PROMOTIONS", pages: ["TNG BOXING EVENTS", "Event Check-In", "Promoter", "Fight Calendar", "Fighter Portal Videos"] },
  { label: "GROWTH", pages: ["Leads", "QR Referrals", "Marketing Center", "My Sales"] },
  { label: "ADMINISTRATION", pages: ["Clover", "Duplicate Review", "Reports", "User Management", "Security Center", "Manager Portal"] },
];
export const WORKSPACE_HINTS = {
  Members: "Profiles, portal access, memberships and renewals",
  "Front Desk": "Gym member QR scanner and member-number check-in",
  "Event Check-In": "Fight-night ticket scanner and paper ticket activation",
  "TNG BOXING EVENTS": "Fight cards, contracts, ticket sales and printed tickets",
  Promoter: "Fighter scouting, opponents, managers and matchmaking",
  "System Overview": "Work queue, delivery issues and connection configuration",
  "Marketing Center": "Member email, texts, campaign drafts and AI content",
  Clover: "Payment integration, products and explicit sales sync",
};
export function workspaceSlug(page) { return page.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""); }
export function workspaceHash(page, target = {}) {
  const params = new URLSearchParams();
  if (page === "Members" && Number.isSafeInteger(Number(target.memberId)) && Number(target.memberId) > 0) params.set("member", String(target.memberId));
  if (page === "TNG BOXING EVENTS" && Number.isSafeInteger(Number(target.eventId)) && Number(target.eventId) > 0) params.set("event", String(target.eventId));
  return `#/${workspaceSlug(page)}${params.size ? `?${params}` : ""}`;
}
export function readWorkspace(hash, role) {
  const [slug, query = ""] = String(hash || "").replace(/^#\/?/, "").split("?");
  const page = (ROLE_MENUS[role] || []).find(p => workspaceSlug(p) === slug);
  if (!page) return null;
  const params = new URLSearchParams(query), target = {};
  for (const [key, name] of [["member", "memberId"], ["event", "eventId"]]) {
    const value = Number(params.get(key));
    if (Number.isSafeInteger(value) && value > 0 && ((key === "member" && page === "Members") || (key === "event" && page === "TNG BOXING EVENTS"))) target[name] = value;
  }
  return { page, target };
}
