# task_line.py
import micropython
from time import ticks_ms, ticks_diff, ticks_us

S0_WAIT = micropython.const(0)
S1_RUN  = micropython.const(1)

class task_line:
    def __init__(self, sensor, enable_share, steer_share,
                 kp, ki, kd, steer_limit):
        self._sensor = sensor
        self._en = enable_share
        self._steer = steer_share

        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.steer_limit = steer_limit

        self._state = S0_WAIT
        self._e_prev = 0.0
        self._i = 0.0
        self._t_prev = ticks_ms()
        self._t0_us = ticks_us()
        self._printed_header = False
        # centroid logging
        self._startTime = ticks_us()
        self._dbg_ctr = 0
        self._steer_smooth = 0.0   # EMA-filtered steer output
        self._ema_alpha    = 0.45   # 0=no update, 1=no filter; tau ≈ 33 ms at 22 ms period
        self._lost_ctr     = 0     # ticks since line was last seen
        self._LOST_HOLD    = 4     # hold steer for this many ticks (~200 ms) before decaying

    def run(self):
        while True:
            if self._state == S0_WAIT:
                # Do NOT zero steer every tick — checkpoint_task may be using
                # the steer share to command spin differentials while line
                # following is idle.  Steer is zeroed only on the S1_RUN→S0_WAIT
                # transition below.
                if self._en.get():
                    self._e_prev = 0.0
                    self._i = 0.0
                    self._t_prev = ticks_ms()
                    self._startTime = ticks_us()   # start timestamp for centroid log
                    self._dbg_ctr = 0
                    self._steer_smooth = 0.0
                    self._lost_ctr = 0
                    print("LINE: task entered S1_RUN")
                    self._state = S1_RUN

            elif self._state == S1_RUN:
                if not self._en.get():
                    self._steer.put(0.0)
                    self._state = S0_WAIT
                else:
                    pos_mm, seen, raw = self._sensor.read_line(samples=2)  
                    pos_mm, seen, raw = self._sensor.read_line(samples=2)
                    mn = min(raw)
                    mx = max(raw)
                    rng = mx - mn
                    if self._dbg_ctr == 0 and self._lost_ctr == 0:
                        print("LINE FIRST: seen={} pos={} rng={}".format(
                            int(seen),
                            "{:.1f}".format(pos_mm) if pos_mm is not None else "None",
                            rng))
                    self._dbg_ctr += 1
                    if self._dbg_ctr >= 50:
                        self._dbg_ctr = 0
                        print("LINE: seen={} pos={} rng={} steer={:.1f}".format(
                            int(seen),
                            "{:.1f}".format(pos_mm) if pos_mm is not None else "None",
                            rng,
                            self._steer.get()))

                    if not seen or pos_mm is None:
                        # Hold the last steer command for up to _LOST_HOLD ticks
                        # so the robot keeps turning through the curve.
                        # After that, decay slowly to avoid runaway if the line
                        # is truly gone.
                        self._lost_ctr += 1
                        if self._lost_ctr > self._LOST_HOLD:
                            self._steer_smooth *= 0.85
                        self._steer.put(self._steer_smooth)
                        yield self._state
                        continue

                    self._lost_ctr = 0  # line reacquired

                    # PID steering
                    e = pos_mm

                    now = ticks_ms()
                    dt_ms = ticks_diff(now, self._t_prev)
                    self._t_prev = now
                    dt = dt_ms/1000.0 if dt_ms > 0 else 0.001

                    self._i += e * dt
                    d = (e - self._e_prev) / dt
                    self._e_prev = e

                    u = self.kp*e + self.ki*self._i + self.kd*d

                    # clamp
                    if u > self.steer_limit: u = self.steer_limit
                    if u < -self.steer_limit: u = -self.steer_limit

                    # EMA low-pass filter to smooth out sensor noise
                    self._steer_smooth = (self._ema_alpha * u
                                          + (1.0 - self._ema_alpha) * self._steer_smooth)
                    self._steer.put(self._steer_smooth)

            yield self._state