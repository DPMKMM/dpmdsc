import io
import csv
import datetime
from typing import List
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from backend.models import DscIssue, DscPayment


def generate_excel_export(issues: List[DscIssue]) -> io.BytesIO:
    wb = Workbook()
    
    # -------------------------------------------------------------
    # 1. Sheet: DSC Distribution Register
    # -------------------------------------------------------------
    ws_issues = wb.active
    ws_issues.title = "DSC Distribution Register"
    
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Dark Blue
    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    issue_headers = [
        "Issue ID",
        "Token Given Date",
        "Mandal",
        "Gram Panchayat",
        "Recipient Name",
        "Designation",
        "Phone Number",
        "Token Variant",
        "No. of DSCs",
        "Rate per Key (₹)",
        "Total Billed (₹)",
        "Total Paid (₹)",
        "Balance Pending (₹)",
        "Payment Status",
        "Remarks",
    ]

    ws_issues.append(issue_headers)
    for col_idx in range(1, len(issue_headers) + 1):
        cell = ws_issues.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws_issues.row_dimensions[1].height = 28

    status_fills = {
        "Paid": PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid"),     # Green
        "Partial": PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid"),  # Amber
        "Pending": PatternFill(start_color="FFE4E6", end_color="FFE4E6", fill_type="solid"),  # Rose
    }

    row_idx = 2
    for issue in issues:
        ws_issues.append([
            issue.id,
            issue.token_given_date.strftime("%d-%m-%Y") if issue.token_given_date else "",
            issue.mandal_name,
            issue.gram_panchayat_name or "—",
            issue.recipient_name,
            issue.designation,
            issue.phone_number,
            issue.token_variant,
            issue.dsc_count,
            issue.unit_price,
            issue.total_amount,
            issue.total_paid,
            issue.balance_amount,
            issue.payment_status,
            issue.remarks or "",
        ])

        # Style row
        for col_idx in range(1, len(issue_headers) + 1):
            cell = ws_issues.cell(row=row_idx, column=col_idx)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")

            # Numeric alignments
            if col_idx in [1, 9]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in [10, 11, 12, 13]:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = "₹#,##0.00"
            elif col_idx == 14:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if issue.payment_status in status_fills:
                    cell.fill = status_fills[issue.payment_status]

        row_idx += 1

    # Auto-adjust column widths
    for col in ws_issues.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_issues.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # -------------------------------------------------------------
    # 2. Sheet: Date-Wise Payment Ledger
    # -------------------------------------------------------------
    ws_payments = wb.create_sheet(title="Date-Wise Payments Ledger")
    pay_header_fill = PatternFill(start_color="065F46", end_color="065F46", fill_type="solid") # Dark Emerald

    pay_headers = [
        "Payment ID",
        "Issue Ref ID",
        "Mandal",
        "Gram Panchayat",
        "Recipient Name",
        "Payment Date",
        "Amount Paid (₹)",
        "Payment Mode",
        "Payment Note / Ref",
        "Created At",
    ]

    ws_payments.append(pay_headers)
    for col_idx in range(1, len(pay_headers) + 1):
        cell = ws_payments.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = pay_header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws_payments.row_dimensions[1].height = 28

    p_row_idx = 2
    for issue in issues:
        for payment in sorted(issue.payments, key=lambda p: (p.payment_date, p.id)):
            ws_payments.append([
                payment.id,
                issue.id,
                issue.mandal_name,
                issue.gram_panchayat_name,
                issue.recipient_name,
                payment.payment_date.strftime("%d-%m-%Y") if payment.payment_date else "",
                payment.amount_paid,
                payment.payment_mode,
                payment.payment_note or "",
                payment.created_at.strftime("%d-%m-%Y %H:%M") if payment.created_at else "",
            ])
            for col_idx in range(1, len(pay_headers) + 1):
                cell = ws_payments.cell(row=p_row_idx, column=col_idx)
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center")
                if col_idx in [1, 2, 6, 8]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                elif col_idx == 7:
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    cell.number_format = "₹#,##0.00"

            p_row_idx += 1

    for col in ws_payments.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_payments.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # -------------------------------------------------------------
    # 3. Sheet: Mandal-Wise Summary
    # -------------------------------------------------------------
    ws_mandals = wb.create_sheet(title="Mandal Abstract")
    mandal_header_fill = PatternFill(start_color="4338CA", end_color="4338CA", fill_type="solid") # Indigo

    m_headers = [
        "Mandal Name",
        "HYP Keys",
        "Proxkey Keys",
        "Total DSCs",
        "GPs Covered",
        "Total Billed (₹)",
        "Total Collected (₹)",
        "Pending Balance (₹)",
        "Collection %",
    ]

    ws_mandals.append(m_headers)
    for col_idx in range(1, len(m_headers) + 1):
        cell = ws_mandals.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = mandal_header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws_mandals.row_dimensions[1].height = 28

    # Aggregate by mandal
    m_dict = {}
    for issue in issues:
        m = issue.mandal_name
        if m not in m_dict:
            m_dict[m] = {"hyp": 0, "prox": 0, "total_dsc": 0, "gps": set(), "billed": 0.0, "paid": 0.0, "bal": 0.0}
        if issue.token_variant == "HYP":
            m_dict[m]["hyp"] += issue.dsc_count
        else:
            m_dict[m]["prox"] += issue.dsc_count
        m_dict[m]["total_dsc"] += issue.dsc_count
        m_dict[m]["gps"].add(issue.gram_panchayat_name)
        m_dict[m]["billed"] += issue.total_amount
        m_dict[m]["paid"] += issue.total_paid
        m_dict[m]["bal"] += issue.balance_amount

    m_row_idx = 2
    for m, d in sorted(m_dict.items()):
        rate = round(d["paid"] / d["billed"] * 100, 1) if d["billed"] > 0 else 0.0
        ws_mandals.append([
            m,
            d["hyp"],
            d["prox"],
            d["total_dsc"],
            len(d["gps"]),
            d["billed"],
            d["paid"],
            d["bal"],
            f"{rate}%",
        ])
        for col_idx in range(1, len(m_headers) + 1):
            cell = ws_mandals.cell(row=m_row_idx, column=col_idx)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")
            if col_idx in [2, 3, 4, 5, 9]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in [6, 7, 8]:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = "₹#,##0.00"

        m_row_idx += 1

    for col in ws_mandals.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_mandals.column_dimensions[col_letter].width = max(max_len + 4, 12)

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream


