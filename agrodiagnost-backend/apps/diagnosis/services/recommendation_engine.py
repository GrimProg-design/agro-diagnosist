"""
АгроДиагност — RecommendationEngine service.

Formats the DiagnosisResult into the final JSON payload expected
by the frontend.
"""
from __future__ import annotations

from datetime import datetime, timezone

from apps.diagnosis.services.diagnosis_engine import DiagnosisResult


class RecommendationEngine:
    """
    Transforms a DiagnosisResult into the response dict that is sent
    back to the frontend.

    Responsibilities:
      - Format recommendations list.
      - Assemble the final response payload.
      - Inject metadata (crop type, timestamp).
    """

    def build_response(
        self,
        result: DiagnosisResult,
        crop_type: str,
    ) -> dict:
        """
        Build the JSON-serialisable response dict.

        Args:
            result:    Completed DiagnosisResult from DiagnosisEngine.
            crop_type: The crop code string as received from the frontend.

        Returns:
            Dict matching the frontend contract:
            {
              "success": true,
              "data": { ... }
            }
        """
        disease = result.disease

        return {
            "success": True,
            "data": {
                "diagnosis":       disease.name,
                "confidence":      result.confidence,
                "severity":        disease.severity,
                "symptoms":        result.symptoms,
                "recommendations": self._format_recommendations(disease.recommendations),
                "cropType":        crop_type,
                "analyzedAt":      datetime.now(tz=timezone.utc).isoformat(),
            },
        }

    def build_error_response(self, message: str) -> dict:
        """Return a standardised error payload."""
        return {
            "success": False,
            "error":   message,
        }

    # ── Private helpers ───────────────────────────────────────────────

    @staticmethod
    def _format_recommendations(raw: list) -> list[str]:
        """Ensure each recommendation is a clean, non-empty string."""
        return [str(r).strip() for r in (raw or []) if str(r).strip()]
