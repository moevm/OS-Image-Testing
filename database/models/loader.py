from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class LoaderBase(Base):
    __tablename__ = "loaders"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.experiment_id"))
    command: Mapped[str] = mapped_column(String(30))
    result: Mapped[dict] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    experiment: Mapped["ExperimentBase"] = relationship("ExperimentBase", back_populates="loaders")

    def __repr__(self) -> str:
        return (
            f"<id={self.id}, command={self.command}, start={self.started_at}, end={self.ended_at}>"
        )
