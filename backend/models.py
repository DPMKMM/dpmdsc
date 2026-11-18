import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base


class DscIssue(Base):
    __tablename__ = "dsc_issues"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    token_given_date = Column(Date, nullable=False, default=datetime.date.today)
    mandal_name = Column(String(100), nullable=False, index=True)
    gram_panchayat_name = Column(String(150), nullable=True, index=True, default="")
    recipient_name = Column(String(150), nullable=False)
    designation = Column(String(100), nullable=False, default="Panchayat Secretary")
    phone_number = Column(String(20), nullable=True, default="")
    token_variant = Column(String(20), nullable=False, default="HYP")  # "HYP" or "Proxkey"
    dsc_count = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False, default=1500.0)
    total_amount = Column(Float, nullable=False, default=1500.0)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    payments = relationship("DscPayment", back_populates="issue", cascade="all, delete-orphan", order_by="DscPayment.payment_date.asc()")

    @property
    def total_paid(self) -> float:
        if not self.payments:
            return 0.0
        return round(sum(p.amount_paid for p in self.payments), 2)

    @property
    def balance_amount(self) -> float:
        return round(max(0.0, self.total_amount - self.total_paid), 2)

    @property
    def payment_status(self) -> str:
        paid = self.total_paid
        total = self.total_amount
        if paid >= total:
            return "Paid"
        elif paid > 0:
            return "Partial"
        else:
            return "Pending"


class DscPayment(Base):
    __tablename__ = "dsc_payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    issue_id = Column(Integer, ForeignKey("dsc_issues.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_date = Column(Date, nullable=False, default=datetime.date.today)
    amount_paid = Column(Float, nullable=False)
    payment_mode = Column(String(50), nullable=False, default="Cash")  # "Cash", "UPI / PhonePe / GPay", "Bank Transfer", "Cheque"
    payment_note = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    issue = relationship("DscIssue", back_populates="payments")
