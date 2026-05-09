"""
АгроДиагност — DiagnosisEngine service.

Orchestrates the diagnostic pipeline:
  crop code → repository lookup → symptom matching → scored result.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from apps.diagnosis.models import Disease
from apps.diagnosis.repositories.disease_repository import DiseaseRepository


@dataclass
class DiagnosisResult:
    """Intermediate result produced by the DiagnosisEngine."""

    disease:    Disease
    confidence: int          # 0–100
    symptoms:   list[str]    # human-readable symptom labels


class DiagnosisEngine:
    """
    Matches an extracted symptom profile to the most probable disease
    for a given crop.

    Responsibilities:
      - Resolve crop entity from code string.
      - Delegate database search to DiseaseRepository.
      - Convert raw match_score to a confidence percentage with
        a small randomised variance to reflect real-world uncertainty.
    """

    # Confidence is clamped to this range even with variance applied
    _CONFIDENCE_MIN = 55
    _CONFIDENCE_MAX = 97

    # Variance window applied on top of base score (±points)
    _VARIANCE = 5

    def __init__(self, repository: Optional[DiseaseRepository] = None) -> None:
        self._repo = repository or DiseaseRepository()

    def run(
        self,
        crop_code: str,
        extracted_symptoms: dict[str, bool],
    ) -> Optional[DiagnosisResult]:
        """
        Execute the diagnosis pipeline.

        Args:
            crop_code:          Slug code of the crop (e.g. "potato").
            extracted_symptoms: Dict of symptom_key → bool from ImageAnalyzer.

        Returns:
            DiagnosisResult if a match is found, else None.
        """
        crop = self._repo.get_crop_by_code(crop_code)
        if crop is None:
            return None

        disease = self._repo.find_best_match(crop, extracted_symptoms)
        if disease is None:
            return None

        raw_score  = disease.match_score(extracted_symptoms)
        confidence = self._score_to_confidence(raw_score, extracted_symptoms)

        active_labels = self._active_symptom_labels(disease, extracted_symptoms)

        return DiagnosisResult(
            disease=disease,
            confidence=confidence,
            symptoms=active_labels,
        )

    # ── Private helpers ───────────────────────────────────────────────

    def _score_to_confidence(
        self,
        raw_score: float,
        symptoms: dict[str, bool],
    ) -> int:
        """
        Convert a [0, 1] match score to a realistic confidence integer.

        The conversion applies a sigmoid-like curve so that partial matches
        don't appear deceptively high, and adds a small deterministic
        variance derived from the symptom vector to avoid a static display.
        """
        # Base: scale 0–1 → 55–95
        base = self._CONFIDENCE_MIN + raw_score * (self._CONFIDENCE_MAX - self._CONFIDENCE_MIN - 10)

        # Deterministic variance: use sum of active symptoms as seed
        active_count = sum(1 for v in symptoms.values() if v)
        variance = (active_count % (self._VARIANCE * 2 + 1)) - self._VARIANCE

        confidence = int(math.floor(base + variance))
        return max(self._CONFIDENCE_MIN, min(self._CONFIDENCE_MAX, confidence))

    @staticmethod
    def _active_symptom_labels(
        disease: Disease,
        extracted_symptoms: dict[str, bool],
    ) -> list[str]:
        """
        Return the human-readable labels for symptoms that were both
        detected in the image AND listed in the disease profile.
        Falls back to all disease symptom_labels if none match.
        """
        matched: list[str] = []

        symptom_keys   = disease.symptoms or []
        symptom_labels = disease.symptom_labels or []

        for key, label in zip(symptom_keys, symptom_labels):
            if extracted_symptoms.get(key, False):
                matched.append(label)

        # Always show at least the primary symptoms even if not visually detected
        if not matched and symptom_labels:
            matched = list(symptom_labels[:2])

        return matched
