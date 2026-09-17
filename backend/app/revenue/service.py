def clamp_score(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 0

    return max(0, min(100, value))


def calculate_sponsor_fit_score(
    marketing_activity_score,
    sponsorship_history_score,
    audience_fit_score,
    business_capacity_score,
    distance_score,
    relationship_score,
):
    """
    Sponsor Fit weighting:

    Marketing activity ............ 25%
    Sponsorship/community history . 20%
    Audience fit .................. 20%
    Business capacity ............. 15%
    Distance ...................... 10%
    Existing TNG relationship ..... 10%
    """

    marketing_activity_score = clamp_score(marketing_activity_score)
    sponsorship_history_score = clamp_score(sponsorship_history_score)
    audience_fit_score = clamp_score(audience_fit_score)
    business_capacity_score = clamp_score(business_capacity_score)
    distance_score = clamp_score(distance_score)
    relationship_score = clamp_score(relationship_score)

    score = (
        marketing_activity_score * 0.25
        + sponsorship_history_score * 0.20
        + audience_fit_score * 0.20
        + business_capacity_score * 0.15
        + distance_score * 0.10
        + relationship_score * 0.10
    )

    return round(score)


def classify_fit_score(score):
    score = clamp_score(score)

    if score >= 85:
        return "HOT"
    elif score >= 70:
        return "STRONG"
    elif score >= 50:
        return "DEVELOPING"
    else:
        return "LOW_PRIORITY"


def marketing_propensity_to_score(propensity):
    value = (propensity or "UNKNOWN").upper()

    mapping = {
        "HIGH": 90,
        "MEDIUM": 65,
        "LOW": 30,
        "UNKNOWN": 45,
    }

    return mapping.get(value, 45)


def distance_to_score(distance_miles):
    """
    Initial event-distance scoring.

    0-1 mile   = 100
    1-3 miles  = 90
    3-5 miles  = 80
    5-10 miles = 65
    10-15      = 50
    15-25      = 35
    25+        = 20
    """

    if distance_miles is None:
        return 40

    try:
        distance = float(distance_miles)
    except (TypeError, ValueError):
        return 40

    if distance <= 1:
        return 100
    elif distance <= 3:
        return 90
    elif distance <= 5:
        return 80
    elif distance <= 10:
        return 65
    elif distance <= 15:
        return 50
    elif distance <= 25:
        return 35

    return 20


def build_fit_summary(
    marketing_activity_score,
    sponsorship_history_score,
    audience_fit_score,
    business_capacity_score,
    distance_score,
    relationship_score,
):
    fit_score = calculate_sponsor_fit_score(
        marketing_activity_score=marketing_activity_score,
        sponsorship_history_score=sponsorship_history_score,
        audience_fit_score=audience_fit_score,
        business_capacity_score=business_capacity_score,
        distance_score=distance_score,
        relationship_score=relationship_score,
    )

    return {
        "fit_score": fit_score,
        "fit_category": classify_fit_score(fit_score),
        "breakdown": {
            "marketing_activity": clamp_score(marketing_activity_score),
            "sponsorship_history": clamp_score(sponsorship_history_score),
            "audience_fit": clamp_score(audience_fit_score),
            "business_capacity": clamp_score(business_capacity_score),
            "distance": clamp_score(distance_score),
            "relationship": clamp_score(relationship_score),
        },
    }
