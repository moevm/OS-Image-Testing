import logging
from concurrent.futures import ThreadPoolExecutor

from imgtests.exec.exec import SSHClient
from imgtests.exec.loaders.pts import PhoronixTestSuite, setup_pts

logger = logging.getLogger(__name__)


def run_pts_tests(executor: ThreadPoolExecutor, client: SSHClient | None = None) -> None:
    pts = PhoronixTestSuite(client)
    future = executor.submit(setup_pts, client)
    future.result()

    future = executor.submit(pts.run, test_name="pts/ctx-clock", run_count=1)
    try:
        result = future.result()
        logger.info(result)
    except RuntimeError as e:
        logger.error(e)
