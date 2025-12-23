import requests
import re
import sys
from bs4 import BeautifulSoup

url = "https://download.opensuse.org/repositories/Cloud:/Images:/Leap_" + sys.argv[1] + "/images/"

response = requests.get(url, timeout=30)
soup = BeautifulSoup(response.content, 'html.parser')

re_patt = r"openSUSE-Leap-15\.6\.x86_64-1\.0\.2-NoCloud-Build.{1,8}qcow2"
if sys.argv[1] == "15.5":
    re_patt = r"openSUSE-Leap-15\.5\.x86_64-1\.0\.1-NoCloud-Build.{1,8}qcow2"

err_msg = "No correct image!"

res = soup.find('td', class_="name", string=re.compile(re_patt))
if (res):
    print(res.get_text().strip())
else:
    raise SystemError(err_msg)