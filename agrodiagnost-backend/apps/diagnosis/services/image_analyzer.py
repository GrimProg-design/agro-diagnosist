"""
АгроДиагност — ImageAnalyzer service.

Uses classical OpenCV image processing (no ML) to extract visible
symptom signals from a plant photograph.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict

import cv2
import numpy as np

logger = logging.getLogger(__name__)

class SymptomProfile(TypedDict):
    yellowing:      bool
    dark_spots:     bool
    deformation:    bool
    plant_present:  bool
    healthy:        bool

class ImageAnalyzer:
    """
    Использует адаптивную фильтрацию шумов и усиление контраста симптомов.
    """

    _PLANT_GREEN_LOWER = np.array([25, 35, 35], dtype=np.uint8)
    _PLANT_GREEN_UPPER = np.array([95, 255, 255], dtype=np.uint8)
    
    _YELLOW_LOWER = np.array([18, 100, 100], dtype=np.uint8)
    _YELLOW_UPPER = np.array([32, 255, 255], dtype=np.uint8)
    _YELLOW_MIN_RATIO = 0.07

    _DARK_L_THRESHOLD = 50    
    _DARK_MIN_RATIO   = 0.03   

    _DEFORM_SOLIDITY_THRESHOLD = 0.45   

    def __init__(self, resize_to: tuple[int, int] = (512, 512)) -> None:
        self._resize_to = resize_to

    def analyze(self, image_path: str | Path) -> SymptomProfile:
        bgr = self._load(image_path)
        
        # Получаем чистую маску растения
        plant_mask = self._get_plant_mask(bgr)
        plant_pixels = int(np.count_nonzero(plant_mask))
        total_pixels = bgr.shape[0] * bgr.shape[1]

        if (plant_pixels / total_pixels) < 0.03:
            return SymptomProfile(yellowing=False, dark_spots=False, deformation=False, plant_present=False, healthy=False)

        # 1. Детекция желтизны
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        yellow_mask = cv2.inRange(hsv, self._YELLOW_LOWER, self._YELLOW_UPPER)
        yellow_mask = cv2.bitwise_and(yellow_mask, plant_mask)
        yellowing = (np.count_nonzero(yellow_mask) / plant_pixels) >= self._YELLOW_MIN_RATIO

        # 2. Детекция пятен (с фильтрацией теней)
        dark_spots = self._check_dark_spots(bgr, plant_mask)

        # 3. Детекция деформации
        deformation = self._check_deformation(bgr, plant_mask)

        healthy = not (yellowing or dark_spots or deformation)

        return SymptomProfile(
            yellowing=yellowing,
            dark_spots=dark_spots,
            deformation=deformation,
            plant_present=True,
            healthy=healthy,
        )

    def _check_dark_spots(self, bgr: np.ndarray, plant_mask: np.ndarray) -> bool:
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2Lab)
        l_channel = lab[:, :, 0]
        
        # Инвертированный порог для поиска именно черных/коричневых зон
        _, dark = cv2.threshold(l_channel, self._DARK_L_THRESHOLD, 255, cv2.THRESH_BINARY_INV)
        dark = cv2.bitwise_and(dark, plant_mask)
        
        # Убираем мелкий шум (тени в прожилках)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, kernel)
        
        plant_area = np.count_nonzero(plant_mask)
        return (np.count_nonzero(dark) / plant_area) >= self._DARK_MIN_RATIO

    def _check_deformation(self, bgr: np.ndarray, plant_mask: np.ndarray) -> bool:
        # Используем саму маску растения для анализа формы, а не Canny (это надежнее)
        contours, _ = cv2.findContours(plant_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        deformed_count = 0
        significant = 0
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 2000: continue # Игнорируем мусор
            
            significant += 1
            hull = cv2.convexHull(cnt)
            solidity = area / cv2.contourArea(hull) if cv2.contourArea(hull) > 0 else 1
            
            if solidity < self._DEFORM_SOLIDITY_THRESHOLD:
                deformed_count += 1
                
        if significant == 0: return False
        return (deformed_count / significant) >= 0.4

    def _get_plant_mask(self, bgr: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self._PLANT_GREEN_LOWER, self._PLANT_GREEN_UPPER)
        
        # Сглаживаем маску, чтобы дырки внутри листа не мешали
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    def _load(self, path: str | Path) -> np.ndarray:
        img = cv2.imread(str(path))
        if img is None: raise ValueError("Error loading image")
        img = cv2.resize(img, self._resize_to)
        
        # Адаптивное улучшение контраста (помогает при плохом свете в поле)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        l = clahe.apply(l)
        return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_Lab2BGR)