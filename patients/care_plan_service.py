# patients/care_plan_service.py
import os
from openai import OpenAI
from django.conf import settings
from .models import Patient, Order


def generate_care_plan_text(patient: Patient, order: Order) -> str:
    """
    Generate care plan text using LLM based on patient data and order information.
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise Exception("OPENAI_API_KEY environment variable is not set")
    
    client = OpenAI(api_key=api_key)
    
    # Build patient information context
    additional_diagnoses_str = ', '.join(patient.additional_diagnoses) if patient.additional_diagnoses else "None"
    medication_history_str = ', '.join(patient.medication_history) if patient.medication_history else "None"
    
    # Construct prompt
    prompt = f"""You are a clinical pharmacist generating a comprehensive care plan for a patient. 
Generate a detailed care plan following this exact structure:

**Problem list / Drug therapy problems (DTPs)**
[List the key problems and drug therapy issues]

**Goals (SMART)**
[Primary goals, Safety goals, Process goals - make them Specific, Measurable, Achievable, Relevant, Time-bound]

**Pharmacist interventions / plan**
Include detailed sections for:
- Dosing & Administration
- Premedication
- Infusion rates & titration
- Hydration & renal protection
- Thrombosis risk mitigation
- Concomitant medications
- Monitoring during infusion
- Adverse event management
- Documentation & communication

**Monitoring plan & lab schedule**
[Pre-infusion, during infusion, post-infusion monitoring requirements]

Use the following patient information:

PATIENT INFORMATION:
- Name: {patient.first_name} {patient.last_name}
- MRN: {patient.mrn}
- Primary Diagnosis: {patient.primary_diagnosis}
- Additional Diagnoses: {additional_diagnoses_str}
- Medication: {order.medication_name}
- Medication History: {medication_history_str}
- Provider: {patient.provider.name} (NPI: {patient.provider.npi})

PATIENT RECORDS:
{patient.records_text if patient.records_text else "No additional patient records provided."}

Generate a detailed, clinically appropriate care plan for this patient receiving {order.medication_name}. 
Base your recommendations on standard clinical practice guidelines and the patient's specific information provided.
Make it comprehensive and actionable for clinical staff."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # or "gpt-4-turbo" or "gpt-3.5-turbo" for cost savings
            messages=[
                {"role": "system", "content": "You are an experienced clinical pharmacist specializing in specialty medications and care plan development."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        
        content = response.choices[0].message.content
        if not content:
            raise Exception("LLM returned empty response")
        
        return content
    except Exception as e:
        raise Exception(f"Failed to generate care plan: {str(e)}")


def format_care_plan_with_header(patient: Patient, order: Order, care_plan_text: str) -> str:
    """
    Format the care plan text with patient information header.
    Returns a formatted text string ready for download.
    """
    header = f"""
================================================================================
                        CLINICAL CARE PLAN
================================================================================

PATIENT INFORMATION
--------------------------------------------------------------------------------
Patient Name:       {patient.first_name} {patient.last_name}
MRN:                {patient.mrn}
Primary Diagnosis:  {patient.primary_diagnosis}
Medication:         {order.medication_name}
Provider:           {patient.provider.name} (NPI: {patient.provider.npi})
Order ID:           {order.id}
Date Generated:     {order.created_at.strftime('%B %d, %Y')}

"""
    
    if patient.additional_diagnoses:
        header += f"Additional Diagnoses:  {', '.join(patient.additional_diagnoses)}\n"
    if patient.medication_history:
        header += f"Medication History:   {', '.join(patient.medication_history)}\n"
    
    header += """
================================================================================
                           CARE PLAN
================================================================================

"""
    
    return header + care_plan_text

