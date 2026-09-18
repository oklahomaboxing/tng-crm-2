from datetime import datetime, timedelta
import os

import resend

from . import models


TERMINAL_PROSPECT_STATUSES = {
    "REPLIED",
    "COMMITTED",
    "PAID",
    "DECLINED",
    "NO_RESPONSE",
}

STOP_EMAIL_STATUSES = {
    "BOUNCED",
    "FAILED",
    "COMPLAINED",
    "CANCELLED",
}


def run_due_followups(db):
    enabled = (
        os.getenv("AUTO_SPONSOR_FOLLOWUPS", "false")
        .strip()
        .lower()
        in {"1", "true", "yes", "on"}
    )

    now = datetime.utcnow()

    prospects = (
        db.query(models.EventRevenueProspect)
        .filter(
            models.EventRevenueProspect.next_follow_up_at.isnot(None),
            models.EventRevenueProspect.next_follow_up_at <= now,
            models.EventRevenueProspect.do_not_contact == False,
        )
        .all()
    )

    summary = {
        "checked": len(prospects),
        "sent": 0,
        "stopped": 0,
        "skipped": 0,
        "disabled": not enabled,
    }

    for prospect in prospects:
        status = (prospect.status or "").upper()

        if status in TERMINAL_PROSPECT_STATUSES:
            prospect.next_follow_up_at = None
            summary["stopped"] += 1
            continue

        organization = prospect.organization

        if not organization or not organization.email:
            prospect.status = "NEEDS_CONTACT"
            prospect.next_follow_up_at = None
            summary["stopped"] += 1
            continue

        latest_email = (
            db.query(models.RevenueOutreachMessage)
            .filter(
                models.RevenueOutreachMessage.event_id
                == prospect.event_id,
                models.RevenueOutreachMessage.prospect_id
                == prospect.id,
                models.RevenueOutreachMessage.channel == "EMAIL",
            )
            .order_by(
                models.RevenueOutreachMessage.created_at.desc()
            )
            .first()
        )

        if not latest_email:
            summary["skipped"] += 1
            continue

        latest_status = (latest_email.status or "").upper()

        if latest_status in STOP_EMAIL_STATUSES:
            prospect.next_follow_up_at = None
            summary["stopped"] += 1
            continue

        followup_count = (
            db.query(models.RevenueOutreachMessage)
            .filter(
                models.RevenueOutreachMessage.event_id
                == prospect.event_id,
                models.RevenueOutreachMessage.prospect_id
                == prospect.id,
                models.RevenueOutreachMessage.template_key
                == "SPONSOR_FOLLOWUP",
            )
            .count()
        )

        # Maximum 2 automatic follow-ups.
        if followup_count >= 2:
            prospect.status = "NO_RESPONSE"
            prospect.next_follow_up_at = None
            summary["stopped"] += 1
            continue

        # Job can run safely while sending is disabled.
        if not enabled:
            summary["skipped"] += 1
            continue

        api_key = os.getenv("RESEND_API_KEY")
        email_from = os.getenv("EMAIL_FROM")

        if not api_key or not email_from:
            summary["skipped"] += 1
            continue

        business_name = (
            organization.business_name
            or "your organization"
        )

        ask = prospect.recommended_ask

        if followup_count == 0:
            subject = (
                "Following up on our TNG Boxing "
                "sponsorship opportunity"
            )

            body = f"""
Hello,

I wanted to follow up regarding the sponsorship opportunity
we shared with {business_name}.

We believe there is a strong fit between your organization
and the audience surrounding our upcoming TNG Boxing event.

"""

            if ask:
                body += (
                    f"Our suggested partnership level is "
                    f"${float(ask):,.0f}, although we are happy "
                    f"to discuss the best fit for your goals.\n\n"
                )

            body += """If sponsorship or community partnerships are
handled by someone else on your team, I would appreciate being
connected with the appropriate person.

Thank you,

TNG Promotions
"""

            next_delay = 4

        else:
            subject = "TNG Boxing partnership follow-up"

            body = f"""
Hello,

I wanted to make one final follow-up regarding a potential
partnership between {business_name} and TNG Boxing.

If this opportunity is something your team would like to
discuss, we would be glad to provide additional information
or customize a sponsorship option around your objectives.

If now is not the right time, no problem at all.

Thank you,

TNG Promotions
"""

            next_delay = None

        resend.api_key = api_key

        try:
            result = resend.Emails.send({
                "from": email_from,
                "to": [organization.email],
                "subject": subject,
                "text": body,
            })

            provider_message_id = None

            if isinstance(result, dict):
                provider_message_id = (
                    result.get("id")
                    or result.get("message_id")
                )
            else:
                provider_message_id = getattr(
                    result,
                    "id",
                    None,
                )

            outreach = models.RevenueOutreachMessage(
                event_id=prospect.event_id,
                prospect_id=prospect.id,
                channel="EMAIL",
                template_key="SPONSOR_FOLLOWUP",
                subject=subject,
                body=body,
                status="SENT",
                provider_message_id=provider_message_id,
                sent_at=now,
            )

            db.add(outreach)

            prospect.last_contacted_at = now

            if next_delay:
                prospect.next_follow_up_at = (
                    now + timedelta(days=next_delay)
                )
            else:
                prospect.next_follow_up_at = None

            summary["sent"] += 1

        except Exception as exc:
            print(
                f"Follow-up failed for prospect "
                f"{prospect.id}: {exc}"
            )

            summary["skipped"] += 1

    db.commit()

    return summary
