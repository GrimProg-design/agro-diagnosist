/**
 * app.js — АгроДиагност
 * Main application controller. Wires up all UI interactions.
 */

import { analyzeImage } from "./api.js";
import {
  setButtonLoading,
  renderResults,
  showSection,
  hideSection,
  showFilePreview,
  resetUploadZone,
} from "./ui.js";

/* ------------------------------------------------------------------ */
/* State                                                                */
/* ------------------------------------------------------------------ */
const state = {
  selectedCrop: null,
  uploadedFile: null,
  previewSrc: null,
};

/* ------------------------------------------------------------------ */
/* DOM refs                                                             */
/* ------------------------------------------------------------------ */
const cropSelector = document.getElementById("cropSelector");
const uploadZone = document.getElementById("uploadZone");
const fileInput = document.getElementById("fileInput");
const uploadBtn = document.getElementById("uploadBtn");
const removeImgBtn = document.getElementById("removeImg");
const analyseBtn = document.getElementById("analyseBtn");
const analyseHint = document.getElementById("analyseHint");
const resultsSection = document.getElementById("results");
const newDiagnosisBtn = document.getElementById("newDiagnosisBtn");

/* ------------------------------------------------------------------ */
/* Crop selection                                                       */
/* ------------------------------------------------------------------ */
cropSelector.addEventListener("click", (e) => {
  const btn = e.target.closest(".crop-btn");
  if (!btn) return;

  document.querySelectorAll(".crop-btn").forEach((b) => {
    b.classList.remove("active");
    b.setAttribute("aria-pressed", "false");
  });

  btn.classList.add("active");
  btn.setAttribute("aria-pressed", "true");
  state.selectedCrop = btn.dataset.crop;

  updateAnalyseState();
});

/* ------------------------------------------------------------------ */
/* File upload                                                          */
/* ------------------------------------------------------------------ */
uploadBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  fileInput.click();
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

removeImgBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  clearFile();
});

/* Drag & Drop */
uploadZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadZone.classList.add("drag-over");
});

["dragleave", "dragend"].forEach((ev) =>
  uploadZone.addEventListener(ev, () =>
    uploadZone.classList.remove("drag-over"),
  ),
);

uploadZone.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

/* Keyboard accessibility for zone */
uploadZone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});

async function handleFile(file) {
  if (!validateFile(file)) return;
  state.uploadedFile = file;
  state.previewSrc = await showFilePreview(file);
  updateAnalyseState();
}

function clearFile() {
  state.uploadedFile = null;
  state.previewSrc = null;
  resetUploadZone();
  updateAnalyseState();
}

function validateFile(file) {
  const allowedTypes = ["image/jpeg", "image/png", "image/webp"];
  const maxSize = 10 * 1024 * 1024; // 10 MB

  if (!allowedTypes.includes(file.type)) {
    showToast(
      "Формат не поддерживается. Используйте JPG, PNG или WEBP.",
      "error",
    );
    return false;
  }
  if (file.size > maxSize) {
    showToast("Файл слишком большой. Максимум 10 МБ.", "error");
    return false;
  }
  return true;
}

/* ------------------------------------------------------------------ */
/* Analyse button state                                                 */
/* ------------------------------------------------------------------ */
function updateAnalyseState() {
  const ready = state.selectedCrop && state.uploadedFile;
  analyseBtn.disabled = !ready;
  analyseBtn.setAttribute("aria-disabled", String(!ready));

  if (!state.selectedCrop && !state.uploadedFile) {
    analyseHint.textContent = "Выберите культуру и загрузите изображение";
  } else if (!state.selectedCrop) {
    analyseHint.textContent = "Выберите тип культуры";
  } else if (!state.uploadedFile) {
    analyseHint.textContent = "Загрузите изображение растения";
  } else {
    analyseHint.textContent = "Готово к анализу";
  }
}

/* ------------------------------------------------------------------ */
/* Analysis                                                             */
/* ------------------------------------------------------------------ */
analyseBtn.addEventListener("click", async () => {
  if (!state.selectedCrop || !state.uploadedFile) return;

  setButtonLoading(analyseBtn, true);
  hideSection(resultsSection);

  try {
    const response = await analyzeImage(state.uploadedFile, state.selectedCrop);

    if (response.success) {
      renderResults(response.data, state.previewSrc);
      showSection(resultsSection);
    } else {
      showToast(
        response.error || "Ошибка анализа. Попробуйте ещё раз.",
        "error",
      );
    }
  } catch (err) {
    console.error("[АгроДиагност] Analysis error:", err);
    showToast("Сервер недоступен. Проверьте подключение.", "error");
  } finally {
    setButtonLoading(analyseBtn, false);
  }
});

/* ------------------------------------------------------------------ */
/* New diagnosis                                                        */
/* ------------------------------------------------------------------ */
newDiagnosisBtn.addEventListener("click", () => {
  hideSection(resultsSection);
  clearFile();
  document.querySelectorAll(".crop-btn").forEach((b) => {
    b.classList.remove("active");
    b.setAttribute("aria-pressed", "false");
  });
  state.selectedCrop = null;
  updateAnalyseState();
  document.getElementById("upload").scrollIntoView({ behavior: "smooth" });
});

/* ------------------------------------------------------------------ */
/* Toast notifications                                                  */
/* ------------------------------------------------------------------ */
function showToast(message, type = "info") {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = `toast toast--${type}`;
  toast.setAttribute("role", "alert");
  toast.setAttribute("aria-live", "assertive");
  toast.textContent = message;

  Object.assign(toast.style, {
    position: "fixed",
    bottom: "2rem",
    left: "50%",
    transform: "translateX(-50%) translateY(20px)",
    background: type === "error" ? "#fef2f2" : "#f0fdf4",
    color: type === "error" ? "#dc2626" : "#16a34a",
    border: `1px solid ${type === "error" ? "#fecaca" : "#bbf7d0"}`,
    borderRadius: "12px",
    padding: "0.75rem 1.5rem",
    fontSize: "0.9rem",
    fontWeight: "600",
    fontFamily: "Nunito, sans-serif",
    boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
    zIndex: "9999",
    maxWidth: "calc(100vw - 2rem)",
    textAlign: "center",
    transition: "transform 300ms cubic-bezier(0.4,0,0.2,1), opacity 300ms ease",
    opacity: "0",
  });

  document.body.appendChild(toast);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      toast.style.transform = "translateX(-50%) translateY(0)";
      toast.style.opacity = "1";
    });
  });

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(-50%) translateY(10px)";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

/* ------------------------------------------------------------------ */
/* Init                                                                 */
/* ------------------------------------------------------------------ */
updateAnalyseState();
