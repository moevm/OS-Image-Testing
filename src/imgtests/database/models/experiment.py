from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from imgtests.database.models.base import Base
from imgtests.database.models.loader import LoaderBase
from imgtests.database.models.observer import ObserverBase

if TYPE_CHECKING:
    from imgtests.database.models.configuration import ConfigurationBase


class ExperimentBase(Base):
    __tablename__ = "experiment"

    experiment_id: Mapped[int] = mapped_column(primary_key=True)
    config_id: Mapped[int] = mapped_column(ForeignKey("configuration.config_id"))
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
            f"ExperimentBase(id={self.experiment_id}, "
            f"config_id={self.config_id}, "
            f"description={self.description}, "
            f"type={self.type}, "
            f"started_at={self.started_at}, "
            f"ended_at={self.ended_at})"
        )
