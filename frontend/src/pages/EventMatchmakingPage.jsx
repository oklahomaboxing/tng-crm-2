import React from "react";
import EventFightCardBuilder from "./EventFightCardBuilder.jsx";

export default function EventMatchmakingPage({
  eventId,
  event,
  bouts,
  onRefresh,
  view, onOpenCard, onOpenContracts, onOpenOffers,
}) {
  return (
    <EventFightCardBuilder
      eventId={eventId}
      event={event}
      bouts={bouts}
      onRefresh={onRefresh}
      view={view} onOpenCard={onOpenCard} onOpenContracts={onOpenContracts} onOpenOffers={onOpenOffers}
    />
  );
}
