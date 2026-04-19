import logging
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, get_args
from zoneinfo import ZoneInfo

from deepdiff import DeepDiff
from pydantic import Field
from pydantic_settings import BaseSettings
from sqlalchemy import and_, create_engine
from sqlalchemy.orm import sessionmaker

from imgtests.database.models.base import Base
from imgtests.database.models.configuration import ConfigurationBase
from imgtests.database.models.experiment import ExperimentBase
from imgtests.database.models.util_run_result import UtilRunResult, UtilType

if TYPE_CHECKING:
    from imgtests.sysrep import SystemInfo
    from imgtests.types import TestsCounts

logger = logging.getLogger(__name__)
Table = Literal["configurations", "experiments", "util_run_result"]
ExperimentType = Literal["performance", "endurance", "all"]
CommandValue = str | Sequence[str]


@dataclass(frozen=True)
class UtilityMetricRecord:
    metric_name: str
    value: float
    context: dict[str, Any] | None = None
    description: str | None = None
    command: CommandValue | None = None


@dataclass(frozen=True)
class UtilityResultRecord:
    experiment_id: int
    utility: str
    command: CommandValue
    result: Any
    started_at: datetime
    ended_at: datetime
    description: str | None = None
    context: dict[str, Any] | None = None
    metrics: tuple[UtilityMetricRecord, ...] = ()


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
            (
                f"postgresql+psycopg://{creds.user}:{creds.password}"
                f"@{creds.host}:{creds.port}/{creds.database_name}"
            ),
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
            started_at = datetime.now(ZoneInfo("UTC"))
        if ended_at is None:
            ended_at = datetime.now(ZoneInfo("UTC"))

        experiment_object = ExperimentBase(
            config_id=config_id,
            description=_validate_db_str(description),
            type=_validate_db_str(experiment_type),
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
            started_at = datetime.now(ZoneInfo("UTC"))
        if ended_at is None:
            ended_at = datetime.now(ZoneInfo("UTC"))

        logger.debug("Inserting test '%s' results into experiment '%d'.", command, experiment_id)
        util_run_result = UtilRunResult(
            experiment_id=experiment_id,
            util_type=util_type,
            command=_validate_db_str(command),
            result=_coerce_db_payload(result),
            description=_validate_db_str(description),
            started_at=started_at,
            ended_at=ended_at,
        )

        self._check_session()
        with self.session() as session:
            session.add(util_run_result)
            session.commit()
            session.refresh(util_run_result)
        return util_run_result

    def insert_metric_observation(
        self,
        experiment_id: int,
        utility: str,
        metric: UtilityMetricRecord,
        started_at: datetime,
        ended_at: datetime,
    ) -> UtilRunResult:
        payload: dict[str, Any] = {
            "utility": utility,
            "metric_name": metric.metric_name,
            "value": float(metric.value),
        }
        if metric.context:
            payload.update(_normalize_db_mapping(metric.context))

        if metric.command is not None:
            payload["command"] = _normalize_command_json(metric.command)

        command_label = (
            _command_db_label(metric.command, fallback=utility)
            if metric.command is not None
            else f"{utility}:{metric.metric_name}"
        )

        return self.insert_util_run_result(
            experiment_id=experiment_id,
            util_type="observer",
            command=command_label,
            result=payload,
            description=metric.description or "Observed numeric metric",
            started_at=started_at,
            ended_at=ended_at,
        )

    def insert_utility_result(
        self,
        record: UtilityResultRecord,
    ) -> tuple[UtilRunResult, tuple[UtilRunResult, ...]]:
        result_payload = _coerce_db_payload(record.result)
        result_payload.setdefault("utility", record.utility)
        result_payload.setdefault("command", _normalize_command_json(record.command))

        if record.context:
            for key, value in _normalize_db_mapping(record.context).items():
                result_payload.setdefault(key, value)

        loader = self.insert_util_run_result(
            experiment_id=record.experiment_id,
            util_type="loader",
            command=_command_db_label(record.command, fallback=record.utility),
            result=result_payload,
            description=record.description or f"{record.utility} result",
            started_at=record.started_at,
            ended_at=record.ended_at,
        )

        observers = tuple(
            self.insert_metric_observation(
                experiment_id=record.experiment_id,
                utility=record.utility,
                metric=metric,
                started_at=record.started_at,
                ended_at=record.ended_at,
            )
            for metric in record.metrics
        )
        return loader, observers

    def update_experiment_ended_at(
        self,
        experiment_id: int,
        ended_at: datetime | None = None,
    ) -> None:
        if ended_at is None:
            ended_at = datetime.now(tz=ZoneInfo("UTC"))

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

    def _check_session(self) -> None:
        if not hasattr(self, "session") or self.session is None:
            error_message = "Database session not initialized."
            raise RuntimeError(error_message)


def _validate_db_str(value: str, limit: int = 200) -> str:
    s = str(value)
    if len(s) > limit:
        err_msg = f"Value is too long for DB field: {len(s)} > {limit}. Text: {s}"
        raise ValueError(err_msg)
    return s


def _normalize_command_json(command: CommandValue) -> str | list[str]:
    if isinstance(command, str):
        return command
    return [str(part) for part in command]


def _command_db_label(command: CommandValue, fallback: str) -> str:
    if isinstance(command, str):
        parts = command.strip().split()
        return parts[0] if parts else fallback

    for part in command:
        text = str(part).strip()
        if text:
            return text

    return fallback


def _normalize_db_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _normalize_db_value(value) for key, value in mapping.items()}


def _coerce_db_payload(value: Any) -> dict[str, Any]:
    normalized = _normalize_db_value(value)
    if isinstance(normalized, dict):
        return normalized
    if isinstance(normalized, list):
        return {"items": normalized}
    return {"value": normalized}


def _normalize_db_value(value: Any) -> Any:
    normalized: Any

    if value is None or isinstance(value, (str, int, float, bool)):
        normalized = value
    elif isinstance(value, Path):
        normalized = str(value)
    elif isinstance(value, dict):
        normalized = {str(key): _normalize_db_value(val) for key, val in value.items()}
    elif is_dataclass(value):
        normalized = _normalize_db_value(asdict(value))
    elif hasattr(value, "_asdict"):
        normalized = _normalize_db_value(value._asdict())
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        normalized = [_normalize_db_value(item) for item in value]
    else:
        normalized = str(value)

    return normalized
