from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING, Any, Literal

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from imgtests.database.models.base import Base

if TYPE_CHECKING:
    from imgtests.database.models.experiment import ExperimentBase

UtilType = Literal["loader", "observer"]


class UtilRunResult(Base):
    __tablename__ = "util_run_result"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiment.experiment_id"))
    util_type: Mapped[UtilType] = mapped_column(String(20))
    command: Mapped[str] = mapped_column(String())
    result: Mapped[dict[str, Any] | list[str]] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    experiment: Mapped["ExperimentBase"] = relationship(  # noqa: UP037
        "ExperimentBase",
        back_populates="util_run_results",
    )

    def __repr__(self) -> str:
        return (
            f"UtilRunResult(id={self.id}, "
            f"experiment_id={self.experiment_id}, "
            f"util_type={self.util_type}, "
            f"command={self.command}, "
            f"result={self.result}, "
            f"description={self.description}, "
            f"started_at={self.started_at}, "
            f"ended_at={self.ended_at})"
        )
