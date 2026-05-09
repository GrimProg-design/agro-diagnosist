"""
АгроДиагност — Django admin configuration.
"""
from django.contrib import admin

from .models import Crop, Disease

admin.site.site_header = "АгроДиагност — Панель управления"
admin.site.site_title  = "АгроДиагност"
admin.site.index_title = "Управление базой заболеваний"


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display  = ("name", "code", "disease_count")
    search_fields = ("name", "code")
    ordering      = ("name",)

    @admin.display(description="Болезней")
    def disease_count(self, obj: Crop) -> int:
        return obj.diseases.count()


@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display   = ("name", "crop", "severity", "symptom_count", "recommendation_count")
    list_filter    = ("crop", "severity")
    search_fields  = ("name", "crop__name")
    ordering       = ("crop", "name")
    readonly_fields = ("symptom_count", "recommendation_count")

    fieldsets = (
        ("Основная информация", {
            "fields": ("name", "crop", "severity"),
        }),
        ("Симптомы", {
            "fields": ("symptoms", "symptom_labels"),
            "description": "symptoms — ключи для сопоставления; symptom_labels — русские названия",
        }),
        ("Рекомендации", {
            "fields": ("recommendations",),
        }),
    )

    @admin.display(description="Симптомов")
    def symptom_count(self, obj: Disease) -> int:
        return len(obj.symptoms or [])

    @admin.display(description="Рекомендаций")
    def recommendation_count(self, obj: Disease) -> int:
        return len(obj.recommendations or [])
