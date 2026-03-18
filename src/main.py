from gc import collect
from motor_driver import Motor as motor_driver
from encoder      import Encoder as encoder; collect()
from task_motor   import task_motor; collect()
from task_user    import task_user; collect()
from task_share   import Share, Queue, show_all
from cotask       import Task, task_list; collect()
from pyb import Timer, Pin
from time import ticks_us, ticks_diff
from bluetooth import BTBridge, Tee; collect()
from sys import stdout
from line_follower import QTRLineFollower; collect()
from task_line import task_line; collect()
from BNO055 import BNO055; collect()
from task_state import task_state; collect()
from checkpoint_task import checkpoint_task; collect()



# Variables
bridge = BTBridge(uart_no=4, baud=9600, print_incoming=False)
stdout = Tee(stdout, bridge.uart)

# Build all driver objects first

tim4 = Timer(4, freq=20000)
tim3 = Timer(3, period = 0xFFFF, prescaler = 0)
tim1 = Timer(1, period = 0xFFFF, prescaler = 0)

leftMotor    = motor_driver(tim4.channel(3, Timer.PWM, pin=Pin(Pin.cpu.B8)), Pin.cpu.A6, Pin.cpu.A5)
rightMotor   = motor_driver(tim4.channel(4, Timer.PWM, pin=Pin(Pin.cpu.B9)), Pin.cpu.B6, Pin.cpu.A7)
leftEncoder  = encoder(tim1,Pin.cpu.A8,Pin.cpu.A9,"left")
rightEncoder = encoder(tim3,Pin.cpu.C6,Pin.cpu.C7,"right")
OUT_PINS = [Pin.cpu.C4, Pin.cpu.C5, Pin.cpu.C0, Pin.cpu.C1, Pin.cpu.B0, 
            Pin.cpu.A4, Pin.cpu.C3, Pin.cpu.C2]
CTRL_PIN = Pin.cpu.A10
sensor = QTRLineFollower(OUT_PINS, CTRL_PIN, contrast_thresh=3000, invert=True)

leftMotor.enable()
rightMotor.enable()

imu= BNO055(i2c_bus=2, rst_pin="PB5", mode = "IMU")
imu.setup()

# Bump sensor: button between 3.3V and PB4 (Arduino D5), internal pull-down.
# Reads 1 when button is pressed (wall hit), 0 when free.
bump_pin = Pin(Pin.cpu.C8, Pin.IN, Pin.PULL_DOWN)

# Build shares and queues
leftMotorGo   = Share("B",     name="Left Mot. Go Flag")
rightMotorGo  = Share("B",     name="Right Mot. Go Flag")
leftdataValues    = Queue("f", 300, overwrite=True, name="Data Collection Buffer")
lefttimeValues    = Queue("L", 300, overwrite=True, name="Time Buffer")
leftvelValues     = Queue("f", 300, overwrite=True, name="Velocity Buffer")
rightdataValues    = Queue("f", 300, overwrite=True, name="Data Collection Buffer")
righttimeValues    = Queue("L", 300, overwrite=True, name="Time Buffer")
rightvelValues     = Queue("f", 300, overwrite=True, name="Velocity Buffer")
ki_value      = Share("f", name="Ki Value")
kp_value      = Share("f", name="Kp Value")
setpoint_value = Share("f", name="Set Point Value")
line_enable   = Share("B", name="Line Follow Enable")
steer_value   = Share("f", name="Steering Correction")
queue_enable  = Share("B",     name="Queue Enable Flag")
time_disable  = Share("B",     name="Time Disable Flag")
effort_left  = Share("f", name="Left Effort")
effort_right = Share("f", name="Right Effort")
obs_go       = Share("B", name="Observer Go Flag")
checkpoint_go = Share("B", name="Checkpoint Go Flag")
est_x        = Share("f", name="Est. X (mm)")
est_y        = Share("f", name="Est. Y (mm)")
est_heading  = Share("f", name="Est. Heading (deg)")
est_vel      = Share("f", name="Est. Velocity (mm/s)")








# Build task class objects
stateTask = task_state(imu, leftEncoder, rightEncoder,
                       effort_left, effort_right, obs_go,
                       est_x, est_y, est_heading, est_vel)
lineTask = task_line(sensor, line_enable, steer_value, kp=6.0, ki=0.7, kd=0.9, steer_limit=120.0)
leftMotorTask  = task_motor(leftMotor,  leftEncoder,
                            leftMotorGo, leftdataValues, lefttimeValues, leftvelValues, setpoint_value, 
                            ki_value, kp_value, steer_value,-1, queue_enable, time_disable, effort_left,
                            obs_go)
rightMotorTask = task_motor(rightMotor, rightEncoder,
                            rightMotorGo, rightdataValues, righttimeValues, rightvelValues, setpoint_value,
                            ki_value, kp_value, steer_value,+1, queue_enable, time_disable, effort_right,
                            obs_go)
checkpointTask = checkpoint_task(imu, leftMotor, rightMotor,
                                 line_enable, leftMotorGo, rightMotorGo,
                                 obs_go, est_x, est_y, setpoint_value, steer_value,
                                 time_disable, checkpoint_go, bump_pin)
userTask = task_user(leftMotorGo, rightMotorGo,
                     leftdataValues, lefttimeValues, leftvelValues,
                     rightdataValues, righttimeValues, rightvelValues,
                     ki_value, kp_value, setpoint_value, bridge, line_enable, queue_enable, time_disable, obs_go,
                     est_x, est_y, est_heading, checkpoint_go)


# Add tasks to task list
task_list.append(Task(leftMotorTask.run, name="Left Mot. Task",
                      priority = 1, period = 31, profile=True))
task_list.append(Task(rightMotorTask.run, name="Right Mot. Task",
                      priority = 1, period = 31, profile=True))
task_list.append(Task(lineTask.run, name="Line Task",
                      priority = 1, period = 22, profile=True))
task_list.append(Task(userTask.run, name="User Int. Task",
                      priority = 0, period = 0, profile=False))
task_list.append(Task(stateTask.run, name="State Observer",
                      priority=1, period=31, profile=True))
task_list.append(Task(checkpointTask.run, name="Checkpoint Task",
                      priority=1, period=31, profile=True))


# Run the garbage collector preemptively
collect()

# Run the scheduler until the user quits the program with Ctrl-C
while True:
    try:
        bridge.poll_bt()
        task_list.pri_sched()
        
    except KeyboardInterrupt:
        print("Program Terminating")
        leftMotor.set_effort(0)
        rightMotor.set_effort(0)
        leftMotor.disable()
        rightMotor.disable()
        break
    except Exception as e:
        print("UNHANDLED EXCEPTION:", e)
        leftMotor.set_effort(0)
        rightMotor.set_effort(0)
        leftMotor.disable()
        rightMotor.disable()
        raise

print("\n")
print(task_list)
print(show_all())
