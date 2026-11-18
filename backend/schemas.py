import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator


# Payment Schemas
class PaymentBase(BaseModel):
    payment_date: datetime.date = Field(default_factory=datetime.date.today)
    amount_paid: float = Field(..., gt=0, description="Amount paid in ₹")
    payment_mode: str = Field(default="Cash")
    payment_note: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentOut(PaymentBase):
    id: int
    issue_id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# Issue Schemas
class IssueBase(BaseModel):
    token_given_date: datetime.date = Field(default_factory=datetime.date.today)
    mandal_name: str = Field(..., min_length=1)
    gram_panchayat_name: Optional[str] = Field(default="")
    recipient_name: str = Field(..., min_length=1)
    designation: str = Field(default="Panchayat Secretary")
    phone_number: Optional[str] = Field(default="")
    token_variant: str = Field(default="HYP")  # "HYP" or "Proxkey"
    dsc_count: int = Field(default=1, ge=1)
    unit_price: float = Field(default=1500.0, ge=0)
    remarks: Optional[str] = None

    @field_validator("token_variant")
    @classmethod
    def validate_variant(cls, v: str) -> str:
        v_clean = v.strip()
        if v_clean not in ["HYP", "Proxkey"]:
            raise ValueError("token_variant must be strictly 'HYP' or 'Proxkey'")
        return v_clean


class IssueCreate(IssueBase):
    # Optional initial payment at handover
    initial_amount_paid: Optional[float] = Field(default=0.0, ge=0)
    initial_payment_date: Optional[datetime.date] = None
    initial_payment_mode: Optional[str] = "Cash"
    initial_payment_note: Optional[str] = "Initial handover payment"


class IssueUpdate(BaseModel):
    token_given_date: Optional[datetime.date] = None
    mandal_name: Optional[str] = None
    gram_panchayat_name: Optional[str] = None
    recipient_name: Optional[str] = None
    designation: Optional[str] = None
    phone_number: Optional[str] = None
    token_variant: Optional[str] = None
    dsc_count: Optional[int] = Field(default=None, ge=1)
    unit_price: Optional[float] = Field(default=None, ge=0)
    remarks: Optional[str] = None


class IssueOut(IssueBase):
    id: int
    total_amount: float
    total_paid: float
    balance_amount: float
    payment_status: str
    payments: List[PaymentOut] = []
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


# Dashboard Statistics Schema
class DashboardStats(BaseModel):
    total_records: int
    total_dsc_count: int
    hyp_count: int
    proxkey_count: int
    total_billed: float
    total_collected: float
    total_balance: float
    collection_rate: float
    status_counts: Dict[str, int]


# Mandal Summary Schema
class MandalSummary(BaseModel):
    mandal_name: str
    hyp_keys: int
    proxkey_keys: int
    total_dscs: int
    gp_count: int
    total_billed: float
    total_paid: float
    pending_balance: float
    collection_rate: float


# Login / Auth Schemas
class AuthRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    pin: Optional[str] = None


class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str
