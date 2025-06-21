import json


class config_agent:
    def __init__(self) -> None:
        with open("./config.json", "r", encoding="utf-8") as f:
            self.config = json.loads("".join(f.readlines()))
        self.credit = self.config["credentials"]
        self.formatter = self.config["formatter"]
        self.expected = self.config["expected"]
        settings = self.config["settings"]
        self.update_interval = settings["tele time"]
        self.update_warn_time = settings["updated warn time"]
        self.daily_list = {}
        for i, j in settings["daily time"].items():
            self.daily_list[float(i)] = j
        self.obs_grp = settings["grp"]["obs"]
        self.warn_grp = settings["grp"]["warn"]
        self.daily_grp = settings["grp"]["daily"]
        self.obs_grp_debug = settings["debug_grp"]["obs"]
        self.warn_grp_debug = settings["debug_grp"]["warn"]
        self.daily_grp_debug = settings["debug_grp"]["daily"]
        self.last_obs_num = self.expected["TMZT0023"]["record"]

    def update_record(self, code, value):
        self.expected[code]["record"] = value
        config_str = json.dumps(self.config, ensure_ascii=False, indent=4, separators=(",", ": "))
        with open("./config.json", "w", encoding="utf-8") as f:
            f.write(config_str)

    def update_push_list(self):
        self.config["settings"]["daily time"] = self.daily_list
        config_str = json.dumps(self.config, ensure_ascii=False, indent=4, separators=(",", ": "))
        with open("./config.json", "w", encoding="utf-8") as f:
            f.write(config_str)
