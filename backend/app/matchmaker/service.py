import re
from datetime import datetime
from sqlalchemy import or_
from .models import BoxingFighter, BoxingBout

def parse_record(value):
    nums = [int(x) for x in re.findall(r"\d+", (value or "").strip())]
    if len(nums) < 2:
        return {"total": 0, "win_pct": None}
    wins, losses = nums[0], nums[1]
    draws = nums[2] if len(nums) > 2 else 0
    total = wins + losses + draws
    return {"total": total, "win_pct": wins / total if total else None}

def age_from_dob(dob):
    if not dob:
        return None
    try:
        born = datetime.strptime(str(dob)[:10], "%Y-%m-%d").date()
        today = datetime.utcnow().date()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except Exception:
        return None

def is_eligible(f):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return (
        (f.suspension_status or "") == "verified_clear"
        and (f.ok_license_status or "") in ("active", "pending")
        and (f.bloodwork_status or "") == "verified"
        and (not f.bloodwork_expires or f.bloodwork_expires >= today)
        and f.available is not False
    )

def fighter_dict(f):
    return {
        "id": f.id,
        "legal_name": f.legal_name,
        "dob": f.dob,
        "phone": f.phone,
        "email": f.email,
        "city": f.city,
        "state": f.state,
        "country": f.country,
        "stance": f.stance,
        "gym": f.gym,
        "coach": f.coach,
        "height_in": f.height_in,
        "reach_in": f.reach_in,
        "walk_weight": f.walk_weight,
        "fight_weight": f.fight_weight,
        "pro_record": f.pro_record,
        "amateur_record": f.amateur_record,
        "boxrec_id": f.boxrec_id,
        "boxrec_url": f.boxrec_url,
        "boxrec_id": getattr(f, "boxrec_id", "") or "",
        "instagram": getattr(f, "instagram", "") or "",
        "facebook": getattr(f, "facebook", "") or "",
        "tiktok": getattr(f, "tiktok", "") or "",
        "twitter": getattr(f, "twitter", "") or "",
        "submitted_by_name": getattr(f, "submitted_by_name", "") or "",
        "submitted_by_role": getattr(f, "submitted_by_role", "") or "",
        "submitted_by_phone": getattr(f, "submitted_by_phone", "") or "",
        "submitted_by_email": getattr(f, "submitted_by_email", "") or "",
        "manager_name": f.manager_name,
        "manager_phone": f.manager_phone,
        "manager_email": f.manager_email,
        "ok_license_status": f.ok_license_status,
        "federal_id_status": f.federal_id_status,
        "suspension_status": f.suspension_status,
        "bloodwork_status": f.bloodwork_status,
        "bloodwork_expires": f.bloodwork_expires,
        "available": bool(f.available),
        "available_weight_min": f.available_weight_min,
        "available_weight_max": f.available_weight_max,
        "last_fight_date": f.last_fight_date,
        "eligible": is_eligible(f),
        "source": f.source,
        "source_id": f.source_id,
    }

def already_booked(db, fighter_id, event_id):
    if not event_id:
        return False
    return db.query(BoxingBout).filter(
        BoxingBout.event_id == event_id,
        BoxingBout.status.notin_(["void", "cancelled"]),
        or_(
            BoxingBout.red_fighter_id == fighter_id,
            BoxingBout.blue_fighter_id == fighter_id,
        ),
    ).first() is not None

def prior_bouts(db, a_id, b_id):
    return db.query(BoxingBout).filter(
        or_(
            (BoxingBout.red_fighter_id == a_id) & (BoxingBout.blue_fighter_id == b_id),
            (BoxingBout.red_fighter_id == b_id) & (BoxingBout.blue_fighter_id == a_id),
        )
    ).count()

def fighter_weight_range(fighter):
    low = fighter.available_weight_min
    high = fighter.available_weight_max
    fight = fighter.fight_weight

    if low is None and fight is not None:
        low = float(fight)

    if high is None and fight is not None:
        high = float(fight)

    if low is None or high is None:
        return None

    low = float(low)
    high = float(high)

    if low > high:
        low, high = high, low

    return low, high


def weight_compatibility(base, candidate):
    a = fighter_weight_range(base)
    b = fighter_weight_range(candidate)

    if not a or not b:
        return {
            "has_ranges": False,
            "overlap": False,
            "overlap_low": None,
            "overlap_high": None,
            "suggested_weight": None,
            "gap": None,
        }

    a_low, a_high = a
    b_low, b_high = b

    overlap_low = max(a_low, b_low)
    overlap_high = min(a_high, b_high)

    if overlap_low <= overlap_high:
        suggested = round((overlap_low + overlap_high) / 2, 1)

        return {
            "has_ranges": True,
            "overlap": True,
            "overlap_low": round(overlap_low, 1),
            "overlap_high": round(overlap_high, 1),
            "suggested_weight": suggested,
            "gap": 0,
        }

    if a_high < b_low:
        gap = b_low - a_high
    else:
        gap = a_low - b_high

    return {
        "has_ranges": True,
        "overlap": False,
        "overlap_low": None,
        "overlap_high": None,
        "suggested_weight": None,
        "gap": round(abs(gap), 1),
    }


