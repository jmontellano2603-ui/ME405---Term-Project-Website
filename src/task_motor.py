from utime import ticks_us, ticks_diff
import micropython



S0_INIT = micropython.const(0) # State 0 - initialiation
S1_WAIT = micropython.const(1) # State 1 - wait for go command
S2_RUN  = micropython.const(2) # State 2 - run closed loop control


class task_motor:

    def __init__(self, mot, enc, goFlag, dataValues, timeValues, velValues,
                 setpoint_value, ki_value, kp_value, steer_value, side,
                 queue_enable, time_disable, effort_share, obs_go):
        self._state        = S0_INIT
        self._mot          = mot
        self._enc          = enc
        self._goFlag       = goFlag
        self._dataValues   = dataValues
        self._timeValues   = timeValues
        self._velValues    = velValues
        self._setpoint_value = setpoint_value
        self._startTime    = 0
        self.ki_value      = ki_value
        self.kp_value      = kp_value
        self._steer_value  = steer_value
        self._side         = side
        self._error        = 0
        self._integral     = 0
        self._setpoint     = 0
        self._change       = 0
        self.queue_enable  = queue_enable
        self.time_disable  = time_disable
        self._effort_share = effort_share
        self._obs_go       = obs_go
        self._print_ctr    = 0
        print("Motor Task instantiated")

    def run(self):
        
        while True:

            if self._state == S0_INIT: # Init state (can be removed if unneeded)
                # print("Initializing motor task")
                self._state = S1_WAIT
                
            elif self._state == S1_WAIT: # Wait for "go command" state
                if self._goFlag.get():
                    # print("Starting motor loop")
                    
                    # Capture a start time in microseconds so that each sample
                    # can be timestamped with respect to this start time. The
                    # start time will be off by however long it takes to
                    # transition and run the next state, so the time values may
                    # need to be zeroed out again during data processing.
                    self._mot.set_effort(0)
                    self._integral = 0
                    self._change = 0
                    self._mot.enable()
                    self._startTime = ticks_us()

                    self._state = S2_RUN
                
            elif self._state == S2_RUN: # Closed-loop control state
                # print(f"Running motor loop, cycle {self._dataValues.num_in()}")
                
                # Run the encoder update algorithm and then capture the present
                # position of the encoder. You will eventually need to capture
                # the motor speed instead of position here.
                self._enc.update()
                pos = self._enc.get_position()
                velocity = self._enc.get_velocity()

                # Collect a timestamp to use for this sample
                t   = ticks_us()
                
                # Actuate the motor using a control law. The one used here in
                # the example is a "bang bang" controller, and will work very
                # poorly in practice. Note that the set position is zero. You
                # will replace this with the output of your PID controller that
                # uses feedback from the velocity measurement.

                # in run(), where you print every loop:

                Kp = self.kp_value.get()
                Ki = self.ki_value.get()
                if Kp == 0 and Ki == 0:
                    Kp = 0.1
                    Ki = 0.00005
                

                base = self._setpoint_value.get()
                if base == 0:
                    base = 60.0

                steer = 0.0
                if self._steer_value is not None:
                    steer = self._steer_value.get()

                # Read flags from Share objects into local variables
                if self.queue_enable is not None:
                    queue_enabled = bool(self.queue_enable.get())
                else:
                    queue_enabled = False


                if self.time_disable is not None:
                    time_disabled = bool(self.time_disable.get())
                else:
                    time_disabled = True

                self._setpoint = base + (self._side * steer)
                
                self._error =  self._setpoint - velocity
                if self._error > 50:
                    self._error = 50
                elif self._error < -50:
                    self._error = -50
                self._integral = self._error + self._integral
                self._change = self._change + (Kp * self._error)+(Ki * self._integral)
                if self._change > 100:
                    self._change = 100
                elif self._change < -100:
                    self._change = -100
                self._mot.set_effort(self._change)

                if self._effort_share is not None:
                    self._effort_share.put(self._change)

                self._print_ctr += 1
                if self._print_ctr >= 50:
                    self._print_ctr = 0
                    print("MOT{}: sp={:.0f} vel={:.0f} err={:.0f} chg={:.1f}".format(
                        self._side, self._setpoint, velocity, self._error, self._change))               
                # Store the sampled values in the queues

                self._timeValues.put(ticks_diff(t, self._startTime))
                self._velValues.put(velocity)
                if queue_enabled:
                    self._timeValues.put(ticks_diff(t, self._startTime))
                    self._velValues.put(velocity)
                    self._dataValues.put(pos)
                    if self._dataValues.full():
                        self._state = S1_WAIT
                        print("Queue was enabled")
                        self._goFlag.put(False)
                        self._obs_go.put(False)
                        self._mot.disable()
                elif time_disabled:
                    if ticks_diff(t, self._startTime) >= 500000000:
                        self._state = S1_WAIT
                        self._goFlag.put(False)
                        self._obs_go.put(False)
                        self._mot.disable()
                elif not time_disabled:
                    if ticks_diff(t, self._startTime) >= 20000000:
                        self._state = S1_WAIT
                        self._goFlag.put(False)
                        self._obs_go.put(False)
                        self._mot.disable()
                
            yield self._state