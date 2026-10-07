import React from "react";
import EventRevenue from "./EventRevenue";

export default function EventRevenuePage({
  eventId,
  event,
}) {
  return (
    <EventRevenue
      eventId={eventId}
      event={event}
    />
  );
}
