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
    mockup_image_base64: str | None = None,
    mockup_asset_name: str | None = None,
    mockup_sponsor_name: str | None = None,
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

    mockup_html = ""
    attachments = []

    if mockup_image_base64:
        clean_mockup = str(
            mockup_image_base64
        ).strip()

        if clean_mockup.startswith("data:") and "," in clean_mockup:
            clean_mockup = clean_mockup.split(",", 1)[1]

        safe_asset_name = html.escape(
            mockup_asset_name
            or package_name
            or "Sponsorship Asset"
        )

        safe_mockup_sponsor = html.escape(
            mockup_sponsor_name
            or business_name
            or "Sponsor"
        )

        mockup_html = f"""
        <div style="
            border:1px solid #dddddd;
            border-radius:10px;
            padding:18px;
            margin:24px 0;
        ">
            <h3 style="margin-top:0;">
                Sponsorship Branding Concept
            </h3>

            <p style="
                color:#666666;
                font-size:13px;
            ">
                Concept preview for
                <strong>{safe_mockup_sponsor}</strong>
                on the
                <strong>{safe_asset_name}</strong>.
            </p>

            <img
                src="cid:tng-sponsorship-mockup"
                alt="Sponsorship branding concept"
                style="
                    display:block;
                    width:100%;
                    max-width:600px;
                    height:auto;
                    margin:16px 0;
                    border-radius:8px;
                    border:1px solid #dddddd;
                "
            >

            <p style="
                color:#777777;
                font-size:11px;
            ">
                Conceptual branding preview only.
                Final artwork, dimensions, and placement
                are confirmed before production.
            </p>
        </div>
        """

        attachments.append({
            "filename": "tng-sponsorship-mockup.png",
            "content": clean_mockup,
            "content_type": "image/png",
            "content_id": "tng-sponsorship-mockup",
        })
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

        {mockup_html}

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
        os.getenv("RESEND_FROM_EMAIL")
        or os.getenv("EMAIL_FROM")
        or os.getenv("TICKET_FROM_EMAIL")
        or "TNG Boxing <marketing@tngboxinggym.com>"
    )

    params = {
        "from": from_email,
        "to": [to_email],
        "reply_to": [
            os.getenv("REVENUE_REPLY_TO")
            or "revenue@inbound.tngboxinggym.com"
        ],
        "subject": proposal_title,
        "html": email_html,
    }

    if attachments:
        params["attachments"] = attachments

    return resend.Emails.send(params)
