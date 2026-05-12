from django.contrib import admin

from .models import Distribution


@admin.register(Distribution)
class DistributionAdmin(admin.ModelAdmin):
    list_display = ("id", "display_name", "name", "version", "is_active", "order")
    list_display_links = ("display_name",)
    list_editable = ("order", "is_active")
    list_filter = ("is_active", "name")
    search_fields = ("display_name", "name", "description", "version")

    fieldsets = (
        (
            "General information",
            {"fields": ("name", "version", "display_name", "description")},
        ),
        ("Settings", {"fields": ("order", "is_active")}),
    )
