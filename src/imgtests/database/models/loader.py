from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from imgtests.database.models.base import Base

if TYPE_CHECKING:
    from imgtests.database.models.experiment import ExperimentBase


class LoaderBase(Base):
    __tablename__ = "loader"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiment.experiment_id"))
    command: Mapped[str] = mapped_column(String(200))
    result: Mapped[dict] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    experiment: Mapped["ExperimentBase"] = relationship("ExperimentBase", back_populates="loaders")

    def __repr__(self) -> str:
        return (
            f"LoaderBase(id={self.id}, command={self.command}, "
            f"start={self.started_at}, end={self.ended_at})"
        )
