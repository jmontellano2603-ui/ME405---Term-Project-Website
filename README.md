# ME 405 Term Project
### By John Urrutia and Pierce Baugher

## Overview
This readme file will give a brief overview over the repository and basic details about the project

## Repository
- Used images and videos embedded into the website can be located in the [Image](/Image/) folder
- Miscellaneous items such as CAD drawings can be located in the [MISC](/MISC/) folder
- Details regarding the backend of our website created by Doxygen can be located in the [docs](/docs/) folder
- The final python files that controlled Romi and gathered sensor data can be located in the [src](/src/) folder

## Quarter Overview
First off, this class has been one of the most informative and enjoyable classes we have ever taken. We have learned an incredible amount regarding how encoders work, coding structure, the encoding/decoding/transfer of data through binary and hexadecimal, how different communication protocols work (I2C, UART, ...), and so much more. With that said, it was also very time consuming with many failures before success. Still, we agree it has been one of the most informative classes we have taken at Cal Poly.

- To start this project, we began with getting familiar with communicating to the Nucleo through PuTTY by detecting a button press and toggling an LED light on the board.
- Next we assembled our Romi kit, attached our Nucleo, and wired our motors and encoders to the board. We programmed simple tests to control each wheel, and measure the encoder ticks.
- We then used that information to calculate the velocity of each wheel by converting each tick into a distance measurement, time stamping when each tick position, and dividing that distance by the time difference.
- Our next objective was to create tasks for each motor, as well as for a user interface, and run the tasks in a scheduler. This lets the drivers we created run cooperatively, as well lets us assign priority and a period of how often they should run to the tasks.
- Then we enhanced our user interface, allowing the user to modify more aspects of the code like altering the target velocity, and Kp/Ki values used when targeting a velocity. We also setup automatic data collection, printing the step responses alongside timestamps in csv format in order to create graphs of how well the PID controller reached and maintained the target velocity. This alongside the enhanced UI to quickly change Kp and Ki let us run many tests to find our optimal values.
- We then incorporated the line following sensor we purchased from Polulu (QTRX-MD-08A). In order to do this, we added another "line_task" as well as another driver for interfacing and gathering information from the sensor. This has its Kp, Ki, and Kd values that alter how much control this part of our program has over motor control depending on the location of the line. There were slight issues with Ki and Kp oversteering, so we also included a clamp that only allows so much change in motor power to follow the line. In order to not need to calibrate our sensor every time, we thought it would be a good idea to normalize the sensor readings once it passed a certain threshold. That way, it allows Romi to "see" the line much more clearly in more conditions. This was talked about on our main webpage, but the following is a sample of sensor data, and how we calculated where the centroid of the line would be with it.
  
$$
\frac{0.07 \times 0 + 0.14 \times 8 + 0.47 \times 16 + 0.87 \times 24 + 1 \times 32 + 0.54 \times 40 + 0.27 \times 48 + 0 \times 56}{0.07 + 0.14 + 0.47 + 0.87 + 1 + 0.54 + 0.27 + 0} \approx 29.595 \text{mm}
$$

-  The final sensor we integrated was a BNO055 9-DOF sensor. Setting up the driver for this sensor was not easy, and required a lot of reading documentation and learning about the various registers that can be used in the BNO055 sensor. Once we were able to get data from it, we utilized it to create a state estimation program to estimate the robots location. This part of the project was by far the most difficult and time consuming, and required lots of array math in matlab to find suitable arrays that were somewhat accurate.
-  The final part of this project was utilizing all of the drivers and sensors to complete a course designed by the professor. A video of our robot completing this course can be found on our website as well. We designed a FSM to separate the course in states, and to be able to easily optimize each state to be completed as quickly as possible. To view how we tackled each part of the course, view [Final Task](/Final%20Task.md/)
![Course](/Image/Final_Task_Playfield.png)


## Introduction
This years ME 405 term project centered around the construction of "Romi", a small robot kit by Polulu. The computer controlling Romi is a STM32 NUCLEO-L476RG, with an additional power distribution board to provide safe power. The purpose was to gain hands on experience with wiring motors and sensors, creating structured and adaptable code with the goal of creating a reliable closed feedback system that would be tested on a playing field.

## Wiring
[Wiring Diagram](/Image/Wiring%20Pinout.png)
[](/Image/Wiring%20Pinout%202.png)
[](/Image/Wiring%20Pine%20out%203.png)

