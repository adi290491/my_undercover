"""The shapes of the API's requests and responses."""

from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["waiting", "in_progress", "awaiting_signoff", "decided"]
Outcome = Literal["approve", "decline", "refer"]
StepKind = Literal["tool_call", "tool_result", "message", "error"]


class Item(BaseModel):
    description: str
    category: str
    amount: float


class Document(BaseModel):
    name: str
    type: str
    content: str


class ClaimSummary(BaseModel):
    claim_id: str
    claim_type: str
    customer_name: str
    amount_claimed: float
    submitted_on: str
    status: Status
    decision: Outcome | None
    payout: float | None


class Section(BaseModel):
    number: int
    title: str
    text: str


class Decision(BaseModel):
    decision: Outcome
    payout: float
    reason: str
    policy_section: Section
    decided_at: str


class Payment(BaseModel):
    amount: float
    paid_at: str


class SignOff(BaseModel):
    handler_id: str
    handler_name: str
    signed_at: str


class ClaimState(BaseModel):
    claim_id: str
    status: Status
    thread_id: str | None
    decision: Decision | None
    payment: Payment | None
    sign_off: SignOff | None


class Claim(ClaimState):
    policy_id: str
    customer_id: str
    customer_name: str
    claim_type: str
    submitted_on: str
    incident_date: str
    incident_location: str
    summary: str
    story: str
    items: list[Item]
    amount_claimed: float
    documents: list[Document]


class Trip(BaseModel):
    destination: str
    departs_on: str
    returns_on: str
    trip_cost: float


class Policy(BaseModel):
    policy_id: str
    customer_id: str
    plan: str
    add_ons: list[str]
    purchased_on: str
    sold_through: str
    trip: Trip
    travelers: list[str]
    status: str


class Plan(BaseModel):
    plan: str
    name: str
    trip_cancellation_max: float
    trip_delay_waiting_hours: int
    trip_delay_max: float
    baggage_delay_waiting_hours: int
    baggage_delay_max: float
    baggage_max: float
    per_item_limit: float
    passport_max: float
    emergency_medical_max: float
    deductible: float
    deductible_applies_to: list[str]


class PastClaim(BaseModel):
    claim_id: str
    filed_on: str
    incident_date: str
    claim_type: str
    summary: str
    outcome: str
    amount_paid: float


class Handler(BaseModel):
    handler_id: str
    name: str
    role: str
    can_approve_over_limit: bool


class Text(BaseModel):
    text: str


class Step(BaseModel):
    step_id: int
    claim_id: str
    thread_id: str
    kind: StepKind
    text: str
    created_at: str


class StartRequest(BaseModel):
    thread_id: str = Field(description="The id of the run that works the claim.")


class StepRequest(BaseModel):
    thread_id: str = Field(description="The id of the run the step belongs to.")
    kind: StepKind
    text: str


class DecisionRequest(BaseModel):
    decision: Outcome
    payout: float = Field(description="The payout in US dollars, or 0.")
    reason: str = Field(description="Two or three sentences explaining the decision.")
    policy_section: int = Field(
        description="The number of the policy wording section it rests on."
    )


class PaymentRequest(BaseModel):
    amount: float = Field(description="The approved payout in US dollars.")


class SignOffRequest(BaseModel):
    handler_id: str = Field(description="The handler signing off, such as HND-01.")


class ReleaseRequest(BaseModel):
    thread_id: str = Field(description="The id of the run releasing the claim.")


class RunStarted(BaseModel):
    claim_id: str
    thread_id: str
