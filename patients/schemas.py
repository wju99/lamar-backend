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
    referring_provider: str
    provider_npi: str
    medication_name: str
    additional_diagnoses: List[str] = []
    medication_history: List[str] = []
    records_text: str = ""


class PatientOut(Schema):
    id: int
    first_name: str
    last_name: str
    mrn: str
    primary_diagnosis: str
    referring_provider: str
    provider_npi: str
    provider_id: int  # Keep for backward compatibility and direct database reference
    additional_diagnoses: List[str] = []
    medication_history: List[str] = []
    records_text: str = ""


class PatientOrderOut(Schema):
    message: str
    patient_id: int
    order_id: int

class OrderIn(Schema):
    patient_id: int
    medication_name: str

class OrderOut(OrderIn):
    id: int
    warning: Optional[str] = None
