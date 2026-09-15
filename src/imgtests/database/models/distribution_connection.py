from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from imgtests.database.models.base import Base


class DistributionConnection(Base):
    __tablename__ = "distribution_connection"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    host: Mapped[str] = mapped_column(String(100))
    user: Mapped[str] = mapped_column(String(100))
    password: Mapped[str] = mapped_column(String(100))
    port: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")

    def __repr__(self) -> str:
        return (
            f"DistributionConnection(name={self.name}, "
            f"host={self.host}, user={self.user}, "
            f"port={self.port}, is_active={self.is_active})"
        )
