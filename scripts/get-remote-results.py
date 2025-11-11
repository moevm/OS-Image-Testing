from imgtests.exec.exec import SSHClient

ssh_client = SSHClient("10.5.0.10", root, "", 2222)
ssh_client.download(remotepath="/root/results_file", localpath="/home/user/results_file")