def generate_csv_export(issues: List[DscIssue]) -> str:
    output = io.StringIO()
    # Write BOM for UTF-8 so Excel opens Indian Rupee and symbols properly
    output.write("\ufeff")
    writer = csv.writer(output)

    writer.writerow([
        "Issue ID",
        "Token Given Date",
        "Mandal",
        "Gram Panchayat",
        "Recipient Name",
        "Designation",
        "Phone Number",
        "Token Variant",
        "No. of DSCs",
        "Rate per Key (INR)",
        "Total Billed (INR)",
        "Total Paid (INR)",
        "Balance Pending (INR)",
        "Payment Status",
        "Remarks",
        "Payment History Summary",
    ])

    for issue in issues:
        history_summary = " | ".join(
            f"{p.payment_date.strftime('%d-%m-%Y')}: ₹{p.amount_paid:.2f} ({p.payment_mode})"
            for p in issue.payments
        )
        writer.writerow([
            issue.id,
            issue.token_given_date.strftime("%d-%m-%Y") if issue.token_given_date else "",
            issue.mandal_name,
            issue.gram_panchayat_name or "—",
            issue.recipient_name,
            issue.designation,
            issue.phone_number,
            issue.token_variant,
            issue.dsc_count,
            f"{issue.unit_price:.2f}",
            f"{issue.total_amount:.2f}",
            f"{issue.total_paid:.2f}",
            f"{issue.balance_amount:.2f}",
            issue.payment_status,
            issue.remarks or "",
            history_summary,
        ])

    return output.getvalue()
