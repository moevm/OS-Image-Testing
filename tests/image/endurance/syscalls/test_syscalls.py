from imgtests.exec.loaders.stress_ng import StressNg


def test_syscalls_all_endurance(stress_ng: StressNg) -> None:
    _, (_, _) = stress_ng.run(
        timeout_sec=20,
        syscall=1,
        syscall_method="all",
    )


def test_syscalls_with_other_stressors_parsed_together(stress_ng: StressNg) -> None:
    _, (_, _) = stress_ng.run(
        timeout_sec=20,
        cpu=1,
        cpu_method="all",
        syscall=1,
        syscall_method="all",
    )
