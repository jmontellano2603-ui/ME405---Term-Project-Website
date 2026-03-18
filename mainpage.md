Romi Autonomous Robot — ME 405

# Project Overview

Hello and welcome to our website to recap our work on the Term Project for the ME 405 - Mechatronics Winter 2026 class! Our names' are Pierce Baugher and John Urrutia and we are both graduate students studying under the BioResource and Agricultural Engineering department focusing on agriculture robotics and automation. The information within this page contains descriptions, overview, and explanations to our design for our Romi robot to complete the term project for this class.

If you have any questions, feel free to contact us!
Pierce:	pbaugher@calpoly.edu
John:	jjmontel@calpoly.edu

# Hardware

- STM32 L476RG microcontroller with Shoe of Brian Attachment
- Pololu Romi chassis with motor driver and power distribution board (dual DRV8838)
- BNO055 Inertial Measurement Unit (IMU)
- QTR-8A analog IR line sensor array
- Quadrature wheel encoders
- HC-05 Bluetooth module
- Front mounted bump switch 

# Software Architecture

All control runs inside a cooperative round-robin scheduler from the cotask library (courtesy of Dr. JR Ridgley)
Six tasks share states, tuning variables, and more through Share and Queue objects:

- task_motor (x2: Left and Right): PI velocity control, 31ms period
- task_line: PID line following using IR Sensor, 22ms period  
- task_state: State Estimation using IMU and Encoders, 31ms period
- checkpoint_task: Multi-State FSM for Game Board, 31ms period
- task_user: User Interface for robot action customization, 0 ms period

# State Estimation

The observer tracks four state variables:
- s: forward displacement (mm)
- psi: heading (rad)
- omL: left wheel angular speed (rad/s)
- omR: right wheel angular speed (rad/s)

Update law: x_{k+1} = AD * x_k + BD * u*_k

Encoder positions, BNO055 heading and yaw rate, and motor effort values are used in the state estimation to do corrective predictions based on both the kinematics and physics of the Romi robot.
Note: X and Y absolute positons are not included in the state estimation and are instead found through outside means (instantaneous velocity conversions over time).

# Line Following

Line following is accomplished using a front mounted QTR-8A IR sensor that does dynamic thresholding from sensor readings and calculates a centroid position in mm from the sensor
center. A PID controller (Kp=6.0, Ki=0.7, Kd=0.9) converts this error
into a steering correction that is sent to both motors for adaptive speed setpoints.

# Object Detection

Our Romi also has a front mounted button used for object detection. One of the pins (C8) is set up as a pull down input pin and is set high whenever the button is pressed and an object is detected. In reference to the game track, this tells Romi that the wall has been reached and to move backwards. This same process could be followed for more bump detection (buttons) attached, however our Romi only uses the 1 front mounted button.

# Video Demonstration

See the robot complete a full lap: https://YOUR_VIDEO_URL_HERE

# Results

The robot successfully navigated the course. Key lessons learned throughout this course/project:
- creation of classes and implementation of classes when making new objects
- PID tuning of different objects to achieve tasks (motor velocity, steering correction)
- Cooperative scheduling of robot tasks and sharing of task information through Queues/Shares
- Utilization of IMU and encoder informtation for more accurate and corrected state estimation
