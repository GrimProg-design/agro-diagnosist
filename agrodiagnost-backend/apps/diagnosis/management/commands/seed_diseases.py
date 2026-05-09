"""
АгроДиагност — seed_diseases management command.

Usage:
    python manage.py seed_diseases
    python manage.py seed_diseases --flush
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.diagnosis.models import Crop, Disease

CROPS: list[dict] = [
    {"name": "Пшеница",          "code": "wheat"},
    {"name": "Ячмень",           "code": "barley"},
    {"name": "Кукуруза",         "code": "corn"},
    {"name": "Картофель",        "code": "potato"},
    {"name": "Овощные культуры", "code": "vegetables"},
]

DISEASES: list[dict] = [
    # ── Wheat ──────────────────────────────────────────────────────────
    {
        "crop": "wheat",
        "name": "Бурая листовая ржавчина",
        "severity": "high",
        "symptoms": ["yellowing", "dark_spots"],
        "symptom_labels": ["Пожелтение листьев", "Ржаво-коричневые пустулы"],
        "recommendations": [
            "Обработать фунгицидом на основе пропиконазола (Тилт 250 КЭ) из расчёта 0.5 л/га",
            "Провести обработку в фазе кущения при первых признаках",
            "Соблюдать севооборот — возврат пшеницы не ранее чем через 2 года",
            "Удалить и сжечь сильно поражённые растения",
        ],
    },
    {
        "crop": "wheat",
        "name": "Мучнистая роса пшеницы",
        "severity": "medium",
        "symptoms": ["deformation", "yellowing"],
        "symptom_labels": ["Белый мучнистый налёт", "Скручивание и пожелтение листьев"],
        "recommendations": [
            "Применить фунгицид триазольной группы (тебуконазол 0.6 л/га)",
            "Снизить дозу азотных удобрений",
            "Улучшить вентиляцию посевов путём снижения нормы высева",
            "Использовать устойчивые сорта в следующем сезоне",
        ],
    },
    {
        "crop": "wheat",
        "name": "Фузариоз колоса",
        "severity": "high",
        "symptoms": ["dark_spots", "deformation"],
        "symptom_labels": ["Розово-оранжевый налёт на колосе", "Деформация и щуплость зерна"],
        "recommendations": [
            "Протравить семена препаратом Витавакс 200 ФФ (2.5 л/т)",
            "Провести обработку фунгицидом в период цветения",
            "Избегать переувлажнения почвы",
            "Очистить и откалибровать семенной материал",
            "Убрать и уничтожить растительные остатки после уборки",
        ],
    },
    # ── Barley ─────────────────────────────────────────────────────────
    {
        "crop": "barley",
        "name": "Гельминтоспориоз ячменя",
        "severity": "high",
        "symptoms": ["dark_spots", "yellowing"],
        "symptom_labels": ["Тёмные продолговатые пятна на листьях", "Пожелтение краёв листа"],
        "recommendations": [
            "Протравить семена препаратом Витавакс 200 (2 л/т)",
            "Провести листовую обработку системным фунгицидом в фазе выхода в трубку",
            "Избегать загущённых посевов (норма высева не более 4.5 млн/га)",
            "Убрать растительные остатки после уборки",
        ],
    },
    {
        "crop": "barley",
        "name": "Полосатая пятнистость ячменя",
        "severity": "medium",
        "symptoms": ["yellowing", "deformation"],
        "symptom_labels": ["Жёлто-коричневые продольные полосы", "Деформация листовой пластины"],
        "recommendations": [
            "Использовать сертифицированный здоровый семенной материал",
            "Протравливание семян фунгицидом Феразим 500 СК (1.5 л/т)",
            "Соблюдать оптимальные сроки посева",
        ],
    },
    # ── Corn ───────────────────────────────────────────────────────────
    {
        "crop": "corn",
        "name": "Пузырчатая головня кукурузы",
        "severity": "medium",
        "symptoms": ["deformation", "dark_spots"],
        "symptom_labels": ["Белые вздутия-галлы на листьях и стебле", "Чёрная порошкообразная масса"],
        "recommendations": [
            "Использовать устойчивые гибриды кукурузы",
            "Протравливание семян перед посевом препаратом ТМТД",
            "Механическое удаление головнёвых галлов до их разрыва",
            "Глубокая заделка растительных остатков (на 20–25 см)",
        ],
    },
    {
        "crop": "corn",
        "name": "Серая стеблевая гниль кукурузы",
        "severity": "high",
        "symptoms": ["dark_spots", "deformation", "yellowing"],
        "symptom_labels": ["Потемнение и размягчение стебля", "Деформация початков", "Преждевременное пожелтение"],
        "recommendations": [
            "Соблюдать севооборот (возврат кукурузы через 3–4 года)",
            "Протравить семена системным фунгицидом",
            "Нормализовать минеральное питание: снизить дозу азота, повысить калий",
            "Убрать урожай в оптимальные сроки во избежание полегания",
        ],
    },
    # ── Potato ─────────────────────────────────────────────────────────
    {
        "crop": "potato",
        "name": "Фитофтороз картофеля",
        "severity": "high",
        "symptoms": ["yellowing", "dark_spots", "deformation"],
        "symptom_labels": ["Пожелтение и увядание листьев", "Тёмные водянистые пятна", "Белый налёт снизу листа"],
        "recommendations": [
            "Обработать фунгицидом Ридомил Голд МЦ каждые 7–10 дней",
            "Уменьшить влажность почвы, нормализовать полив",
            "Удалить и уничтожить все поражённые листья и стебли",
            "Окучить растения для защиты клубней",
            "Провести скашивание ботвы за 2 недели до уборки",
        ],
    },
    {
        "crop": "potato",
        "name": "Альтернариоз картофеля",
        "severity": "medium",
        "symptoms": ["dark_spots", "yellowing"],
        "symptom_labels": ["Концентрические тёмные кольца на листьях", "Хлороз вокруг пятен"],
        "recommendations": [
            "Обработка фунгицидом Дитан М-45 (2 кг/га) с интервалом 7 дней",
            "Соблюдение 4-летнего севооборота",
            "Использование здорового сертифицированного семенного материала",
            "Оптимизировать азотное питание",
        ],
    },
    {
        "crop": "potato",
        "name": "Чёрная парша (ризоктониоз)",
        "severity": "medium",
        "symptoms": ["dark_spots", "deformation"],
        "symptom_labels": ["Чёрные склероции на клубнях", "Деформация и некроз ростков"],
        "recommendations": [
            "Протравить клубни перед посадкой препаратом Максим XL",
            "Прогреть посадочный материал при 15–18°C в течение 2 недель",
            "Соблюдать оптимальные сроки посадки (температура почвы ≥8°C)",
            "Глубокое окучивание после появления всходов",
        ],
    },
    # ── Vegetables ─────────────────────────────────────────────────────
    {
        "crop": "vegetables",
        "name": "Серая гниль (Botrytis cinerea)",
        "severity": "medium",
        "symptoms": ["dark_spots", "deformation"],
        "symptom_labels": ["Серый пушистый налёт", "Мягкая гниль тканей"],
        "recommendations": [
            "Снизить влажность воздуха до 70–75%",
            "Обработать препаратом Свитч 62.5 WG (0.6 кг/га)",
            "Удалить и уничтожить все поражённые части растений",
            "Обеспечить хорошую циркуляцию воздуха в теплице/поле",
        ],
    },
    {
        "crop": "vegetables",
        "name": "Пероноспороз (ложная мучнистая роса)",
        "severity": "high",
        "symptoms": ["yellowing", "deformation"],
        "symptom_labels": ["Жёлто-зелёные пятна сверху листа", "Серо-фиолетовый налёт снизу"],
        "recommendations": [
            "Обработать медьсодержащим препаратом (Бордосская жидкость 1%)",
            "Избегать переувлажнения и дождевого полива",
            "Улучшить дренаж почвы",
            "Провести профилактическую обработку в период прохладной влажной погоды",
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the database with crops and diseases for АгроДиагност"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing crops and diseases before seeding",
        )

    def handle(self, *args, **options) -> None:
        if options["flush"]:
            Disease.objects.all().delete()
            Crop.objects.all().delete()
            self.stdout.write(self.style.WARNING("Existing data flushed."))

        crop_map: dict[str, Crop] = {}

        for crop_data in CROPS:
            crop, created = Crop.objects.get_or_create(
                code=crop_data["code"],
                defaults={"name": crop_data["name"]},
            )
            crop_map[crop.code] = crop
            status_label = "создана" if created else "уже существует"
            self.stdout.write(f"  Культура '{crop.name}' — {status_label}")

        disease_count = 0
        for d in DISEASES:
            crop = crop_map.get(d["crop"])
            if crop is None:
                self.stdout.write(self.style.ERROR(f"  Культура '{d['crop']}' не найдена, пропуск."))
                continue

            _, created = Disease.objects.get_or_create(
                name=d["name"],
                crop=crop,
                defaults={
                    "severity":        d["severity"],
                    "symptoms":        d["symptoms"],
                    "symptom_labels":  d["symptom_labels"],
                    "recommendations": d["recommendations"],
                },
            )
            if created:
                disease_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Готово: {len(CROPS)} культур, {disease_count} новых болезней добавлено."
            )
        )
