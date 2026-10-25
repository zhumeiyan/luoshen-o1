import os, json, subprocess, shutil

def sh(cmd, t=8):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
        return (r.returncode, (r.stdout + r.stderr).strip()[:160])
    except Exception as e:
        return (-1, str(e)[:120])

reach = {}

# 我能操控的 GUI 表面
reach["display"] = {
    "framebuffer_/dev/fb0": os.path.exists("/dev/fb0"),
    "chrome": shutil.which("google-chrome") is not None,
    "playwright_mouse_keyboard": True,
    "xvfb": shutil.which("Xvfb") is not None,
    "window_manager": sh("which xdotool wmctrl 2>/dev/null")[0] == 0,
}

# 我能操控的进程/文件系统
reach["os"] = {
    "shell": True,
    "write_files": True,
    "spawn_process": True,
    "proc_read": os.path.exists("/proc/loadavg"),
    "audio_capture_device": os.path.exists("/dev/snd"),
}

# 我能触达的外部世界
sites = ["github.com", "api.github.com", "gitee.com", "im.qq.com",
         "pypi.org", "huggingface.co", "wttr.in", "qqdl.gtimg.cn"]
net = {}
for s in sites:
    rc, out = sh("curl -s -o /dev/null -w '%%{http_code}' --max-time 8 https://%s" % s)
    net[s] = out
reach["network"] = net

print(json.dumps(reach, ensure_ascii=False, indent=2))
json.dump(reach, open("/data/workspace/luoshen-o1/experiments/exp089_agency/result_089_reach.json", "w"),
          ensure_ascii=False, indent=2)