def score_candidate(db, base, candidate, event_id=None):
    if candidate.id == base.id or not is_eligible(candidate):
        return None

    if event_id and already_booked(db, candidate.id, event_id):
        return None

    if base.gym and candidate.gym and base.gym.strip().lower() == candidate.gym.strip().lower():
        return None

    compatibility = weight_compatibility(base, candidate)

    score = 100.0
    reasons = []
    warnings = []

    bw = float(base.fight_weight or 0)
    cw = float(candidate.fight_weight or 0)

    if compatibility["has_ranges"]:
        if compatibility["overlap"]:
            overlap_size = (
                compatibility["overlap_high"]
                - compatibility["overlap_low"]
            )

            reasons.append(
                f'Weight overlap: {compatibility["overlap_low"]}-'
                f'{compatibility["overlap_high"]} lb'
            )

            reasons.append(
                f'Suggested weight: '
                f'{compatibility["suggested_weight"]} lb'
            )

            if overlap_size >= 3:
                score += 3
            elif overlap_size < 1:
                score -= 2
        else:
            gap = compatibility["gap"] or 0

            reasons.append(f"Weight range gap: {gap:.1f} lb")

            if gap <= 1:
                score -= 8
            elif gap <= 2:
                score -= 15
            elif gap <= 3:
                score -= 25
                warnings.append("Weight ranges do not overlap")
            elif gap <= 5:
                score -= 40
                warnings.append("Large weight range gap")
            else:
                return None

    elif bw > 0 and cw > 0:
        wd = abs(bw - cw)

        if wd <= 1:
            penalty = 0
        elif wd <= 2:
            penalty = 3
        elif wd <= 3:
            penalty = 7
        elif wd <= 5:
            penalty = 14
        elif wd <= 8:
            penalty = 24
        else:
            return None

        score -= penalty
        reasons.append(f"Fight weight difference: {wd:.1f} lb")
    else:
        return None

    br = parse_record(base.pro_record)
    cr = parse_record(candidate.pro_record)
    if br["total"] and cr["total"]:
        fd = abs(br["total"] - cr["total"])
        if fd <= 2:
            penalty = 0
        elif fd <= 5:
            penalty = 5
        elif fd <= 10:
            penalty = 10
        else:
            penalty = 18
        score -= penalty
        reasons.append(f"Experience: {br['total']} vs {cr['total']} pro fights")

        if br["win_pct"] is not None and cr["win_pct"] is not None:
            score -= min(15.0, abs(br["win_pct"] - cr["win_pct"]) * 20.0)

        reasons.append(f"Records: {base.pro_record or '-'} vs {candidate.pro_record or '-'}")
    else:
        warnings.append("Incomplete pro record data")

    ba = age_from_dob(base.dob)
    ca = age_from_dob(candidate.dob)
    if ba is not None and ca is not None:
        ad = abs(ba - ca)
        score -= 0 if ad <= 3 else 3 if ad <= 5 else 6 if ad <= 8 else 10
        reasons.append(f"Age difference: {ad} years")

    if base.height_in and candidate.height_in:
        hd = abs(base.height_in - candidate.height_in)
        score -= min(2.5, hd * 0.5)
        reasons.append(f"Height difference: {hd} in")

    if base.reach_in and candidate.reach_in:
        rd = abs(base.reach_in - candidate.reach_in)
        score -= min(2.5, rd * 0.5)
        reasons.append(f"Reach difference: {rd} in")

    previous = prior_bouts(db, base.id, candidate.id)
    if previous:
        score -= min(12, previous * 6)
        warnings.append(f"Prior bouts together: {previous}")

    if base.state and candidate.state:
        if base.state.strip().lower() == candidate.state.strip().lower():
            reasons.append("Same-state travel")
        else:
            score -= 3
            warnings.append("Out-of-state travel")

    score = max(0, min(100, round(score)))
    tier = "Excellent" if score >= 90 else "Strong" if score >= 80 else "Possible" if score >= 70 else "Review"

    return {
        "fighter": fighter_dict(candidate),
        "score": score,
        "tier": tier,
        "weight_diff": round(abs(bw - cw), 1) if bw and cw else None,
        "weight_overlap": compatibility.get("overlap"),
        "overlap_low": compatibility.get("overlap_low"),
        "overlap_high": compatibility.get("overlap_high"),
        "suggested_weight": compatibility.get("suggested_weight"),
        "weight_gap": compatibility.get("gap"),
        "age": ca,
        "reasons": reasons,
        "warnings": warnings,
    }

def ranked_matches(db, fighter_id, event_id=None, limit=40):
    base = db.query(BoxingFighter).filter(BoxingFighter.id == fighter_id).first()
    if not base:
        return None, []

    results = []
    for candidate in db.query(BoxingFighter).all():
        item = score_candidate(db, base, candidate, event_id)
        if item:
            results.append(item)

    results.sort(
        key=lambda x: (
            -x["score"],
            0 if x.get("weight_overlap") else 1,
            x.get("weight_gap") or 0,
            x.get("weight_diff") or 999,
            x["fighter"]["legal_name"],
        )
    )
    return fighter_dict(base), results[:limit]
