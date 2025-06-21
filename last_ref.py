import os, time, json
from selenium import webdriver
from larkmsg import send_message
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class A:
    def __init__(self) -> None:
        self.init_config()
        self.init_info()
        self.tele_time = ""
        self.push_warn = False
        self._is_warning = False
        self._last_warning = False
        self._last_update = time.time()

    def init_info(self):
        self.obs_info = ""
        self.warn_info = ""
        self.daily_info = self.formatter["daily"]["info"]

    def init_config(self):
        with open("./config.json", "r", encoding="utf-8") as f:
            self.config = json.loads("".join(f.readlines()))
        self.credit = self.config["credentials"]
        self.formatter = self.config["formatter"]
        self.expected = self.config["expected"]
        settings = self.config["settings"]
        self.update_interval = settings["tele time"]
        self.update_warn_time = settings["updated warn time"]
        self.update_time = settings["daily time"]
        self.obs_grp = settings["grp"]["obs"]
        self.warn_grp = settings["grp"]["warn"]
        self.daily_grp = settings["grp"]["daily"]
        self.cur_obs_num = self.expected["TMZT0023"]["record"]

    def warn_add(self, str):
        self._is_warning = True
        self.push_warn = True
        if self.warn_info == "":
            self.warn_info = self.formatter["warn"]["warn"]
        self.warn_info += str

    def process_data(self, cur_time, tele_time, all_data):
        self._last_warning = self._is_warning
        self._is_warning = False
        self.push_warn = False
        self.tele_time = tele_time
        self._last_update = time.mktime(time.strptime(tele_time, r"%Y-%m-%d %H:%M:%S"))
        if cur_time - self._last_update > self.update_warn_time:
            self.warn_add(self.formatter["overtime"]["warn"].replace("last_time", tele_time).replace("warn_interval", str(self.update_warn_time)) + "\n")
        for i in range(len(all_data)):
            try:
                info = self.expected.get(all_data[i][0])
                self.daily_info += f"{all_data[i][1]}:\t{all_data[i][2]}\n"
                ty = info["type"]
            except:
                self.deal_new(all_data[i][1], all_data[i][2])
                continue
            if ty == "state":
                self.deal_state(all_data[i][2])
            elif ty == "trigger":
                self.deal_trigger(int(float(all_data[i][2])))
            elif ty == "match":
                if all_data[i][2] != self.expected[all_data[i][0]]["match"]:
                    self.deal_nozero(all_data[i][1], all_data[i][2])
            elif ty == "nozero":
                if int(all_data[i][2]) == 0:
                    self.deal_nozero(all_data[i][1], all_data[i][2])
            elif ty == "record":
                self.deal_record(all_data[i][0], all_data[i][1], int(all_data[i][2]))
            elif ty == "minmax":
                self.deal_minmax(all_data[i][0], all_data[i][1], float(all_data[i][2]))
        if self._last_warning and not self._is_warning:
            self.push_warn = True
            self.warn_info = self.formatter["warn"]["info"]

    def deal_new(self, name, value):
        self.warn_add(self.formatter["new"]["warn"].replace("name", name).replace("value", value) + "\n")

    def deal_state(self, obs_type):
        types = self.expected["TMZT0022"]
        if obs_type in types["normal"]:
            self.obs_info += self.formatter["state"]["normal"]["info"].replace("cur_utc", self.tele_time).replace("obs_type", obs_type)
        elif obs_type in types["xrt"]:
            self.obs_info += self.formatter["state"]["xrt"]["info"].replace("cur_utc", self.tele_time).replace("obs_type", obs_type)
        else:
            self.obs_info += self.formatter["state"]["unusual"]["info"].replace("cur_utc", self.tele_time).replace("obs_type", obs_type)

    def deal_trigger(self, obs_num):
        if self.cur_obs_num == obs_num:
            self.obs_info = ""
        else:
            self.cur_obs_num = obs_num
            self.obs_info = self.obs_info.replace("obs_num", str(obs_num))
            self.update_record("TMZT0023", "", obs_num)

    def deal_nozero(self, name, value):
        self.warn_add(self.formatter["nozero"]["warn"].replace("name", name).replace("value", value) + "\n")

    def deal_record(self, code, name, value):
        record = self.expected[code]["record"]
        if value > record:
            self.warn_add(self.formatter["record"]["warn"].replace("name", name).replace("value", str(value)).replace("record", str(record)) + "\n")
            self.update_record(code, name, value, True)

    def update_record(self, code, name, value, push=False):
        if push:
            self.warn_add(self.formatter["update"]["info"].replace("name", name).replace("value", str(value)) + "\n")
        self.expected[code]["record"] = value
        config_str = json.dumps(self.config, ensure_ascii=False, indent=4, separators=(",", ": "))
        with open("./config.json", "w", encoding="utf-8") as f:
            f.write(config_str)

    def deal_minmax(self, code, name, value):
        vmin = self.expected[code]["min"]
        vmax = self.expected[code]["max"]
        if value < vmin:
            self.warn_add(self.formatter["minmax"]["warn"][0].replace("name", name).replace("min", str(vmin)).replace("value", str(value)) + "\n")
        if value > vmax:
            self.warn_add(self.formatter["minmax"]["warn"][1].replace("name", name).replace("max", str(vmax)).replace("value", str(value)) + "\n")

    def warn_init(self):
        self.is_warning = True
        if self.warn_info == "":
            self.warn_info = self.formatter["warn"]["warn"]


