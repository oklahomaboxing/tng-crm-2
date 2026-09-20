from typing import Optional, Literal, List
from pydantic import BaseModel, Field


class RevenueOrganizationCreate(BaseModel):
    business_name: str
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    industry: Optional[str] = None
    employee_size: Optional[str] = None

    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    linkedin_url: Optional[str] = None

    notes: Optional[str] = None

    marketing_propensity: Literal[
        "HIGH",
        "MEDIUM",
        "LOW",
        "UNKNOWN",
    ] = "UNKNOWN"

    verified_sponsorship_history: Optional[bool] = None


class RevenueContactCreate(BaseModel):
    organization_id: int

    first_name: str = ""
    last_name: str = ""
    job_title: Optional[str] = None

    email: Optional[str] = None
    phone: Optional[str] = None

    primary_contact: bool = False

    source: str = "manual"
    verified: bool = False


class EventRevenuePackageCreate(BaseModel):
    package_type: Literal[
        "SPONSOR",
        "VENDOR",
        "PARTNER",
    ]

    name: str
    description: Optional[str] = None

    price: float = Field(default=0, ge=0)

    quantity_available: Optional[int] = Field(
        default=None,
        ge=0,
    )

    clover_payment_url: Optional[str] = None

    active: bool = True


class EventRevenueProspectCreate(BaseModel):
    organization_id: int

    prospect_type: Literal[
        "SPONSOR",
        "VENDOR",
        "PARTNER",
    ] = "SPONSOR"

    marketing_activity_score: int = Field(default=0, ge=0, le=100)
    sponsorship_history_score: int = Field(default=0, ge=0, le=100)
    audience_fit_score: int = Field(default=0, ge=0, le=100)
    business_capacity_score: int = Field(default=0, ge=0, le=100)
    distance_score: int = Field(default=0, ge=0, le=100)
    relationship_score: int = Field(default=0, ge=0, le=100)

    recommended_package_id: Optional[int] = None
    recommended_ask: Optional[float] = Field(default=None, ge=0)

    lead_source: str = "MANUAL"

    distance_miles: Optional[float] = Field(default=None, ge=0)

    assigned_to_user_id: Optional[int] = None


class EventRevenueProspectStatusUpdate(BaseModel):
    status: str


class EventRevenueProposalCreate(BaseModel):
    prospect_id: int
    package_id: Optional[int] = None

    title: str
    message: str


class EventRevenueProposalUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    clover_payment_url: Optional[str] = None


class EventRevenuePaymentCreate(BaseModel):
    organization_id: int
    prospect_id: Optional[int] = None
    package_id: Optional[int] = None

    provider: str = "CLOVER"

    provider_payment_id: Optional[str] = None
    payment_link: Optional[str] = None

    amount: float = Field(ge=0)

    status: str = "PENDING"


class RevenueOutreachCreate(BaseModel):
    prospect_id: int

    channel: Literal[
        "EMAIL",
        "SMS",
    ] = "EMAIL"

    template_key: Optional[str] = None

    subject: Optional[str] = None
    body: str


class VendorOperationsCreate(BaseModel):
    prospect_id: int

    booth_number: Optional[str] = None
    booth_size: Optional[str] = None

    power_required: bool = False
    power_amps: Optional[str] = None

    tables_required: int = Field(default=0, ge=0)
    chairs_required: int = Field(default=0, ge=0)

    food_vendor: bool = False

    food_permit_required: bool = False
    food_permit_received: bool = False

    insurance_required: bool = False
    insurance_received: bool = False

    arrival_time: Optional[str] = None
    setup_time: Optional[str] = None

    check_in_status: str = "NOT_CHECKED_IN"

    special_requests: Optional[str] = None


class RevenueSearchRequest(BaseModel):
    radius_miles: float = Field(default=5, gt=0, le=100)

    categories: List[str] = []

    minimum_fit_score: int = Field(default=0, ge=0, le=100)

    marketing_propensity: Optional[
        Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
    ] = None

    include_previous_contacts: bool = False
    include_previous_sponsors: bool = True

    max_results: int = Field(default=25, ge=1, le=100)


class RevenueOrganizationUpdate(BaseModel):
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

    industry: Optional[str] = None
    employee_size: Optional[str] = None

    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    linkedin_url: Optional[str] = None

    notes: Optional[str] = None

    marketing_propensity: Optional[
        Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
    ] = None

    verified_sponsorship_history: Optional[bool] = None


class SponsorScoutPipelineCreate(BaseModel):
    business_name: str
    website: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    industry: Optional[str] = None

    why_good_fit: Optional[str] = None

    marketing_evidence: list[str] = []
    sponsorship_evidence: list[str] = []
    source_urls: list[str] = []

    marketing_activity_score: int = Field(default=0, ge=0, le=100)
    sponsorship_history_score: int = Field(default=0, ge=0, le=100)
    audience_fit_score: int = Field(default=0, ge=0, le=100)
    business_capacity_score: int = Field(default=0, ge=0, le=100)
    distance_score: int = Field(default=0, ge=0, le=100)
    relationship_score: int = Field(default=20, ge=0, le=100)

    distance_miles: Optional[float] = Field(default=None, ge=0)

    marketing_propensity: Literal[
        "HIGH",
        "MEDIUM",
        "LOW",
        "UNKNOWN",
    ] = "UNKNOWN"

    verified_sponsorship_history: Optional[bool] = None
    lead_source: str = "OPENAI_WEB_SEARCH"


class AIRevenueProposalRequest(BaseModel):
    prospect_id: int
    package_id: Optional[int] = None

    event_name: str
    event_date: Optional[str] = None
    event_venue: Optional[str] = None
    event_address: Optional[str] = None

    additional_instructions: Optional[str] = None


class SponsorContactSearchRequest(BaseModel):
    prospect_id: int

    business_name: str
    website: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class AutoSponsorOutreachRequest(BaseModel):
    event_name: str
    event_date: Optional[str] = None
    event_venue: Optional[str] = None
    event_address: Optional[str] = None
    additional_instructions: Optional[str] = None
    send_if_ready: bool = True
