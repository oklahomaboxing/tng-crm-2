import React from "react";

const contact = <><a href="mailto:marketing@tngboxinggym.com">marketing@tngboxinggym.com</a> or <a href="tel:+14059595823">405-959-5823</a></>;

export default function TicketPolicies({ privacy = false }) {
  return <main style={{ maxWidth: 820, margin: "32px auto", padding: 24, lineHeight: 1.7, background: "white", color: "#182432", borderRadius: 12 }}>
    <a href="/">TNG Boxing</a>
    <h1>{privacy ? "Ticket Privacy Notice" : "Ticket Terms"}</h1>
    <p>Effective October 13, 2026. These policies cover TNG Boxing event ticket purchases and optional ticket texts. Contact: {contact}.</p>
    {privacy ? <>
      <h2>Information used for your tickets</h2>
      <p>We collect your name, email, ticket selections, order and payment references, and the fighter or seller associated with your purchase. If you request ticket texts, we collect your mobile number and record the consent wording and time. We use these records to process purchases, deliver QR tickets, check admission, resolve purchase and delivery issues, and account for seller sales and commissions.</p>
      <h2>Service providers and access</h2>
      <p>Clover processes payments, Resend delivers ticket emails, and Twilio delivers optional ticket texts. These providers receive the information needed to provide their services. Authorized event staff can access records needed to support purchases and admission. Keep your private ticket link and QR ticket secure.</p>
      <h2>Optional ticket texts</h2>
      <p>Text consent is optional and is not a condition of purchase. Ticket consent does not enroll you in promotional texts. Message frequency varies. Message and data rates may apply. Reply STOP to opt out. For help, contact {contact}.</p>
      <p>Customer mobile numbers and text-message consent are not sold or shared with third parties or affiliates for marketing or promotional purposes. We share them with service providers only as needed to deliver the service.</p>
      <h2>Questions and corrections</h2>
      <p>Contact {contact} with privacy questions or requests to access, correct, or delete your ticket information. We may need to verify your identity and retain records required to administer purchases, resolve disputes, or meet accounting and legal obligations.</p>
    </> : <>
      <h2>Purchase and admission</h2>
      <p>Checkout shows your event, ticket selection, quantity, and total before payment through Clover. Tickets are issued after verified successful payment. Each valid QR ticket permits one admission for its event and ticket type. Used, void, or refunded tickets cannot be reused. Keep your ticket and private access link secure. Contact {contact} if a paid ticket is missing.</p>
      <h2>Ticket delivery and optional texts</h2>
      <p>Tickets are available on the ticket page and by email. Optional ticket texts require a valid mobile number and your express consent. Texts concern your purchase, including QR ticket links and delivery updates. Message frequency varies. Message and data rates may apply. Reply STOP to opt out. Consent is not a condition of purchase. For help, contact {contact}. Carrier restrictions can affect text delivery; email and the ticket page remain available.</p>
      <h2>Refunds and event changes</h2>
      <p>Tickets are nonrefundable when a customer cancels their purchase. If TNG cancels the event, the ticket purchase will be refunded. If TNG reschedules the event, existing tickets remain valid; customers unable to attend the new date may request a refund by contacting {contact}.</p>
      <h2>Privacy</h2>
      <p>See our <a href="/ticket-privacy">Ticket Privacy Notice</a> for how we handle ticket information and text consent.</p>
    </>}
    <p><a href={privacy ? "/ticket-terms" : "/ticket-privacy"}>{privacy ? "Ticket Terms" : "Ticket Privacy Notice"}</a></p>
  </main>;
}
