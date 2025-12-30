import logging
import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models.base import Base
from database.models.configuration import ConfigurationBase
from database.models.experiment import ExperimentBase
from database.models.loader import LoaderBase
from database.models.observer import ObserverBase

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        user = os.environ["POSTGRES_USER"].strip()
        password = os.environ["POSTGRES_PASSWORD"].strip()
        db_name = os.environ["POSTGRES_DB"].strip()
        host = "imgtests-postgres"
        port = os.environ["SSH_POSTGRES_PORT"].strip()
        self.engine = create_engine(f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}")
        self.Session = sessionmaker(self.engine)
        Base.metadata.create_all(self.engine)

    def insert_configuration(self, configuration: dict[str, Any]) -> None:
        configuration_object = ConfigurationBase(configuration=configuration)
        with self.Session() as session:
            session.add(configuration_object)
            session.commit()

    def insert_experiment(
        self,
        config_id: int,
        description: str | None = None,
        experiment_type: str | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> None:
        if started_at is None:
            started_at = datetime.now(ZoneInfo("UTC"))
        if ended_at is None:
            ended_at = datetime.now(ZoneInfo("UTC"))
        experiment_object = ExperimentBase(
            config_id=config_id,
            description=description,
            type=experiment_type,
            started_at=started_at,
            ended_at=ended_at,
        )
        with self.Session() as session:
            session.add(experiment_object)
            session.commit()

    def insert_loader(  # noqa: PLR0913
        self,
        experiment_id: int,
        command: str,
        result: dict[str, Any],
        description: str | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> None:
        if started_at is None:
            started_at = datetime.now(ZoneInfo("UTC"))
        if ended_at is None:
            ended_at = datetime.now(ZoneInfo("UTC"))
        loader_object = LoaderBase(
            experiment_id=experiment_id,
            command=command,
            result=result,
            description=description,
            started_at=started_at,
            ended_at=ended_at,
        )
        with self.Session() as session:
            session.add(loader_object)
            session.commit()

    def insert_observer(  # noqa: PLR0913
        self,
        experiment_id: int,
        command: str,
        result: dict[str, Any],
        description: str | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> None:
        if started_at is None:
            started_at = datetime.now(ZoneInfo("UTC"))
        if ended_at is None:
            ended_at = datetime.now(ZoneInfo("UTC"))
        observer_object = ObserverBase(
            experiment_id=experiment_id,
            command=command,
            result=result,
            description=description,
            started_at=started_at,
            ended_at=ended_at,
        )
        with self.Session() as session:
            session.add(observer_object)
            session.commit()

    def return_table(self, table_name: str):
        with self.Session() as session:
            models = {
                "configurations": ConfigurationBase,
                "experiments": ExperimentBase,
                "loaders": LoaderBase,
                "observers": ObserverBase,
            }
            if table_name not in models:
                logger.error("Table '%s' doesn't exist.", table_name)

            return session.query(models[table_name]).all()
