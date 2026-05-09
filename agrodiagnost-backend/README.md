# АгроДиагност — Backend

Decision support system for diagnosing agricultural crop diseases.

## Quick start

```bash
cd backend

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate
python manage.py seed_diseases
python manage.py createsuperuser   # optional: for admin panel

python manage.py runserver
```

## API

**POST** `/api/v1/diagnosis/`

| Field       | Type            | Description              |
|-------------|-----------------|--------------------------|
| `image`     | file (multipart)| Plant photo (JPG/PNG/WEBP, ≤10 MB) |
| `crop_type` | string          | One of: wheat, barley, corn, potato, vegetables |

**Response**
```json
{
  "success": true,
  "data": {
    "diagnosis":       "Фитофтороз",
    "confidence":      87,
    "severity":        "high",
    "symptoms":        ["Пожелтение листьев", "Тёмные водянистые пятна"],
    "recommendations": ["Обработать фунгицидом Ридомил Голд МЦ каждые 7–10 дней"],
    "cropType":        "potato",
    "analyzedAt":      "2025-01-15T09:30:00+00:00"
  }
}
```

## Tests

```bash
python manage.py test apps.diagnosis.tests
```

## Admin panel

`http://localhost:8000/admin/`

## Frontend wiring

Replace the mock in `client/js/api.js`:

```js
export async function analyzeImage(imageFile, cropType) {
  const form = new FormData();
  form.append("image", imageFile);
  form.append("crop_type", cropType);

  const res = await fetch("http://localhost:8000/api/v1/diagnosis/", {
    method: "POST",
    body: form,
  });

  return res.json();
}
```
