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
    yellowing:   bool
    dark_spots:  bool
    deformation: bool


class ImageAnalyzer:
    """
    Analyses a plant image and returns a symptom profile.

    All detection methods operate on the HSV colour space and
    basic morphological analysis — no machine-learning models required.
    """

    # ── Yellowing thresholds (HSV) ────────────────────────────────────
    _YELLOW_LOWER = np.array([18, 60, 80],  dtype=np.uint8)
    _YELLOW_UPPER = np.array([38, 255, 255], dtype=np.uint8)
    _YELLOW_MIN_RATIO = 0.04   # ≥4 % of leaf area flagged as yellow

    # ── Dark spot thresholds (L*a*b* lightness) ──────────────────────
    _DARK_L_THRESHOLD = 55     # L < 55 → dark region
    _DARK_MIN_RATIO   = 0.02   # ≥2 % of image area covered by dark blobs

    # ── Deformation — contour-based ───────────────────────────────────
    _DEFORM_SOLIDITY_THRESHOLD = 0.72   # convexity ratio below this → deformed

    def __init__(self, resize_to: tuple[int, int] = (512, 512)) -> None:
        self._resize_to = resize_to

    # ── Public API ────────────────────────────────────────────────────

    def analyze(self, image_path: str | Path) -> SymptomProfile:
        """
        Run all detectors on the image at *image_path*.

        Args:
            image_path: Filesystem path to the uploaded image.

        Returns:
            SymptomProfile dict with bool values for each symptom.

        Raises:
            ValueError: If the image cannot be loaded.
        """
        bgr = self._load(image_path)

        return SymptomProfile(
            yellowing=self.detect_yellowing(bgr),
            dark_spots=self.detect_dark_spots(bgr),
            deformation=self.detect_deformation(bgr),
        )

    def detect_yellowing(self, bgr: np.ndarray) -> bool:
        """
        Detect abnormal yellowing by measuring the proportion of pixels
        that fall within the yellow HSV range relative to total leaf pixels.
        """
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        yellow_mask = cv2.inRange(hsv, self._YELLOW_LOWER, self._YELLOW_UPPER)

        # Isolate green-ish plant pixels as denominator (avoid sky/soil)
        green_lower = np.array([30, 30, 30], dtype=np.uint8)
        green_upper = np.array([90, 255, 255], dtype=np.uint8)
        plant_mask  = cv2.inRange(hsv, green_lower, green_upper)

        plant_pixels  = int(np.count_nonzero(plant_mask))
        yellow_pixels = int(np.count_nonzero(yellow_mask))

        if plant_pixels < 500:
            # Likely not a plant photo — fall back to total area
            total = bgr.shape[0] * bgr.shape[1]
            return (yellow_pixels / total) >= self._YELLOW_MIN_RATIO

        return (yellow_pixels / plant_pixels) >= self._YELLOW_MIN_RATIO

    def detect_dark_spots(self, bgr: np.ndarray) -> bool:
        """
        Detect dark necrotic spots by analysing the L* channel of L*a*b*
        colour space and identifying low-lightness blobs.
        """
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2Lab)
        l_channel = lab[:, :, 0]

        _, dark_mask = cv2.threshold(
            l_channel, self._DARK_L_THRESHOLD, 255, cv2.THRESH_BINARY_INV
        )

        # Remove tiny noise with morphological opening
        kernel    = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, kernel)

        dark_pixels = int(np.count_nonzero(dark_mask))
        total       = bgr.shape[0] * bgr.shape[1]

        return (dark_pixels / total) >= self._DARK_MIN_RATIO

    def detect_deformation(self, bgr: np.ndarray) -> bool:
        """
        Detect leaf deformation by comparing each leaf contour's area
        to the area of its convex hull.  A low solidity ratio (area/hull)
        indicates irregular, deformed edges.
        """
        gray   = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        edges  = cv2.Canny(blurred, 30, 100)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_area = (bgr.shape[0] * bgr.shape[1]) * 0.005  # ignore tiny blobs

        deformed_count = 0
        significant_count = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue

            significant_count += 1
            hull     = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)

            if hull_area == 0:
                continue

            solidity = area / hull_area
            if solidity < self._DEFORM_SOLIDITY_THRESHOLD:
                deformed_count += 1

        if significant_count == 0:
            return False

        return (deformed_count / significant_count) >= 0.4

    # ── Private helpers ───────────────────────────────────────────────

    def _load(self, path: str | Path) -> np.ndarray:
        """Load and resize the image; raise ValueError on failure."""
        bgr = cv2.imread(str(path))
        if bgr is None:
            raise ValueError(f"Cannot load image: {path}")

        bgr = cv2.resize(bgr, self._resize_to, interpolation=cv2.INTER_AREA)
        return bgr
