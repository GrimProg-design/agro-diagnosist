"""
АгроДиагност — MaturityRecommendationEngine service.

Formats maturity analysis results into the JSON response for the frontend.
"""
from __future__ import annotations

from datetime import datetime, timezone

from apps.diagnosis.models import Maturity
from apps.diagnosis.services.maturity_analyzer import MaturityProfile


class MaturityRecommendationEngine:
    """
    Transforms a MaturityProfile into a response dict for the frontend.

    Responsibilities:
      - Get recommendations from the database based on maturity stage.
      - Assemble the final maturity response payload.
      - Inject metadata (crop type, timestamp).
    """

    # Stage display names
    STAGE_LABELS = {
        "immature": "Незрелое",
        "early": "Ранняя зрелость",
        "optimal": "Оптимальная зрелость",
        "overripe": "Перезрелое",
    }

    def build_response(
        self,
        profile: MaturityProfile,
        crop_type: str,
        maturity_obj: Maturity | None = None,
    ) -> dict:
        """
        Build the maturity response JSON.

        Args:
            profile: MaturityProfile from MaturityAnalyzer
            crop_type: Crop code string
            maturity_obj: Optional Maturity model instance for recommendations

        Returns:
            Dict with maturity analysis results
        """
        # Get recommendations from database if available
        recommendations = []
        if maturity_obj:
            recommendations = maturity_obj.get_stage_recommendation(profile["stage"])

        # Default recommendations if none in DB
        if not recommendations:
            recommendations = self._get_default_recommendations(profile["stage"])

        return {
            "success": True,
            "data": {
                "maturity_stage": profile["stage"],
                "stage_label": self.STAGE_LABELS.get(profile["stage"], profile["stage"]),
                "confidence": profile["confidence"],
                "maturity_indicators": {
                    "color_score": round(profile["color_score"], 2),
                    "texture_score": round(profile["texture_score"], 2),
                    "size_score": round(profile["size_score"], 2),
                    "yellow_ratio": round(profile["yellow_ratio"], 3),
                    "green_ratio": round(profile["green_ratio"], 3),
                },
                "status_message": self._get_status_message(profile),
                "recommendations": recommendations,
                "harvest_readiness": self._get_harvest_readiness(profile, maturity_obj),
                "care_tips": self._get_care_tips(profile),
                "cropType": crop_type,
                "analyzedAt": datetime.now(tz=timezone.utc).isoformat(),
            },
        }

    def build_error_response(self, message: str) -> dict:
        """Return a standardised error payload."""
        return {
            "success": False,
            "error": message,
        }

    # ── Private helpers ───────────────────────────────────────────────

    @staticmethod
    def _get_status_message(profile: MaturityProfile) -> str:
        """Get a human-readable status message."""
        stage = profile["stage"]
        confidence = profile["confidence"]

        if stage == "immature":
            return f"Растение еще не достигло зрелости (уверенность: {confidence}%)"
        elif stage == "early":
            return f"Растение в ранней стадии зрелости (уверенность: {confidence}%)"
        elif stage == "optimal":
            return f"Растение достигло оптимальной зрелости (уверенность: {confidence}%)"
        elif stage == "overripe":
            return f"Растение перезрелое (уверенность: {confidence}%)"
        else:
            return f"Неизвестная стадия зрелости: {stage}"

    @staticmethod
    def _get_harvest_readiness(profile: MaturityProfile, maturity_obj: Maturity | None) -> dict:
        """Get harvest readiness assessment."""
        stage = profile["stage"]
        color_score = profile["color_score"]

        readiness = {
            "immature": 0,
            "early": 30,
            "optimal": 95,
            "overripe": 60,
        }

        return {
            "ready": stage == "optimal",
            "percentage": readiness.get(stage, 0),
            "message": {
                "immature": "Растение не готово к уборке. Требуется дополнительное время для развития.",
                "early": "Растение близко к зрелости. Можно начинать подготовку к уборке.",
                "optimal": "Растение готово к уборке! Текущее время - оптимально для сбора.",
                "overripe": "Растение перезрелое. Урожайность может снизиться. Рекомендуется срочная уборка.",
            }.get(stage, "Неизвестное состояние"),
        }

    @staticmethod
    def _get_care_tips(profile: MaturityProfile) -> list[str]:
        """Get care tips based on maturity stage."""
        stage = profile["stage"]

        tips = {
            "immature": [
                "Убедитесь в достаточном поливе растения",
                "Внесите азотные удобрения для лучшего развития",
                "Защитите растение от вредителей на ранней стадии",
                "Регулярно проверяйте листья на признаки болезней",
            ],
            "early": [
                "Продолжайте регулярный полив",
                "Начните вносить калийные удобрения",
                "Подготавливайте оборудование для уборки",
                "Мониторьте погодные условия",
            ],
            "optimal": [
                "Растение готово к уборке при благоприятных условиях",
                "Завершите внесение удобрений",
                "Приготовьте оборудование для уборки",
                "Планируйте сбор урожая на ближайшие дни",
            ],
            "overripe": [
                "Срочно начните уборку во избежание потерь урожая",
                "Увеличьте скорость работы уборочного оборудования",
                "Проверьте влажность продукции для правильного хранения",
                "Готовьте хранилища для собранного урожая",
            ],
        }

        return tips.get(stage, [])

    @staticmethod
    def _get_default_recommendations(stage: str) -> list[str]:
        """Get default recommendations if not in database."""
        recommendations = {
            "immature": [
                "Продолжайте уход за растением согласно агротехнике",
                "Обеспечьте достаточное питание и полив",
                "Защищайте растение от болезней и вредителей",
            ],
            "early": [
                "Подготавливайте растение к созреванию",
                "Внесите калийные удобрения",
                "Мониторьте состояние влаги в почве",
            ],
            "optimal": [
                "Растение достигло оптимальной зрелости для сбора",
                "Планируйте уборку в ближайшие дни",
                "Проверьте условия хранения урожая",
            ],
            "overripe": [
                "Немедленно начните уборку",
                "Минимизируйте потери при сборке",
                "Обеспечьте правильное хранение урожая",
            ],
        }

        return recommendations.get(stage, ["Проверьте состояние растения"])
