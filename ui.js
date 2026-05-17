/**
 * ui.js — АгроДиагност
 * UI rendering and DOM manipulation helpers.
 */

const CROP_LABELS = {
  wheat: "Пшеница",
  barley: "Ячмень",
  corn: "Кукуруза",
  potato: "Картофель",
  vegetables: "Овощные культуры",
};

const SEVERITY_LABELS = {
  high: "Высокая угроза",
  medium: "Умеренная угроза",
  low: "Низкая угроза",
};

export function setButtonLoading(btn, loading) {
  const content = btn.querySelector(".btn__content");
  const loadingEl = btn.querySelector(".btn__loading");

  if (loading) {
    content.hidden = true;
    loadingEl.hidden = false;
    btn.disabled = true;
    btn.setAttribute("aria-busy", "true");
  } else {
    content.hidden = false;
    loadingEl.hidden = true;
    btn.disabled = false;
    btn.setAttribute("aria-busy", "false");
  }
}

/**
 * Render diagnostic results into the results section.
 * @param {Object} result - The result data from the API
 * @param {string} imageSrc - Base64 or URL of the analysed image
 */
export function renderResults(result, imageSrc) {
  const {
    diagnosis,
    confidence,
    severity,
    symptoms,
    recommendations,
    cropType,
    analyzedAt,
  } = result;

  // главная карточка
  const badge = document.getElementById("resultSeverity");
  badge.textContent = SEVERITY_LABELS[severity] || severity;
  badge.className = `result-card__badge severity--${severity}`;

  document.getElementById("resultCrop").textContent =
    CROP_LABELS[cropType] || cropType;
  document.getElementById("resultTimestamp").textContent =
    _formatDate(analyzedAt);
  document.getElementById("resultDiagnosis").textContent = diagnosis;

  // анимации
  const fill = document.getElementById("confidenceFill");
  const valueEl = document.getElementById("confidenceValue");
  const track = document.getElementById("confidenceTrack");

  fill.style.width = "0%";
  valueEl.textContent = "0%";
  track.setAttribute("aria-valuenow", 0);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      fill.style.width = `${confidence}%`;
      track.setAttribute("aria-valuenow", confidence);
      _animateNumber(valueEl, 0, confidence, 1200, (v) => `${v}%`);
    });
  });

  // симптомы
  const symptomList = document.getElementById("symptomList");
  symptomList.innerHTML = "";
  symptoms.forEach((s, i) => {
    const li = document.createElement("li");
    li.textContent = s;
    li.style.animationDelay = `${i * 80}ms`;
    symptomList.appendChild(li);
  });

  // рекомендации
  const treatmentList = document.getElementById("treatmentList");
  treatmentList.innerHTML = "";
  recommendations.forEach((r, i) => {
    const li = document.createElement("li");
    li.textContent = r;
    li.style.animationDelay = `${i * 100}ms`;
    treatmentList.appendChild(li);
  });

  // изображения
  const resultImage = document.getElementById("resultImage");
  resultImage.src = imageSrc;
  resultImage.alt = `Снимок для диагностики: ${diagnosis}`;
}

/**
 * Render maturity analysis results into the results section.
 * @param {Object} result - The result data from maturity API
 * @param {string} imageSrc - Base64 or URL of the analysed image
 */
