import datetime
from sqlalchemy.orm import Session
from backend.models import DscIssue, DscPayment, DscStock

KHAMMAM_MANDALS = [
    "Bonakal",
    "Chinthakani",
    "Enkoor",
    "Kalluru",
    "Kamepalli",
    "Khammam Rural",
    "Konijerla",
    "Kusumanchi",
    "Madhira",
    "Mudigonda",
    "Nelakondapalli",
    "Penuballi",
    "Raghunadhapalem",
    "Sathupalli",
    "Singareni",
    "Thallada",
    "Tirumalayapalem",
    "Vemsoor",
    "Wyra",
    "Yerrupalem",
]

DEFAULT_DESIGNATIONS = [
    "Panchayat Secretary",
    "Sarpanch",
    "Junior Assistant / GPEO",
    "Computer Operator",
    "Other",
]


def seed_initial_data_if_empty(db: Session):
    # No dummy data - real user data only
    pass