class B:
    def __init__(self, url, username, password) -> None:
        self.last_update = time.time()
        self.driver = self.init_driver()
        self.login(url, username, password)
        self.load_page()

    def read_data(self):
        all_read = self.get_table()
        tele_time = all_read[0].find_elements(By.TAG_NAME, "td")[6].text.split(".")[0]
        all_data = []
        for tr in all_read:
            tds = tr.text.split()
            all_data.append((tds[0], tds[1], tds[2]))
        return tele_time, all_data

    def init_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        return webdriver.Chrome(options=options)

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
            time.sleep(0.3)
        self.wait(EC.presence_of_element_located((By.CLASS_NAME, "topNav")))
        time.sleep(2)
        # 切换至监视页面
        while True:
            try:
                self.js("changePage(1)")
                time.sleep(0.1)
                temp = self.element("class", "active")
            except:
                continue
            if temp.text == "任务监视":
                break
            time.sleep(0.3)
        self.driver.get(self.element("tag", "iframe").get_property("src"))
        self.wait(EC.presence_of_element_located((By.CLASS_NAME, "el-submenu")))
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


class C:
    def __init__(self, a_B: None) -> None:
        self.gettime()
        self.update_config()
        if a_B:
            self.B = a_B
        else:
            self.B = B(self.A.credit["url"], self.A.credit["username"], self.A.credit["password"])

    def time_run(self):
        while True:
            tele_time, all_data = self.B.read_data()
            self.A.init_info()
            self.A.process_data(time.time(), tele_time, all_data)

            self.push_obs()

            if self.A.push_warn:
                self.push_warn()

            if self.do_daily_push():
                self.push_daily()

            self.cal_sleep_time()
            time.sleep(self.sleep_time)

    def cal_sleep_time(self):
        t0 = (time.time() - 57600) % (self.interval_time)
        self.sleep_time = self.interval_time - t0

    def push_obs(self):
        if not self.A.obs_info == "":
            send_message(self.A.obs_grp, self.A.obs_info)

    def push_warn(self):
        send_message(self.A.warn_grp, self.A.warn_info)

    def push_daily(self):
        send_message(self.A.daily_grp, self.A.daily_info)

    def do_daily_push(self):
        temp = False
        for i in range(self.daily_len):
            if self.daily_push[i] and self.cur_time >= self.daily_list[i]:
                temp = True
                self.daily_push[i] = False
        return temp

    def update_config(self):
        """
        更新config
        """
        self.A = A()
        self.interval_time = self.A.update_interval / 10

        try:
            self.__getattribute__("daily_list")
        except:
            self.init_daily_list()
            return

        if self.daily_list != self.A.update_time:
            self.init_daily_list()
        else:
            self.init_daily_list(False)

    def init_daily_list(self, force=True):
        temp = (self.interval_time / 3600) * 0.9
        if force:
            self.daily_list = self.A.update_time
            self.daily_len = len(self.daily_list)
        self.daily_push = [True for _ in self.daily_list]
        for i in range(self.daily_len):
            if self.cur_time > self.daily_list[i] + temp:
                self.daily_push[i] = False

    def gettime(self):
        """
        更新类的共有时间cur_time，并每四个小时的前6min更新config
        """
        self.cur_time = self.current_time()
        if self.cur_time % 4 < 0.1:
            self.update_config()

    def current_time(self) -> int:
        """
        返回以小时计的当前时间，以当天0000为起点
        """
        return (time.time() - 57600) % (24 * 3600) / 3600


if __name__ == "__main__":
    with open("pid.txt", "w") as f:
        f.write(str(os.getpid()))

    C().time_run()
