import os
import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend.database import engine, get_db, Base, SessionLocal
from backend.models import DscIssue, DscPayment, DscStock
from backend import crud, schemas, export
from backend.seed_data import KHAMMAM_MANDALS, DEFAULT_DESIGNATIONS

# Create tables if not present (clean production database)
Base.metadata.create_all(bind=engine)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "nareshdpm")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "7159")
ADMIN_PIN = ADMIN_PASSWORD

app = FastAPI(
    title="DSC & USB Token Distribution Tracker",
    description="Administrative web dashboard for tracking Digital Signature Certificate & USB token distribution and date-wise part-payments.",
    version="1.0.0",
)

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# Static and template setup
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from backend.seed_data import seed_initial_data_if_empty
        seed_initial_data_if_empty(db)
    finally:
        db.close()


# -------------------------------------------------------------
# Frontend Page
# -------------------------------------------------------------
@app.get("/")
def get_dashboard():
    return FileResponse("templates/index.html")


# -------------------------------------------------------------
# Authentication API
# -------------------------------------------------------------
@app.post("/api/auth/verify", response_model=schemas.AuthResponse)
def verify_admin_login(req: schemas.AuthRequest):
    # Support username and password authentication
    if req.username and req.password:
        if req.username.strip().lower() == ADMIN_USERNAME.lower() and req.password.strip() == ADMIN_PASSWORD:
            return schemas.AuthResponse(
                success=True,
                token="admin-authorized-session-key",
                message="Login successful. Welcome!",
            )
    elif req.pin and req.pin.strip() == ADMIN_PASSWORD:
        return schemas.AuthResponse(
            success=True,
            token="admin-authorized-session-key",
            message="PIN verified successfully",
        )
    return schemas.AuthResponse(
        success=False,
        token=None,
        message="Invalid Username or Password. Please try again.",
    )


# -------------------------------------------------------------
# Metadata APIs
# -------------------------------------------------------------
@app.get("/api/metadata/mandals", response_model=List[str])
def get_all_mandals(db: Session = Depends(get_db)):
    # Combines Khammam rural 20 mandals with any custom mandals entered in DB
    db_mandals = [m[0] for m in db.query(DscIssue.mandal_name).distinct().all() if m[0]]
    combined = sorted(list(set(KHAMMAM_MANDALS + db_mandals)))
    return combined


@app.get("/api/metadata/gps", response_model=List[str])
def get_gram_panchayats(mandal: Optional[str] = None, db: Session = Depends(get_db)):
    return crud.get_gps_by_mandal(db, mandal)


@app.get("/api/metadata/designations", response_model=List[str])
def get_designations():
    return DEFAULT_DESIGNATIONS


# -------------------------------------------------------------
# DSC Issue Records APIs
# -------------------------------------------------------------
@app.get("/api/issues", response_model=List[schemas.IssueOut])
def list_issues(
    mandal: Optional[str] = Query(None),
    variant: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[datetime.date] = Query(None),
    to_date: Optional[datetime.date] = Query(None),
    db: Session = Depends(get_db),
):
    issues = crud.get_issues(
        db=db,
        mandal=mandal,
        variant=variant,
        status=status,
        search=search,
        from_date=from_date,
        to_date=to_date,
    )
    return issues


@app.get("/api/issues/{issue_id}", response_model=schemas.IssueOut)
def get_issue(issue_id: int, db: Session = Depends(get_db)):
    issue = crud.get_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="DSC issue record not found")
    return issue


@app.post("/api/issues", response_model=schemas.IssueOut, status_code=status.HTTP_201_CREATED)
def create_issue(issue_in: schemas.IssueCreate, db: Session = Depends(get_db)):
    issue = crud.create_issue(db, issue_in)
    return issue


