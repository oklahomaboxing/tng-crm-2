from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from . import models, schemas
from .emailing import send_revenue_proposal_email
from .service import (
    build_fit_summary,
    distance_to_score,
    marketing_propensity_to_score,
)

router = APIRouter(
    prefix="/api/events/{event_id}/revenue",
    tags=["event-revenue"],
)

webhook_router = APIRouter(
    prefix="/api/revenue",
    tags=["revenue-webhooks"],
)


@router.post("/organizations")
def create_organization(
    event_id: int,
    payload: schemas.RevenueOrganizationCreate,
    db: Session = Depends(get_db),
):
    organization = models.RevenueOrganization(
        **payload.model_dump()
    )

    db.add(organization)
    db.commit()
    db.refresh(organization)

    return organization


@router.get("/organizations")
def list_organizations(
    event_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(models.RevenueOrganization)
        .order_by(models.RevenueOrganization.business_name.asc())
        .all()
    )


@router.post("/contacts")
def create_contact(
    event_id: int,
    payload: schemas.RevenueContactCreate,
    db: Session = Depends(get_db),
):
    organization = (
        db.query(models.RevenueOrganization)
        .filter(models.RevenueOrganization.id == payload.organization_id)
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    contact = models.RevenueOrganizationContact(
        **payload.model_dump()
    )

    db.add(contact)
    db.commit()
    db.refresh(contact)

    return contact


@router.post("/packages")
def create_package(
    event_id: int,
    payload: schemas.EventRevenuePackageCreate,
    db: Session = Depends(get_db),
):
    package = models.EventRevenuePackage(
        event_id=event_id,
        **payload.model_dump(),
    )

    db.add(package)
    db.commit()
    db.refresh(package)

    return package


@router.get("/packages")
def list_packages(
    event_id: int,
    package_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.EventRevenuePackage).filter(
        models.EventRevenuePackage.event_id == event_id,
        models.EventRevenuePackage.active.is_(True),
    )

    if package_type:
        query = query.filter(
            models.EventRevenuePackage.package_type == package_type.upper()
        )

    return query.order_by(
        models.EventRevenuePackage.price.asc()
    ).all()


@router.post("/prospects")
def create_prospect(
    event_id: int,
    payload: schemas.EventRevenueProspectCreate,
    db: Session = Depends(get_db),
):
    organization = (
        db.query(models.RevenueOrganization)
        .filter(models.RevenueOrganization.id == payload.organization_id)
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    existing = (
        db.query(models.EventRevenueProspect)
        .filter(
            models.EventRevenueProspect.event_id == event_id,
            models.EventRevenueProspect.organization_id == payload.organization_id,
            models.EventRevenueProspect.prospect_type == payload.prospect_type,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="This organization is already in this event pipeline",
        )

    marketing_score = payload.marketing_activity_score

    if marketing_score == 0:
        marketing_score = marketing_propensity_to_score(
            organization.marketing_propensity
        )

    distance_score = payload.distance_score

    if distance_score == 0 and payload.distance_miles is not None:
        distance_score = distance_to_score(
            payload.distance_miles
        )

    fit = build_fit_summary(
        marketing_activity_score=marketing_score,
        sponsorship_history_score=payload.sponsorship_history_score,
        audience_fit_score=payload.audience_fit_score,
        business_capacity_score=payload.business_capacity_score,
        distance_score=distance_score,
        relationship_score=payload.relationship_score,
    )

    prospect = models.EventRevenueProspect(
        event_id=event_id,
        organization_id=payload.organization_id,
        prospect_type=payload.prospect_type,

        fit_score=fit["fit_score"],

        marketing_activity_score=marketing_score,
        sponsorship_history_score=payload.sponsorship_history_score,
        audience_fit_score=payload.audience_fit_score,
        business_capacity_score=payload.business_capacity_score,
        distance_score=distance_score,
        relationship_score=payload.relationship_score,

        recommended_package_id=payload.recommended_package_id,
        recommended_ask=payload.recommended_ask,

        lead_source=payload.lead_source,
        distance_miles=payload.distance_miles,

        assigned_to_user_id=payload.assigned_to_user_id,
    )

    db.add(prospect)
    db.commit()
    db.refresh(prospect)

    return {
        "prospect": prospect,
        "fit_category": fit["fit_category"],
        "score_breakdown": fit["breakdown"],
    }


@router.get("/prospects")
def list_prospects(
    event_id: int,
    prospect_type: Optional[str] = None,
    status: Optional[str] = None,
    minimum_fit_score: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(models.EventRevenueProspect).filter(
        models.EventRevenueProspect.event_id == event_id,
        models.EventRevenueProspect.fit_score >= minimum_fit_score,
    )

    if prospect_type:
        query = query.filter(
            models.EventRevenueProspect.prospect_type
            == prospect_type.upper()
        )

    if status:
        query = query.filter(
            models.EventRevenueProspect.status
            == status.upper()
        )

    rows = query.order_by(
        models.EventRevenueProspect.fit_score.desc(),
        models.EventRevenueProspect.created_at.desc(),
    ).all()

    results = []

    for row in rows:
        results.append({
            "id": row.id,
            "event_id": row.event_id,
            "prospect_type": row.prospect_type,
            "status": row.status,
            "fit_score": row.fit_score,
            "organization_id": row.organization_id,
            "business_name": (
                row.organization.business_name
                if row.organization
                else None
            ),
            "industry": (
                row.organization.industry
                if row.organization
                else None
            ),
            "email": (
                row.organization.email
                if row.organization
                else None
            ),
            "phone": (
                row.organization.phone
                if row.organization
                else None
            ),
            "marketing_propensity": (
                row.organization.marketing_propensity
                if row.organization
                else None
            ),
            "verified_sponsorship_history": (
                row.organization.verified_sponsorship_history
                if row.organization
                else None
            ),
            "distance_miles": row.distance_miles,
            "recommended_ask": row.recommended_ask,
            "recommended_package_id": row.recommended_package_id,
            "last_contacted_at": row.last_contacted_at,
            "next_follow_up_at": row.next_follow_up_at,
        })

    return results


@router.patch("/prospects/{prospect_id}/status")
def update_prospect_status(
    event_id: int,
    prospect_id: int,
    payload: schemas.EventRevenueProspectStatusUpdate,
    db: Session = Depends(get_db),
):
    prospect = (
        db.query(models.EventRevenueProspect)
        .filter(
            models.EventRevenueProspect.id == prospect_id,
            models.EventRevenueProspect.event_id == event_id,
        )
        .first()
    )

    if not prospect:
        raise HTTPException(
            status_code=404,
            detail="Prospect not found",
        )

    prospect.status = payload.status.upper()
    prospect.updated_at = datetime.utcnow()

    if prospect.status in {
        "CONTACTED",
        "PROPOSAL_SENT",
        "INVITED",
    }:
        prospect.last_contacted_at = datetime.utcnow()

    db.commit()
    db.refresh(prospect)

    return prospect


@router.post("/proposals")
def create_proposal(
    event_id: int,
    payload: schemas.EventRevenueProposalCreate,
    db: Session = Depends(get_db),
):
    prospect = (
        db.query(models.EventRevenueProspect)
        .filter(
            models.EventRevenueProspect.id == payload.prospect_id,
            models.EventRevenueProspect.event_id == event_id,
        )
        .first()
    )

    if not prospect:
        raise HTTPException(
            status_code=404,
            detail="Prospect not found",
        )

    package = None

    if payload.package_id:
        package = (
            db.query(models.EventRevenuePackage)
            .filter(
                models.EventRevenuePackage.id == payload.package_id,
                models.EventRevenuePackage.event_id == event_id,
            )
            .first()
        )

        if not package:
            raise HTTPException(
                status_code=404,
                detail="Revenue package not found",
            )

    proposal = models.EventRevenueProposal(
        event_id=event_id,
        prospect_id=payload.prospect_id,
        package_id=payload.package_id,

        title=payload.title,
        message=payload.message,

        clover_payment_url=(
            package.clover_payment_url
            if package
            else None
        ),
    )

    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    return proposal


@router.post("/proposals/{proposal_id}/mark-sent")
def mark_proposal_sent(
    event_id: int,
    proposal_id: int,
    db: Session = Depends(get_db),
):
    proposal = (
        db.query(models.EventRevenueProposal)
        .filter(
            models.EventRevenueProposal.id == proposal_id,
            models.EventRevenueProposal.event_id == event_id,
        )
        .first()
    )

    if not proposal:
        raise HTTPException(
            status_code=404,
            detail="Proposal not found",
        )

    proposal.status = "SENT"
    proposal.sent_at = datetime.utcnow()
    proposal.updated_at = datetime.utcnow()

    prospect = (
        db.query(models.EventRevenueProspect)
        .filter(
            models.EventRevenueProspect.id == proposal.prospect_id
        )
        .first()
    )

    if prospect:
        prospect.status = "PROPOSAL_SENT"
        prospect.last_contacted_at = datetime.utcnow()
        prospect.updated_at = datetime.utcnow()

    db.commit()

    return {
        "ok": True,
        "proposal_id": proposal.id,
        "status": proposal.status,
    }


@router.post("/outreach")
def create_outreach_message(
    event_id: int,
    payload: schemas.RevenueOutreachCreate,
    db: Session = Depends(get_db),
):
    prospect = (
        db.query(models.EventRevenueProspect)
        .filter(
            models.EventRevenueProspect.id == payload.prospect_id,
            models.EventRevenueProspect.event_id == event_id,
        )
        .first()
    )

    if not prospect:
        raise HTTPException(
            status_code=404,
            detail="Prospect not found",
        )

    message = models.RevenueOutreachMessage(
        event_id=event_id,
        prospect_id=payload.prospect_id,
        channel=payload.channel,
        template_key=payload.template_key,
        subject=payload.subject,
        body=payload.body,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


@router.get("/dashboard")
def revenue_dashboard(
    event_id: int,
    db: Session = Depends(get_db),
):
    prospects = (
        db.query(models.EventRevenueProspect)
        .filter(
            models.EventRevenueProspect.event_id == event_id
        )
        .all()
    )

    payments = (
        db.query(models.EventRevenuePayment)
        .filter(
            models.EventRevenuePayment.event_id == event_id
        )
        .all()
    )

    pipeline_value = sum(
        float(p.recommended_ask or 0)
        for p in prospects
        if p.status not in {
            "DECLINED",
            "NO_RESPONSE",
        }
    )

    collected = sum(
        float(payment.amount or 0)
        for payment in payments
        if payment.status == "PAID"
    )

    committed = sum(
        float(p.recommended_ask or 0)
        for p in prospects
        if p.status in {
            "COMMITTED",
            "PAID",
        }
    )

    return {
        "event_id": event_id,
        "prospects": len(prospects),
        "high_intent_prospects": len([
            p for p in prospects
            if (p.fit_score or 0) >= 80
        ]),
        "pipeline_value": round(pipeline_value, 2),
        "committed": round(committed, 2),
        "collected": round(collected, 2),
    }



@router.post("/proposals/{proposal_id}/send-email")
def send_proposal_email(
    event_id: int,
    proposal_id: int,
    db: Session = Depends(get_db),
):
    proposal = (
        db.query(models.EventRevenueProposal)
        .filter(
            models.EventRevenueProposal.id == proposal_id,
            models.EventRevenueProposal.event_id == event_id,
        )
        .first()
    )

    if not proposal:
        raise HTTPException(
            status_code=404,
            detail="Proposal not found",
        )

    prospect = (
        db.query(models.EventRevenueProspect)
        .filter(
            models.EventRevenueProspect.id == proposal.prospect_id,
            models.EventRevenueProspect.event_id == event_id,
        )
        .first()
    )

    if not prospect:
        raise HTTPException(
            status_code=404,
            detail="Prospect not found",
        )

    if prospect.do_not_contact:
        raise HTTPException(
            status_code=400,
            detail="This prospect is marked do not contact",
        )

    organization = prospect.organization

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    if not organization.email:
        raise HTTPException(
            status_code=400,
            detail="Organization does not have an email address",
        )

    package = None

    if proposal.package_id:
        package = (
            db.query(models.EventRevenuePackage)
            .filter(
                models.EventRevenuePackage.id == proposal.package_id
            )
            .first()
        )

    try:
        email_result = send_revenue_proposal_email(
            to_email=organization.email,
            business_name=organization.business_name,
            proposal_title=proposal.title,
            proposal_message=proposal.message,
            package_name=package.name if package else "",
            package_price=float(package.price or 0) if package else 0,
            clover_payment_url=proposal.clover_payment_url,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Email send failed: {str(exc)}",
        )

    provider_message_id = None

    if isinstance(email_result, dict):
        provider_message_id = (
            email_result.get("id")
            or email_result.get("message_id")
        )

    outreach = models.RevenueOutreachMessage(
        event_id=event_id,
        prospect_id=prospect.id,
        channel="EMAIL",
        template_key="SPONSOR_PROPOSAL",
        subject=proposal.title,
        body=proposal.message,
        status="SENT",
        provider_message_id=provider_message_id,
        sent_at=datetime.utcnow(),
    )

    db.add(outreach)

    proposal.status = "SENT"
    proposal.sent_at = datetime.utcnow()
    proposal.updated_at = datetime.utcnow()

    prospect.status = "PROPOSAL_SENT"
    prospect.last_contacted_at = datetime.utcnow()
    prospect.updated_at = datetime.utcnow()

    db.commit()

    return {
        "ok": True,
        "proposal_id": proposal.id,
        "prospect_id": prospect.id,
        "business_name": organization.business_name,
        "email": organization.email,
        "status": "SENT",
        "provider_message_id": provider_message_id,
    }


@router.patch("/organizations/{organization_id}")
def update_organization(
    event_id: int,
    organization_id: int,
    payload: schemas.RevenueOrganizationUpdate,
    db: Session = Depends(get_db),
):
    organization = (
        db.query(models.RevenueOrganization)
        .filter(
            models.RevenueOrganization.id == organization_id
        )
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(organization, field, value)

    organization.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(organization)

    return organization


# ============================================================
# SPONSOR SCOUT
# ============================================================

from typing import Optional
from pydantic import BaseModel, Field
from fastapi import HTTPException

from .scout import run_sponsor_scout


class SponsorScoutRequest(BaseModel):
    event_name: str
    event_address: str
    radius_miles: float = Field(default=15, ge=1, le=50)
    category: Optional[str] = None
    max_results: int = Field(default=20, ge=1, le=30)


@router.post("/scout/sponsors")
def scout_sponsors(
    event_id: int,
    payload: SponsorScoutRequest,
):
    try:
        results = run_sponsor_scout(
            event_name=payload.event_name,
            event_address=payload.event_address,
            radius_miles=payload.radius_miles,
            category=payload.category,
            max_results=payload.max_results,
        )

        return {
            "event_id": event_id,
            "count": len(results),
            "radius_miles": payload.radius_miles,
            "category": payload.category,
            "results": results,
        }

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        )


@router.post("/scout/sponsors/add-to-pipeline")
def add_scout_sponsor_to_pipeline(
    event_id: int,
    payload: schemas.SponsorScoutPipelineCreate,
    db: Session = Depends(get_db),
):
    import json

    organization = (
        db.query(models.RevenueOrganization)
        .filter(
            models.RevenueOrganization.business_name
            == payload.business_name
        )
        .first()
    )

    if not organization and payload.website:
        organization = (
            db.query(models.RevenueOrganization)
            .filter(
                models.RevenueOrganization.website
                == payload.website
            )
            .first()
        )

    evidence_payload = {
        "marketing_evidence": payload.marketing_evidence,
        "sponsorship_evidence": payload.sponsorship_evidence,
        "source_urls": payload.source_urls,
    }

    if organization is None:
        organization = models.RevenueOrganization(
            business_name=payload.business_name,
            website=payload.website,
            city=payload.city,
            state=payload.state,
            industry=payload.industry,
            notes=payload.why_good_fit,
            marketing_propensity=payload.marketing_propensity,
            verified_sponsorship_history=(
                payload.verified_sponsorship_history
            ),
            marketing_evidence_json=json.dumps(
                evidence_payload
            ),
        )

        db.add(organization)
        db.flush()

    else:
        if payload.website and not organization.website:
            organization.website = payload.website

        if payload.city and not organization.city:
            organization.city = payload.city

        if payload.state and not organization.state:
            organization.state = payload.state

        if payload.industry and not organization.industry:
            organization.industry = payload.industry

        organization.marketing_propensity = (
            payload.marketing_propensity
        )

        organization.verified_sponsorship_history = (
            payload.verified_sponsorship_history
        )

        organization.marketing_evidence_json = json.dumps(
            evidence_payload
        )

        if payload.why_good_fit:
            organization.notes = payload.why_good_fit

    existing = (
        db.query(models.EventRevenueProspect)
        .filter(
            models.EventRevenueProspect.event_id == event_id,
            models.EventRevenueProspect.organization_id
            == organization.id,
            models.EventRevenueProspect.prospect_type
            == "SPONSOR",
        )
        .first()
    )

    if existing:
        db.commit()

        return {
            "added": False,
            "already_exists": True,
            "organization_id": organization.id,
            "prospect_id": existing.id,
            "fit_score": existing.fit_score,
            "message": (
                "Sponsor is already in this event pipeline"
            ),
        }

    fit = build_fit_summary(
        marketing_activity_score=(
            payload.marketing_activity_score
        ),
        sponsorship_history_score=(
            payload.sponsorship_history_score
        ),
        audience_fit_score=payload.audience_fit_score,
        business_capacity_score=(
            payload.business_capacity_score
        ),
        distance_score=payload.distance_score,
        relationship_score=payload.relationship_score,
    )

    prospect = models.EventRevenueProspect(
        event_id=event_id,
        organization_id=organization.id,
        prospect_type="SPONSOR",

        status="NEW",
        fit_score=fit["fit_score"],

        marketing_activity_score=(
            payload.marketing_activity_score
        ),
        sponsorship_history_score=(
            payload.sponsorship_history_score
        ),
        audience_fit_score=payload.audience_fit_score,
        business_capacity_score=(
            payload.business_capacity_score
        ),
        distance_score=payload.distance_score,
        relationship_score=payload.relationship_score,

        lead_source=payload.lead_source,
        distance_miles=payload.distance_miles,
    )

    db.add(prospect)
    db.commit()
    db.refresh(organization)
    db.refresh(prospect)

    return {
        "added": True,
        "already_exists": False,
        "organization_id": organization.id,
        "prospect_id": prospect.id,
        "fit_score": prospect.fit_score,
        "message": "Sponsor added to pipeline",
    }


@router.post("/proposals/generate-ai")
def generate_ai_revenue_proposal(
    event_id: int,
    payload: schemas.AIRevenueProposalRequest,
    db: Session = Depends(get_db),
):
    import json
    import os

    from openai import OpenAI

    prospect = (
        db.query(models.EventRevenueProspect)
        .filter(
            models.EventRevenueProspect.id == payload.prospect_id,
            models.EventRevenueProspect.event_id == event_id,
        )
        .first()
    )

    if not prospect:
        raise HTTPException(
            status_code=404,
            detail="Prospect not found",
        )

    organization = (
        db.query(models.RevenueOrganization)
        .filter(
            models.RevenueOrganization.id
            == prospect.organization_id
        )
        .first()
    )

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    package = None

    if payload.package_id:
        package = (
            db.query(models.EventRevenuePackage)
            .filter(
                models.EventRevenuePackage.id
                == payload.package_id,
                models.EventRevenuePackage.event_id
                == event_id,
            )
            .first()
        )

        if not package:
            raise HTTPException(
                status_code=404,
                detail="Revenue package not found",
            )

    evidence = {}

    if organization.marketing_evidence_json:
        try:
            evidence = json.loads(
                organization.marketing_evidence_json
            )
        except Exception:
            evidence = {}

    package_text = "No specific package selected."

    if package:
        package_text = f"""
Package: {package.name}
Price: ${package.price:,.2f}
Description: {package.description or ""}
Payment Link: {package.clover_payment_url or "Not yet assigned"}
"""

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        timeout=45.0,
        max_retries=0,
    )

    prompt = f"""
You are the sponsorship proposal assistant for TNG Promotions.

Write a professional, persuasive sponsorship proposal for a real business.

EVENT
Name: {payload.event_name}
Date: {payload.event_date or "Not provided"}
Venue: {payload.event_venue or "Not provided"}
Address: {payload.event_address or "Not provided"}

SPONSOR
Business: {organization.business_name}
Industry: {organization.industry or "Not provided"}
City: {organization.city or ""}
State: {organization.state or ""}
Website: {organization.website or ""}

TNGOS SPONSOR FIT
Fit score: {prospect.fit_score}/100
Marketing activity score: {prospect.marketing_activity_score}/100
Sponsorship history score: {prospect.sponsorship_history_score}/100
Audience fit score: {prospect.audience_fit_score}/100
Business capacity score: {prospect.business_capacity_score}/100

WHY THEY FIT
{organization.notes or "No notes provided"}

RESEARCH EVIDENCE
{json.dumps(evidence, indent=2)}

PACKAGE
{package_text}

ADDITIONAL INSTRUCTIONS
{payload.additional_instructions or "None"}

Write specifically for this business.

Do not invent claims, audience numbers, sponsorship history,
deliverables, attendance, or benefits that are not provided.

Return ONLY valid JSON:

{{
  "title": "proposal title",
  "message": "complete proposal body"
}}
"""

    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt,
        )

        raw = response.output_text.strip()

        if raw.startswith("```"):
            raw = raw.replace("```json", "", 1)
            raw = raw.replace("```", "").strip()

        generated = json.loads(raw)

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"AI proposal generation failed: {exc}",
        )

    title = generated.get("title")
    message = generated.get("message")

    if not title or not message:
        raise HTTPException(
            status_code=503,
            detail="AI proposal response was incomplete",
        )

    proposal = models.EventRevenueProposal(
        event_id=event_id,
        prospect_id=prospect.id,
        package_id=payload.package_id,
        title=title,
        message=message,
        clover_payment_url=(
            package.clover_payment_url
            if package
            else None
        ),
    )

    db.add(proposal)

    prospect.status = "PROPOSAL_SENT" if False else "INTERESTED"

    db.commit()
    db.refresh(proposal)

    return {
        "proposal_id": proposal.id,
        "prospect_id": prospect.id,
        "title": proposal.title,
        "message": proposal.message,
        "package_id": proposal.package_id,
        "clover_payment_url": proposal.clover_payment_url,
        "status": proposal.status,
    }


@router.post("/prospects/{prospect_id}/send-latest-proposal")
def send_latest_proposal_email(
    event_id: int,
    prospect_id: int,
    db: Session = Depends(get_db),
):
    prospect = (
        db.query(models.EventRevenueProspect)
        .filter(
            models.EventRevenueProspect.id == prospect_id,
            models.EventRevenueProspect.event_id == event_id,
        )
        .first()
    )

    if not prospect:
        raise HTTPException(
            status_code=404,
            detail="Prospect not found",
        )

    proposal = (
        db.query(models.EventRevenueProposal)
        .filter(
            models.EventRevenueProposal.event_id == event_id,
            models.EventRevenueProposal.prospect_id == prospect_id,
        )
        .order_by(models.EventRevenueProposal.created_at.desc())
        .first()
    )

    if not proposal:
        raise HTTPException(
            status_code=400,
            detail="Generate a proposal before sending email",
        )

    return send_proposal_email(
        event_id=event_id,
        proposal_id=proposal.id,
        db=db,
    )


# ============================================================
# RESEND EMAIL STATUS WEBHOOK
# ============================================================

from fastapi import Request
import json
import os
import resend


@webhook_router.post("/webhooks/resend")
async def resend_revenue_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    webhook_secret = os.getenv("RESEND_WEBHOOK_SECRET")

    if not webhook_secret:
        raise HTTPException(
            status_code=500,
            detail="RESEND_WEBHOOK_SECRET is not configured",
        )

    raw_body = await request.body()
    payload = raw_body.decode("utf-8")

    try:
        event = resend.Webhooks.verify(
            {
                "payload": payload,
                "headers": {
                    "svix-id": request.headers.get("svix-id"),
                    "svix-timestamp": request.headers.get("svix-timestamp"),
                    "svix-signature": request.headers.get("svix-signature"),
                },
                "secret": webhook_secret,
            }
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Resend webhook signature: {exc}",
        )

    if not isinstance(event, dict):
        event = dict(event)

    event_type = event.get("type")
    data = event.get("data") or {}

    email_id = data.get("email_id")

    if not email_id:
        return {
            "ok": True,
            "ignored": True,
            "reason": "No email_id",
        }

    outreach = (
        db.query(models.RevenueOutreachMessage)
        .filter(
            models.RevenueOutreachMessage.provider_message_id
            == email_id
        )
        .order_by(
            models.RevenueOutreachMessage.created_at.desc()
        )
        .first()
    )

    if not outreach:
        return {
            "ok": True,
            "ignored": True,
            "reason": "No matching outreach message",
        }

    now = datetime.utcnow()

    if event_type == "email.sent":
        outreach.status = "SENT"

        if not outreach.sent_at:
            outreach.sent_at = now

    elif event_type == "email.delivered":
        outreach.status = "DELIVERED"

    elif event_type == "email.opened":
        outreach.status = "OPENED"

        if not outreach.opened_at:
            outreach.opened_at = now

    elif event_type == "email.clicked":
        outreach.status = "CLICKED"

        if not outreach.clicked_at:
            outreach.clicked_at = now

    elif event_type == "email.bounced":
        outreach.status = "BOUNCED"

        if not outreach.bounced_at:
            outreach.bounced_at = now

    elif event_type == "email.failed":
        outreach.status = "FAILED"

    elif event_type == "email.complained":
        outreach.status = "COMPLAINED"

        prospect = (
            db.query(models.EventRevenueProspect)
            .filter(
                models.EventRevenueProspect.id
                == outreach.prospect_id
            )
            .first()
        )

        if prospect:
            prospect.do_not_contact = True

    else:
        return {
            "ok": True,
            "ignored": True,
            "event_type": event_type,
        }

    db.commit()

    return {
        "ok": True,
        "event_type": event_type,
        "outreach_id": outreach.id,
        "status": outreach.status,
    }
