# patients/api.py
from ninja import Router
from django.shortcuts import get_object_or_404
from .models import Provider, Patient, Order
from .schemas import ProviderIn, ProviderOut, PatientIn, PatientOut, OrderIn, OrderOut

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
@router.post("/patients", response=PatientOut)
@router.post("/patients/", response=PatientOut)  # Handle trailing slash
def create_patient(request, payload: PatientIn):
    provider = get_object_or_404(Provider, id=payload.provider_id)
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
    return patient

@router.get("/patients", response=list[PatientOut])
@router.get("/patients/", response=list[PatientOut])  # Handle trailing slash
def list_patients(request):
    return Patient.objects.all()


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
