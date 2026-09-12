import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

def send_ticket_email(
    to_email: str,
    event_name: str,
    receipt_number: str,
    tickets: list[dict],
    total_cents: int,
):
    ticket_html = ""
    attachments = []

    for index, ticket in enumerate(tickets, start=1):
        qr = ticket.get("qr_png_base64")
        cid = f"ticketqr{index}"

        if qr:
            attachments.append({
                "filename": f"{ticket.get('ticket_number')}.png",
                "content": qr,
                "content_id": cid,
            })

        ticket_html += f"""
        <div style="border:1px solid #ddd;padding:16px;margin:16px 0;border-radius:8px;">
            <h3>{ticket.get('ticket_number')}</h3>
            <p>Status: {ticket.get('status')}</p>
            <p>Price: ${ticket.get('price_cents', 0) / 100:.2f}</p>
            {
                f'<img src="cid:{cid}" width="220" height="220" alt="Ticket QR Code" />'
                if qr else ''
            }
        </div>
        """

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;">
        <h2>TNG Promotions</h2>
        <h3>{event_name}</h3>

        <p>Thank you for your purchase.</p>

        <p><strong>Receipt:</strong> {receipt_number}</p>
        <p><strong>Total Paid:</strong> ${total_cents / 100:.2f}</p>

        <hr>

        <h3>Your Ticket(s)</h3>

        {ticket_html}

        <p>Present each QR code at the door. Each ticket can only be scanned once.</p>

        <p>Earned Not Given.</p>
    </div>
    """

    return resend.Emails.send({
        "from": os.getenv(
            "TICKET_FROM_EMAIL",
            "TNG Promotions <onboarding@resend.dev>"
        ),
        "to": [to_email],
        "subject": f"Your TNG Tickets — {event_name}",
        "html": html,
        "attachments": attachments,
    })
def send_fighter_report(
    to_email: str,
    fighter_name: str,
    event_name: str,
    tickets_sold: int,
    gross_sales_cents: int,
    commission_earned_cents: int,
    commission_paid_cents: int = 0,
):
    balance_due_cents = commission_earned_cents - commission_paid_cents

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:650px;margin:auto;">
        <h2>TNG Promotions</h2>
        <h3>{event_name}</h3>

        <p>Hello {fighter_name},</p>

        <p>Here is your final ticket sales and commission report.</p>

        <table style="width:100%;border-collapse:collapse;margin-top:20px;">
            <tr>
                <td style="padding:10px;border-bottom:1px solid #ddd;">
                    Tickets Sold
                </td>
                <td style="padding:10px;border-bottom:1px solid #ddd;text-align:right;">
                    <strong>{tickets_sold}</strong>
                </td>
            </tr>

            <tr>
                <td style="padding:10px;border-bottom:1px solid #ddd;">
                    Gross Ticket Sales
                </td>
                <td style="padding:10px;border-bottom:1px solid #ddd;text-align:right;">
                    <strong>${gross_sales_cents / 100:.2f}</strong>
                </td>
            </tr>

            <tr>
                <td style="padding:10px;border-bottom:1px solid #ddd;">
                    Commission Earned
                </td>
                <td style="padding:10px;border-bottom:1px solid #ddd;text-align:right;">
                    <strong>${commission_earned_cents / 100:.2f}</strong>
                </td>
            </tr>

            <tr>
                <td style="padding:10px;border-bottom:1px solid #ddd;">
                    Commission Paid
                </td>
                <td style="padding:10px;border-bottom:1px solid #ddd;text-align:right;">
                    ${commission_paid_cents / 100:.2f}
                </td>
            </tr>

            <tr>
                <td style="padding:10px;">
                    Balance Due
                </td>
                <td style="padding:10px;text-align:right;">
                    <strong>${balance_due_cents / 100:.2f}</strong>
                </td>
            </tr>
        </table>

        <p style="margin-top:24px;">
            Thank you for helping promote the event.
        </p>

        <p>Earned Not Given.</p>
    </div>
    """

    return resend.Emails.send({
        "from": os.getenv(
            "TICKET_FROM_EMAIL",
            "TNG Promotions <onboarding@resend.dev>"
        ),
        "to": [to_email],
        "subject": f"{event_name} — Ticket Sales & Commission Report",
        "html": html,
    })


def send_seller_ticket_link(
    to_email: str,
    seller_name: str,
    event_name: str,
    ticket_url: str,
    qr_png_base64: str,
):
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:650px;margin:auto;">
        <h2>TNG Promotions</h2>
        <h3>{event_name}</h3>

        <p>Hello {seller_name},</p>

        <p>
            Your personal ticket sales link is ready.
            Tickets purchased through this link will be credited to you.
        </p>

        <div style="margin:24px 0;">
            <a
                href="{ticket_url}"
                style="
                    display:inline-block;
                    background:#d71920;
                    color:#ffffff;
                    padding:12px 20px;
                    text-decoration:none;
                    border-radius:8px;
                    font-weight:bold;
                "
            >
                Open My Ticket Sales Page
            </a>
        </div>

        <p style="word-break:break-all;">
            <strong>Your personal link:</strong><br>
            {ticket_url}
        </p>

        <div style="margin-top:24px;">
            <p><strong>Your QR Code</strong></p>
            <img
                src="cid:sellerqr"
                width="240"
                height="240"
                alt="Personal Ticket Sales QR Code"
            />
        </div>

        <p style="margin-top:24px;">
            Share either the link or QR code with your supporters.
        </p>

        <p>Earned Not Given.</p>
    </div>
    """

    return resend.Emails.send({
        "from": os.getenv(
            "TICKET_FROM_EMAIL",
            "TNG Promotions <onboarding@resend.dev>"
        ),
        "to": [to_email],
        "subject": f"{event_name} - Your Personal Ticket Sales Link",
        "html": html,
        "attachments": [
            {
                "filename": "tng-ticket-sales-qr.png",
                "content": qr_png_base64,
                "content_id": "sellerqr",
            }
        ],
    })
