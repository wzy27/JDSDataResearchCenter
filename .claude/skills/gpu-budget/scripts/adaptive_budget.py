"""自适应 GPU 预算：在前台使用者活跃时主动让路。

背景 —— 本机可用的手段极其有限：
  * GeForce 无 MIG，无法硬件分区；
  * WSL2 无 MPS，无法限制 SM 份额；
  * nvidia-smi 在 WSL 内无权限设置功耗限制或计算模式（驱动在 Windows 侧）；
  * `nvidia-smi --query-compute-apps` 与 `pmon` 在 WSL 内返回空，
    因此无法按进程区分「谁在用 GPU」。

由此本模块不做「分区」，只做「让路」。核心观测是：

    在本进程节流休眠的窗口内采样到的整卡利用率，就是其他进程（即使用者）的负载。

据此动态调整本进程的目标占空比：他人负载高则压低，空闲则放开。
这不是抢占式调度，是协作式退让；本进程主动缩小自己，无法阻止对方变慢。
"""
import subprocess, threading, time
from collections import deque

import torch

_SMI = ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
        "--format=csv,noheader,nounits"]


def sample_gpu():
    try:
        o = subprocess.run(_SMI, capture_output=True, text=True, timeout=4).stdout.strip()
        u, used, total = [int(x) for x in o.split(",")]
        return u, used, total
    except Exception:
        return None, None, None


class AdaptiveBudget:
    """按前台负载自适应调整本进程占空比。

    policy: [(other_util_upper_bound, duty), ...] 按上界升序，最后一项为兜底。
    默认策略在使用者几乎空闲时放开到 0.85，重载时压到 0.15。
    """

    DEFAULT_POLICY = [(25, 0.85), (50, 0.60), (75, 0.35), (101, 0.15)]

    def __init__(self, policy=None, mem_fraction=0.6, min_free_mb=3000,
                 sample_interval=0.5, window=20, device=0, verbose=False):
        self.policy = policy or self.DEFAULT_POLICY
        self.mem_fraction = mem_fraction
        self.min_free_mb = min_free_mb
        self.sample_interval = sample_interval
        self.device = device
        self.verbose = verbose
        self.idle_samples = deque(maxlen=window)   # 只在本进程休眠时采集
        self.duty = self.policy[1][1]
        self._sleeping = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._t = None
        self.total_busy = 0.0
        self.total_sleep = 0.0
        self.n = 0
        self.busy_ema = None
        self.mem_pressure_events = 0

    # ---- 生命周期 ----
    def start(self):
        torch.cuda.set_per_process_memory_fraction(self.mem_fraction, self.device)
        self._t = threading.Thread(target=self._sampler, daemon=True)
        self._t.start()
        return self

    def stop(self):
        self._stop.set()
        if self._t:
            self._t.join(timeout=3)

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()
        return False

    # ---- 采样与决策 ----
    def _sampler(self):
        while not self._stop.is_set():
            if self._sleeping.is_set():
                u, used, total = sample_gpu()
                if u is not None:
                    with self._lock:
                        self.idle_samples.append((u, used, total))
            time.sleep(self.sample_interval)

    @property
    def other_util(self):
        """休眠窗口内的整卡利用率中位数，即他人负载的估计。"""
        with self._lock:
            if not self.idle_samples:
                return None
            v = sorted(x[0] for x in self.idle_samples)
            return v[len(v) // 2]

    @property
    def free_mb(self):
        with self._lock:
            if not self.idle_samples:
                return None
            u, used, total = self.idle_samples[-1]
            return total - used

    def _target_duty(self):
        ou = self.other_util
        if ou is None:
            return self.policy[1][1]
        for bound, duty in self.policy:
            if ou < bound:
                base = duty
                break
        else:
            base = self.policy[-1][1]
        free = self.free_mb
        if free is not None and free < self.min_free_mb:
            self.mem_pressure_events += 1
            base = min(base, 0.15)     # 显存吃紧时进一步退让
        return base

    # ---- 每轮工作包裹 ----
    def __call__(self):
        return _Step(self)

    def summary(self):
        t = self.total_busy + self.total_sleep
        return {"iterations": self.n,
                "measured_duty": round(self.total_busy / t, 4) if t else None,
                "current_target_duty": self.duty,
                "estimated_other_util": self.other_util,
                "free_mb": self.free_mb,
                "mem_pressure_events": self.mem_pressure_events,
                "total_busy_s": round(self.total_busy, 1),
                "total_sleep_s": round(self.total_sleep, 1)}


class _Step:
    def __init__(self, b):
        self.b = b

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        b = self.b
        torch.cuda.synchronize()
        busy = time.perf_counter() - self.t0
        b.busy_ema = busy if b.busy_ema is None else 0.7 * b.busy_ema + 0.3 * busy
        b.total_busy += busy
        b.n += 1
        b.duty = b._target_duty()
        if b.duty < 1.0:
            sleep = min(b.busy_ema * (1.0 / b.duty - 1.0), 1.0)
            if sleep > 0:
                b._sleeping.set()
                time.sleep(sleep)
                b._sleeping.clear()
                b.total_sleep += sleep
        if b.verbose and b.n % 25 == 0:
            print(f"[budget] iter={b.n} other_util={b.other_util} "
                  f"target_duty={b.duty} measured={b.summary()['measured_duty']}", flush=True)
        return False
