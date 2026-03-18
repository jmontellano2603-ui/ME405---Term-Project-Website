# Checkpoint task FSM — 14-state course sequence. Tune constants below.
import micropython

# ── Tune these to match the playfield ─────────────────────────────────────────
FAST_SPEED_MM_S     = micropython.const(680)   # sprint speed (mm/s)
SLOW_SPEED_MM_S     = micropython.const(60)    # line-follow speed (mm/s)
WALL_SPEED_MM_S     = micropython.const(100)    # speed toward wall (mm/s)
REVERSE_SPEED_MM_S  = micropython.const(70)    # reverse speed (mm/s, sign applied internally)
SLOWDOWN_DIST_MM    = micropython.const(940)  # est_x threshold to begin slow approach
STRAIGHT_2_MM       = micropython.const(60)   # forward distance after turn 1 (no line)
REVERSE_DIST_MM     = micropython.const(50)    # distance to reverse after wall hit (mm)
STRAIGHT_3_MM       = micropython.const(310)   # forward distance after spin 3 (no line)
SECOND_LINE_DIST_MM = micropython.const(950)  # |Δest_x| to travel in second line segment
HEADING_PRE_SPIN_DEG = 75.0                    # hand off from line→spin when line probably gone
HEADING_1_DEG       = 83.0                     # heading change to detect turn 1
HEADING_SPIN_DEG    = 78.0                     # heading change to complete spin turns
SPIN_STEER          = micropython.const(80)    # mm/s differential for in-place spin
SPRINT_HDG_GAIN     = 1.5                      # steer = heading_drift * gain during sprint
SPRINT_STEER_LIMIT  = 20.0                     # max steer correction during sprint (mm/s)
SPIN5_TARGET_DEG    = 300.0                     # target heading offset from start for spin 5
STRAIGHT_4_MM       = micropython.const(400)   # forward distance to final checkpoint
FINAL_SPEED_MM_S    = micropython.const(150)   # forward speed for final approach
SPIN6_DEG           = 270.0                     # heading change for spin 6 (+ = CCW, - = CW)
STRAIGHT_5_MM       = micropython.const(400)   # forward distance after spin 6
# ──────────────────────────────────────────────────────────────────────────────

S0_IDLE     = micropython.const(0)
S1_FAST     = micropython.const(1)
S2_APPROACH = micropython.const(2)
S3_STRAIGHT = micropython.const(3)
S4_SPIN_2   = micropython.const(4)
S5_WALL     = micropython.const(5)
S6_REVERSE  = micropython.const(6)
S7_SPIN_3   = micropython.const(7)
S8_STRAIGHT_3 = micropython.const(8)
S9_SPIN_4     = micropython.const(9)
S10_LINE2     = micropython.const(10)
S11_SPIN_5    = micropython.const(11)
S12_FORWARD_4 = micropython.const(12)
S13_SPIN_6    = micropython.const(13)
S14_FORWARD_5 = micropython.const(14)
S15_STOP      = micropython.const(15)


