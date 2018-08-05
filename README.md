# tripipy
Python driver for Trinamic tmc5130 connected to Raspberry Pi

The Trinamic stepper control chips (like the tmc5130 and tmc5160) are FAR more sophisticated than the older 
stepper chips like the A4988. They are more expensive (around £15 mounted on a breakput board), but the 
added functionality dramtically reduces the compexity of the software needed to control the stepper, with goto 
and ramping available.

I have used the SPI interface to control the chip as this enables control of at least a couple of motors with minimal
effort - 2 tmc5130s can be mounted on an adafruit prototyping hat making a nice compact controller.

So far the driver is pretty simplistic, but it does have good diagnstics and behaves fairly well.

This driver is far easier to install and run than the example code on the trinamic website. Their example code 
requres installation of both bcm2835 drivers and wiringpi, neither of which are standard on raspbian lite, and require
local compilation.

This has not yet been tested with more than 1 motor.

## Software Dependencies
This package is Python3, and requires pigpio to be running.

## Hardware dependencies
The driver uses 1 SPI channel per motor control chip, and 3 gpio pins:
You should use the Raspberry pi gpio harware clock (GPIO 4) This can be shared if you have more than 1 motor controller.
The other 2 pins (output stage enable and vcc-io / reset) can potentially be any ordinary gpio pin. The gpio pins and SPI settings are settable on the contructor interface for trinamicDriver.TrinamicDriver.

You will need a stepper motor and a suitable power supply.

## Overview
There are 3 files required:
- TrinamicDriver.py: (400 lines) This sets up and drives the SPI interface as well as the 3 straight gpio pins required by the tmc5130. I have tested this on the primary SPI interface using both available channels. It may not work on the Aux SPI interface as this may not support mode 3 SPI. It provides methods to read and write the chip's registers as well as chip reset and enabling the output stage.
- tmc5130regs.py: (120 lines) This contains mappings for all the register names and some of the bit flag registers to make usage more readable.
- chipdrive.py: (100 lines) This contains a single class, each instance can control a single motor. It can be used directly from the Python command line for testing and experimentation.


# Installation
git clone this repository or download the zip file and unzip it.

# demo use
cd to the directory containing the 3 python files.
start the pigpio daemon if it is not already running I use `sudo gpiod -c 256`
At the moment the gpio pins are set in the chipdrive module around line 40. You may need to change these depending on how you wired the hardware.
run python3 and in the console:
`import chipdrive`
`mot=chipdrive.tmc5130(stepsPerRev=xxx)`    # set xxx to your motor's full steps per rev count
`mot.goto(100)`                             # The motor will ramp up then down and stop at 100 revs
`mot.goto(500)`                             # the motor will ramp up then down, moving an additional 400 revs
`mot.goto(25)`                              # the motor will backup to 25 revs from initial position.
`mot.close()`                               # close the motor, release resources
`exit()`                                    # close python
The default for goto monitors the chip's status, reporting position and speed. Once the motor reaches the target position , it disables the chip's output stage and returns. Disabling the chip's output stage does mean the motor moves slightly, but it prevents the motor from heating up if the current limit is too high.

The ramping is set to slow values so it is easy to see and hear what is happening, these values, as well as the maximum speed can all be tuned.