## Sensor Mount
This is an image from our [CAD](MISC/Romi.SLDPRT) that combines both our bump sensor mount (a button), and our Polulu line following sensor (QTRX-MD-08A). This part is front mounted so that we can detect object collisions when moving forward and detect lines ahead of us. This helps to give the robot time to process the readings from the line sensor and then act on them once the robot is above that detected point.
[Sensor CAD](/Image/romi%201.png)

## Highlights
- A problem we first discovered when driving the motors on Romi was that the left motor was stronger than the right one, given the same PWM signal. A solution that served us well throughout the quarter was calculating the velocity of each wheel through encoder ticks, and using a PI controller for each wheel to target a velocity. This allowed our romi to drive straight, and later allowed us to dynamically change the target velocity of each wheel when following a line. There is only a small issue however when attempting to target a velocity that the right motor can achieve but not the left, causing unintended turning.
- Our state estimator is accurate with an approximate ~2% margin of error after many hours of tuning. After many attempts, we successfully had a somewhat reasonable and reliable set of arrays, that we then tuned by multiplying our B array by the percent error. We repeated this process a few times, using various speeds and distances to not overtune to specific settings, until we were satisfied that the remaining error was caused by drift.

## BOM
| Name | Description | Quantity |
| :---     |    :---: |     ---: |
|     Nucleo    |      STM32 Nucleo L476RG       |   x 1    |
| Shoe of Brian |  Micropython Interpreter        |   x 1    |
|   32U4 Board  |    Romi 32U4 Control Board     |   x 2    |
|   Base Plate  |     Romi Chasis Base Plate     |   x 1    |
|   Gear Motors | 120:1 Mini Plastic Gear Motors |   x 2    |
|   Motor Clip  |    Romi Chassis Motor Clips     |   x 2    |
|     Wheels    |    Polulu Wheel 70 x 8 mm      |   x 2    |
|  Ball Casters |    Romi Chasis Ball Casters    |   x 2    |
|    Batteries  |   6 Rechargable AA Batteries   |   x 2    |
|  QTRX-MD-08A  |     Line Following Sensor      |   x 1    |

## Software Architecture

All control runs inside a cooperative round-robin scheduler from the cotask library (courtesy of Dr. JR Ridgley)
Six tasks share states, tuning variables, and more through Share and Queue objects:

- task_motor (x2: Left and Right): PI velocity control, 31ms period
- task_line: PID line following using IR Sensor, 22ms period  
- task_state: State Estimation using IMU and Encoders, 31ms period
- checkpoint_task: Multi-State FSM for Game Board, 31ms period
- task_user: User Interface for robot action customization, 0 ms period

## Line Following

Line following is accomplished using a front mounted QTR-8A IR sensor that does dynamic thresholding from sensor readings and calculates a centroid position in mm from the sensor
center. A PID controller (Kp=6.0, Ki=0.7, Kd=0.9) converts this error
into a steering correction that is sent to both motors for adaptive speed setpoints.
Below is an example of a one sensor reading, and how it is mnaipulated to find where the centroid of the line is. It is important to note that our "0" mm is equal to being directly over the first sensor, and our sensor spacing was 8mm.
|Initial sensor readings (1-8)|5500|54000|49000| 43000| 41000| 48000| 52000| 56000|
| :---     |    :---: |    :---: |    :---: |    :---: |    :---: |    :---: |    :---: |    :---: |
|Subtracted Min.| 14000|13000|8000|2000|0000|7000|11000|15000| 
|Divided BY Range| 0.93|0.86|0.53|0.13|0|0.46|0.73|1|
|Inverted Strenth|0.07|0.14|0.47|0.87|1|0.54|0.27|0|

$$
\frac{0.07 \times 0 + 0.14 \times 8 + 0.47 \times 16 + 0.87 \times 24 + 1 \times 32 + 0.54 \times 40 + 0.27 \times 48 + 0 \times 56}{0.07 + 0.14 + 0.47 + 0.87 + 1 + 0.54 + 0.27 + 0} \approx 29.595 \text{mm}
$$

## State Estimation

The observer tracks four state variables:
- s: forward displacement (mm)
- psi: heading (rad)
- omL: left wheel angular speed (rad/s)
- omR: right wheel angular speed (rad/s)

Update law: x_{k+1} = AD * x_k + BD * u*_k

Encoder positions, BNO055 heading and yaw rate, and motor effort values are used in the state estimation to do corrective predictions based on both the kinematics and physics of the Romi robot.
Note: X and Y absolute positions are not included in the state estimation and are instead found through outside means (instantaneous velocity conversions over time).

## Video Demonstration

See the robot complete a full lap of the playfield [here](https://youtube.com/shorts/_OimBy4oKCs)

