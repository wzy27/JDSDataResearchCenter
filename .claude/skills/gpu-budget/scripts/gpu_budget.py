"""进程级 GPU 预算控制。

本机不具备硬件级手段：GeForce 无 MIG；WSL2 无 MPS；nvidia-smi 在 WSL 下无权限
设置功耗限制（驱动在 Windows 侧）。因此只能在应用层做两件事：

  1. MemoryCap  —— 通过 torch.cuda.set_per_process_memory_fraction 限制本进程可用显存。
  2. DutyThrottle —— 测量本进程每轮的 GPU 忙时，按目标占空比插入 sleep。

限制的是「本进程的占空比」，不是「整卡利用率」。整卡利用率 = 本进程 + 其他进程。
"""
import time
import torch


class MemoryCap:
    """把本进程可用显存限制为总量的 fraction。"""

    def __init__(self, fraction=0.6, device=0):
        self.fraction = fraction
        self.device = device

    def apply(self):
        torch.cuda.set_per_process_memory_fraction(self.fraction, self.device)
        total = torch.cuda.get_device_properties(self.device).total_memory
        return {"fraction": self.fraction,
                "cap_gb": round(total * self.fraction / 1024 ** 3, 2),
                "total_gb": round(total / 1024 ** 3, 2)}


class DutyThrottle:
    """按目标占空比限制本进程的 GPU 使用。

    用法：
        t = DutyThrottle(target=0.6)
        for step in loop:
            with t:
                ...  # 一轮 GPU 工作
    每轮结束后按 busy * (1/target - 1) 休眠，使 busy / (busy + sleep) ≈ target。
    休眠时长按 max_sleep 截断，避免个别超长轮次导致长时间停顿。
    """

    def __init__(self, target=0.6, max_sleep=0.25, sync=True, ema=0.2):
        assert 0 < target <= 1.0
        self.target = target
        self.max_sleep = max_sleep
        self.sync = sync
        self.ema = ema
        self.busy_ema = None
        self.total_busy = 0.0
        self.total_sleep = 0.0
        self.n = 0
        self._t0 = None

    def __enter__(self):
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        if self.sync:
            torch.cuda.synchronize()
        busy = time.perf_counter() - self._t0
        self.busy_ema = busy if self.busy_ema is None else \
            (1 - self.ema) * self.busy_ema + self.ema * busy
        self.total_busy += busy
        self.n += 1
        if self.target < 1.0:
            sleep = min(self.busy_ema * (1.0 / self.target - 1.0), self.max_sleep)
            if sleep > 0:
                time.sleep(sleep)
                self.total_sleep += sleep
        return False

    @property
    def measured_duty(self):
        t = self.total_busy + self.total_sleep
        return self.total_busy / t if t > 0 else None

    def summary(self):
        return {"iterations": self.n, "target_duty": self.target,
                "measured_duty": round(self.measured_duty, 4) if self.measured_duty else None,
                "total_busy_s": round(self.total_busy, 2),
                "total_sleep_s": round(self.total_sleep, 2)}
