import os
from typing import Final
from imgtests.exec.exec import SSHClient

PASSWORD: Final = os.environ.get("SSH_PASSWORD")
USER: Final = os.environ.get("SSH_USER")

ssh_client = SSHClient("10.5.0.10", USER, PASSWORD, 22)
ssh_client.download(remotepath="/home/user/results_file", localpath="/home/user/results_file")
