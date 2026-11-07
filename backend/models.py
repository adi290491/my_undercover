"""The shapes the UnderCover API takes and returns."""

import re
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

Status = Literal["waiting", "in_progress", "awaiting_signoff", "decided"]
StepKind = Literal["tool_call", "tool_result", "message", "error"]
MAX_SENTENCES = 3


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
    summary: str
    status: Status


class NewDecision(BaseModel):
    decision: Literal["approve", "decline", "refer"]
    payout: float = Field(ge=0)
    reason: str = Field(min_length=1)
    policy_section: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def short_reason(cls, reason: str) -> str:
        if len(re.findall(r"[.!?](?=\s|$)", reason.strip())) > MAX_SENTENCES:
            raise ValueError("The reason must be two or three sentences")
        return reason

    @model_validator(mode="after")
    def payout_matches_decision(self) -> Self:
        if self.decision == "approve" and self.payout == 0:
            raise ValueError("An approval needs a payout")
        if self.decision != "approve" and self.payout != 0:
            raise ValueError("A decline or a referral has a payout of 0")
        return self


class Decision(NewDecision):
    decided_at: str


class NewPayment(BaseModel):
    amount: float = Field(gt=0)


class Payment(NewPayment):
    paid_at: str


class NewSignOff(BaseModel):
    handler_id: str


class SignOff(NewSignOff):
    handler_name: str
    signed_at: str


class NewStep(BaseModel):
    kind: StepKind
    text: str


class Step(NewStep):
    step_id: int
    at: str


class Start(BaseModel):
    thread_id: str = Field(min_length=1)


class Claim(ClaimSummary):
    policy_id: str
    customer_id: str
    incident_date: str
    incident_location: str
    story: str
    items: list[Item]
    documents: list[Document]
    thread_id: str | None
    decision: Decision | None
    payment: Payment | None
    sign_off: SignOff | None


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


class ClaimHistory(BaseModel):
    customer_id: str
    customer_since: str
    previous_claims: list[PastClaim]


class Handler(BaseModel):
    handler_id: str
    name: str
    role: str
    can_approve_over_limit: bool


class PolicyWording(BaseModel):
    policy_wording: str


class Instructions(BaseModel):
    instructions: str
