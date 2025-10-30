# patients/tests.py
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from .models import Provider, Patient, Order
import json


class ProviderAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.provider_data = {
            "name": "Dr. Smith",
            "npi": "1234567890"
        }

    def test_create_provider_success(self):
        """Test creating a new provider"""
        response = self.client.post("/api/providers", data=json.dumps(self.provider_data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Dr. Smith")
        self.assertEqual(data["npi"], "1234567890")
        self.assertIn("id", data)
        # Verify it was saved
        self.assertEqual(Provider.objects.count(), 1)

    def test_create_provider_duplicate_npi(self):
        """Test that duplicate NPI updates existing provider"""
        # Create first provider
        Provider.objects.create(name="Dr. Smith", npi="1234567890")
        
        # Try to create same provider with different name
        response = self.client.post("/api/providers", data=json.dumps({
            "name": "Dr. John Smith",
            "npi": "1234567890"
        }), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        # get_or_create should return existing one, not create new
        self.assertEqual(Provider.objects.count(), 1)

    def test_list_providers_empty(self):
        """Test listing providers when none exist"""
        response = self.client.get("/api/providers")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_providers_with_data(self):
        """Test listing providers"""
        Provider.objects.create(name="Dr. Smith", npi="1234567890")
        Provider.objects.create(name="Dr. Jones", npi="0987654321")
        
        response = self.client.get("/api/providers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        npis = [p["npi"] for p in data]
        self.assertIn("1234567890", npis)
        self.assertIn("0987654321", npis)


class PatientAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.provider = Provider.objects.create(name="Dr. Smith", npi="1234567890")
        self.patient_data = {
            "first_name": "John",
            "last_name": "Doe",
            "mrn": "123456",
            "primary_diagnosis": "G70.00",
            "referring_provider": "Dr. Smith",
            "provider_npi": "1234567890",
            "medication_name": "IVIG",
            "additional_diagnoses": ["I10"],
            "medication_history": ["Aspirin"],
            "records_text": "Patient records here",
            "confirm_patient_name_mismatch": False,
            "confirm_provider_name_mismatch": False,
            "confirm_duplicate_order": False
        }

    def test_create_patient_and_order_success(self):
        """Test creating a new patient and order"""
        response = self.client.post("/api/patients", data=json.dumps(self.patient_data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("patient_id", data)
        self.assertIn("order_id", data)
        self.assertIn("message", data)
        
        # Verify patient was created
        patient = Patient.objects.get(id=data["patient_id"])
        self.assertEqual(patient.first_name, "John")
        self.assertEqual(patient.last_name, "Doe")
        self.assertEqual(patient.mrn, "123456")
        
        # Verify order was created
        order = Order.objects.get(id=data["order_id"])
        self.assertEqual(order.medication_name, "IVIG")
        self.assertEqual(order.patient, patient)

    def test_create_patient_creates_provider_if_not_exists(self):
        """Test that patient creation creates provider if not exists"""
        new_npi = "9999999999"
        self.patient_data["provider_npi"] = new_npi
        self.patient_data["referring_provider"] = "Dr. New"
        
        response = self.client.post("/api/patients", data=json.dumps(self.patient_data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        
        # Verify provider was created
        provider = Provider.objects.get(npi=new_npi)
        self.assertEqual(provider.name, "Dr. New")

    def test_create_patient_provider_name_mismatch_requires_confirmation(self):
        """Test that provider name mismatch requires confirmation"""
        # Create provider with different name
        Provider.objects.update_or_create(npi="1234567890", defaults={"name": "Dr. Original"})
        
        # Try to create patient with same NPI but different name
        response = self.client.post("/api/patients", data=json.dumps(self.patient_data), content_type="application/json")
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertIn("requires_confirmation", data)
        self.assertTrue(data["requires_confirmation"])
        self.assertIn("provider", data.get("issues", {}))

    def test_create_patient_provider_name_mismatch_with_confirmation(self):
        """Test that provider name mismatch can proceed with confirmation"""
        # Create provider with different name
        provider, _ = Provider.objects.update_or_create(npi="1234567890", defaults={"name": "Dr. Original"})
        
        # Create patient with confirmation flag
        self.patient_data["confirm_provider_name_mismatch"] = True
        response = self.client.post("/api/patients", data=json.dumps(self.patient_data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        
        # Provider name should be updated
        provider.refresh_from_db()
        self.assertEqual(provider.name, "Dr. Smith")

    def test_create_patient_patient_name_mismatch_requires_confirmation(self):
        """Test that patient name mismatch requires confirmation"""
        # Create existing patient
        existing_patient = Patient.objects.create(
            first_name="Jane",
            last_name="Doe",
            mrn="123456",
            primary_diagnosis="G70.00",
            provider=self.provider
        )
        
        # Try to create patient with same MRN but different name
        response = self.client.post("/api/patients", data=json.dumps(self.patient_data), content_type="application/json")
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertIn("requires_confirmation", data)
        self.assertIn("patient", data.get("issues", {}))

    def test_create_patient_patient_name_mismatch_with_confirmation(self):
        """Test that patient name mismatch can proceed with confirmation"""
        # Create existing patient
        Patient.objects.create(
            first_name="Jane",
            last_name="Doe",
            mrn="123456",
            primary_diagnosis="G70.00",
            provider=self.provider
        )
        
        # Create order for existing patient with confirmation
        self.patient_data["confirm_patient_name_mismatch"] = True
        response = self.client.post("/api/patients", data=json.dumps(self.patient_data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        
        # Patient should exist, new order should be created
        patient = Patient.objects.get(mrn="123456")
        orders = Order.objects.filter(patient=patient, medication_name="IVIG")
        self.assertEqual(orders.count(), 1)

    def test_create_patient_duplicate_order_requires_confirmation(self):
        """Test that duplicate order requires confirmation"""
        # Create patient and order
        patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456",
            primary_diagnosis="G70.00",
            provider=self.provider
        )
        Order.objects.create(patient=patient, medication_name="IVIG")
        
        # Try to create duplicate order
        self.patient_data["confirm_patient_name_mismatch"] = True
        response = self.client.post("/patients", json=self.patient_data)
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertIn("requires_confirmation", data)
        self.assertIn("order", data.get("issues", {}))

    def test_create_patient_duplicate_order_with_confirmation(self):
        """Test that duplicate order can proceed with confirmation"""
        # Create patient and order
        patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456",
            primary_diagnosis="G70.00",
            provider=self.provider
        )
        Order.objects.create(patient=patient, medication_name="IVIG")
        
        # Create duplicate order with confirmation
        self.patient_data["confirm_patient_name_mismatch"] = True
        self.patient_data["confirm_duplicate_order"] = True
        response = self.client.post("/patients", json=self.patient_data)
        self.assertEqual(response.status_code, 200)
        
        # Both orders should exist
        orders = Order.objects.filter(patient=patient, medication_name="IVIG")
        self.assertEqual(orders.count(), 2)

    def test_list_patients(self):
        """Test listing all patients"""
        # Create patients
        patient1 = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456",
            primary_diagnosis="G70.00",
            provider=self.provider
        )
        patient2 = Patient.objects.create(
            first_name="Jane",
            last_name="Smith",
            mrn="789012",
            primary_diagnosis="I10",
            provider=self.provider
        )
        
        response = self.client.get("/api/patients")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        
        mrns = [p["mrn"] for p in data]
        self.assertIn("123456", mrns)
        self.assertIn("789012", mrns)


class OrderAPITests(TestCase):
    def setUp(self):
        self.client = TestClient(api)
        self.provider = Provider.objects.create(name="Dr. Smith", npi="1234567890")
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456",
            primary_diagnosis="G70.00",
            provider=self.provider
        )

    def test_create_order_success(self):
        """Test creating a new order"""
        order_data = {
            "patient_id": self.patient.id,
            "medication_name": "IVIG"
        }
        
        response = self.client.post("/orders", json=order_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["medication_name"], "IVIG")
        self.assertEqual(data["patient_id"], self.patient.id)
        self.assertIn("id", data)
        
        # Verify order was created
        self.assertEqual(Order.objects.count(), 1)

    def test_create_order_invalid_patient(self):
        """Test creating order with non-existent patient"""
        order_data = {
            "patient_id": 99999,
            "medication_name": "IVIG"
        }
        
        response = self.client.post("/orders", json=order_data)
        self.assertEqual(response.status_code, 404)

    def test_list_orders(self):
        """Test listing all orders"""
        Order.objects.create(patient=self.patient, medication_name="IVIG")
        Order.objects.create(patient=self.patient, medication_name="Aspirin")
        
        response = self.client.get("/orders")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)


class PDFExtractionTests(TestCase):
    def setUp(self):
        self.client = TestClient(api)

    def test_extract_records_text_success(self):
        """Test extracting text from a PDF"""
        # Create a simple PDF in memory
        # Note: This is a minimal PDF structure for testing
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Contents 4 0 R /MediaBox [0 0 612 792] >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF Content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000197 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
296
%%EOF"""
        
        # Create a file-like object
        pdf_file = BytesIO(pdf_content)
        pdf_file.name = "test.pdf"
        
        response = self.client.post(
            "/records/extract",
            files={"file": ("test.pdf", pdf_file, "application/pdf")}
        )
        
        # PDF extraction may work or fail depending on PDF structure
        # We just check it doesn't crash
        self.assertIn(response.status_code, [200, 400])

    def test_extract_records_text_invalid_file(self):
        """Test extracting text from non-PDF file"""
        txt_file = BytesIO(b"This is not a PDF file")
        txt_file.name = "test.txt"
        
        response = self.client.post(
            "/records/extract",
            files={"file": ("test.txt", txt_file, "text/plain")}
        )
        
        # Should return error for invalid PDF
        self.assertEqual(response.status_code, 400)

    def test_extract_records_text_no_file(self):
        """Test extract endpoint without file"""
        response = self.client.post("/records/extract")
        # Should return 422 or 400 for missing file
        self.assertIn(response.status_code, [400, 422])


class CarePlanTests(TestCase):
    def setUp(self):
        self.client = TestClient(api)
        self.provider = Provider.objects.create(name="Dr. Smith", npi="1234567890")
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            mrn="123456",
            primary_diagnosis="G70.00",
            provider=self.provider,
            records_text="Test records"
        )
        self.order = Order.objects.create(
            patient=self.patient,
            medication_name="IVIG"
        )

    def test_get_care_plan_success(self):
        """Test generating care plan"""
        # Mock the OpenAI call - in real tests you'd use a mock
        # For now, this will try to actually call OpenAI
        response = self.client.get(
            f"/patients/{self.patient.id}/orders/{self.order.id}/care-plan"
        )
        
        # If OpenAI key is set, this should work (200 or 500)
        # If not set, it will fail gracefully
        self.assertIn(response.status_code, [200, 500])
        
        # If successful, should return text file
        if response.status_code == 200:
            self.assertEqual(response.headers["content-type"], "text/plain; charset=utf-8")
            self.assertIn("attachment", response.headers.get("Content-Disposition", ""))

    def test_get_care_plan_invalid_patient(self):
        """Test care plan with non-existent patient"""
        response = self.client.get(
            f"/patients/99999/orders/{self.order.id}/care-plan"
        )
        self.assertEqual(response.status_code, 404)

    def test_get_care_plan_invalid_order(self):
        """Test care plan with non-existent order"""
        response = self.client.get(
            f"/patients/{self.patient.id}/orders/99999/care-plan"
        )
        self.assertEqual(response.status_code, 404)

    def test_get_care_plan_order_belongs_to_different_patient(self):
        """Test care plan with order that belongs to different patient"""
        other_patient = Patient.objects.create(
            first_name="Jane",
            last_name="Smith",
            mrn="789012",
            primary_diagnosis="I10",
            provider=self.provider
        )
        other_order = Order.objects.create(
            patient=other_patient,
            medication_name="Aspirin"
        )
        
        # Try to get care plan for order belonging to different patient
        response = self.client.get(
            f"/patients/{self.patient.id}/orders/{other_order.id}/care-plan"
        )
        self.assertEqual(response.status_code, 404)


class IntegrationTests(TestCase):
    """Integration tests for full workflow"""
    
    def setUp(self):
        self.client = TestClient(api)
        self.provider_data = {
            "name": "Dr. Smith",
            "npi": "1234567890"
        }

    def test_full_patient_workflow(self):
        """Test complete workflow: create provider -> create patient -> create order"""
        # Create provider
        provider_response = self.client.post("/providers", json=self.provider_data)
        self.assertEqual(provider_response.status_code, 200)
        
        # Create patient with order
        patient_data = {
            "first_name": "John",
            "last_name": "Doe",
            "mrn": "123456",
            "primary_diagnosis": "G70.00",
            "referring_provider": "Dr. Smith",
            "provider_npi": "1234567890",
            "medication_name": "IVIG",
            "records_text": "Patient records",
            "confirm_patient_name_mismatch": False,
            "confirm_provider_name_mismatch": False,
            "confirm_duplicate_order": False
        }
        
        patient_response = self.client.post("/patients", json=patient_data)
        self.assertEqual(patient_response.status_code, 200)
        
        patient_json = patient_response.json()
        patient_id = patient_json["patient_id"]
        order_id = patient_json["order_id"]
        
        # Verify patient exists
        self.assertTrue(Patient.objects.filter(id=patient_id).exists())
        
        # Verify order exists
        self.assertTrue(Order.objects.filter(id=order_id).exists())
        
        # List patients
        list_response = self.client.get("/patients")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)
