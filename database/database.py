import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

from database.models.base import Base
from database.models.configuration import ConfigurationBase
from database.models.experiment import ExperimentBase
from database.models.loader import LoaderBase
from database.models.observer import ObserverBase
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        user = os.environ['POSTGRES_USER'].strip()
        password = os.environ['POSTGRES_PASSWORD'].strip()
        db_name = os.environ['POSTGRES_DB'].strip()
        host = 'imgtests-postgres'
        port = os.environ['SSH_POSTGRES_PORT'].strip()
        self.engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db_name}")
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
        started_at: datetime = datetime.now(ZoneInfo('UTC')),
        ended_at: datetime = datetime.now(ZoneInfo('UTC')),
    ) -> None:
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
        started_at: datetime = datetime.now(ZoneInfo('UTC')),
        ended_at: datetime = datetime.now(ZoneInfo('UTC')),
    ) -> None:
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
        started_at: datetime = datetime.now(ZoneInfo('UTC')),
        ended_at: datetime = datetime.now(ZoneInfo('UTC')),
    ) -> None:
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
