"""
АгроДиагност — unit and integration tests.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.diagnosis.models import Crop, Disease
from apps.diagnosis.repositories.disease_repository import DiseaseRepository
from apps.diagnosis.services.diagnosis_engine import DiagnosisEngine
from apps.diagnosis.services.recommendation_engine import RecommendationEngine

from django.core.files.uploadedfile import SimpleUploadedFile


# ── Model tests ────────────────────────────────────────────────────────────

class DiseaseMatchScoreTest(TestCase):
    def setUp(self) -> None:
        self.crop = Crop.objects.create(name="Картофель", code="potato")
        self.disease = Disease.objects.create(
            name="Фитофтороз",
            crop=self.crop,
            symptoms=["yellowing", "dark_spots", "deformation"],
            symptom_labels=["Пожелтение", "Тёмные пятна", "Деформация"],
            recommendations=["Обработать фунгицидом"],
            severity="high",
        )

    def test_full_match_returns_one(self) -> None:
        score = self.disease.match_score(
            {"yellowing": True, "dark_spots": True, "deformation": True}
        )
        self.assertAlmostEqual(score, 1.0)

    def test_partial_match(self) -> None:
        score = self.disease.match_score(
            {"yellowing": True, "dark_spots": False, "deformation": False}
        )
        self.assertAlmostEqual(score, 1 / 3)

    def test_no_match_returns_zero(self) -> None:
        score = self.disease.match_score(
            {"yellowing": False, "dark_spots": False, "deformation": False}
        )
        self.assertAlmostEqual(score, 0.0)

    def test_empty_symptoms_returns_zero(self) -> None:
        self.disease.symptoms = []
        score = self.disease.match_score({"yellowing": True})
        self.assertEqual(score, 0.0)


# ── Repository tests ───────────────────────────────────────────────────────

class DiseaseRepositoryTest(TestCase):
    def setUp(self) -> None:
        self.crop = Crop.objects.create(name="Картофель", code="potato")
        Disease.objects.create(
            name="Фитофтороз",
            crop=self.crop,
            symptoms=["yellowing", "dark_spots"],
            symptom_labels=["Пожелтение", "Тёмные пятна"],
            recommendations=[],
            severity="high",
        )
        Disease.objects.create(
            name="Альтернариоз",
            crop=self.crop,
            symptoms=["dark_spots"],
            symptom_labels=["Пятна"],
            recommendations=[],
            severity="medium",
        )
        self.repo = DiseaseRepository()

    def test_get_by_crop_returns_all(self) -> None:
        diseases = self.repo.get_by_crop(self.crop)
        self.assertEqual(len(diseases), 2)

    def test_find_best_match_selects_highest_score(self) -> None:
        symptoms = {"yellowing": True, "dark_spots": True, "deformation": False}
        best = self.repo.find_best_match(self.crop, symptoms)
        self.assertEqual(best.name, "Фитофтороз")

    def test_get_crop_by_code_missing(self) -> None:
        result = self.repo.get_crop_by_code("nonexistent")
        self.assertIsNone(result)


# ── DiagnosisEngine tests ──────────────────────────────────────────────────

class DiagnosisEngineTest(TestCase):
    def setUp(self) -> None:
        self.crop = Crop.objects.create(name="Картофель", code="potato")
        Disease.objects.create(
            name="Фитофтороз",
            crop=self.crop,
            symptoms=["yellowing", "dark_spots"],
            symptom_labels=["Пожелтение", "Тёмные пятна"],
            recommendations=["Обработать фунгицидом"],
            severity="high",
        )
        self.engine = DiagnosisEngine()

    def test_run_returns_result(self) -> None:
        result = self.engine.run("potato", {"yellowing": True, "dark_spots": True, "deformation": False})
        self.assertIsNotNone(result)
        self.assertEqual(result.disease.name, "Фитофтороз")

    def test_run_unknown_crop_returns_none(self) -> None:
        result = self.engine.run("unknown_crop", {"yellowing": True})
        self.assertIsNone(result)

    def test_confidence_within_bounds(self) -> None:
        result = self.engine.run("potato", {"yellowing": True, "dark_spots": True})
        self.assertGreaterEqual(result.confidence, 55)
        self.assertLessEqual(result.confidence, 97)


# ── RecommendationEngine tests ─────────────────────────────────────────────

class RecommendationEngineTest(TestCase):
    def test_build_response_structure(self) -> None:
        crop = Crop(name="Картофель", code="potato")
        disease = Disease(
            name="Фитофтороз",
            crop=crop,
            severity="high",
            recommendations=["Обработать фунгицидом", "Удалить листья"],
        )
        from apps.diagnosis.services.diagnosis_engine import DiagnosisResult
        result = DiagnosisResult(disease=disease, confidence=87, symptoms=["Пожелтение"])

        engine = RecommendationEngine()
        response = engine.build_response(result, "potato")

        self.assertTrue(response["success"])
        data = response["data"]
        self.assertEqual(data["diagnosis"], "Фитофтороз")
        self.assertEqual(data["confidence"], 87)
        self.assertEqual(data["severity"], "high")
        self.assertEqual(data["cropType"], "potato")
        self.assertIn("analyzedAt", data)

    def test_build_error_response(self) -> None:
        engine = RecommendationEngine()
        resp = engine.build_error_response("Ошибка теста")
        self.assertFalse(resp["success"])
        self.assertEqual(resp["error"], "Ошибка теста")


# ── API integration test ───────────────────────────────────────────────────

class DiagnosisAPITest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.crop = Crop.objects.create(name="Картофель", code="potato")
        Disease.objects.create(
            name="Фитофтороз",
            crop=self.crop,
            symptoms=["yellowing", "dark_spots"],
            symptom_labels=["Пожелтение", "Тёмные пятна"],
            recommendations=["Обработать фунгицидом"],
            severity="high",
        )

    def test_missing_fields_returns_400(self) -> None:
        response = self.client.post("/api/v1/diagnosis/", data={}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("apps.diagnosis.views.ImageAnalyzer.analyze")
    def test_valid_request_returns_200(self, mock_analyze: MagicMock) -> None:
        mock_analyze.return_value = {"yellowing": True, "dark_spots": True, "deformation": False}

        import io
        from PIL import Image as PILImage

        img_bytes = io.BytesIO()
        PILImage.new("RGB", (100, 100), color=(34, 139, 34)).save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        image_file = SimpleUploadedFile("leaf.jpg", img_bytes.getvalue(), content_type="image/jpeg")

        response = self.client.post(
            "/api/v1/diagnosis/",
            data={"image": image_file, "crop_type": "potato"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("diagnosis", data["data"])
        self.assertIn("confidence", data["data"])
        self.assertIn("recommendations", data["data"])

    @patch("apps.diagnosis.views.ImageAnalyzer.analyze")
    def test_nonplant_request_returns_422(self, mock_analyze: MagicMock) -> None:
        mock_analyze.return_value = {
            "plant_present": False,
            "healthy": False,
            "yellowing": False,
            "dark_spots": False,
            "deformation": False,
        }

        import io
        from PIL import Image as PILImage

        img_bytes = io.BytesIO()
        PILImage.new("RGB", (100, 100), color=(128, 128, 128)).save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        image_file = SimpleUploadedFile("not_plant.jpg", img_bytes.getvalue(), content_type="image/jpeg")

        response = self.client.post(
            "/api/v1/diagnosis/",
            data={"image": image_file, "crop_type": "potato"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Загрузите фотографию растения.")

    @patch("apps.diagnosis.views.ImageAnalyzer.analyze")
    def test_healthy_plant_returns_200(self, mock_analyze: MagicMock) -> None:
        mock_analyze.return_value = {
            "plant_present": True,
            "healthy": True,
            "yellowing": False,
            "dark_spots": False,
            "deformation": False,
        }

        import io
        from PIL import Image as PILImage

        img_bytes = io.BytesIO()
        PILImage.new("RGB", (100, 100), color=(34, 139, 34)).save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        image_file = SimpleUploadedFile("healthy_leaf.jpg", img_bytes.getvalue(), content_type="image/jpeg")

        response = self.client.post(
            "/api/v1/diagnosis/",
            data={"image": image_file, "crop_type": "potato"},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["diagnosis"], "Растение полностью здорово")
        self.assertEqual(data["data"]["severity"], "low")
        self.assertEqual(data["data"]["cropType"], "potato")
