# task_state.py
import micropython
import math
from ulab import numpy as np
from utime import ticks_us, ticks_diff
from task_share import Share

S0_INIT = micropython.const(0)
S1_WAIT = micropython.const(1)
S2_RUN  = micropython.const(2)

# ── Discretized observer matrices ─────────────────────────────────────────────
# Computed using professor's method (LQE + c2d ZOH) with:
#   r=35mm, w=141mm, tau=0.057s, Km=9.26/35 rad/s per effort, Ts=0.031s
#   Q=diag([1,1,10,10]), R=diag([0.1,0.1,0.01,1.0])
#
# State vector:  x = [s (mm), psi (rad), omL (rad/s), omR (rad/s)]
# Input vector:  u* = [uL, uR, sL (mm), sR (mm), psi (rad), psidot (rad/s)]

AD = np.array([
    [ 0.82531337,  0.00000000,  0.38062706,  0.38062706],
    [ 0.00000000,  0.00005588, -0.00048319,  0.00048319],
    [-0.07731724,  0.00045768,  0.56043394, -0.01943210],
    [-0.07731724, -0.00045768, -0.01943210,  0.56043394]
])

BD = np.array([
    [ 0.02426532,  0.02426532,  0.08734331,  0.08734331,  0.00000000,  0.00000000],
    [-0.00006277,  0.00006277, -0.00708468,  0.00708468,  0.00100492,  0.00000245],
    [ 0.08603749, -0.00080431,  0.03866186,  0.03865538, -0.00000046, -0.00168906],
    [-0.00080431,  0.08603749,  0.03865538,  0.03866186,  0.00000046,  0.00168906]
])

# C is exact from kinematics — state uses angular wheel speeds (rad/s)
# Row 3: psidot = (-r/w)*omL + (r/w)*omR  where r/w = 35/141 = 0.24823
C_mat = np.array([
    [1.0,  -70,      0.0,        0.0      ],
    [1.0,   70,      0.0,        0.0      ],
    [0.0,   1.0,       0.0,        0.0      ],
    [0.0,   0.0,      -0.24822695, 0.24822695]
])

_MM_PER_COUNT = 0.153   # encoder counts to mm
_DEG_TO_RAD   = math.pi / 180.0
_R            = 35.0    # wheel radius [mm] — needed to get v from omega


class task_state:
    """
    Discrete-time Luenberger state observer for the Romi robot.

    State vector: x = [s (mm), psi (rad), omL (rad/s), omR (rad/s)]
    Update law:   x_{k+1} = AD @ x_k + BD @ u*_k
    where u* = [uL, uR, sL, sR, psi, psidot]
    """

    def __init__(self, imu, enc_left, enc_right,
                 effort_left:  Share,
                 effort_right: Share,
                 go_flag:      Share,
                 est_x:        Share,
                 est_y:        Share,
                 est_heading:  Share,
                 est_vel:      Share):

        self._imu     = imu
        self._enc_l   = enc_left
        self._enc_r   = enc_right
        self._eff_l   = effort_left
        self._eff_r   = effort_right
        self._go      = go_flag
        self._est_x   = est_x
        self._est_y   = est_y
        self._est_hdg = est_heading
        self._est_vel = est_vel

        # State as plain floats between ticks
        self._s   = 0.0   # forward displacement (mm)
        self._psi = 0.0   # heading (rad)
        self._omL = 0.0   # left  wheel angular speed (rad/s)
        self._omR = 0.0   # right wheel angular speed (rad/s)

        self._pos_x     = 0.0
        self._pos_y     = 0.0
        self._print_ctr = 0
        self._state     = S0_INIT
        self._last_t    = ticks_us()

        print("State observer task instantiated.")

    def _encoder_mm(self, enc):
        return enc.get_position() * _MM_PER_COUNT

    def _reset(self):
        self._s   = 0.0
        self._psi = 0.0
        self._omL = 0.0
        self._omR = 0.0
        self._pos_x  = 0.0
        self._pos_y  = 0.0
        self._last_t = ticks_us()
        self._enc_l.zero()
        self._enc_r.zero()

    def run(self):
        while True:

            if self._state == S0_INIT:
                self._reset()
                self._state = S1_WAIT

            elif self._state == S1_WAIT:
                if self._go.get():
                    self._reset()
                    print("State observer: starting.")
                    self._state = S2_RUN

            elif self._state == S2_RUN:
                if not self._go.get():
                    print("State observer: stopped.")
                    self._state = S1_WAIT

                else:
                    # -- 1. Read sensors --------------------------------------
                    sL      = self._encoder_mm(self._enc_l)
                    sR      = self._encoder_mm(self._enc_r)
                    self._imu.update()
                    psi     = self._imu.heading  * _DEG_TO_RAD   # rad
                    psi_dot = self._imu.yaw_rate * _DEG_TO_RAD   # rad/s
                    uL      = self._eff_l.get()
                    uR      = self._eff_r.get()

                    # -- 2. Build state and input vectors ---------------------
                    x = np.array([[self._s  ],
                                  [self._psi],
                                  [self._omL],
                                  [self._omR]])

                    u_star = np.array([[uL     ],
                                       [uR     ],
                                       [sL     ],
                                       [sR     ],
                                       [psi    ],
                                       [psi_dot]])

                    # -- 3. Observer update -----------------------------------
                    x_new = np.dot(AD, x) + np.dot(BD, u_star)

                    # -- 4. Unpack to plain floats ----------------------------
                    self._s   = x_new[0, 0]
                    self._psi = x_new[1, 0]
                    self._omL = x_new[2, 0]
                    self._omR = x_new[3, 0]

                    # -- 5. Forward velocity ----------------------------------
                    # omL/omR are in rad/s so multiply by r to get mm/s
                    v_hat = _R * (self._omL + self._omR) / 2.0

                    # -- 6. Integrate x/y position ----------------------------
                    now  = ticks_us()
                    dt   = ticks_diff(now, self._last_t) / 1_000_000.0
                    self._last_t = now
                    self._pos_x += v_hat * math.cos(self._psi) * dt
                    self._pos_y += v_hat * math.sin(self._psi) * dt

                    # -- 7. Compute y_hat = C @ x -----------------------------
                    y_hat = np.dot(C_mat, x_new)

                    sL_hat      = y_hat[0, 0]
                    sR_hat      = y_hat[1, 0]
                    psi_hat_deg = y_hat[2, 0] / _DEG_TO_RAD
                    psidot_hat  = y_hat[3, 0] / _DEG_TO_RAD   # deg/s

                    # -- 8. Publish to shares ---------------------------------
                    self._est_x.put(self._pos_x)
                    self._est_y.put(self._pos_y)
                    self._est_hdg.put(psi_hat_deg)
                    self._est_vel.put(v_hat)

                    # -- 9. Print ~once per second ----------------------------
                    self._print_ctr += 1
                    if self._print_ctr >= 32:
                        self._print_ctr = 0
                        print(
                            "y_hat: sL={:.1f} sR={:.1f} psi={:.1f}deg "
                            "psidot={:.1f}deg/s | x={:.1f}mm y={:.1f}mm".format(
                                sL_hat, sR_hat, psi_hat_deg, psidot_hat,
                                self._pos_x, self._pos_y))

            yield self._state