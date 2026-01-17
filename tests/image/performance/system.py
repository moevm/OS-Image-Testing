import logging
from concurrent.futures import ThreadPoolExecutor

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders import PhoronixTestSuite, setup_pts

logger = logging.getLogger(__name__)


def test_pts_system(executor: ThreadPoolExecutor, client: SSHClient | None) -> None:
    pts = PhoronixTestSuite(client)
    future = executor.submit(setup_pts, client)
    future.result()

    future = executor.submit(pts.run, test_name="pts/ctx-clock", run_count=1)
    result = future.result()
    logger.info(result)

    future = executor.submit(pts.run, test_name="pts/appleseed", run_count=1)
    result = future.result()
    logger.info(result)
