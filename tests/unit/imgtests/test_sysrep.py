from imgtests.sysrep import OsInfo
from imgtests.types import Version


def test_osinfo_str() -> None:
    assert str(OsInfo("ubuntu", Version("20.04"))) == "ubuntu 20.4"
