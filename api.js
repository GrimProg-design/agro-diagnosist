/**
 * api.js
 * Реальная работа с Django backend
 */

const API_BASE = "https://agro-diagnosist.onrender.com/api/v1";

export async function analyzeImage(imageFile, cropType) {
  const formData = new FormData();

  formData.append("image", imageFile);
  formData.append("crop_type", cropType);

  const response = await fetch(`${API_BASE}/diagnosis/`, {
    method: "POST",
    body: formData,
  });

  const data = await response.json();

  console.log("BACKEND RESPONSE:", data);

  if (!response.ok) {
    return {
      success: false,
      error: data.error || "Ошибка анализа. Попробуйте ещё раз.",
    };
  }

  return data;
}

export async function analyzeMaturity(imageFile, cropType) {
  const formData = new FormData();

  formData.append("image", imageFile);
  formData.append("crop_type", cropType);

  const response = await fetch(`${API_BASE}/maturity/`, {
    method: "POST",
    body: formData,
  });

  const data = await response.json();

  console.log("MATURITY RESPONSE:", data);

  if (!response.ok) {
    return {
      success: false,
      error: data.error || "Ошибка анализа зрелости. Попробуйте ещё раз.",
    };
  }

  return data;
}
