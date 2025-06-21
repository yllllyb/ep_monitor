import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class driver_agent:
    def __init__(self) -> None:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(options=options)
        self.has_init = False

    def do_init(self, url, username, password):
        self.login(url, username, password)
        self.load_page()
        self.has_init = True

    def get_data(self):
        all_read = self.get_table()
        tele_time = all_read[0].find_elements(By.TAG_NAME, "td")[6].text.split(".")[0]
        all_data = []
        for tr in all_read:
            tds = tr.text.split()
            all_data.append((tds[0], tds[1], tds[2]))
        return tele_time, all_data

    def login(self, url, username, password):
        self.driver.get(url)
        self.element("name", "username").send_keys(username)
        self.element("name", "password").send_keys(password)
        self.element("id", "input1").send_keys(self.element("id", "checkCode").get_property("value"))
        self.js("submitForm()")
        self.wait(EC.url_contains("cu=ep_ta@naoc"))
        self.wait(EC.presence_of_element_located((By.CLASS_NAME, "ul01")))

    def load_page(self):
        # 切换至ep页面
        while True:
            try:
                self.js("toSatellitePage('KX06')")
                temp = self.element("class", "satelliteClass")
            except:
                continue
            if temp.text == "EP":
                break
            time.sleep(0.5)
        self.wait(EC.presence_of_element_located((By.CLASS_NAME, "topNav")))
        time.sleep(2)
        # 切换至监视页面
        while True:
            try:
                self.js("changePage(1)")
                time.sleep(0.3)
                temp = self.element("class", "active")
            except:
                continue
            if temp.text == "任务监视":
                break
            time.sleep(0.5)
        self.driver.get(self.element("tag", "iframe").get_property("src"))
        self.wait(EC.presence_of_element_located((By.CLASS_NAME, "el-submenu")))
        time.sleep(1)
        # 打开关键载荷页面
        self.init_table()
        while True:
            if self.test_table():
                break
            time.sleep(2)

    def init_table(self):
        menu = self.element("class", "el-submenu")
        if not "is-active" in menu.get_attribute("class"):
            menu.click()
        time.sleep(1)
        self.driver.find_elements(By.CLASS_NAME, "el-menu-item")[2].click()

    def test_table(self):
        return len(self.driver.find_elements(By.TAG_NAME, "table")[1].text.split()) > 300

    def get_table(self):
        return self.driver.find_elements(By.TAG_NAME, "table")[1].find_element(By.TAG_NAME, "tbody").find_elements(By.TAG_NAME, "tr")

    def js(self, command):
        self.driver.execute_script(command)

    def element(self, by, str):
        if by == "name":
            return self.driver.find_element(By.NAME, str)
        elif by == "id":
            return self.driver.find_element(By.ID, str)
        elif by == "tag":
            return self.driver.find_element(By.TAG_NAME, str)
        elif by == "class":
            return self.driver.find_element(By.CLASS_NAME, str)

    def wait(self, condition):
        WebDriverWait(self.driver, 50).until(condition)
