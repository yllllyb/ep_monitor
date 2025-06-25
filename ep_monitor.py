import time
from larkmsg import send_message
from pull_info import driver_agent
from load_config import config_agent


class ep_monitor:
    def __init__(self, dv_agent=None) -> None:
        # 是否报告运行状态
        self.debug = True
        # 是否实际推送信息
        self.push_info = False
        # 读取配置，载入变量
        self.restore()
        # 加载dv_agent，用于读取监控信息
        if dv_agent:
            self.dv_agent = dv_agent
        else:
            self.dv_agent = driver_agent(self.debug_grp)

    def restore(self) -> None:
        """
        加载cf_agent，读取配置文件
        配置推送目标、推送格式
        读取监控范式、监控信息缓存
        适配热更新，即修改配置文件即可更新配置，不需要重启监控程序
        """
        try:
            self.cf_agent
        except:
            # 如果首次启动，需要补充{最后一次调取监控时的警报列表}与{当前观测信息}
            # 非首次启动，则直接继承
            self.last_warn_list = []
            self.obs_info = {}

        # 加载cf_agent，读取配置文件
        self.cf_agent = config_agent()
        self.last_obs_num = self.cf_agent.last_obs_num

        if self.push_info:
            # 若实际进行推送，则配置为实际推送目标；否则配置为测试推送目标
            self.obs_grp = self.cf_agent.obs_grp
            self.warn_grp = self.cf_agent.warn_grp
            self.daily_grp = self.cf_agent.daily_grp
        else:
            self.obs_grp = self.cf_agent.obs_grp_debug
            self.warn_grp = self.cf_agent.warn_grp_debug
            self.daily_grp = self.cf_agent.daily_grp_debug

        if self.debug:
            try:
                self.dv_agent
                send_message(self.debug_grp, "restore")
            except:
                # 若第一次运行，则报告为启动；否则报告更新配置
                send_message(self.cf_agent.daily_grp_debug, "start")

        self.debug_grp = self.cf_agent.daily_grp_debug

    def do_init(self):
        """
        打开监控页面
        与类的初始化分离，避免页面加载失败时导致类初始化失败
        需要在类外部显式调用
        """
        if not self.dv_agent.has_init:
            login_config = self.cf_agent.credit
            self.dv_agent.do_init(login_config["url"], login_config["username"], login_config["password"])
            send_message(self.debug_grp, "login success")

    def survey(self) -> None:
        """
        单次监控程序运行
        """
        self.cur_time = time.time()
        self.warn_list = []
        self.warn_str = self.cf_agent.formatter["warn"]["warn"]
        obs_time, all_data = self.dv_agent.get_data()
        obs_t = time.mktime(time.strptime(obs_time, r"%Y-%m-%d %H:%M:%S"))
        if not self.check_obs_time(obs_t):
            self.process_obs_time(obs_time)
            return
        for item in all_data:
            code, _, val = item
            try:
                info = self.cf_agent.expected[code]
                d_type = info["type"]
            except:
                self.process_new(*item)
                continue
            if d_type == "state":
                self.process_state(code, val)
            elif d_type == "trigger":
                self.process_trigger(int(val))
            elif d_type == "match":
                self.process_match(*item)
            elif d_type == "nozero":
                self.process_nozero(*item)
            elif d_type == "record":
                self.process_record(*item)
            elif d_type == "minmax":
                self.process_minmax(*item)
        self.process_obs(obs_time)
        self.process_warn()
        self.process_daily(all_data)

    def cal_sleep_time(self) -> int:
        """
        计算距离下次监控运行需要间隔多久
        """
        interval_time = self.cf_agent.update_interval
        sleep_time = interval_time - (time.time() - 57600) % interval_time
        if sleep_time < 1:
            sleep_time += interval_time
        return sleep_time

    # ========================日常监测========================
    def process_daily(self, all_data):
        do_daily_push = self.check_push_daily()
        daily_str = self.gen_daily_str(all_data)
        if do_daily_push:
            send_message(self.daily_grp, daily_str)
        if self.debug:
            len_daily_str = len(daily_str)
            cur_hour = (self.cur_time - 57600) % (24 * 3600) / 3600
            debug_str = f"cur_time:{self.cur_time}, cur_hour:{cur_hour}, do_push:{do_daily_push}"
            debug_str += f"{self.cf_agent.daily_list}\nlen_daily_str:{len_daily_str}"
            send_message(self.cf_agent.daily_grp_debug, debug_str)

    def check_push_daily(self) -> bool:
        cur_hour = (self.cur_time - 57600) % (24 * 3600) / 3600
        critical_t = float(self.cf_agent.update_interval) / 6000
        if cur_hour < min(list(self.cf_agent.daily_list.keys())) - critical_t:
            for time in self.cf_agent.daily_list:
                self.cf_agent.daily_list[time] = True
                self.cf_agent.update_push_list()
            return False
        for time, do_push in self.cf_agent.daily_list.items():
            if abs(cur_hour - time) < critical_t and do_push:
                self.cf_agent.daily_list[time] = False
                self.cf_agent.update_push_list()
                return True
        return False

    def gen_daily_str(self, all_data) -> str:
        d_str = self.cf_agent.formatter["daily"]["info"]
        for item in all_data:
            if item[0] in self.warn_list:
                # 如果有异常项，则添加警示
                # d_str += f"<font color='red'>{item[1]}:\t{item[2]}</font>\n"
                d_str += f"{item[1]}:\t{item[2]}❗\n"
            else:
                d_str += f"{item[1]}:\t{item[2]}\n"
        return d_str

    # ========================数据处理========================
    def process_minmax(self, code, name, val):
        vmin = self.cf_agent.expected[code]["min"]
        vmax = self.cf_agent.expected[code]["max"]
        val = float(val)
        if val < vmin:
            self.warn_list.append(code)
            self.warn_str += self.str_replace(self.cf_agent.formatter["minmax"]["warn"][0], name, val).replace("min", str(vmin))
        if val > vmax:
            self.warn_list.append(code)
            self.warn_str += self.str_replace(self.cf_agent.formatter["minmax"]["warn"][1], name, val).replace("max", str(vmax))

    def process_record(self, code, name, val):
        record = self.cf_agent.expected[code]["record"]
        val = int(val)
        if val > record:
            self.warn_list.append(code)
            self.warn_str += self.str_replace(self.cf_agent.formatter["record"]["warn"], name, val).replace("record", str(record))
            self.warn_list += self.str_replace(self.cf_agent.formatter["update"]["info"], name, val)
            self.cf_agent.update_record(code, val)
        else:
            self.cf_agent.update_record(code, val)

    def process_nozero(self, code, name, val):
        if int(val) == 0:
            self.warn_list.append(code)
            self.warn_str += self.str_replace(self.cf_agent.formatter["nozero"]["warn"], name, val)

    def process_match(self, code, name, val):
        if val != self.cf_agent.expected[code]["match"]:
            self.warn_list.append(code)
            self.warn_str += self.str_replace(self.cf_agent.formatter["nozero"]["warn"], name, val)

    # ========================当前观测========================
    def process_obs(self, obs_time):
        obs_num = self.obs_info["num"]
        if self.last_obs_num != obs_num:
            obs_type = self.obs_info["type"]
            self.last_obs_num = obs_num
            self.cf_agent.update_record("TMZT0023", obs_num)
            types = self.obs_info["expect"]
            if obs_type in types["normal"]:
                self.obs_str = self.gen_obs_str(self.cf_agent.formatter["state"]["normal"]["info"], obs_time, obs_type, obs_num)
            elif obs_type in types["xrt"]:
                self.obs_str = self.gen_obs_str(self.cf_agent.formatter["state"]["xrt"]["info"], obs_time, obs_type, obs_num)
            else:
                self.obs_str = self.gen_obs_str(self.cf_agent.formatter["state"]["unusual"]["info"], obs_time, obs_type, obs_num)
                self.warn_list.append(obs_type)
                self.warn_str += self.gen_obs_str(self.cf_agent.formatter["state"]["unusual"]["warn"], obs_time, obs_type, obs_num)
            send_message(self.obs_grp, self.obs_str)
        if self.debug:
            send_message(self.cf_agent.obs_grp_debug, f"{obs_num}  {self.obs_info["type"]}")

    def process_trigger(self, val):
        self.obs_info["num"] = val

    def process_state(self, code, val):
        self.obs_info["type"] = val
        types = self.cf_agent.expected[code]
        self.obs_info["expect"] = types

    # ========================新监测项========================
    def process_new(self, code, name, val):
        self.warn_list.append(code)
        self.warn_str += self.str_replace(self.cf_agent.formatter["new"]["warn"], name, val)

    # ========================监测更新时间========================
    def process_obs_time(self, obs_time):
        self.warn_list.append("overtime")
        self.warn_str += self.cf_agent.formatter["overtime"]["warn"].replace("last_time", obs_time).replace("warn_interval", str(self.cf_agent.update_warn_time))
        self.process_warn()

    def check_obs_time(self, obs_time: float) -> bool:
        # 检查是否正常更新
        return self.cur_time - obs_time < self.cf_agent.update_warn_time

    # ========================警报生成========================
    def process_warn(self) -> None:
        if self.warn_list != self.last_warn_list:
            self.last_warn_list = self.warn_list
            if len(self.warn_list) > 0:
                send_message(self.warn_grp, self.warn_str)
            else:
                send_message(self.warn_grp, self.cf_agent.formatter["warn"]["info"])
        if self.debug:
            send_message(self.cf_agent.warn_grp_debug, f"warn_list: {self.warn_list}")

    # ========================工具========================
    def str_replace(self, rstr, name, val):
        return rstr.replace("name", name).replace("value", str(val))

    def gen_obs_str(self, rstr, cur_time, obs_type, obs_num):
        return rstr.replace("cur_utc", cur_time).replace("obs_type", obs_type).replace("obs_num", str(obs_num))
