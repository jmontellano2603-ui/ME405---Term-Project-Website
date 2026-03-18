# ME 405 Term Project
## By John Urrutia and Pierce Baugher

## Introduction
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
- A problem we first discovered when driving the motors on Romi was that the left motor was stronger than the right one, given the same PWM signal. A solution that served us well throughout the quearter was calcualting the velocity of each wheel through encoder ticks, and using a PI controller for each wheel to target a velocity. This allowed our romi to drive straight, and later allowed us to dynamically change the target velocity of each wheel when following a line. There is only a small issue however when attempting to target a velocity that the right motor can acheieve but not the left, causing unintended turning.\
- Our state estimator is accurate with an approximate ~2% margin of error after many hours of tuning. After many attempts we succefsul had a somewhat reasonable and reliable set of arrays, that we then tuned by multiplying our B array by the percent error. We repeated this process a few times, using various speeds and distances to not overtune to specific settings, until we were satisfied that the reaminaing error was casued by drift.

## Results

## BOM
|      Name     |            Description         | Quantity | 
|----------------------------------------------------------|
|     Nucleo    |      STM32 Nucleo L476RG       |   x 1    |
| Shoe of Brian |    Polulu Wheel 70 x 8 mm      |   x 2    |
|   32U4 Board  |    Polulu Wheel 70 x 8 mm      |   x 2    |
|   Base Plate  |     Romi Chasis Base Plate     |   x 1    |
|   Gear Motors | 120:1 Mini Plastic Gear Motors |   x 2    |
|   Motor Clip  |    Romi Chasis Motor Clips     |   x 2    |
|     Wheels    |    Polulu Wheel 70 x 8 mm      |   x 2    |
|  Ball Casters |    Romi Chasis Ball Casters    |   x 2    |
|    Batteries  |   6 Rechargable AA Batteries   |   x 2    |
|  QTRX-MD-08A  | Line Following Sensor  |   x 1    |
