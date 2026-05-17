"""
АгроДиагност — MaturityAnalyzer service.

Uses OpenCV image processing to analyze plant maturity indicators
such as color, size, and texture patterns specific to each crop type.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class MaturityProfile(TypedDict):
    """Результат анализа зрелости растения."""
    stage: str  # "immature", "early", "optimal", "overripe"
    confidence: int  # 0-100
    yellow_ratio: float  # Процент желтого цвета (для кукурузы)
    green_ratio: float  # Процент зеленого цвета
    color_score: float  # 0-1, индекс зрелости по цвету
    size_score: float  # 0-1, индекс зрелости по размеру
    texture_score: float  # 0-1, гладкость поверхности


class MaturityAnalyzer:
    """
    Анализирует изображение растения для определения уровня зрелости.
    Использует обработку цвета и текстуры для определения параметров зрелости.
    """

    # HSV диапазоны для определения цвета
    _GREEN_LOWER = np.array([25, 35, 35], dtype=np.uint8)
    _GREEN_UPPER = np.array([95, 255, 255], dtype=np.uint8)

    # Желтый для кукурузы
    _YELLOW_LOWER = np.array([18, 100, 100], dtype=np.uint8)
    _YELLOW_UPPER = np.array([32, 255, 255], dtype=np.uint8)

    # Оранжевый для других культур
    _ORANGE_LOWER = np.array([6, 100, 100], dtype=np.uint8)
    _ORANGE_UPPER = np.array([18, 255, 255], dtype=np.uint8)

    def __init__(self, resize_to: tuple[int, int] = (512, 512)) -> None:
        self._resize_to = resize_to

    def analyze(self, image_path: str | Path, crop_type: str = "corn") -> MaturityProfile:
        """
        Анализирует изображение и определяет уровень зрелости.

        Args:
            image_path: Path to the plant image
            crop_type: Type of crop (corn, wheat, etc.)

        Returns:
            MaturityProfile with maturity stage and confidence
        """
        bgr = self._load(image_path)

        # Получаем маску растения
        plant_mask = self._get_plant_mask(bgr)
        plant_pixels = int(np.count_nonzero(plant_mask))

        if plant_pixels < 1000:  # Недостаточно пикселей растения
            return self._build_profile("immature", 0, {})

        # Анализируем цвет
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        color_analysis = self._analyze_colors(hsv, plant_mask, crop_type)

        # Анализируем текстуру
        texture_score = self._analyze_texture(bgr, plant_mask)

        # Определяем размер (контуры)
        size_score = self._analyze_size(plant_mask)

        # Вычисляем общий индекс зрелости
        stage, confidence = self._determine_stage(
            color_analysis, texture_score, size_score, crop_type
        )

        return MaturityProfile(
            stage=stage,
            confidence=confidence,
            yellow_ratio=color_analysis.get("yellow_ratio", 0.0),
            green_ratio=color_analysis.get("green_ratio", 0.0),
            color_score=color_analysis.get("color_score", 0.0),
            size_score=size_score,
            texture_score=texture_score,
        )

    # ── Private methods ───────────────────────────────────────────────

    def _analyze_colors(
        self, hsv: np.ndarray, plant_mask: np.ndarray, crop_type: str
    ) -> dict:
        """Анализирует цветовой состав растения."""
        # Зеленый
        green_mask = cv2.inRange(hsv, self._GREEN_LOWER, self._GREEN_UPPER)
        green_mask = cv2.bitwise_and(green_mask, plant_mask)

        # Желтый
        yellow_mask = cv2.inRange(hsv, self._YELLOW_LOWER, self._YELLOW_UPPER)
        yellow_mask = cv2.bitwise_and(yellow_mask, plant_mask)

        # Оранжевый
        orange_mask = cv2.inRange(hsv, self._ORANGE_LOWER, self._ORANGE_UPPER)
        orange_mask = cv2.bitwise_and(orange_mask, plant_mask)

        plant_pixels = np.count_nonzero(plant_mask)
        green_pixels = np.count_nonzero(green_mask)
        yellow_pixels = np.count_nonzero(yellow_mask)
        orange_pixels = np.count_nonzero(orange_mask)

        green_ratio = green_pixels / plant_pixels if plant_pixels > 0 else 0
        yellow_ratio = yellow_pixels / plant_pixels if plant_pixels > 0 else 0
        orange_ratio = orange_pixels / plant_pixels if plant_pixels > 0 else 0

        # Цветовой индекс зрелости
        # Для кукурузы: больше желтого = более зрелое
        # Для пшеницы: золотистый цвет = зрелое
        if crop_type in ("corn", "кукуруза"):
            color_score = yellow_ratio
        else:
            color_score = (yellow_ratio + orange_ratio) / 2

        return {
            "green_ratio": float(green_ratio),
            "yellow_ratio": float(yellow_ratio),
            "orange_ratio": float(orange_ratio),
            "color_score": float(min(color_score, 1.0)),
        }

    def _analyze_texture(self, bgr: np.ndarray, plant_mask: np.ndarray) -> float:
        """
        Анализирует текстуру поверхности.
        Более гладкая поверхность = более зрелое растение.
        """
        # Применяем Gaussian Blur
        blurred = cv2.GaussianBlur(bgr, (5, 5), 0)

        # Вычисляем разницу (детали)
        diff = cv2.absdiff(bgr, blurred)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        diff_mask = cv2.bitwise_and(diff_gray, plant_mask)

        # Чем меньше деталей = глаже поверхность = выше зрелость
        detail_level = np.mean(diff_mask)
        # Нормализуем к 0-1 (обратное значение)
        texture_score = 1.0 - min(detail_level / 50, 1.0)

        return float(texture_score)

    def _analyze_size(self, plant_mask: np.ndarray) -> float:
        """
        Анализирует размер растения.
        Больший размер = более развитое растение.
        """
        plant_pixels = np.count_nonzero(plant_mask)
        total_pixels = plant_mask.shape[0] * plant_mask.shape[1]

        # Нормализуем к 0-1
        size_ratio = plant_pixels / total_pixels
        # Оптимум ~ 30-50% изображения
        if size_ratio < 0.1:
            size_score = size_ratio * 10  # 0 -> 0, 0.1 -> 1
        elif size_ratio > 0.6:
            size_score = 1.0
        else:
            size_score = (size_ratio - 0.1) / 0.5

        return float(min(size_score, 1.0))

    def _determine_stage(
        self,
        color_analysis: dict,
        texture_score: float,
        size_score: float,
        crop_type: str,
    ) -> tuple[str, int]:
        """
        Определяет стадию зрелости на основе анализа.

        Стадии:
        - immature: < 0.4
        - early: 0.4 - 0.6
        - optimal: 0.6 - 0.85
        - overripe: > 0.85
        """
        color_score = color_analysis.get("color_score", 0.0)
        green_ratio = color_analysis.get("green_ratio", 0.0)

        # Вычисляем общий индекс зрелости
        # Цвет важен на 50%, текстура на 30%, размер на 20%
        maturity_index = (
            color_score * 0.5 +
            texture_score * 0.3 +
            size_score * 0.2
        )

        # Определяем стадию
        if maturity_index < 0.35:
            stage = "immature"
        elif maturity_index < 0.6:
            stage = "early"
        elif maturity_index < 0.8:
            stage = "optimal"
        else:
            stage = "overripe"

        # Доверие зависит от наличия зеленого (должно быть меньше для зрелого)
        if stage == "overripe" and green_ratio > 0.3:
            # Не совсем перезрелое если еще много зелени
            confidence = min(int(maturity_index * 100), 95)
        else:
            confidence = min(int(maturity_index * 100), 98)

        return stage, confidence

    def _get_plant_mask(self, bgr: np.ndarray) -> np.ndarray:
        """Получает маску растения (зеленые пиксели)."""
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self._GREEN_LOWER, self._GREEN_UPPER)

        # Добавляем желтый и оранжевый для полноты
        yellow_mask = cv2.inRange(hsv, self._YELLOW_LOWER, self._YELLOW_UPPER)
        orange_mask = cv2.inRange(hsv, self._ORANGE_LOWER, self._ORANGE_UPPER)
        mask = cv2.bitwise_or(mask, yellow_mask)
        mask = cv2.bitwise_or(mask, orange_mask)

        # Сглаживаем маску
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        return mask

    def _load(self, path: str | Path) -> np.ndarray:
        """Загружает и подготавливает изображение."""
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f"Error loading image from {path}")

        img = cv2.resize(img, self._resize_to)

        # Адаптивное улучшение контраста
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        l = clahe.apply(l)
        return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_Lab2BGR)

    @staticmethod
    def _build_profile(stage: str, confidence: int, data: dict) -> MaturityProfile:
        """Создает профиль зрелости."""
        return MaturityProfile(
            stage=stage,
            confidence=confidence,
            yellow_ratio=data.get("yellow_ratio", 0.0),
            green_ratio=data.get("green_ratio", 0.0),
            color_score=data.get("color_score", 0.0),
            size_score=data.get("size_score", 0.0),
            texture_score=data.get("texture_score", 0.0),
        )
