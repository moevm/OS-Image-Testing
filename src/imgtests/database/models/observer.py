from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from imgtests.database.models.base import Base

if TYPE_CHECKING:
    from imgtests.database.models.experiment import ExperimentBase


class ObserverBase(Base):
    __tablename__ = "observer"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiment.experiment_id"))
    command: Mapped[str] = mapped_column(String(300))
    result: Mapped[dict] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    experiment: Mapped["ExperimentBase"] = relationship(  # noqa: UP037
        "ExperimentBase",
        back_populates="observers",
    )

    def __repr__(self) -> str:
        return (
            f"ObserverBase(id={self.id}, "
            f"experiment_id={self.experiment_id}, "
            f"command={self.command}, "
            f"result={self.result}, "
            f"description={self.description}, "
            f"start={self.started_at}, "
            f"end={self.ended_at})"
        )