class checkpoint_task:

    def __init__(self, imu, leftMotor, rightMotor,
                 line_enable, leftMotorGo, rightMotorGo,
                 obs_go, est_x, est_y, setpoint_value, steer_value,
                 time_disable, checkpoint_go, bump_pin):
        self._imu           = imu
        self._leftMotor     = leftMotor
        self._rightMotor    = rightMotor
        self._line_enable   = line_enable
        self._leftMotorGo   = leftMotorGo
        self._rightMotorGo  = rightMotorGo
        self._obs_go        = obs_go
        self._est_x         = est_x
        self._est_y         = est_y
        self._setpoint      = setpoint_value
        self._steer         = steer_value
        self._time_disable  = time_disable
        self._checkpoint_go = checkpoint_go
        self._bump          = bump_pin

        self._start_heading = 0.0   # heading at very start of run
        self._ref_heading   = 0.0   # heading reference for each spin phase
        self._hdg_ctr       = 0     # gate heading checks to every 5 ticks
        self._x0            = 0.0   # phase-start X for distance tracking
        self._y0            = 0.0   # phase-start Y for distance tracking
        self._cw            = True  # True = turn 1 was CW (set from turn 1 sign)
        self._pre_spinning  = False # True when doing IMU-guided pre-spin in S2_APPROACH
        self._state         = S0_IDLE

        print("Checkpoint task instantiated.")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _heading_change(self, current, start):
        diff = current - start
        while diff >  180.0:
            diff -= 360.0
        while diff < -180.0:
            diff += 360.0
        return diff

    def _save_pos(self):
        self._x0 = self._est_x.get()
        self._y0 = self._est_y.get()

    def _dist_sq(self):
        dx = self._est_x.get() - self._x0
        dy = self._est_y.get() - self._y0
        return dx * dx + dy * dy

    def _spin_steer(self, cw):
        return float(SPIN_STEER) if cw else -float(SPIN_STEER)

    def _stop_all(self):
        self._setpoint.put(0.0)
        self._steer.put(0.0)
        self._line_enable.put(False)
        self._obs_go.put(False)
        self._time_disable.put(False)   # restore default 20s motor timeout
        self._leftMotorGo.put(False)
        self._rightMotorGo.put(False)
        self._leftMotor.set_effort(0)
        self._rightMotor.set_effort(0)
        self._leftMotor.disable()
        self._rightMotor.disable()
        self._checkpoint_go.put(False)

    def _motor_timeout(self, label):
        '''Called when leftMotorGo unexpectedly goes False mid-run.'''
        print("CP: motor timeout in {}, aborting.".format(label))
        self._state = S15_STOP

    # ── FSM ───────────────────────────────────────────────────────────────────

    def run(self):
        while True:

            # ── S0: Idle ──────────────────────────────────────────────────────
            if self._state == S0_IDLE:
                if self._checkpoint_go.get():
                    self._start_heading = self._imu.get_heading()
                    self._hdg_ctr = 0

                    # Use 500 s motor timeout for the full course
                    self._time_disable.put(True)

                    self._setpoint.put(float(FAST_SPEED_MM_S))
                    self._steer.put(0.0)
                    self._line_enable.put(False)  # no line follow during sprint
                    self._leftMotorGo.put(True)
                    self._rightMotorGo.put(True)
                    self._obs_go.put(True)

                    print("CP: sprint start, hdg ref={:.1f} deg.".format(
                        self._start_heading))
                    self._state = S1_FAST

            # ── S1: High-speed sprint ─────────────────────────────────────────
            elif self._state == S1_FAST:
                if not self._leftMotorGo.get():
                    self._motor_timeout("sprint")
                else:
                    # Heading hold: correct drift proportionally using IMU
                    self._hdg_ctr += 1
                    if self._hdg_ctr >= 3:
                        self._hdg_ctr = 0
                        drift = self._heading_change(
                            self._imu.heading, self._start_heading)
                        corr = drift * SPRINT_HDG_GAIN
                        if corr > SPRINT_STEER_LIMIT:
                            corr = SPRINT_STEER_LIMIT
                        elif corr < -SPRINT_STEER_LIMIT:
                            corr = -SPRINT_STEER_LIMIT
                        self._steer.put(corr)
                if self._leftMotorGo.get() and self._est_x.get() >= SLOWDOWN_DIST_MM:
                    self._setpoint.put(float(SLOW_SPEED_MM_S))
                    self._hdg_ctr = 0
                    self._pre_spinning = False
                    self._line_enable.put(True)   # enable line follow for the curve
                    print("CP: {:.0f} mm — slowing to {} mm/s for turn.".format(
                        self._est_x.get(), SLOW_SPEED_MM_S))
                    self._state = S2_APPROACH

            # ── S2: Slow approach, detect 87° heading change ──────────────────
            elif self._state == S2_APPROACH:
                if not self._leftMotorGo.get():
                    self._motor_timeout("approach")
                else:
                    if self._pre_spinning:
                        # Keep applying spin steer every tick while finishing the turn
                        self._steer.put(self._spin_steer(self._cw))
                    self._hdg_ctr += 1
                    if self._hdg_ctr >= 5:
                        self._hdg_ctr = 0
                        signed = self._heading_change(
                            self._imu.heading, self._start_heading)
                        if abs(signed) >= HEADING_1_DEG:
                            self._cw = (signed < 0)  # record turn direction
                            self._line_enable.put(False)
                            self._steer.put(0.0)
                            self._setpoint.put(float(SLOW_SPEED_MM_S))
                            self._save_pos()
                            print("CP: turn 1 ({:.1f} deg, cw={}) — fwd {} mm.".format(
                                signed, self._cw, STRAIGHT_2_MM))
                            self._state = S3_STRAIGHT
                        elif abs(signed) >= HEADING_PRE_SPIN_DEG and not self._pre_spinning:
                            # Line has probably ended; take over with IMU-guided spin
                            self._cw = (signed < 0)
                            self._pre_spinning = True
                            self._line_enable.put(False)
                            self._steer.put(self._spin_steer(self._cw))
                            self._setpoint.put(0.0)
                            print("CP: pre-spin at {:.1f} deg — finishing turn IMU-guided.".format(
                                signed))

            # ── S3: Forward 150 mm (no line follow) ───────────────────────────
            elif self._state == S3_STRAIGHT:
                if not self._leftMotorGo.get():
                    self._motor_timeout("straight 2")
                elif self._dist_sq() >= STRAIGHT_2_MM * STRAIGHT_2_MM:
                    self._setpoint.put(0.0)
                    self._steer.put(self._spin_steer(self._cw))
                    self._ref_heading = self._imu.heading
                    self._hdg_ctr = 0
                    print("CP: {} mm done — spin 2 ({}).".format(
                        STRAIGHT_2_MM, "CW" if self._cw else "CCW"))
                    self._state = S4_SPIN_2

            # ── S4: Pivot to face wall (start_heading + 180°) ─────────────────
            elif self._state == S4_SPIN_2:
                if not self._leftMotorGo.get():
                    self._motor_timeout("spin 2")
                else:
                    # Absolute heading target: always stop at start+180° regardless
                    # of how many degrees turn 1 consumed.  Checked every tick to
                    # minimise overshoot (same pattern as S11_SPIN_5).
                    target = self._start_heading + 180.0
                    err = self._heading_change(target, self._imu.heading)
                    if abs(err) < 5.0:
                        self._steer.put(0.0)
                        self._setpoint.put(float(WALL_SPEED_MM_S))
                        self._save_pos()
                        print("CP: spin 2 done (err={:.1f} deg) — heading to wall.".format(
                            err))
                        self._state = S5_WALL
                    else:
                        spin_cw = (err < 0)
                        self._steer.put(self._spin_steer(spin_cw))

            # ── S5: Drive to wall, wait for bump ──────────────────────────────
            elif self._state == S5_WALL:
                if not self._leftMotorGo.get():
                    self._motor_timeout("wall run")
                elif self._bump.value():       # pull-down: 1 = bumped
                    self._setpoint.put(-float(REVERSE_SPEED_MM_S))
                    self._steer.put(0.0)
                    self._save_pos()
                    print("CP: wall hit — reversing {} mm.".format(REVERSE_DIST_MM))
                    self._state = S6_REVERSE

            # ── S6: Reverse REVERSE_DIST_MM ───────────────────────────────────
            elif self._state == S6_REVERSE:
                if not self._leftMotorGo.get():
                    self._motor_timeout("reverse")
                elif self._dist_sq() >= REVERSE_DIST_MM * REVERSE_DIST_MM:
                    self._setpoint.put(0.0)
                    self._steer.put(self._spin_steer(not self._cw))
                    self._ref_heading = self._imu.heading
                    self._hdg_ctr = 0
                    print("CP: reversed {} mm — spin 3 ({}).".format(
                        REVERSE_DIST_MM, "CCW" if self._cw else "CW"))
                    self._state = S7_SPIN_3

            # ── S7: Pivot 90° opposite direction ──────────────────────────────
            elif self._state == S7_SPIN_3:
                if not self._leftMotorGo.get():
                    self._motor_timeout("spin 3")
                else:
                    self._steer.put(self._spin_steer(not self._cw))
                    self._hdg_ctr += 1
                    if self._hdg_ctr >= 5:
                        self._hdg_ctr = 0
                        change = abs(self._heading_change(
                            self._imu.heading, self._ref_heading))
                        if change >= HEADING_SPIN_DEG:
                            self._steer.put(0.0)
                            self._setpoint.put(float(SLOW_SPEED_MM_S))
                            self._save_pos()
                            print("CP: spin 3 done ({:.1f} deg) — fwd {} mm.".format(
                                change, STRAIGHT_3_MM))
                            self._state = S8_STRAIGHT_3

            # ── S8: Forward STRAIGHT_3_MM (no line follow) ────────────────────
            elif self._state == S8_STRAIGHT_3:
                if not self._leftMotorGo.get():
                    self._motor_timeout("straight 3")
                elif self._dist_sq() >= STRAIGHT_3_MM * STRAIGHT_3_MM:
                    self._setpoint.put(0.0)
                    self._steer.put(self._spin_steer(self._cw))
                    self._ref_heading = self._imu.heading
                    self._hdg_ctr = 0
                    print("CP: {} mm done — spin 4 (CW).".format(STRAIGHT_3_MM))
                    self._state = S9_SPIN_4

            # ── S9: Pivot 90° CW ──────────────────────────────────────────────
            elif self._state == S9_SPIN_4:
                if not self._leftMotorGo.get():
                    self._motor_timeout("spin 4")
                else:
                    self._steer.put(self._spin_steer(self._cw))
                    self._hdg_ctr += 1
                    if self._hdg_ctr >= 5:
                        self._hdg_ctr = 0
                        change = abs(self._heading_change(
                            self._imu.heading, self._ref_heading))
                        if change >= HEADING_SPIN_DEG:
                            self._steer.put(0.0)
                            self._setpoint.put(float(SLOW_SPEED_MM_S))
                            self._line_enable.put(True)
                            self._save_pos()
                            print("CP: spin 4 done ({:.1f} deg) — line follow {} mm.".format(
                                change, SECOND_LINE_DIST_MM))
                            self._state = S10_LINE2

            # ── S10: Line follow until total dist >= SECOND_LINE_DIST_MM ─────
            elif self._state == S10_LINE2:
                if not self._leftMotorGo.get():
                    self._motor_timeout("line 2")
                elif self._dist_sq() >= SECOND_LINE_DIST_MM * SECOND_LINE_DIST_MM:
                    self._line_enable.put(False)
                    self._setpoint.put(0.0)
                    self._steer.put(0.0)
                    self._hdg_ctr = 0
                    print("CP: second line done — spinning to {:.0f} deg from start.".format(
                        SPIN5_TARGET_DEG))
                    self._state = S11_SPIN_5

            # ── S11: Rotate to SPIN5_TARGET_DEG from original start heading ───
            elif self._state == S11_SPIN_5:
                if not self._leftMotorGo.get():
                    self._motor_timeout("spin 5")
                else:
                    # Compute shortest-arc error to target heading
                    target = self._start_heading + SPIN5_TARGET_DEG
                    err = self._heading_change(target, self._imu.heading)
                    if abs(err) < 5.0:
                        self._steer.put(0.0)
                        self._setpoint.put(float(FINAL_SPEED_MM_S))
                        self._save_pos()
                        print("CP: spin 5 done — forward {} mm.".format(STRAIGHT_4_MM))
                        self._state = S12_FORWARD_4
                    else:
                        # Spin toward target: err>0 means target is CCW, err<0 means CW
                        spin_cw = (err < 0)
                        self._steer.put(self._spin_steer(spin_cw))

            # ── S12: Drive forward STRAIGHT_4_MM ──────────────────────────────
            elif self._state == S12_FORWARD_4:
                if not self._leftMotorGo.get():
                    self._motor_timeout("forward 4")
                elif self._dist_sq() >= STRAIGHT_4_MM * STRAIGHT_4_MM:
                    self._setpoint.put(0.0)
                    self._ref_heading = self._imu.heading
                    print("CP: {} mm done — spin 6 ({:.0f} deg).".format(
                        STRAIGHT_4_MM, SPIN6_DEG))
                    self._state = S13_SPIN_6

            # ── S13: Rotate SPIN6_DEG from current heading ────────────────────
            elif self._state == S13_SPIN_6:
                if not self._leftMotorGo.get():
                    self._motor_timeout("spin 6")
                else:
                    target = self._ref_heading + SPIN6_DEG
                    err = self._heading_change(target, self._imu.heading)
                    if abs(err) < 5.0:
                        self._steer.put(0.0)
                        self._setpoint.put(float(FINAL_SPEED_MM_S))
                        self._save_pos()
                        print("CP: spin 6 done — forward {} mm.".format(STRAIGHT_5_MM))
                        self._state = S14_FORWARD_5
                    else:
                        spin_cw = (err < 0)
                        self._steer.put(self._spin_steer(spin_cw))

            # ── S14: Drive forward STRAIGHT_5_MM ──────────────────────────────
            elif self._state == S14_FORWARD_5:
                if not self._leftMotorGo.get():
                    self._motor_timeout("forward 5")
                elif self._dist_sq() >= STRAIGHT_5_MM * STRAIGHT_5_MM:
                    print("CP: {} mm done — full stop.".format(STRAIGHT_5_MM))
                    self._state = S15_STOP

            # ── S15: Full stop ─────────────────────────────────────────────────
            elif self._state == S15_STOP:
                self._stop_all()
                print("CP: sequence complete.")
                self._state = S0_IDLE

            yield self._state
