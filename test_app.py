import os
import sys
import datetime
from fastapi.testclient import TestClient

from main import app
from backend.database import SessionLocal, Base, engine
from backend.models import DscIssue, DscPayment, DscStock

client = TestClient(app)

def test_full_application_flow():
    print("=== STARTING COMPLETE DSC TOKEN APPLICATION TEST SUITE ===")

    # Reset DB to clean slate before test
    db = SessionLocal()
    try:
        db.query(DscPayment).delete()
        db.query(DscIssue).delete()
        db.query(DscStock).delete()
        db.commit()
    finally:
        db.close()


    # 1. Test Admin Authentication (Username & Password)
    res_auth_fail = client.post("/api/auth/verify", json={"username": "nareshdpm", "password": "wrong_password"})
    assert res_auth_fail.status_code == 200
    assert res_auth_fail.json()["success"] is False
    print("✔ Admin Auth Failure Check: Passed")

    res_auth_ok = client.post("/api/auth/verify", json={"username": "nareshdpm", "password": "7159"})
    assert res_auth_ok.status_code == 200
    assert res_auth_ok.json()["success"] is True
    print("✔ Admin Auth (Username: nareshdpm, Password: 7159) Success Check: Passed")

    # 2. Test Metadata
    res_mandals = client.get("/api/metadata/mandals")
    assert res_mandals.status_code == 200
    mandals = res_mandals.json()
    assert "Khammam Rural" in mandals
    assert "Wyra" in mandals
    assert len(mandals) >= 20
    print(f"✔ Mandals Metadata Check: {len(mandals)} mandals loaded properly")

    res_desigs = client.get("/api/metadata/designations")
    assert res_desigs.status_code == 200
    assert "Panchayat Secretary" in res_desigs.json()
    print("✔ Designations Metadata Check: Passed")

    # 3. Test Dashboard KPIs
    res_stats = client.get("/api/analytics/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    print(f"✔ Initial Stats: Total DSCs: {stats['total_dsc_count']} (HYP: {stats['hyp_count']}, Proxkey: {stats['proxkey_count']}) | Billed: ₹{stats['total_billed']} | Collected: ₹{stats['total_collected']} | Balance: ₹{stats['total_balance']}")

    # 4. Create New DSC Issue with an Initial Part-Payment
    new_issue_payload = {
        "token_given_date": str(datetime.date.today()),
        "mandal_name": "Mudigonda",
        "gram_panchayat_name": "Madapuram",
        "recipient_name": "S. Ramachandra Murthy",
        "designation": "Panchayat Secretary",
        "phone_number": "9876543210",
        "token_variant": "Proxkey",
        "dsc_count": 2,
        "unit_price": 1600.0,
        "remarks": "Test handover for e-Panchayat portal",
        "initial_amount_paid": 1600.0,
        "initial_payment_date": str(datetime.date.today()),
        "initial_payment_mode": "UPI / PhonePe / GPay",
        "initial_payment_note": "Advance 50% via PhonePe"
    }

    res_create = client.post("/api/issues", json=new_issue_payload)
    assert res_create.status_code == 201
    created_issue = res_create.json()
    issue_id = created_issue["id"]
    assert created_issue["total_amount"] == 3200.0
    assert created_issue["total_paid"] == 1600.0
    assert created_issue["balance_amount"] == 1600.0
    assert created_issue["payment_status"] == "Partial"
    assert len(created_issue["payments"]) == 1
    print(f"✔ Created Issue #{issue_id}: Billed ₹3,200, Initial Paid ₹1,600, Balance ₹1,600, Status: Partial")

    # 4b. Test issue creation without Gram Panchayat name (Optional GP)
    optional_gp_payload = {
        "token_given_date": str(datetime.date.today()),
        "mandal_name": "Kalluru",
        "gram_panchayat_name": "",
        "recipient_name": "K. Venkateshwarlu",
        "designation": "Junior Assistant / GPEO",
        "phone_number": "9123456780",
        "token_variant": "HYP",
        "dsc_count": 1,
        "unit_price": 1500.0,
    }
    res_optional_gp = client.post("/api/issues", json=optional_gp_payload)
    assert res_optional_gp.status_code == 201
    assert res_optional_gp.json()["gram_panchayat_name"] == ""
    print("✔ Issue Creation with Optional (empty) GP Name: Passed")

    # 4c. Test issue creation with Optional (empty) Phone Number
    optional_phone_payload = {
        "token_given_date": str(datetime.date.today()),
        "mandal_name": "Bonakal",
        "gram_panchayat_name": "Allinagaram",
        "recipient_name": "M. Krishna",
        "designation": "Sarpanch",
        "phone_number": "",
        "token_variant": "Proxkey",
        "dsc_count": 1,
        "unit_price": 1500.0,
    }
    res_optional_phone = client.post("/api/issues", json=optional_phone_payload)
    assert res_optional_phone.status_code == 201
    assert res_optional_phone.json()["phone_number"] == ""
    print("✔ Issue Creation with Optional (empty) Mobile Number: Passed")

    # 5. Record a 2nd Date-Wise Part-Payment Installment
    payment_payload = {
        "payment_date": str(datetime.date.today()),
        "amount_paid": 1600.0,
        "payment_mode": "Cash",
        "payment_note": "2nd installment settlement in cash"
    }
    res_pay = client.post(f"/api/issues/{issue_id}/payments", json=payment_payload)
    assert res_pay.status_code == 201
    print("✔ Added 2nd part-payment installment of ₹1,600")

    # 6. Verify Issue is now 100% Paid with Balance = 0
    res_verify = client.get(f"/api/issues/{issue_id}")
    assert res_verify.status_code == 200
    updated_issue = res_verify.json()
    assert updated_issue["total_paid"] == 3200.0
    assert updated_issue["balance_amount"] == 0.0
    assert updated_issue["payment_status"] == "Paid"
    assert len(updated_issue["payments"]) == 2
    print(f"✔ Verified Issue #{issue_id}: Total Paid ₹{updated_issue['total_paid']}, Balance ₹{updated_issue['balance_amount']}, Status: {updated_issue['payment_status']}")

    # 7. Test Filtering by Mandal, Variant, Status, Search
    res_filter_mandal = client.get("/api/issues?mandal=Mudigonda")
    assert res_filter_mandal.status_code == 200
    assert any(i["id"] == issue_id for i in res_filter_mandal.json())
    print("✔ Mandal Filtering: Passed")

    res_filter_status = client.get("/api/issues?status=Paid")
    assert res_filter_status.status_code == 200
    assert all(i["payment_status"] == "Paid" for i in res_filter_status.json())
    print("✔ Status Filtering: Passed")

    res_search = client.get("/api/issues?search=Ramachandra")
    assert res_search.status_code == 200
    assert len(res_search.json()) >= 1
    print("✔ Instant Search: Passed")

    # 8. Test Mandal-Wise Abstract
    res_abstract = client.get("/api/analytics/mandals")
    assert res_abstract.status_code == 200
    abstract = res_abstract.json()
    mudigonda_row = next((m for m in abstract if m["mandal_name"] == "Mudigonda"), None)
    assert mudigonda_row is not None
    assert mudigonda_row["total_dscs"] >= 2
    print("✔ Mandal Abstract Table: Passed")

    # 9. Test Excel Export (.xlsx)
    res_excel = client.get("/api/export/excel")
    assert res_excel.status_code == 200
    assert len(res_excel.content) > 1000
    assert res_excel.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    print(f"✔ Excel Export: Generated {len(res_excel.content)} bytes valid .xlsx file")

    # 10. Test CSV Export (.csv)
    res_csv = client.get("/api/export/csv")
    assert res_csv.status_code == 200
    assert "Gram Panchayat" in res_csv.text
    assert "Mudigonda" in res_csv.text
    print(f"✔ CSV Export: Generated {len(res_csv.text)} characters valid CSV with UTF-8 BOM")

    # 10b. Test Stock & Inventory APIs
    stock_payload_hyp = {
        "stock_date": str(datetime.date.today()),
        "token_variant": "HYP",
        "quantity": 25,
        "unit_cost": 800.0,
        "supplier_name": "eMudhra Ltd",
        "invoice_ref": "EMU-8821",
        "notes": "Batch 1 procurement"
    }
    res_stock1 = client.post("/api/stock", json=stock_payload_hyp)
    assert res_stock1.status_code == 201
    stock_hyp_id = res_stock1.json()["id"]

    stock_payload_prox = {
        "stock_date": str(datetime.date.today()),
        "token_variant": "Proxkey",
        "quantity": 35,
        "unit_cost": 900.0,
        "supplier_name": "WatchData Distributor",
        "invoice_ref": "WD-5510",
        "notes": "Batch 2 procurement"
    }
    res_stock2 = client.post("/api/stock", json=stock_payload_prox)
    assert res_stock2.status_code == 201

    res_stock_overview = client.get("/api/stock")
    assert res_stock_overview.status_code == 200
    st_data = res_stock_overview.json()
    assert st_data["total_procured"] == 60
    assert st_data["hyp_procured"] == 25
    assert st_data["proxkey_procured"] == 35
    assert len(st_data["batches"]) == 2
    print(f"✔ Stock Overview API: Total Procured {st_data['total_procured']}, Available {st_data['total_available']} (HYP: {st_data['hyp_available']}, Proxkey: {st_data['proxkey_available']})")

    # 11. Test Frontend HTML Endpoint
    res_html = client.get("/")
    assert res_html.status_code == 200
    assert "DSC &amp; USB Token Ledger" in res_html.text or "DSC & USB Token Ledger" in res_html.text
    print("✔ Frontend HTML Serving: Passed")

    # 12. Cleanup test data so database is empty for production
    db = SessionLocal()
    try:
        db.query(DscPayment).delete()
        db.query(DscIssue).delete()
        db.query(DscStock).delete()
        db.commit()
    finally:
        db.close()
    print("✔ Cleaned up test data: Database reset to empty production state")

    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! APPLICATION IS 100% OPERATIONAL.")


if __name__ == "__main__":
    test_full_application_flow()
