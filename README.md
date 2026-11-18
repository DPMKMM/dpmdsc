# Digital Signature Certificate (DSC) & USB Token Distribution Tracker

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/DPMKMM/dpmdsc)

* **GitHub Repository:** [https://github.com/DPMKMM/dpmdsc](https://github.com/DPMKMM/dpmdsc)
* **Production Render URL:** [https://dpmdsc.onrender.com](https://dpmdsc.onrender.com)
* **Admin Credentials:** Username: `nareshdpm` | Password: `7159`

A responsive, production-ready web application for tracking Digital Signature Certificate (DSC) and physical USB token (**HYP** and **Proxkey**) handovers across Mandals and Gram Panchayats (specifically pre-configured for Khammam District's 20 rural mandals), featuring a date-wise part-payment ledger, balance tracker, and multi-sheet Excel / CSV exports.

---

## 🎯 Core Features

1. **Token Distribution Register:**
   - Record token handover date (`token_given_date`), Mandal name, Gram Panchayat (GP) name, recipient official name, designation, and phone number.
   - Distinct color badges for token variants: **HYP** (Indigo) and **Proxkey** (Emerald).
   - Multi-DSC quantity tracking with customizable unit rates (₹) and live total amount calculation.
   - Pre-loaded with all **20 rural mandals of Khammam District** (Bonakal, Chinthakani, Enkoor, Kalluru, Kamepalli, Khammam Rural, Konijerla, Kusumanchi, Madhira, Mudigonda, Nelakondapalli, Penuballi, Raghunadhapalem, Sathupalli, Singareni, Thallada, Tirumalayapalem, Vemsoor, Wyra, Yerrupalem) plus an option to add custom mandals.
   - Gram Panchayat autocomplete based on previously recorded GPs under that specific Mandal.

2. **Date-Wise Part-Payment Ledger (`+ Add Payment` Drawer / Modal):**
   - Record multiple installment payments received on different dates against a single DSC issue record.
   - Support for payment modes: **Cash**, **UPI / PhonePe / GPay**, **Bank Transfer (NEFT/IMPS)**, and **Cheque**.
   - Audit trail of payment dates, amounts, and reference notes.
   - Automatic live calculation of **Total Paid**, **Remaining Balance**, and **Status** (`Paid`, `Partial`, `Pending`).
   - Quick one-click "Fill Full Balance" and preset amount buttons (`₹500`, `₹1,000`, `₹1,500`).
   - Dynamic overpayment warning preventing unintentional over-collection.

3. **Live Financial & Distribution KPI Cards:**
   - **Total DSCs Issued:** Overall key count with live variant split (`HYP: X` vs `Proxkey: Y`).
   - **Total Billed Amount (₹):** Cumulative billed value.
   - **Total Collected (₹):** Green recovery metric with recovery percentage.
   - **Total Balance Pending (₹):** Real-time dues with count of pending/partial GPs.

4. **Instant Filters & Search:**
   - Filter by Mandal, Token Variant (`HYP` / `Proxkey`), Payment Status (`Pending`, `Partial`, `Paid`), and Date Range (`From Date` to `To Date`).
   - Instant search across GP Name, Recipient Name, Phone Number, and Remarks.
   - Click-to-call (`tel:`) and direct WhatsApp reminder links (`wa.me/91...`) for rapid follow-ups with Panchayat Secretaries and Sarpanches.

5. **Mandal-Wise Summary Abstract (Secondary View):**
   - High-level abstract table showing Mandal Name, HYP Keys, Proxkey Keys, Total DSCs, GPs Covered, Total Billed, Total Paid, Pending Balance, and Collection Recovery %.
   - One-click drill-down: clicking "View GPs" instantly filters the main ledger to that Mandal.

6. **Comprehensive Export:**
   - **Export to Excel (.xlsx):** Generates a multi-sheet, styled workbook containing:
     1. *DSC Distribution Register* (all distribution records, pricing, paid, balance, status)
     2. *Date-Wise Payments Ledger* (full audit history of every installment)
     3. *Mandal Abstract* (mandal-level recovery summary)
   - **Export to CSV (.csv):** UTF-8 encoded with BOM for opening directly in Microsoft Excel.

7. **Admin Security PIN:**
   - Lockable administrative dashboard with configurable PIN (defaults to `1234`).
   - Safe session storage authentication with backend verification.

---

## 🏗️ Architecture & Folder Structure

```
Token_Distrubution/
├── backend/
│   ├── __init__.py
│   ├── database.py       # SQLAlchemy engine & SQLite session management
│   ├── models.py         # Relational database models (DscIssue & DscPayment)
│   ├── schemas.py        # Pydantic schemas for data validation
│   ├── crud.py           # Database queries, updates, and live aggregations
│   ├── export.py         # Excel (.xlsx) and CSV generators with styling
│   └── seed_data.py      # Khammam 20 mandals list & realistic starter data
├── static/
│   ├── css/
│   │   └── style.css     # Custom animations, badges, typography, print styles
│   └── js/
│       └── app.js        # Vue 3 reactive dashboard logic & API integration
├── templates/
│   └── index.html        # Responsive single-page dashboard with Tailwind CSS & Lucide icons
├── main.py               # FastAPI backend entry point & RESTful API routes
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
└── README.md             # Documentation
```

---

## 🗄️ Database Schema

### Table 1: `dsc_issues`
| Field | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment unique ID |
| `token_given_date` | Date | Date token was handed over (defaults to today) |
| `mandal_name` | String(100) | Mandal name (indexed) |
| `gram_panchayat_name` | String(150) | Gram Panchayat name (indexed) |
| `recipient_name` | String(150) | Person who collected/took the token |
| `designation` | String(100) | Designation (Panchayat Secretary, Sarpanch, etc.) |
| `phone_number` | String(20) | Mobile number of the recipient |
| `token_variant` | String(20) | Variant: strictly `"HYP"` or `"Proxkey"` |
| `dsc_count` | Integer | Number of DSCs/keys issued (default `1`) |
| `unit_price` | Float | Rate per DSC key in ₹ (default `1500.0`) |
| `total_amount` | Float | Calculated as `dsc_count * unit_price` |
| `remarks` | Text | Optional notes, validity, USB serial number |
| `created_at` | DateTime | Timestamp of record creation |
| `updated_at` | DateTime | Timestamp of last modification |

### Table 2: `dsc_payments`
| Field | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment unique payment ID |
| `issue_id` | Integer (FK) | References `dsc_issues.id` (`ON DELETE CASCADE`) |
| `payment_date` | Date | Exact date this part-payment installment was received |
| `amount_paid` | Float | Amount received in ₹ |
| `payment_mode` | String(50) | `"Cash"`, `"UPI / PhonePe / GPay"`, `"Bank Transfer"`, `"Cheque"` |
| `payment_note` | String(255) | Optional reference or note (e.g. "PhonePe Txn 48210") |
| `created_at` | DateTime | Timestamp when payment was logged |

---

## 🚀 Installation & Running Instructions

### 1. Prerequisites
- Python 3.9 or higher (tested on Python 3.12)
- `pip` package manager

### 2. Setup Virtual Environment (Recommended)

**Windows (PowerShell):**
```powershell
# Navigate to project folder
cd "e:\Google Antigravity\Token_Distrubution"

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Configure Environment Variables
You can copy `.env.example` to `.env` or set environment variables directly:
```bash
# Optional: Change Admin PIN (defaults to 1234)
# Windows PowerShell:
$env:ADMIN_PIN="2024"

# Linux / macOS:
export ADMIN_PIN="2024"
```

### 5. Start the Web Server
```bash
python main.py
```
*Or using uvicorn directly:*
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 6. Access the Application
Open your web browser and navigate to:
```
http://127.0.0.1:8000
```
- **Default Admin PIN:** `1234`

---

## 📡 RESTful API Endpoints

### Authentication
- `POST /api/auth/verify`: Verifies Admin PIN and issues authorization token.

### Metadata & Autocomplete
- `GET /api/metadata/mandals`: Returns all Khammam rural mandals + any user-added custom mandals.
- `GET /api/metadata/gps?mandal={mandal_name}`: Returns existing Gram Panchayat names under the selected mandal for autocomplete suggestions.
- `GET /api/metadata/designations`: Returns standard designation options.

### DSC Distribution Records
- `GET /api/issues`: List DSC records with query parameters (`mandal`, `variant`, `status`, `search`, `from_date`, `to_date`).
- `GET /api/issues/{id}`: Detailed issue record including all date-wise installment payments.
- `POST /api/issues`: Create new DSC handover record (optionally records initial payment).
- `PUT /api/issues/{id}`: Update handover record details.
- `DELETE /api/issues/{id}`: Delete record and cascading payments.

### Date-Wise Payments
- `POST /api/issues/{id}/payments`: Record a date-wise part payment against a DSC issue.
- `DELETE /api/payments/{id}`: Delete an installment payment (automatically recalculates balance).

### Analytics & Reporting
- `GET /api/analytics/stats`: Real-time KPI summary (counts, HYP/Proxkey split, billed, collected, balance, status breakdown).
- `GET /api/analytics/mandals`: Mandal-wise abstract table with recovery rates.

### Data Export
- `GET /api/export/excel`: Download multi-sheet Excel file (`.xlsx`) with styling and formulas.
- `GET /api/export/csv`: Download UTF-8 CSV register.
