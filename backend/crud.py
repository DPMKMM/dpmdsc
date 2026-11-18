import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from backend.models import DscIssue, DscPayment, DscStock
from backend.schemas import IssueCreate, IssueUpdate, PaymentCreate, StockCreate


def get_issues(
    db: Session,
    mandal: Optional[str] = None,
    variant: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    from_date: Optional[datetime.date] = None,
    to_date: Optional[datetime.date] = None,
) -> List[DscIssue]:
    query = db.query(DscIssue).options(joinedload(DscIssue.payments)).order_by(DscIssue.token_given_date.desc(), DscIssue.id.desc())

    if mandal and mandal.strip() and mandal.lower() != "all":
        query = query.filter(DscIssue.mandal_name == mandal.strip())

    if variant and variant.strip() and variant.lower() != "all":
        query = query.filter(DscIssue.token_variant == variant.strip())

    if from_date:
        query = query.filter(DscIssue.token_given_date >= from_date)

    if to_date:
        query = query.filter(DscIssue.token_given_date <= to_date)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            (DscIssue.gram_panchayat_name.ilike(term))
            | (DscIssue.recipient_name.ilike(term))
            | (DscIssue.phone_number.ilike(term))
            | (DscIssue.mandal_name.ilike(term))
            | (DscIssue.remarks.ilike(term))
        )

    results = query.all()

    # Filter by calculated payment_status if requested
    if status and status.strip() and status.lower() != "all":
        target_status = status.strip().capitalize()
        results = [issue for issue in results if issue.payment_status.lower() == target_status.lower()]

    return results


def get_issue_by_id(db: Session, issue_id: int) -> Optional[DscIssue]:
    return db.query(DscIssue).options(joinedload(DscIssue.payments)).filter(DscIssue.id == issue_id).first()


def create_issue(db: Session, issue_in: IssueCreate) -> DscIssue:
    total_amount = round(issue_in.dsc_count * issue_in.unit_price, 2)
    
    db_issue = DscIssue(
        token_given_date=issue_in.token_given_date,
        mandal_name=issue_in.mandal_name.strip(),
        gram_panchayat_name=issue_in.gram_panchayat_name.strip() if issue_in.gram_panchayat_name else "",
        recipient_name=issue_in.recipient_name.strip(),
        designation=issue_in.designation.strip(),
        phone_number=issue_in.phone_number.strip() if issue_in.phone_number else "",
        token_variant=issue_in.token_variant.strip(),
        dsc_count=issue_in.dsc_count,
        unit_price=round(issue_in.unit_price, 2),
        total_amount=total_amount,
        remarks=issue_in.remarks.strip() if issue_in.remarks else None,
    )
    db.add(db_issue)
    db.flush()  # to get db_issue.id

    # If initial payment was made at handover, record it
    if issue_in.initial_amount_paid and issue_in.initial_amount_paid > 0:
        pay_date = issue_in.initial_payment_date or issue_in.token_given_date
        db_payment = DscPayment(
            issue_id=db_issue.id,
            payment_date=pay_date,
            amount_paid=round(issue_in.initial_amount_paid, 2),
            payment_mode=issue_in.initial_payment_mode or "Cash",
            payment_note=issue_in.initial_payment_note or "Initial handover payment",
        )
        db.add(db_payment)

    db.commit()
    db.refresh(db_issue)
    return db_issue


def update_issue(db: Session, issue_id: int, issue_in: IssueUpdate) -> Optional[DscIssue]:
    db_issue = db.query(DscIssue).filter(DscIssue.id == issue_id).first()
    if not db_issue:
        return None

    update_data = issue_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None and isinstance(value, str):
            value = value.strip()
        setattr(db_issue, field, value)

    # Recalculate total amount if count or unit price changed
    db_issue.total_amount = round(db_issue.dsc_count * db_issue.unit_price, 2)
    db_issue.updated_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(db_issue)
    return db_issue


def delete_issue(db: Session, issue_id: int) -> bool:
    db_issue = db.query(DscIssue).filter(DscIssue.id == issue_id).first()
    if not db_issue:
        return False
    db.delete(db_issue)
    db.commit()
    return True


