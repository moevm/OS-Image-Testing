from typing import TYPE_CHECKING

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from imgtests.database.models.base import Base

if TYPE_CHECKING:
    from imgtests.database.models.experiment import ExperimentBase


class ConfigurationBase(Base):
    __tablename__ = "configuration"

    config_id: Mapped[int] = mapped_column(primary_key=True)
    os: Mapped[str] = mapped_column(String(30))
    packages: Mapped[dict | None] = mapped_column(JSON)
    core_info: Mapped[str | None] = mapped_column(String(300))
    core_config: Mapped[dict | None] = mapped_column(JSON)
    experiments: Mapped[list["ExperimentBase"]] = relationship(
        "ExperimentBase", back_populates="configuration"
    )

    def __repr__(self) -> str:
        return (
            f"ConfigurationBase(id={self.config_id}, "
            f"os={self.os}), "
            f"packages={self.packages}, "
            f"core_info={self.core_info}, "
            f"core_config={self.core_config}"
        )
