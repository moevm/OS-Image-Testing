from imgtests.exec.exec import SSHClient

ssh_client = SSHClient("10.5.0.10", "user", "password", 22)
ssh_client.download(remotepath="/home/user/results_file", localpath="/home/user/results_file")
