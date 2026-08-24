"""从外部对已在运行的训练进程做占空比节流（SIGSTOP / SIGCONT）。

为什么不用 skill 里的 AdaptiveBudget：那个要在训练循环里包 `with budget()`，
需要改代码并重启。阶段一已经跑了 40 多分钟，重启要重来。
外部停/续对我们自己的进程是安全的，且立刻生效。
阶段二（185k 步，尚未开始）会改用 skill 的进程内包装，那才是正规做法。

沿用 skill 的核心思路：**在我们自己的停止窗口里采样总利用率**，
读到的就是前台负载（因为此刻我们不发新的 kernel）。
"""
import os, signal, subprocess, sys, time

pid = int(sys.argv[1])
target = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
period = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
logp = os.path.expanduser("~/fastrelight/analysis/extern_throttle.log")

run_t, stop_t = period * target, period * (1 - target)
busy = idle = 0.0
others, n = [], 0
t0 = time.time()


def util():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=5).stdout.strip()
        return float(o.split("\n")[0])
    except Exception:
        return float("nan")


def alive():
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def resume(*_):
    try:
        os.kill(pid, signal.SIGCONT)
    except OSError:
        pass
    write_summary()
    sys.exit(0)


def write_summary():
    tot = busy + idle
    valid = [x for x in others if x == x]
    with open(logp, "a") as f:
        f.write("[{}] pid={} 目标占空比={:.2f} 实测={:.3f} "
                "运行{:.0f}s 停止{:.0f}s 周期数={} "
                "停止窗口内总利用率 中位数={} 最大={}\n".format(
                    time.strftime("%H:%M:%S"), pid, target,
                    busy / tot if tot else 0, busy, idle, n,
                    round(sorted(valid)[len(valid) // 2], 1) if valid else "n/a",
                    round(max(valid), 1) if valid else "n/a"))


signal.signal(signal.SIGTERM, resume)
signal.signal(signal.SIGINT, resume)

try:
    while alive():
        os.kill(pid, signal.SIGCONT)
        a = time.time(); time.sleep(run_t); busy += time.time() - a

        if not alive():
            break
        os.kill(pid, signal.SIGSTOP)
        a = time.time()
        # 采样点放在停止窗口中段，避开刚停下时残留的 kernel
        time.sleep(stop_t * 0.5)
        others.append(util())
        time.sleep(max(0.0, stop_t * 0.5))
        idle += time.time() - a
        n += 1

        if n % 240 == 0:
            write_summary()
finally:
    try:
        os.kill(pid, signal.SIGCONT)
    except OSError:
        pass
    write_summary()
