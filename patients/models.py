from django.db import models
from django.core.validators import RegexValidator

class Provider(models.Model):
    name = models.CharField(max_length=255)
    npi = models.CharField(
        max_length=10,
        unique=True,
        validators=[RegexValidator(r'^\d{10}$', 'NPI must be 10 digits')]
    )

    def __str__(self):
        return f"{self.name} (NPI: {self.npi})"
    

class Patient(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    mrn = models.CharField(
        max_length=6,
        unique=True,
        validators=[RegexValidator(r'^\d{6}$', 'MRN must be 6 digits')]
    )
    primary_diagnosis = models.CharField(max_length=10)
    additional_diagnoses = models.JSONField(blank=True, null=True)
    medication_history = models.JSONField(blank=True, null=True)
    records_text = models.TextField(blank=True, null=True)

    provider = models.ForeignKey(
        Provider, on_delete=models.PROTECT, related_name='patients'
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} (MRN: {self.mrn})"
    
class Order(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='orders')
    medication_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order for {self.patient} - {self.medication_name}"

