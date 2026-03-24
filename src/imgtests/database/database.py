import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, get_args
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from imgtests.database.models.base import Base
from imgtests.database.models.configuration import ConfigurationBase
from imgtests.database.models.experiment import ExperimentBase
from imgtests.database.models.loader import LoaderBase
from imgtests.database.models.observer import ObserverBase

if TYPE_CHECKING:
    from imgtests.sysrep import SystemInfo

logger = logging.getLogger(__name__)
Table = Literal["configurations", "experiments", "loaders", "observers"]
ExperimentType = Literal["performance", "endurance", "all"]


class PostgresCreds(BaseSettings):
    user: str = Field(validation_alias="POSTGRES_USER")
    password: str = Field(validation_alias="POSTGRES_PASSWORD")
    database_name: str = Field(validation_alias="POSTGRES_DB")
    host: str = Field(validation_alias="POSTGRES_HOST")
    port: int = Field(validation_alias="POSTGRES_PORT")


class ImgtestsDatabase:
    def __init__(self, database: str = "postgres") -> None:
        if database == "postgres":
            creds = PostgresCreds()
            self.initialize_postgres(creds)
        else:
            logger.error("Incorrect database name.")

    def initialize_postgres(self, creds: PostgresCreds) -> None:
        self.engine = create_engine(
            f"postgresql+psycopg://{creds.user}:{creds.password}@{creds.host}:{creds.port}/{creds.database_name}"
        )
        self.session = sessionmaker(self.engine)
        Base.metadata.create_all(self.engine)

    def insert_from_system_info(self, sys_info: SystemInfo) -> ConfigurationBase:
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
        return self.insert_configuration(db_os, db_pkgs, db_cinfo, db_kconf)

    def insert_configuration(
        self,
        os: str,
        packages: dict[str, Any] | None = None,
        core_info: str | None = None,
        core_config: dict[str, Any] | None = None,
    ) -> ConfigurationBase:
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
            session.refresh(configuration_object)
        return configuration_object

    def insert_experiment(
        self,
        config_id: int,
        description: str,
        experiment_type: ExperimentType,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> ExperimentBase:
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
            session.refresh(experiment_object)
        return experiment_object

    def insert_loader(  # noqa: PLR0913
        self,
        experiment_id: int,
        command: str,
        result: dict[str, Any],
        description: str,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> LoaderBase:
        if started_at is None:
            started_at = datetime.now(ZoneInfo("UTC"))
        if ended_at is None:
            ended_at = datetime.now(ZoneInfo("UTC"))

        logger.debug("Inserting test '%s' results into experiment '%d'.", command, experiment_id)
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
            session.refresh(loader_object)
        return loader_object

    def insert_observer(  # noqa: PLR0913
        self,
        experiment_id: int,
        command: str,
        result: dict[str, Any],
        description: str,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> ObserverBase:
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
            session.refresh(observer_object)
        return observer_object

    def update_experiment_ended_at(self, experiment_id: int) -> None:
        self._check_session()
        with self.session() as session:
            experiment = session.query(ExperimentBase).filter_by(experiment_id=experiment_id).one()
            experiment.ended_at = datetime.now(tz=ZoneInfo("UTC"))
            session.commit()

    def return_table(self, table_name: Table) -> list[Any]:
        available_tables = get_args(Table)
        if table_name not in available_tables:
            err_msg = f"Table name not in list of valid tables. Available: {available_tables}."
            raise ValueError(err_msg)

        self._check_session()
        with self.session() as session:
            models: dict[
                Table, type[ConfigurationBase | ExperimentBase | LoaderBase | ObserverBase]
            ] = {
                "configurations": ConfigurationBase,
                "experiments": ExperimentBase,
                "loaders": LoaderBase,
                "observers": ObserverBase,
            }
            if table_name not in models:
                logger.error("Table '%s' doesn't exist.", table_name)

            return session.query(models[table_name]).all()

    def _check_session(self) -> None:
        if not hasattr(self, "session") or self.session is None:
            error_message = "Database session not initialized."
            raise RuntimeError(error_message)
