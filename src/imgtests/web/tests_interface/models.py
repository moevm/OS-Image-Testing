from django.db import models


class Distribution(models.Model):
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=50, blank=True, default="")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        """Metadata options for Distribution model."""

        ordering = ["order", "display_name"]  # noqa: RUF012
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(fields=["name", "version"], name="unique_name_version"),
        ]

    def __str__(self):
        if self.version:
            return f"{self.display_name} ({self.version})"
        return self.display_name
