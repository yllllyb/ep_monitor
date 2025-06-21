import os, time
from ep_monitor import ep_monitor

pid = os.getpid()

end_script = "end.vbs"
if os.path.exists(end_script):
    os.remove(end_script)

with open(end_script, "w") as f:
    f.write(f'Set WshShell = CreateObject("WScript.Shell")\nWshShell.Run "taskkill /pid {pid} -t -f", 0')

em = ep_monitor()
em.do_init()

while True:
    em.restore()
    cur_time = time.time()
    em.survey(cur_time)
    sleep_time = em.cal_sleep_time()
    time.sleep(sleep_time)
