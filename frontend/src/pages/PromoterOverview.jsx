import React, { useState } from "react";
import { Box, Button, Card, Chip, Stack, TextField, Typography } from "@mui/material";
import { ArrowUpRight, CalendarDays, ChevronRight, Copy, Plus, Users, Swords, Network, Ticket } from "lucide-react";

export function eventDate(value) {
  if (!value) return null;
  const date = new Date(/^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T12:00:00` : value);
  return Number.isNaN(date.getTime()) ? null : date;
}
export function displayEventDate(value) {
  return eventDate(value)?.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) || "Date to be announced";
}
const statusLabel = (event) => String(event.status || "planning").replaceAll("_", " ");
const lanes = [
  ["events", CalendarDays, "Events", "Plan the promotion. Run the show."],
  ["fighter-pool", Users, "Fighter pool", "Talent, profiles and availability."],
  ["matchmaking", Swords, "Matchmaking", "Find opponents. Build your card."],
  ["managers", Network, "Managers", "Relationships and represented talent."],
];

export default function PromoterOverview({ events, fighters, eligible, onNavigate, onCreate, onOpen, onCopyRegistration }) {
  const [search, setSearch] = useState("");
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const upcoming = events.filter(e => !["cancelled", "canceled", "completed", "complete"].includes(e.status) && eventDate(e.event_date) && eventDate(e.event_date) >= today);
  upcoming.sort((a, b) => eventDate(a.event_date) - eventDate(b.event_date));
  const featured = upcoming[0] || events.find(e => !["cancelled", "canceled", "completed", "complete"].includes(e.status));
  const visible = [...events].sort((a, b) => (eventDate(b.event_date)?.getTime() || 0) - (eventDate(a.event_date)?.getTime() || 0))
    .filter(e => `${e.name} ${e.venue || ""}`.toLowerCase().includes(search.toLowerCase())).slice(0, 5);
  return <Stack spacing={3}>
    <Box className="promotion-hero">
      <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2} flexWrap="wrap" useFlexGap>
        <Box><Typography className="promotion-eyebrow">TNG BOXING / PROMOTIONS</Typography><Typography component="h1" sx={{ fontSize: { xs: 34, md: 54 }, fontWeight: 900, letterSpacing: "-.055em", lineHeight: 1.1, mt: 1.5 }}>Build the card.<br />Own the night.</Typography><Typography sx={{ color: "#b8bec8", mt: 2, maxWidth: 470 }}>Your events, talent and operations. One clear view of what comes next.</Typography></Box>
        <Button variant="contained" sx={{ alignSelf: "center", height: 44, flexShrink: 0 }} startIcon={<Plus size={18} />} onClick={onCreate}>Create event</Button>
      </Stack>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "repeat(2,1fr)", md: "repeat(4,1fr)" }, mt: 4, gap: 3, pt: 3, borderTop: "1px solid #ffffff24" }}>
        {[[events.length, "Total events"], [upcoming.length, "Upcoming events"], [fighters.length, "Fighters in pool"], [eligible, "Eligible fighters"]].map(([value, label]) => <Box key={label}><Typography sx={{ fontSize: 30, fontWeight: 850, fontVariantNumeric: "tabular-nums" }}>{value}</Typography><Typography sx={{ color: "#b8bec8", fontSize: 12 }}>{label}</Typography></Box>)}
    </Box>
    </Box>
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(4,1fr)" }, gap: 1.5 }}>
      {lanes.map(([key, Icon, title, detail]) => <Button key={key} className="promotion-lane" onClick={() => onNavigate(key)}><Icon size={21} /><Box sx={{ flex: 1, textAlign: "left" }}><Typography fontWeight={800}>{title}</Typography><Typography sx={{ fontSize: 12, color: "text.secondary", mt: .5 }}>{detail}</Typography></Box><ArrowUpRight size={17} /></Button>)}
    </Box>
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "minmax(0,1.7fr) minmax(280px,1fr)" }, gap: 3 }}>
      <Card sx={{ p: { xs: 2, md: 3 } }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}><Box><Typography component="h2" variant="h6">Event desk</Typography><Typography color="text.secondary" variant="body2">Pick up where your promotion left off.</Typography></Box><Button onClick={() => onNavigate("events")} endIcon={<ChevronRight size={16} />}>View all</Button></Stack>
        <TextField size="small" fullWidth label="Find an event or venue" value={search} onChange={e => setSearch(e.target.value)} sx={{ my: 2.5 }} />
        {visible.map(e => <Button key={e.id} onClick={() => onOpen(e.id)} className="promotion-event-row"><Box sx={{ color: "primary.main", bgcolor: "#f5f5f7", p: 1.2, borderRadius: 2 }}><CalendarDays size={21} /></Box><Box sx={{ flex: 1, textAlign: "left", minWidth: 0 }}><Typography fontWeight={800}>{e.name}</Typography><Typography variant="body2" color="text.secondary">{displayEventDate(e.event_date)} · {e.venue || "Venue pending"}</Typography></Box><Chip size="small" label={statusLabel(e)} sx={{ textTransform: "capitalize", display: { xs: "none", sm: "flex" } }} /><ChevronRight size={18} /></Button>)}
        {!visible.length && <Box sx={{ py: 4, textAlign: "center" }}><Typography fontWeight={800}>{events.length ? "No matching events" : "Your next promotion starts here"}</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>{events.length ? "Try another event name or venue." : "Create an event, then build your card and launch ticket sales."}</Typography>{!events.length && <Button onClick={onCreate} sx={{ mt: 2 }} startIcon={<Plus size={16} />}>Create event</Button>}</Box>}
      </Card>
      <Stack spacing={2}>
        <Card sx={{ p: 3, borderTop: "3px solid #d71920" }}><Typography className="promotion-eyebrow" color="text.secondary">{upcoming.length ? "NEXT ON THE CALENDAR" : "EVENT IN FOCUS"}</Typography><Typography variant="h5" sx={{ mt: 2 }}>{featured?.name || "Ready for your next event?"}</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>{featured ? displayEventDate(featured.event_date) : "Create a promotion to unlock your event workspace."}</Typography><Typography color="text.secondary" variant="body2" sx={{ mt: .5 }}>{featured?.venue || ""}</Typography>{featured && <Stack spacing={1} sx={{ mt: 3 }}><Button variant="contained" onClick={() => onOpen(featured.id)} endIcon={<ArrowUpRight size={16} />}>Open event workspace</Button><Button variant="outlined" startIcon={<Ticket size={17} />} onClick={() => onOpen(featured.id, 9)}>Tickets & seller sales</Button></Stack>}</Card>
        <Card sx={{ p: 3 }}><Typography fontWeight={850}>Bring talent into your corner.</Typography><Typography variant="body2" color="text.secondary" sx={{ my: 1.5 }}>Share the fighter registration link with fighters, managers and coaches.</Typography><Button variant="outlined" fullWidth startIcon={<Copy size={16} />} onClick={onCopyRegistration}>Copy registration link</Button></Card>
      </Stack>
    </Box>
  </Stack>;
}
