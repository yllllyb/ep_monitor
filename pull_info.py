import time
from selenium import webdriver
from larkmsg import send_message
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC


class driver_agent:
    def __init__(self, debug_grp) -> None:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--start-maximized")
        self.driver = webdriver.Chrome(options=options)
        self.has_init = False
        self.debug_grp = debug_grp

    def do_init(self, url, username, password):
        self.run_util(lambda: self.login(url, username, password), "login")
        self.run_util(self.load_page, "load page")
        self.has_init = True

    def login(self, url, username, password):
        try:
            self.driver.get(url)
            self.element("name", "username").send_keys(username)
            self.element("name", "password").send_keys(password)
            self.element("id", "input1").send_keys(self.element("id", "checkCode").get_property("value"))
            self.js("submitForm()")
            self.wait(EC.url_contains("cu=ep_ta@naoc"))
            self.wait(EC.presence_of_element_located((By.CLASS_NAME, "ul01")))
            return True
        except TimeoutException:
            send_message(self.debug_grp, "time out in login")
            return False

    # 切换至ep页面
    def proc1(self):
        self.js("toSatellitePage('KX06')")
        time.sleep(1)
        try:
            elem = self.element("class", "satelliteClass")
        except:
            return False
        return elem.text == "EP"

    # 切换至监视页面
    def proc2(self):
        self.js("changePage(1)")
        time.sleep(1)
        try:
            elem = self.element("class", "active")
        except:
            return False
        return elem.text == "任务监视"

    def load_page(self):
        try:
            self.run_util(self.proc1, "change to EP page")
            self.wait(EC.presence_of_element_located((By.CLASS_NAME, "topNav")))
            time.sleep(2)

            self.run_util(self.proc2, "change to monitor page")
            self.driver.get(self.element("tag", "iframe").get_property("src"))
            self.wait(EC.presence_of_element_located((By.CLASS_NAME, "el-submenu")))
            time.sleep(1)

            # 打开关键载荷页面
            self.init_table()
            self.run_util(self.test_table, "load table", max_attempts=100, poll_interval=30)

            return True
        except TimeoutException:
            send_message(self.debug_grp, "time out in loadpage")
            return False

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

    def get_data(self):
        all_read = self.get_table()
        tele_time = all_read[0].find_elements(By.TAG_NAME, "td")[6].text.split(".")[0]
        all_data = []
        for tr in all_read:
            tds = tr.text.split()
            all_data.append((tds[0], tds[1], tds[2]))
        return tele_time, all_data

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

    def run_util(self, operation, des, max_attempts=3, poll_interval=1) -> bool:
        """
        重试某个操作，直到成功或达到最大尝试次数
        注意传入函数形式！
        :param operation: 要执行的操作（函数）
        :param max_attempts: 最大尝试次数
        :param des: 操作描述
        """
        for attempt in range(1, max_attempts + 1):
            try:
                if operation():
                    send_message(self.debug_grp, f"{des} 成功")
                    return True
            except Exception as e:
                send_message(self.debug_grp, f"{des} 第 {attempt} 次尝试失败: {e}")
            if attempt < max_attempts:
                time.sleep(poll_interval)
        send_message(self.debug_grp, f"{des} 失败，已达最大尝试次数 ({max_attempts} 次)")
        return False
