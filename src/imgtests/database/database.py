import logging
import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from imgtests.database.models.base import Base
from imgtests.database.models.configuration import ConfigurationBase
from imgtests.database.models.experiment import ExperimentBase
from imgtests.database.models.loader import LoaderBase
from imgtests.database.models.observer import ObserverBase
from imgtests.sysrep import SystemInfo

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, database: str = "postgres") -> None:
        if database == "postgres":
            self.initialize_postgres()
        else:
            logger.error("Incorrect database name.")

    def initialize_postgres(self) -> None:
        user = os.environ["POSTGRES_USER"].strip()
        password = os.environ["POSTGRES_PASSWORD"].strip()
        db_name = os.environ["POSTGRES_DB"].strip()
        host = os.environ["POSTGRES_HOST"].strip()
        port = os.environ["SSH_POSTGRES_PORT"].strip()
        self.engine = create_engine(
            f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"
        )
        self.session = sessionmaker(self.engine)
        Base.metadata.create_all(self.engine)

    def _check_session(self) -> None:
        if not hasattr(self, "session") or self.session is None:
            error_message = "Database session not initialized."
            raise RuntimeError(error_message)

    def insert_from_system_info(self, sys_info: SystemInfo) -> None:
        db_os = str(sys_info.os_info)
        db_cinfo = str(sys_info.uname_info)
        db_pkgs: dict[str, str] = {}
        for line in sys_info.package_list:
            to_dict_tuple = (line.split()[0], line.split()[1])
            db_pkgs[to_dict_tuple[0]] = to_dict_tuple[1]
        db_kconf: dict[str, str] = {}
        for line in sys_info.kernel_config:
            if line:
                if line[0] == "#":
                    if line[0:8] == "# CONFIG":
                        db_kconf[line.split()[1]] = "not set"
                else:
                    idx = line.find("=")
                    to_dict_tuple = (line[0:idx], line[idx + 1 :])
                    db_kconf[line[0:idx]] = line[idx + 1 :]
        self.insert_configuration(db_os, db_pkgs, db_cinfo, db_kconf)

    def insert_configuration(
        self,
        os: str,
        packages: dict[str, Any] | None = None,
        core_info: str | None = None,
        core_config: dict[str, Any] | None = None,
    ) -> None:
        configuration_object = ConfigurationBase(
            os=os,
            packages=packages,
            core_info=core_info,
            core_config=core_config,
        )

        self._check_session()
        with self.session() as session:
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

        self._check_session()
        with self.session() as session:
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

        self._check_session()
        with self.session() as session:
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

        self._check_session()
        with self.session() as session:
            session.add(observer_object)
            session.commit()

    def return_table(self, table_name: str):
        self._check_session()
        with self.session() as session:
            models = {
                "configurations": ConfigurationBase,
                "experiments": ExperimentBase,
                "loaders": LoaderBase,
                "observers": ObserverBase,
            }
            if table_name not in models:
                logger.error("Table '%s' doesn't exist.", table_name)

            return session.query(models[table_name]).all()
