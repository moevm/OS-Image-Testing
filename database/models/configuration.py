from typing import TYPE_CHECKING

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base

if TYPE_CHECKING:
    from database.models.experiment import ExperimentBase


class ConfigurationBase(Base):
    __tablename__ = "configuration"

    config_id: Mapped[int] = mapped_column(primary_key=True)
    configuration: Mapped[dict] = mapped_column(JSON)
    experiments: Mapped[list["ExperimentBase"]] = relationship(
        "ExperimentBase", back_populates="configuration"
    )

    def __repr__(self) -> str:
        return f"<id={self.config_id}, configuration={self.configuration}>"
