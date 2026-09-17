import os
import html
import resend

resend.api_key = os.getenv("RESEND_API_KEY")


def send_revenue_proposal_email(
    to_email: str,
    business_name: str,
    proposal_title: str,
    proposal_message: str,
    package_name: str = "",
    package_price: float = 0,
    clover_payment_url: str | None = None,
):
    safe_business = html.escape(business_name or "Business Partner")
    safe_title = html.escape(proposal_title or "TNG Promotions Partnership")
    safe_message = html.escape(proposal_message or "").replace("\n", "<br>")
    safe_package = html.escape(package_name or "")

    package_html = ""

    if package_name:
        package_html = f"""
        <div style="
            border:1px solid #dddddd;
            border-radius:10px;
            padding:18px;
            margin:24px 0;
        ">
            <h3 style="margin-top:0;">{safe_package}</h3>
            <p style="font-size:22px;font-weight:bold;">
                ${package_price:,.2f}
            </p>
        </div>
        """

    payment_html = ""

    if clover_payment_url:
        safe_payment_url = html.escape(
            clover_payment_url,
            quote=True,
        )

        payment_html = f"""
        <div style="margin:28px 0;">
            <a
                href="{safe_payment_url}"
                style="
                    display:inline-block;
                    background:#111111;
                    color:#ffffff;
                    padding:14px 24px;
                    text-decoration:none;
                    border-radius:8px;
                    font-weight:bold;
                    font-size:16px;
                "
            >
                Secure Sponsorship
            </a>
        </div>

        <p style="font-size:12px;color:#666666;">
            Payment is securely processed through Clover.
        </p>
        """

    email_html = f"""
    <div style="
        font-family:Arial,sans-serif;
        max-width:650px;
        margin:auto;
        color:#111111;
        line-height:1.5;
    ">
        <h2>TNG Promotions</h2>

        <h3>{safe_title}</h3>

        <p>Hello {safe_business},</p>

        <p>{safe_message}</p>

        {package_html}

        {payment_html}

        <hr style="margin:30px 0;border:none;border-top:1px solid #dddddd;">

        <p>
            We would be glad to discuss the partnership,
            customize the package, or answer any questions.
        </p>

        <p>
            TNG Promotions<br>
            Earned Not Given.
        </p>
    </div>
    """

    from_email = (
        os.getenv("EMAIL_FROM")
        or os.getenv("TICKET_FROM_EMAIL")
        or "TNG Promotions <onboarding@resend.dev>"
    )

    return resend.Emails.send({
        "from": from_email,
        "to": [to_email],
        "subject": proposal_title,
        "html": email_html,
    })
