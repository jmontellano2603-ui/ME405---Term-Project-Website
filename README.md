# ME 405 Term Project
## By John Urrutia and Pierce Baugher

## Overview
This readme file will give a brief overview over the repository and basic deatils about the project

### Repository
- Used images and videos embedded into the website can be located in the [Image](/Image/) folder
- Miscelaneous items such as CAD drawings can be located in the [MISC](/MISC/) folder
- Details regarding the backend of our website created by Doxygen can be located in the [docs](/docs/) folder
- The final python files that controlled Romi and gathered sensor data can be located in the [src](/src/) folder

### Overview
First off, this class has been one of the most informative and enjoyable classes we have ever taken. We have learned an incredible amount regarding how enocoders work, coding structure, the encoding/decoding/transfer of data through binary and hexadecimal, how different communication protocals work (I2C, UART, ...), and so much more. With that said, it has also was very time consuming with many failures before success. Still, we agree it has been one of the most informative classes we have taken at Cal Poly.

- To start this project, we began with getting familiar with communicating to the Nucleo through PuTTY by detecing a button pres and toggling an LED light on the board.
- Next we assembled our Romi kit, attached our Nucleo, and wired our motors and encoders to the board. We programmed simple tests to control each wheel, and measure the encoder ticks.
- We then used that information to calculate the velocity of each wheel by converting each tick into a distance measurement, time stamping when each tick position, and dividing that distance by the time difference.
- Our next objective was to create tasks for each motor, as well as for a user interface, and run the tasks in a scheduler. This lets the drivers we created run cooperatively, as well lets us assign priority and a period of how often they should run to the tasks.
- Then we enhanced our user interface, allowing the user to modify more aspects of the code like altering the target velocity, and Kp/Ki values used when targeting a velocity. We also setup autmatic data collection, printing the step responses alongside timestamps in csv format in order to create graphs of how well the PID controller reached and maintained the target velocity. This alongside the enhanced UI to quickly chnage Kp and Ki let us run many tests to find our optimal values.
- We then incorporated the line following sensor we purchased from Polulu (QTRX-MD-08A). In order to do this, we added another "line_task" as well as another driver for interfacing and gathering information fom the sensor. This has its Kp, Ki, and Kd values that alter how much control this part of our program has over motor control depending on the location of the line. There were slight issues with Ki and Kp oversteering, so also included a clamp that only allows so much change in motor power to follow the line. In order to not need to calibrate our sensor every time, we thought it would be a good idea to normalize the sensor readings once it passed a certain threshold. That way, it allows Romi to "see" the line much more clearly in more conditions. This was talked about on our main webpage, but the following is an sample of sensor data, and how we calclated where the centroid of the line would be with it.
  
$$
\frac{0.07 \times 0 + 0.14 \times 8 + 0.47 \times 16 + 0.87 \times 24 + 1 \times 32 + 0.54 \times 40 + 0.27 \times 48 + 0 \times 56}{0.07 + 0.14 + 0.47 + 0.87 + 1 + 0.54 + 0.27 + 0} \approx 29.595 \, \text{mm}
$$

-  The final sensor we integrated was a BNO055 9-DOF sensor. Setting up the driver for this sesnor was not easy, and required a lot of reading documentation and learning about the various registers that can be used in the BNO055 sensor. Once we were able to get data from it, we utilized it to to create a state estimation program to estimate the robots location. This part of the project was by far the most difficult and time consuing, and requried lots of array math in matlab to find suitable arrays that were somewhat accurate.
-  The final part of this project was utilizing all of the drivers and sensors to complete a course designed by the professor. A video fo our robot completing this course can be found on our website as well. We designed a FSM to seperate the course in states, and to be able to easily optimize each state to be completed as quickly as possible. To view how we tackled each part of the course, view [Final Task](/Final%20Task/)
![Course](/Image/Final_Task_Playfield.png)


## Introduction
This years ME 405 term project centered around the construction of "Romi", a small robot kit by Polulu. The computer controlling Romi is a STM32 NUCLEO-L476RG, with an additional power distributin board to proivde safe power, and a " The purpose was to gain hands on expierence with wiring motors and sensors, creating structured and adaptable code with the goal of creating a reliable closed feedback system that would be tested on a playing field.

## Wiring
[Wiring Diagram](/Image/Wiring%20Pinout.png)
[](/Image/Wiring%20Pinout%202.png)
[](/Image/Wiring%20Pine%20out%203.png)

## Sensor Mount
This is an image from our [CAD](MISC/Romi.SLDPRT) that combines both our bump sensor mount (a button), and our Polulu line following sensor (QTRX-MD-08A)
[Sensor CAD](/Image/romi%201.png)

## Highlights
- A problem we first discovered when driving the motors on Romi was that the left motor was stronger than the right one, given the same PWM signal. A solution that served us well throughout the quearter was calcualting the velocity of each wheel through encoder ticks, and using a PI controller for each wheel to target a velocity. This allowed our romi to drive straight, and later allowed us to dynamically change the target velocity of each wheel when following a line. There is only a small issue however when attempting to target a velocity that the right motor can acheieve but not the left, causing unintended turning.\
- Our state estimator is accurate with an approximate ~2% margin of error after many hours of tuning. After many attempts we succefsul had a somewhat reasonable and reliable set of arrays, that we then tuned by multiplying our B array by the percent error. We repeated this process a few times, using various speeds and distances to not overtune to specific settings, until we were satisfied that the reaminaing error was casued by drift.

## BOM
| Name | Description | Quantity |
| :---     |    :---: |     ---: |
|     Nucleo    |      STM32 Nucleo L476RG       |   x 1    |
| Shoe of Brian |  Micropython Interpretor        |   x 1    |
|   32U4 Board  |    Romi 32U4 Control Board     |   x 2    |
|   Base Plate  |     Romi Chasis Base Plate     |   x 1    |
|   Gear Motors | 120:1 Mini Plastic Gear Motors |   x 2    |
|   Motor Clip  |    Romi Chasis Motor Clips     |   x 2    |
|     Wheels    |    Polulu Wheel 70 x 8 mm      |   x 2    |
|  Ball Casters |    Romi Chasis Ball Casters    |   x 2    |
|    Batteries  |   6 Rechargable AA Batteries   |   x 2    |
|  QTRX-MD-08A  |     Line Following Sensor      |   x 1    |
