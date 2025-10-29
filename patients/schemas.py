# patients/schemas.py
from ninja import Schema
from typing import List, Optional

class ProviderIn(Schema):
    name: str
    npi: str

class ProviderOut(ProviderIn):
    id: int

class PatientIn(Schema):
    first_name: str
    last_name: str
    mrn: str
    primary_diagnosis: str
    provider_id: int
    additional_diagnoses: List[str] = []
    medication_history: List[str] = []
    records_text: str = ""


class PatientOut(PatientIn):
    id: int

class OrderIn(Schema):
    patient_id: int
    medication_name: str

class OrderOut(OrderIn):
    id: int
    warning: Optional[str] = None
