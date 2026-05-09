"""
АгроДиагност — database models.

Crop  →  Disease  (one-to-many)
"""
from __future__ import annotations

from typing import List

from django.db import models


class Crop(models.Model):
    """Represents an agricultural crop type."""

    name = models.CharField(max_length=120, verbose_name="Название культуры")
    code = models.SlugField(max_length=60, unique=True, verbose_name="Код культуры")

    class Meta:
        verbose_name = "Культура"
        verbose_name_plural = "Культуры"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Disease(models.Model):
    """Represents a plant disease associated with a specific crop."""

    class Severity(models.TextChoices):
        LOW    = "low",    "Низкая"
        MEDIUM = "medium", "Умеренная"
        HIGH   = "high",   "Высокая"

    name            = models.CharField(max_length=200, verbose_name="Название болезни")
    crop            = models.ForeignKey(
        Crop,
        on_delete=models.CASCADE,
        related_name="diseases",
        verbose_name="Культура",
    )
    symptoms        = models.JSONField(
        default=list,
        verbose_name="Симптомы",
        help_text="Список ключей симптомов: yellowing, dark_spots, deformation, …",
    )
    symptom_labels  = models.JSONField(
        default=list,
        verbose_name="Метки симптомов (для отображения)",
        help_text="Читаемые названия симптомов на русском",
    )
    recommendations = models.JSONField(
        default=list,
        verbose_name="Рекомендации",
    )
    severity        = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MEDIUM,
        verbose_name="Уровень угрозы",
    )

    class Meta:
        verbose_name = "Болезнь"
        verbose_name_plural = "Болезни"
        ordering = ["crop", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.crop.name})"

    def match_score(self, extracted_symptoms: dict[str, bool]) -> float:
        """
        Calculate how well this disease matches the extracted symptom profile.

        Args:
            extracted_symptoms: dict mapping symptom keys to bool
                e.g. {"yellowing": True, "dark_spots": False, "deformation": True}

        Returns:
            A float in [0.0, 1.0] representing the match ratio.
        """
        if not self.symptoms:
            return 0.0

        matches = sum(
            1
            for symptom_key in self.symptoms
            if extracted_symptoms.get(symptom_key, False)
        )
        return matches / len(self.symptoms)
