import React from "react";
import { Card } from "@mui/material";
import TicketingDashboard from "./TicketingDashboard.jsx";

export default function EventTicketsPage({
  eventId,
  event,
}) {
  return (
    <Card>
      <TicketingDashboard
        key={eventId}
        eventId={eventId}
        event={event}
      />
    </Card>
  );
}
