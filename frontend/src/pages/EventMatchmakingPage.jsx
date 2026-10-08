import React from "react";
import EventFightCardBuilder from "./EventFightCardBuilder.jsx";

export default function EventMatchmakingPage({
  eventId,
  event,
  bouts,
  onRefresh,
}) {
  return (
    <EventFightCardBuilder
      eventId={eventId}
      event={event}
      bouts={bouts}
      onRefresh={onRefresh}
    />
  );
}