export function renderMaturityResults(result, imageSrc) {
  const {
    maturity_stage,
    stage_label,
    confidence,
    maturity_indicators,
    status_message,
    recommendations,
    harvest_readiness,
    care_tips,
    cropType,
    analyzedAt,
  } = result;

  const badge = document.getElementById("resultSeverity");
  badge.textContent = stage_label || maturity_stage;
  badge.className = `result-card__badge maturity--${maturity_stage}`;

  document.getElementById("resultCrop").textContent =
    CROP_LABELS[cropType] || cropType;
  document.getElementById("resultTimestamp").textContent =
    _formatDate(analyzedAt);
  document.getElementById("resultDiagnosis").textContent = status_message;

  const fill = document.getElementById("confidenceFill");
  const valueEl = document.getElementById("confidenceValue");
  const track = document.getElementById("confidenceTrack");

  fill.style.width = "0%";
  valueEl.textContent = "0%";
  track.setAttribute("aria-valuenow", 0);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      fill.style.width = `${confidence}%`;
      track.setAttribute("aria-valuenow", confidence);
      _animateNumber(valueEl, 0, confidence, 1200, (v) => `${v}%`);
    });
  });

  const symptomList = document.getElementById("symptomList");
  symptomList.innerHTML = "";

  if (maturity_indicators) {
    const indicators = [
      `Цветовой индекс: ${(maturity_indicators.color_score * 100).toFixed(0)}%`,
      `Индекс текстуры: ${(maturity_indicators.texture_score * 100).toFixed(0)}%`,
      `Индекс размера: ${(maturity_indicators.size_score * 100).toFixed(0)}%`,
      `Желтый цвет: ${(maturity_indicators.yellow_ratio * 100).toFixed(1)}%`,
      `Зеленый цвет: ${(maturity_indicators.green_ratio * 100).toFixed(1)}%`,
    ];

    indicators.forEach((indicator, i) => {
      const li = document.createElement("li");
      li.textContent = indicator;
      li.style.animationDelay = `${i * 80}ms`;
      symptomList.appendChild(li);
    });
  }

  // подсказки о лечении
  const treatmentList = document.getElementById("treatmentList");
  treatmentList.innerHTML = "";

  const tipsToShow =
    care_tips && care_tips.length > 0 ? care_tips : recommendations;
  tipsToShow.forEach((tip, i) => {
    const li = document.createElement("li");
    li.textContent = tip;
    li.style.animationDelay = `${i * 100}ms`;
    treatmentList.appendChild(li);
  });

  // изображение
  const resultImage = document.getElementById("resultImage");
  resultImage.src = imageSrc;
  resultImage.alt = `Снимок для определения зрелости: ${stage_label}`;

  _renderHarvestReadiness(harvest_readiness);
}

function _renderHarvestReadiness(harvestReadiness) {
  if (!harvestReadiness) return;

  const { ready, percentage, message } = harvestReadiness;

  const harvestElement = document.getElementById("harvestReadiness");
  if (harvestElement) {
    harvestElement.innerHTML = `
      <div class="harvest-status ${ready ? "ready" : "not-ready"}">
        <div class="harvest-percentage">${percentage}%</div>
        <p class="harvest-message">${message}</p>
      </div>
    `;
  }
}

/**
 * Show or hide a section with animation.
 */
export function showSection(el) {
  el.hidden = false;
  el.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function hideSection(el) {
  el.hidden = true;
}

/**
 * Display a file preview in the upload zone.
 */
export function showFilePreview(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const src = e.target.result;
      document.getElementById("uploadContent").hidden = true;
      document.getElementById("uploadPreview").hidden = false;
      document.getElementById("previewImg").src = src;
      document.getElementById("previewFilename").textContent =
        _truncateFilename(file.name, 32);
      resolve(src);
    };
    reader.readAsDataURL(file);
  });
}

/**
 * Reset the upload zone to its initial state.
 */
export function resetUploadZone() {
  document.getElementById("uploadContent").hidden = false;
  document.getElementById("uploadPreview").hidden = true;
  document.getElementById("previewImg").src = "";
  document.getElementById("fileInput").value = "";
}

/* ---- Internal helpers ---- */

function _formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function _truncateFilename(name, max) {
  if (name.length <= max) return name;
  const ext = name.slice(name.lastIndexOf("."));
  return name.slice(0, max - ext.length - 3) + "..." + ext;
}

function _animateNumber(el, from, to, duration, formatter = (v) => v) {
  const start = performance.now();
  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = formatter(Math.round(from + (to - from) * eased));
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
