from __future__ import annotations

import logging
import os
import sys
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

import paramiko.ssh_exception

from imgtests.database.database import ImgtestsDatabase
from imgtests.exec.exec import wait_remote
from imgtests.logger import set_handlers
from imgtests.planning import LoadPattern, PlanRequest, Subsystem, TestKind, build_plan
from imgtests.planning.executor import PlanExecutor
from imgtests.reporting import generate_html_report

logger = logging.getLogger()
set_handlers(logger, Path("processing.log"))

yocto_conf = (
    "SSH_YOCTO_ADDR",
    "SSH_YOCTO_USER",
    "SSH_YOCTO_PASS",
    "SSH_YOCTO_PORT",
)

PROFILE_ORDER: tuple[TestKind, ...] = (
    TestKind.LOAD,
    TestKind.STRESS,
    TestKind.STABILITY,
    TestKind.SCALABILITY,
    TestKind.VOLUME,
    TestKind.ISOLATED,
    TestKind.SPIKE,
)


@dataclass(frozen=True)
class RunOneParams:
    profile: TestKind
    duration_sec: int
    subsystems: tuple[Subsystem, ...]
    pattern: LoadPattern | None
    results_root: Path


def parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def parse_subsystems(raw: str) -> tuple[Subsystem, ...]:
    value = raw.strip().lower()
    if value == "all":
        return tuple(Subsystem)

    mapping: dict[str, Subsystem] = {
        "cpu": Subsystem.CPU,
        "memory": Subsystem.MEMORY,
        "disk": Subsystem.DISK,
        "network": Subsystem.NETWORK,
        "syscall": Subsystem.SYSCALL,
    }

    out: list[Subsystem] = []
    seen: set[Subsystem] = set()

    for part in [x.strip().lower() for x in value.split(",") if x.strip()]:
        if part not in mapping:
            allowed = ", ".join(mapping)
            msg = f"Unknown subsystem '{part}'. Allowed: {allowed}"
            raise ValueError(msg)

        subsystem = mapping[part]
        if subsystem not in seen:
            out.append(subsystem)
            seen.add(subsystem)

    if not out:
        msg = "No subsystems provided."
        raise ValueError(msg)

    return tuple(out)


def parse_profile(raw: str) -> TestKind:
    try:
        return TestKind(raw.strip().lower())
    except ValueError as exc:
        allowed = ", ".join(x.value for x in TestKind)
        msg = f"Unknown profile '{raw}'. Allowed: {allowed}"
        raise ValueError(msg) from exc


def parse_profiles(raw: str) -> tuple[TestKind, ...]:
    value = raw.strip().lower()
    if value in {"", "all"}:
        return PROFILE_ORDER

    out: list[TestKind] = []
    seen: set[TestKind] = set()

    for part in [x.strip() for x in value.split(",") if x.strip()]:
        profile = parse_profile(part)
        if profile not in seen:
            out.append(profile)
            seen.add(profile)

    if not out:
        msg = "No profiles provided."
        raise ValueError(msg)

    return tuple(out)


def parse_pattern(raw: str | None) -> LoadPattern | None:
    if raw is None:
        return None

    value = raw.strip().lower()
    if value in {"", "auto"}:
        return None

    try:
        return LoadPattern(value)
    except ValueError as exc:
        allowed = ", ".join(x.value for x in LoadPattern)
        msg = f"Unknown pattern '{raw}'. Allowed: {allowed}"
        raise ValueError(msg) from exc


def run_one(
    *,
    client: Any,
    db: ImgtestsDatabase,
    params: RunOneParams,
) -> tuple[int, Path]:
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    run_name = f"{ts}_{params.profile.value}"
    if params.pattern is not None:
        run_name += f"_{params.pattern.value}"

    run_dir = params.results_root / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    req = PlanRequest(
        duration_sec=params.duration_sec,
        subsystems=params.subsystems,
        test_kind=params.profile,
        pattern=params.pattern,
    )
    plan = build_plan(req)

    executor = PlanExecutor(
        client=client,
        db=db,
        results_dir=run_dir,
        experiment_description=f"Profiled plan: {params.profile.value}",
    )
    execution = executor.execute(plan)

    report_dir = run_dir / "html"
    report_path = generate_html_report(plan, execution, report_dir)

    failures = sum(1 for s in execution.stage_runs for t in s.tasks if t.returncode != 0)

    logger.info(
        "[PROFILED] DONE profile=%s pattern=%s duration=%ss failures=%d experiment_id=%s",
        params.profile.value,
        params.pattern.value if params.pattern else "auto",
        params.duration_sec,
        failures,
        execution.experiment_id,
    )
    logger.info("[PROFILED] plan=%s", execution.plan_path)
    logger.info("[PROFILED] report=%s", report_path)

    return failures, report_path


@contextmanager
def _safe_close_client(client: Any) -> Iterator[Any]:
    try:
        yield client
    finally:
        with suppress(Exception):
            client.close()


def _run_main() -> int:
    subsystems = parse_subsystems(os.getenv("PLAN_SUBSYSTEMS", "cpu,memory,disk,network,syscall"))
    results_root = Path(os.getenv("PLAN_RESULTS_DIR", "results/profiled"))
    run_matrix = parse_bool_env("PLAN_RUN_MATRIX", default=False)

    raw_pattern = os.getenv("PLAN_PATTERN")
    pattern = parse_pattern(raw_pattern)

    client = wait_remote(*yocto_conf)
    if client is None:
        logger.error("Failed to connect to Yocto host via SSH.")
        return 1

    with _safe_close_client(client):
        db = ImgtestsDatabase()

        total_failures = 0
        last_report: Path | None = None

        if run_matrix:
            profiles = parse_profiles(os.getenv("PLAN_MATRIX_PROFILES", "all"))
            default_duration = int(os.getenv("PLAN_DURATION_SEC", "120"))

            for profile in profiles:
                env_key = f"PLAN_DURATION_{profile.value.upper()}"
                raw = os.getenv(env_key)
                duration_sec = int(raw) if raw is not None else default_duration

                failures, report_path = run_one(
                    client=client,
                    db=db,
                    params=RunOneParams(
                        profile=profile,
                        duration_sec=duration_sec,
                        subsystems=subsystems,
                        pattern=pattern,
                        results_root=results_root,
                    ),
                )
                total_failures += failures
                last_report = report_path
        else:
            profile = parse_profile(os.getenv("PLAN_PROFILE", "load"))
            duration_sec = int(os.getenv("PLAN_DURATION_SEC", "120"))

            failures, report_path = run_one(
                client=client,
                db=db,
                params=RunOneParams(
                    profile=profile,
                    duration_sec=duration_sec,
                    subsystems=subsystems,
                    pattern=pattern,
                    results_root=results_root,
                ),
            )
            total_failures = failures
            last_report = report_path

        if last_report is not None:
            logger.info("[PROFILED] Last report path: %s", last_report)

        return 1 if total_failures else 0


def main() -> None:
    try:
        exit_code = _run_main()
    except ValueError:
        logger.exception("Invalid config")
        exit_code = 2
    except paramiko.ssh_exception.SSHException:
        logger.exception("SSH error during profiled execution.")
        exit_code = 1
    except Exception:
        logger.exception("Unexpected error during profiled execution.")
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
