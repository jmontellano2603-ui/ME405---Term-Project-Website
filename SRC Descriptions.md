@page src_descriptions SRC File Descriptions

This page will give brief descriptions for each of the SRC files and how they work in context to the overall functionality of the robot

## BNO055.py
Driver file that has class responsible for containing the functions related to getting information from the IMU. Contains the necessary register addresses, helper functions, calibration procedures, and data collection functions for the IMU's sensors.

## bluetooth.py
Contains the necessary classes to connect to and run the HC-05 bluetooth module.

## checkpoint_task.py
Multi-state checkpoint task file that runs as a normal task within the scheduler for the end of term playfield. See [Final Task](/Final%20Task.md/) for a more detailed layout.

## cotask.py
File from the ME 405 library that contains the class and class functions for both task objects and task list objects. Responsible for the priority scheduler functions.

## encoder.py
Driver file that has class responsible for containing the functions related to motor encoder information. Contains functions for obtaining position, velocity and zeroing the encoder.

## line_follower.py
Driver file that has class responsible for containing the functions related to utilizing the line following sensor. Reads raw data from the sensor and calculates the position of a line based on readings from the IR sensors.

## main.py
Centerpoint file that instantiates all necessary objects and tasks. Manages the cooperative task scheduler and task list to complete the necessary created tasks.

## motor_driver.py
Driver file that has class responsible for containing the functions related to motor movement. Has functions to set certain PWM signals to the motor as well as enable/disable motors when needed.

## task_line.py
File containing the task_line class. Used to create task_line objects so they can be run within the cooperative scheduler. Formatted as a FSM and utilizes the line_follower.py classes to read lines and change motor speed based on a PID controller.

## task_motor.py
File containing the task_motor class. Used to create task_motor objects so they can be run within the cooperative scheduler. Formatted as a FSM and utilizes the motor_driver.py classes to help motor reach necessary setpoint speed values based on a base line setpoint and a steer value. Also has debugging sections that can be used to print motor speed and time readings to the serial monitor.

## task_share.py
File containing the classes for both share and queue objects. Allows for creation of share and queue objects for inter-task communication during cooperative scheduler run times. 

## task_state.py
File containing the task_state class. Used to create task_state objects so they can be run within the cooperative scheduler. Formatted as a FSM and utilizes the BNO055.py classes to do state estimation of the robot during run time. Estimates distance travelled, heading, rotational motor velocities, translational motor velocities, and change in heading. Absolute X and Y positions are integrated from the translational motor velocities.

## task_user.py
File containing the task_user class. Used to create task_user objects so they can be run within the cooperative scheduler. Formatted as a FSM and handles options from the user that are inputted into the serial interface. User can use the user interface to change gain values, create new setpoints, enable/disable certain functions, and run step responses without having to edit the main.py file. 