@app.put("/api/issues/{issue_id}", response_model=schemas.IssueOut)
def update_issue(issue_id: int, issue_in: schemas.IssueUpdate, db: Session = Depends(get_db)):
    updated = crud.update_issue(db, issue_id, issue_in)
    if not updated:
        raise HTTPException(status_code=404, detail="DSC issue record not found")
    return updated


@app.delete("/api/issues/{issue_id}")
def delete_issue(issue_id: int, db: Session = Depends(get_db)):
    success = crud.delete_issue(db, issue_id)
    if not success:
        raise HTTPException(status_code=404, detail="DSC issue record not found")
    return {"success": True, "message": f"Issue #{issue_id} and all related payments deleted"}


# -------------------------------------------------------------
# Date-Wise Part-Payment APIs
# -------------------------------------------------------------
@app.post("/api/issues/{issue_id}/payments", response_model=schemas.PaymentOut, status_code=status.HTTP_201_CREATED)
def add_installment_payment(
    issue_id: int,
    payment_in: schemas.PaymentCreate,
    db: Session = Depends(get_db),
):
    issue = crud.get_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="DSC issue record not found")

    payment = crud.add_payment(db, issue_id, payment_in)
    return payment


@app.delete("/api/payments/{payment_id}")
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    success = crud.delete_payment(db, payment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Payment record not found")
    return {"success": True, "message": f"Payment #{payment_id} deleted"}


# -------------------------------------------------------------
# Analytics & Reports APIs
# -------------------------------------------------------------
@app.get("/api/analytics/stats", response_model=schemas.DashboardStats)
def get_dashboard_kpis(db: Session = Depends(get_db)):
    return crud.get_dashboard_stats(db)


@app.get("/api/analytics/mandals", response_model=List[schemas.MandalSummary])
def get_mandal_abstract(db: Session = Depends(get_db)):
    return crud.get_mandal_summaries(db)


# -------------------------------------------------------------
# Stock & Inventory APIs
# -------------------------------------------------------------
@app.get("/api/stock", response_model=schemas.StockOverview)
def get_stock_overview(db: Session = Depends(get_db)):
    return crud.get_stock_overview(db)


@app.post("/api/stock", response_model=schemas.StockOut, status_code=status.HTTP_201_CREATED)
def add_stock_batch(stock_in: schemas.StockCreate, db: Session = Depends(get_db)):
    stock = crud.add_stock(db, stock_in)
    return stock


@app.delete("/api/stock/{stock_id}")
def delete_stock_batch(stock_id: int, db: Session = Depends(get_db)):
    success = crud.delete_stock(db, stock_id)
    if not success:
        raise HTTPException(status_code=404, detail="Stock batch not found")
    return {"success": True, "message": f"Stock batch #{stock_id} deleted"}


# -------------------------------------------------------------
# Export APIs (Excel & CSV)
# -------------------------------------------------------------
@app.get("/api/export/excel")
def export_excel(
    mandal: Optional[str] = Query(None),
    variant: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[datetime.date] = Query(None),
    to_date: Optional[datetime.date] = Query(None),
    db: Session = Depends(get_db),
):
    issues = crud.get_issues(
        db=db,
        mandal=mandal,
        variant=variant,
        status=status,
        search=search,
        from_date=from_date,
        to_date=to_date,
    )
    stocks = crud.get_stocks(db)
    excel_stream = export.generate_excel_export(issues, stocks=stocks)
    filename = f"DSC_Distribution_Ledger_{datetime.date.today().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/export/csv")
def export_csv(
    mandal: Optional[str] = Query(None),
    variant: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[datetime.date] = Query(None),
    to_date: Optional[datetime.date] = Query(None),
    db: Session = Depends(get_db),
):
    issues = crud.get_issues(
        db=db,
        mandal=mandal,
        variant=variant,
        status=status,
        search=search,
        from_date=from_date,
        to_date=to_date,
    )
    csv_data = export.generate_csv_export(issues)
    filename = f"DSC_Distribution_Ledger_{datetime.date.today().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
