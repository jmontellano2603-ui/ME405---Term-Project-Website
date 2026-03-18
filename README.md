# ME 405 Term Project
## By John Urrutia and Pierce Baugher

##Introduction
This years ME 405 term project centered around the construction of "Romi", a small robot kit by Polulu. The computer controlling Romi is a STM32 NUCLEO-L476RG, with an additional power distributin board to proivde safe power, and a " The purpose was to gain hands on expierence with wiring motors and sensors, creating structured, adaptable, and expandable code with the goal of creating a reliable closed feedback system.

## Wiring
![Wiring Diagram](/Image/Wiring%20Pinout.png)
![](/Image/Wiring%20Pinout%202.png)
![](/Image/Wiring%20Pinout%203.png)

## Sensor Mount
This is an image from our CAD that combines both our bump sensor mount (a button), and our Polulu line following sensor (QTRX-MD-08A)
![Sensor CAD](/Image/romi%201.png)

## Final Product

## Highlights
A problem we first discovered when driving the motors on Romi was that the left motor was stronger than the right one, given the same PWM signal. A solution that served us well throughout the quearter was calcualting the velocity of each wheel through encoder ticks, and using a PI controller for each wheel to target a velocity. This allowed our romi to drive straight, and later allowed us to dynamically change the target velocity of each wheel when following a line. There is only a small issue however when attempting to target a velocity that the right motor can acheieve but not the left, causing unintended turning.

## Results