def add_payment(db: Session, issue_id: int, payment_in: PaymentCreate) -> Optional[DscPayment]:
    db_issue = db.query(DscIssue).filter(DscIssue.id == issue_id).first()
    if not db_issue:
        return None

    payment = DscPayment(
        issue_id=issue_id,
        payment_date=payment_in.payment_date,
        amount_paid=round(payment_in.amount_paid, 2),
        payment_mode=payment_in.payment_mode.strip() if payment_in.payment_mode else "Cash",
        payment_note=payment_in.payment_note.strip() if payment_in.payment_note else None,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def delete_payment(db: Session, payment_id: int) -> bool:
    payment = db.query(DscPayment).filter(DscPayment.id == payment_id).first()
    if not payment:
        return False
    db.delete(payment)
    db.commit()
    return True


def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    issues = db.query(DscIssue).options(joinedload(DscIssue.payments)).all()

    total_records = len(issues)
    total_dsc_count = sum(i.dsc_count for i in issues)
    hyp_count = sum(i.dsc_count for i in issues if i.token_variant == "HYP")
    proxkey_count = sum(i.dsc_count for i in issues if i.token_variant == "Proxkey")
    total_billed = round(sum(i.total_amount for i in issues), 2)
    total_collected = round(sum(i.total_paid for i in issues), 2)
    total_balance = round(sum(i.balance_amount for i in issues), 2)

    collection_rate = round((total_collected / total_billed * 100), 1) if total_billed > 0 else 0.0

    status_counts = {"Pending": 0, "Partial": 0, "Paid": 0}
    for i in issues:
        st = i.payment_status
        if st in status_counts:
            status_counts[st] += 1

    # Stock metrics
    stocks = db.query(DscStock).all()
    hyp_procured = sum(s.quantity for s in stocks if s.token_variant == "HYP")
    proxkey_procured = sum(s.quantity for s in stocks if s.token_variant == "Proxkey")
    total_procured = hyp_procured + proxkey_procured

    hyp_available = hyp_procured - hyp_count
    proxkey_available = proxkey_procured - proxkey_count
    total_available = total_procured - total_dsc_count

    return {
        "total_records": total_records,
        "total_dsc_count": total_dsc_count,
        "hyp_count": hyp_count,
        "proxkey_count": proxkey_count,
        "total_billed": total_billed,
        "total_collected": total_collected,
        "total_balance": total_balance,
        "collection_rate": collection_rate,
        "status_counts": status_counts,
        "stock": {
            "total_procured": total_procured,
            "total_issued": total_dsc_count,
            "total_available": total_available,
            "hyp_procured": hyp_procured,
            "hyp_issued": hyp_count,
            "hyp_available": hyp_available,
            "proxkey_procured": proxkey_procured,
            "proxkey_issued": proxkey_count,
            "proxkey_available": proxkey_available,
        }
    }


def get_mandal_summaries(db: Session) -> List[Dict[str, Any]]:
    issues = db.query(DscIssue).options(joinedload(DscIssue.payments)).all()
    mandals: Dict[str, Dict[str, Any]] = {}

    for i in issues:
        m = i.mandal_name
        if m not in mandals:
            mandals[m] = {
                "mandal_name": m,
                "hyp_keys": 0,
                "proxkey_keys": 0,
                "total_dscs": 0,
                "gps": set(),
                "total_billed": 0.0,
                "total_paid": 0.0,
                "pending_balance": 0.0,
            }
        
        if i.token_variant == "HYP":
            mandals[m]["hyp_keys"] += i.dsc_count
        else:
            mandals[m]["proxkey_keys"] += i.dsc_count
            
        mandals[m]["total_dscs"] += i.dsc_count
        if i.gram_panchayat_name and i.gram_panchayat_name.strip():
            mandals[m]["gps"].add(i.gram_panchayat_name.strip())
        mandals[m]["total_billed"] += i.total_amount
        mandals[m]["total_paid"] += i.total_paid
        mandals[m]["pending_balance"] += i.balance_amount

    result = []
    for m, data in sorted(mandals.items()):
        billed = round(data["total_billed"], 2)
        paid = round(data["total_paid"], 2)
        bal = round(data["pending_balance"], 2)
        rate = round((paid / billed * 100), 1) if billed > 0 else 0.0
        result.append({
            "mandal_name": m,
            "hyp_keys": data["hyp_keys"],
            "proxkey_keys": data["proxkey_keys"],
            "total_dscs": data["total_dscs"],
            "gp_count": len(data["gps"]),
            "total_billed": billed,
            "total_paid": paid,
            "pending_balance": bal,
            "collection_rate": rate,
        })
    return result


def get_gps_by_mandal(db: Session, mandal_name: Optional[str] = None) -> List[str]:
    query = db.query(DscIssue.gram_panchayat_name).distinct()
    if mandal_name and mandal_name.strip() and mandal_name.lower() != "all":
        query = query.filter(DscIssue.mandal_name == mandal_name.strip())
    results = query.order_by(DscIssue.gram_panchayat_name.asc()).all()
    return [r[0] for r in results if r[0]]


# -------------------------------------------------------------
# Stock & Inventory Operations
# -------------------------------------------------------------
def add_stock(db: Session, stock_in: StockCreate) -> DscStock:
    stock = DscStock(
        stock_date=stock_in.stock_date,
        token_variant=stock_in.token_variant.strip(),
        quantity=stock_in.quantity,
        unit_cost=round(stock_in.unit_cost, 2),
        supplier_name=stock_in.supplier_name.strip() if stock_in.supplier_name else "",
        invoice_ref=stock_in.invoice_ref.strip() if stock_in.invoice_ref else "",
        notes=stock_in.notes.strip() if stock_in.notes else None,
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock


def get_stocks(db: Session) -> List[DscStock]:
    return db.query(DscStock).order_by(DscStock.stock_date.desc(), DscStock.id.desc()).all()


def delete_stock(db: Session, stock_id: int) -> bool:
    stock = db.query(DscStock).filter(DscStock.id == stock_id).first()
    if not stock:
        return False
    db.delete(stock)
    db.commit()
    return True


def get_stock_overview(db: Session) -> Dict[str, Any]:
    stocks = db.query(DscStock).order_by(DscStock.stock_date.desc(), DscStock.id.desc()).all()
    issues = db.query(DscIssue).all()

    hyp_procured = sum(s.quantity for s in stocks if s.token_variant == "HYP")
    proxkey_procured = sum(s.quantity for s in stocks if s.token_variant == "Proxkey")
    total_procured = hyp_procured + proxkey_procured

    hyp_issued = sum(i.dsc_count for i in issues if i.token_variant == "HYP")
    proxkey_issued = sum(i.dsc_count for i in issues if i.token_variant == "Proxkey")
    total_issued = hyp_issued + proxkey_issued

    hyp_available = hyp_procured - hyp_issued
    proxkey_available = proxkey_procured - proxkey_issued
    total_available = total_procured - total_issued

    total_investment = round(sum(s.quantity * s.unit_cost for s in stocks), 2)

    batches_data = []
    for s in stocks:
        batches_data.append({
            "id": s.id,
            "stock_date": s.stock_date,
            "token_variant": s.token_variant,
            "quantity": s.quantity,
            "unit_cost": s.unit_cost,
            "total_cost": round(s.quantity * s.unit_cost, 2),
            "supplier_name": s.supplier_name or "",
            "invoice_ref": s.invoice_ref or "",
            "notes": s.notes or "",
            "created_at": s.created_at,
        })

    return {
        "total_procured": total_procured,
        "total_issued": total_issued,
        "total_available": total_available,
        "hyp_procured": hyp_procured,
        "hyp_issued": hyp_issued,
        "hyp_available": hyp_available,
        "proxkey_procured": proxkey_procured,
        "proxkey_issued": proxkey_issued,
        "proxkey_available": proxkey_available,
        "total_investment": total_investment,
        "batches": batches_data,
    }
