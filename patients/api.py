# patients/api.py
from ninja import Router
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from ninja.errors import HttpError
from .models import Provider, Patient, Order
from .schemas import ProviderIn, ProviderOut, PatientIn, PatientOut, OrderIn, OrderOut, PatientOrderOut

router = Router(tags=["Lamar API"])

# ---------- PROVIDERS ----------
@router.post("/providers", response=ProviderOut)
def create_provider(request, payload: ProviderIn):
    provider, _ = Provider.objects.get_or_create(**payload.dict())
    return provider

@router.get("/providers", response=list[ProviderOut])
def list_providers(request):
    return Provider.objects.all()


# ---------- PATIENTS ----------
@router.post("/patients", response=PatientOrderOut)
def create_patient(request, payload: PatientIn):
    # Get or create the provider using name and NPI
    provider, _ = Provider.objects.get_or_create(
        npi=payload.provider_npi,
        defaults={'name': payload.referring_provider}
    )
    # Update provider name if it changed (handles case where provider exists with different name)
    if provider.name != payload.referring_provider:
        provider.name = payload.referring_provider
        provider.save()
    
    # Check if MRN already exists before creating patient
    if Patient.objects.filter(mrn=payload.mrn).exists():
        raise HttpError(
            400,
            f"Duplicate MRN: A patient with MRN '{payload.mrn}' already exists. Please use a unique MRN."
        )
    
    try:
        patient = Patient.objects.create(
            first_name=payload.first_name,
            last_name=payload.last_name,
            mrn=payload.mrn,
            primary_diagnosis=payload.primary_diagnosis,
            additional_diagnoses=payload.additional_diagnoses,
            medication_history=payload.medication_history,
            records_text=payload.records_text,
            provider=provider,
        )
    except IntegrityError as e:
        # Catch any other integrity errors (e.g., unique constraints)
        error_msg = str(e)
        if 'mrn' in error_msg.lower() or 'unique' in error_msg.lower():
            raise HttpError(
                400,
                f"Duplicate MRN: A patient with MRN '{payload.mrn}' already exists. Please use a unique MRN."
            )
        raise HttpError(400, f"Database error: {error_msg}")
    
    # Check for existing similar orders and create new order
    existing = Order.objects.filter(
        patient=patient, medication_name__iexact=payload.medication_name
    )
    warning = None
    if existing.exists():
        warning = f"⚠️ Similar order for '{payload.medication_name}' already exists for this patient."
    
    order = Order.objects.create(
        patient=patient,
        medication_name=payload.medication_name
    )
    
    return PatientOrderOut(
        message="Patient and order created successfully" + (f". {warning}" if warning else ""),
        patient_id=patient.id,
        order_id=order.id,
    )

@router.get("/patients", response=list[PatientOut])
def list_patients(request):
    patients = Patient.objects.all()
    return [
        PatientOut(
            id=p.id,
            first_name=p.first_name,
            last_name=p.last_name,
            mrn=p.mrn,
            primary_diagnosis=p.primary_diagnosis,
            referring_provider=p.provider.name,
            provider_npi=p.provider.npi,
            provider_id=p.provider.id,
            additional_diagnoses=p.additional_diagnoses or [],
            medication_history=p.medication_history or [],
            records_text=p.records_text or "",
        )
        for p in patients
    ]


# ---------- ORDERS ----------
@router.post("/orders", response=OrderOut)
def create_order(request, payload: OrderIn):
    patient = get_object_or_404(Patient, id=payload.patient_id)
    existing = Order.objects.filter(
        patient=patient, medication_name__iexact=payload.medication_name
    )
    warning = None
    if existing.exists():
        warning = f"⚠️ Similar order for '{payload.medication_name}' already exists for this patient."
    order = Order.objects.create(patient=patient, medication_name=payload.medication_name)
    return OrderOut(
        id=order.id,
        patient_id=patient.id,
        medication_name=order.medication_name,
        warning=warning
    )

@router.get("/orders", response=list[OrderOut])
def list_orders(request):
    orders = Order.objects.all()
    return [
        OrderOut(
            id=o.id,
            patient_id=o.patient.id,
            medication_name=o.medication_name,
            warning=None
        )
        for o in orders
    ]
