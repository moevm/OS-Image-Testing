from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base
from database.models.loader import LoaderBase
from database.models.observer import ObserverBase


class ExperimentBase(Base):
    __tablename__ = "experiments"

    experiment_id: Mapped[int] = mapped_column(primary_key=True)
    config_id: Mapped[int] = mapped_column(ForeignKey("configurations.config_id"))
    description: Mapped[str | None] = mapped_column(String(100))
    type: Mapped[str | None] = mapped_column(String(20))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    configuration: Mapped["ConfigurationBase"] = relationship(
        "ConfigurationBase", back_populates="experiments"
    )
    loaders: Mapped[list[LoaderBase]] = relationship("LoaderBase", back_populates="experiment")
    observers: Mapped[list[ObserverBase]] = relationship(
        "ObserverBase", back_populates="experiment"
    )

    def __repr__(self) -> str:
        return (
            f"<exp_id={self.config_id}, desc={self.description}, "
            f"start={self.started_at}, end={self.ended_at}>"
        )
