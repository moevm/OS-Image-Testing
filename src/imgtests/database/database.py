import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal, get_args

from deepdiff import DeepDiff
from pydantic import Field
from pydantic_settings import BaseSettings
from sqlalchemy import and_, create_engine
from sqlalchemy.orm import selectinload, sessionmaker

from imgtests.database.models.base import Base
from imgtests.database.models.configuration import ConfigurationBase
from imgtests.database.models.experiment import ExperimentBase, ExperimentType
from imgtests.database.models.util_run_result import UtilRunResult, UtilType

if TYPE_CHECKING:
    from imgtests.sysrep import SystemInfo
    from imgtests.types import TestsCounts

logger = logging.getLogger(__name__)
Table = Literal["configurations", "experiments", "util_run_result"]


class PostgresCreds(BaseSettings):
    user: str = Field(validation_alias="POSTGRES_USER")
    password: str = Field(validation_alias="POSTGRES_PASSWORD")
    database_name: str = Field(validation_alias="POSTGRES_DB")
    host: str = Field(validation_alias="POSTGRES_HOST")
    port: int = Field(validation_alias="POSTGRES_PORT", ge=0, le=65535)


class ImgtestsDatabase:
    def __init__(self, database: str = "postgres") -> None:
        if database == "postgres":
            creds = PostgresCreds()
            self.initialize_postgres(creds)
        else:
            logger.error("Incorrect database name.")

    def initialize_postgres(self, creds: PostgresCreds) -> None:
        db_url = (
            f"postgresql+psycopg://{creds.user}:{creds.password}"
            f"@{creds.host}:{creds.port}/{creds.database_name}"
        )
        self.engine = create_engine(db_url)
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
        return self.insert_configuration(db_os, db_pkgs, db_cinfo, db_kconf, sys_info.hardware)

    def insert_configuration(
        self,
        os: str,
        packages: dict[str, Any] | None = None,
        core_info: str | None = None,
        core_config: dict[str, Any] | None = None,
        hardware: dict[str, Any] | None = None,
    ) -> ConfigurationBase:
        with self.session() as session:
            configuration_objects = (
                session.query(ConfigurationBase)
                .filter(
                    and_(
                        ConfigurationBase.os == os,
                        ConfigurationBase.core_info == core_info,
                    ),
                )
                .all()
            )
            for configuration_object in configuration_objects:
                if (
                    configuration_object.packages == packages
                    and configuration_object.core_config == core_config
                    and len(DeepDiff(configuration_object.hardware, hardware)) == 0
                ):
                    logger.info(
                        "Configuration already exists, returning existing object with id %d.",
                        configuration_object.config_id,
                    )
                    return configuration_object
        configuration_object = ConfigurationBase(
            os=os,
            packages=packages,
            core_info=core_info,
            core_config=core_config,
            hardware=hardware,
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
            started_at = datetime.now(UTC)
        if ended_at is None:
            ended_at = datetime.now(UTC)

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

    def insert_util_run_result(  # noqa: PLR0913
        self,
        experiment_id: int,
        util_type: UtilType,
        command: str,
        result: dict[str, Any],
        description: str,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
    ) -> UtilRunResult:
        if started_at is None:
            started_at = datetime.now(UTC)
        if ended_at is None:
            ended_at = datetime.now(UTC)

        logger.debug("Inserting test '%s' results into experiment '%d'.", command, experiment_id)
        util_run_result = UtilRunResult(
            experiment_id=experiment_id,
            util_type=util_type,
            command=command,
            result=result,
            description=description,
            started_at=started_at,
            ended_at=ended_at,
        )

        self._check_session()
        with self.session() as session:
            session.add(util_run_result)
            session.commit()
            session.refresh(util_run_result)
        return util_run_result

    def update_experiment_ended_at(
        self,
        experiment_id: int,
        ended_at: datetime | None = None,
    ) -> None:
        if ended_at is None:
            ended_at = datetime.now(UTC)

        self._check_session()
        with self.session() as session:
            experiment = session.query(ExperimentBase).filter_by(experiment_id=experiment_id).one()
            experiment.ended_at = ended_at
            session.commit()

    def update_experiment_tests_count(self, experiment_id: int, counts: TestsCounts) -> None:
        self._check_session()
        with self.session() as session:
            experiment = session.query(ExperimentBase).filter_by(experiment_id=experiment_id).one()
            experiment.tests_total = counts.total_count
            experiment.tests_passed = counts.passed_count
            experiment.tests_failed = counts.failed_count
            experiment.tests_broken = counts.broken_count
            experiment.tests_skipped = counts.skip_count
            session.commit()

    def return_table(self, table_name: Table) -> list[Any]:
        available_tables = get_args(Table)
        if table_name not in available_tables:
            err_msg = f"Table name not in list of valid tables. Available: {available_tables}."
            raise ValueError(err_msg)

        self._check_session()
        with self.session() as session:
            models: dict[
                Table,
                type[ConfigurationBase | ExperimentBase | UtilRunResult],
            ] = {
                "configurations": ConfigurationBase,
                "experiments": ExperimentBase,
                "util_run_result": UtilRunResult,
            }
            if table_name not in models:
                logger.error("Table '%s' doesn't exist.", table_name)

            return session.query(models[table_name]).all()

    def get_experiment_with_details(self, experiment_id: int) -> ExperimentBase:
        """Gets a single experiment with all related entities.

        Args:
            experiment_id (int): id of the experiment to retrieve.

        Return:
            ExperimentBase: experiment object with configuration, util_run_results.
        """
        self._check_session()
        with self.session() as session:
            return (
                session.query(ExperimentBase)
                .options(
                    selectinload(ExperimentBase.configuration),
                    selectinload(ExperimentBase.util_run_results),
                )
                .filter(ExperimentBase.experiment_id == experiment_id)
                .one()
            )

    def _check_session(self) -> None:
        if not hasattr(self, "session") or self.session is None:
            error_message = "Database session not initialized."
            raise RuntimeError(error_message)
