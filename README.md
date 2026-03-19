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
