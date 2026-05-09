"""
АгроДиагност — API views.

Single endpoint: POST /api/v1/diagnosis/
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.diagnosis.serializers import DiagnosisRequestSerializer
from apps.diagnosis.services.diagnosis_engine import DiagnosisEngine
from apps.diagnosis.services.image_analyzer import ImageAnalyzer
from apps.diagnosis.services.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)


class DiagnosisView(APIView):
    """
    Receive a plant image + crop type, run the full analysis pipeline,
    and return a structured diagnosis.

    POST /api/v1/diagnosis/
    Content-Type: multipart/form-data
    Fields: image (file), crop_type (string)
    """

    parser_classes = [MultiPartParser]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._analyzer    = ImageAnalyzer()
        self._engine      = DiagnosisEngine()
        self._recommender = RecommendationEngine()

    def post(self, request: Request) -> Response:
        serializer = DiagnosisRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        image_file = serializer.validated_data["image"]
        crop_type  = serializer.validated_data["crop_type"]

        try:
            symptoms = self._run_image_analysis(image_file)

            if not symptoms.get("plant_present", True):
                return Response(
                    self._recommender.build_error_response(
                        "Загрузите фотографию растения."
                    ),
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            if symptoms.get("healthy"):
                return Response(
                    self._recommender.build_healthy_response(crop_type),
                    status=status.HTTP_200_OK,
                )

            result = self._engine.run(crop_type, symptoms)
            if result is None:
                return Response(
                    self._recommender.build_error_response(
                        "Не удалось определить диагноз. Проверьте изображение и попробуйте снова."
                    ),
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            response_data = self._recommender.build_response(result, crop_type)
            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as exc:
            logger.warning("Image analysis failed: %s", exc)
            return Response(
                self._recommender.build_error_response("Не удалось обработать изображение."),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Unexpected error during diagnosis: %s", exc)
            return Response(
                self._recommender.build_error_response("Внутренняя ошибка сервера."),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ── Private ───────────────────────────────────────────────────────

    def _run_image_analysis(self, image_file) -> dict[str, bool]:
        """
        Save the uploaded file to a temp path, run ImageAnalyzer, clean up.
        """
        suffix = Path(image_file.name).suffix or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            for chunk in image_file.chunks():
                tmp.write(chunk)
            tmp_path = Path(tmp.name)

        try:
            return self._analyzer.analyze(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)
