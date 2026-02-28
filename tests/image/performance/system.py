import logging
from typing import TYPE_CHECKING

from imgtests.exec.loaders import PhoronixTestSuite

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from imgtests.exec.exec import SSHClient


logger = logging.getLogger(__name__)


def test_pts_system(executor: ThreadPoolExecutor, client: SSHClient | None) -> None:
    pts = PhoronixTestSuite(client)
    future = executor.submit(pts.prepare)
    future.result()

    future = executor.submit(pts.run, test_name="pts/ctx-clock", run_count=1)
    _, result = future.result()
    logger.info(PhoronixTestSuite.parse_metrics(result))

    future = executor.submit(pts.run, test_name="pts/appleseed", run_count=1)
    _, result = future.result()
    logger.info(PhoronixTestSuite.parse_metrics(result))
