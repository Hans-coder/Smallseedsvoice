from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')

driver = webdriver.Chrome(options=options)
driver.get('https://tixcraft.com/activity')
time.sleep(3)
html = driver.page_source
driver.quit()

with open("tix.html", "w") as f:
    f.write(html)
