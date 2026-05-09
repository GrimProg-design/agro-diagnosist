"""
АгроДиагност — DiseaseRepository.

Encapsulates all database queries related to Disease and Crop models.
"""
from __future__ import annotations

from typing import Optional

from apps.diagnosis.models import Crop, Disease


class DiseaseRepository:
    """
    Data-access layer for disease lookups.

    All ORM queries are centralised here so that the service layer
    remains free of database-specific concerns.
    """

    def get_crop_by_code(self, code: str) -> Optional[Crop]:
        """Return a Crop instance by its unique code, or None."""
        try:
            return Crop.objects.get(code=code)
        except Crop.DoesNotExist:
            return None

    def get_by_crop(self, crop: Crop) -> list[Disease]:
        """Return all diseases linked to the given crop."""
        return list(Disease.objects.filter(crop=crop).order_by("name"))

    def find_best_match(
        self,
        crop: Crop,
        extracted_symptoms: dict[str, bool],
    ) -> Optional[Disease]:
        """
        Return the Disease with the highest match_score for the given
        symptom profile, or None if no diseases are registered for the crop.

        Args:
            crop: The crop whose disease catalogue is searched.
            extracted_symptoms: Mapping of symptom key → bool from ImageAnalyzer.

        Returns:
            The best-matching Disease instance or None.
        """
        diseases = self.get_by_crop(crop)
        if not diseases:
            return None

        # return max(diseases, key=lambda d: d.match_score(extracted_symptoms))
        return max(
            diseases,
            key=lambda d: (
                d.match_score(extracted_symptoms),
                len(d.symptoms),
            ),
        )
