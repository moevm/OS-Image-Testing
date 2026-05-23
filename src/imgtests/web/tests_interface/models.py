from django.db import models


class Distribution(models.Model):
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        """Metadata options for Distribution model."""

        ordering = ["order", "display_name"]  # noqa: RUF012
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(fields=["name"], name="unique_name"),
        ]

    def __str__(self):
        return self.display_name
