# patients/api.py
from ninja import Router
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from django.http import JsonResponse
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
    # Collect all confirmation issues upfront
    confirmation_issues = {}
    
    # Check if provider already exists with same NPI
    existing_provider = Provider.objects.filter(npi=payload.provider_npi).first()
    provider_name_mismatch = False
    
    if existing_provider:
        # If provider exists, check if name matches
        if existing_provider.name.lower() != payload.referring_provider.lower():
            provider_name_mismatch = True
            if not payload.confirm_provider_name_mismatch:
                confirmation_issues['provider'] = {
                    "existing_name": existing_provider.name,
                    "submitted_name": payload.referring_provider,
                    "npi": payload.provider_npi
                }
    
    # Check if patient already exists by MRN
    existing_patient = Patient.objects.filter(mrn=payload.mrn).first()
    patient_name_mismatch = False
    
    if existing_patient:
        # If patient exists, check if names match
        if (existing_patient.first_name.lower() != payload.first_name.lower() or 
            existing_patient.last_name.lower() != payload.last_name.lower()):
            patient_name_mismatch = True
            if not payload.confirm_patient_name_mismatch:
                confirmation_issues['patient'] = {
                    "existing_name": f"{existing_patient.first_name} {existing_patient.last_name}",
                    "submitted_name": f"{payload.first_name} {payload.last_name}",
                    "mrn": payload.mrn
                }
    
    # If any confirmations are needed (patient/provider), return them together
    # Note: Order confirmation check happens AFTER patient/provider are confirmed
    if confirmation_issues:
        error_response = {
            "requires_confirmation": True,
            "issues": confirmation_issues
        }
        # Use JsonResponse directly for structured error responses
        return JsonResponse(error_response, status=422)
    
    # All patient/provider confirmations passed - proceed with creation
    
    # Handle provider
    if existing_provider:
        provider = existing_provider
        if provider_name_mismatch:
            provider.name = payload.referring_provider
            provider.save()
    else:
        provider = Provider.objects.create(
            npi=payload.provider_npi,
            name=payload.referring_provider
        )
    
    # Handle patient
    if existing_patient:
        patient = existing_patient
    else:
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
    
    # NOW check for existing order (after patient/provider are handled)
    existing_order = Order.objects.filter(
        patient=patient, 
        medication_name__iexact=payload.medication_name
    ).first()
    
    if existing_order and not payload.confirm_duplicate_order:
        # Require confirmation for duplicate order
        error_response = {
            "requires_confirmation": True,
            "issues": {
                "order": {
                    "medication_name": payload.medication_name,
                    "existing_order_id": existing_order.id
                }
            }
        }
        # Use JsonResponse directly for structured error responses
        return JsonResponse(error_response, status=422)
    
    # Create the new order
    order = Order.objects.create(
        patient=patient,
        medication_name=payload.medication_name
    )
    
    # Build success message
    warnings = []
    if provider_name_mismatch:
        warnings.append(f"⚠️ Provider name updated from existing entry.")
    if patient_name_mismatch:
        warnings.append(f"⚠️ Order created for existing patient.")
    if existing_order:
        warnings.append(f"⚠️ Duplicate order created for '{payload.medication_name}'.")
    
    if warnings:
        message = "Order created successfully. " + " ".join(warnings)
    else:
        message = "Patient and order created successfully."
    
    return PatientOrderOut(
        message=message,
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
