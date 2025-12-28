import pytest

from imgtests.exec.exec import ExecResult
from imgtests.exec.loaders.chaosblade import Chaosblade, ChaosResponse


@pytest.mark.parametrize(
    ("raw_result", "expected"),
    [
        (
            '{"code":200,"success":true,"result":"1e6896ba9979b93c"}\n',
            ChaosResponse(code=200, success=True, result="1e6896ba9979b93c", error=None),
        ),
        (
            '{"code":200,"success":true,"result":{"Uid":"1e6896ba9979b93c",'
            '"Command":"cpu","SubCommand":"fullload",'
            '"Flag":" --timeout=2 --cpu-percent=2","Status":"Destroyed",'
            '"Error":"","CreateTime":"2025-12-23T15:16:42.81615009+03:00",'
            '"UpdateTime":"2025-12-23T15:16:46.833154462+03:00"}}\n',
            ChaosResponse(
                code=200,
                success=True,
                result={
                    "Uid": "1e6896ba9979b93c",
                    "Command": "cpu",
                    "SubCommand": "fullload",
                    "Flag": " --timeout=2 --cpu-percent=2",
                    "Status": "Destroyed",
                    "Error": "",
                    "CreateTime": "2025-12-23T15:16:42.81615009+03:00",
                    "UpdateTime": "2025-12-23T15:16:46.833154462+03:00",
                },
                error=None,
            ),
        ),
        (
            '{"code":200,"success":true,"result":"command: cpu fullload  '
            "--timeout=2 --cpu-percent=2, destroy time: "
            '2025-12-23T15:16:46.833154462+03:00"}\n',
            ChaosResponse(
                code=200,
                success=True,
                result=(
                    "command: cpu fullload  --timeout=2 --cpu-percent=2, "
                    "destroy time: 2025-12-23T15:16:46.833154462+03:00"
                ),
                error=None,
            ),
        ),
        (
            '{"code":200,"success":true,"result":"[success] cpu fullload, '
            'success! `taskset` command exists"}\n',
            ChaosResponse(
                code=200,
                success=True,
                result="[success] cpu fullload, success! `taskset` command exists",
                error=None,
            ),
        ),
        (
            "",
            ChaosResponse(code=0, success=False, result=None, error="No output"),
        ),
        (
            "Not a valid JSON response",
            ChaosResponse(
                code=500,
                success=False,
                result=None,
                error="Failed to parse: Not a valid JSON response",
            ),
        ),
    ],
    ids=[
        "Experiment result",
        "Status result",
        "Destroy result",
        "Check result",
        "Empty result",
        "Invalid result",
    ],
)
def test_parse_metrics(raw_result: ExecResult, expected: ChaosResponse) -> None:
    result = Chaosblade.parse_result(raw_result)
    assert result == expected
