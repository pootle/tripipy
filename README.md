# tripipy
Python driver for Trinamic tmc5130 connected to Raspberry Pi

The Trinamic stepper control chips (like the tmc5130 and tmc5160) are FAR more sophisticated than the older 
stepper chips like the A4988. They are more expensive (around £15 mounted on a breakput board), but the 
added functionality dramtically reduces the compexity of the software needed to control the stepper, with goto 
and ramping available.

I have used the SPI interface to control the chip as this enables control of at least a couple of motors with minimal
effort - 2 tmc5130s can be mounted on an adafruit prototyping hat making a nice compact controller.

This driver is far easier to install and run than the example code on the trinamic website. Their example code 
requres installation of both bcm2835 drivers and wiringpi, neither of which are standard on raspbian lite, and require
local compilation.

I've run this with 2 motors on the base Raspiberry Pi SPI interface

## Software Dependencies
This package is Python3, and requires pigpio to be running, it also uses guizero to provide a simple testing interface.
The testing interface requires raspbian or raspbian-full.

` sudo apt-get install python3-pigpio
 sudo pip3 install guizero`

## Hardware dependencies
The driver uses 1 SPI channel per motor control chip, and 3 gpio pins:
You should use the Raspberry pi gpio harware clock (GPIO 4) This can be shared if you have more than 1 motor controller.
The other 2 pins (output stage enable and vcc-io / reset) can potentially be any ordinary gpio pin. The gpio pins and SPI 
settings are settable on the contructor interface for trinamicDriver.TrinamicDriver.

You will need a stepper motor and a suitable power supply.

## Overview
There are 5 python files:
- TrinamicDriver.py: (480 lines) This sets up and drives the SPI interface as well as the 3 straight gpio pins required by the tmc5130. 
  I have tested this on the primary SPI interface using both available channels. It may not work on the Aux SPI interface as this may not 
  support mode 3 SPI. It provides methods to read and write the chip's registers as well as chip reset and enabling the output stage.
- tmc5130regs.py: (170 lines) This contains mappings for all the register names and some of the bit flag registers defined as IntFlags
  to make usage more readable. Each of the chip's registers is defined as an instance of a register class.
- chipdrive.py: (250 lines) This contains a class tmc5130, each instance can control a single motor. There is a sample app (motors3.py) that 
  can drive the motor displaying live status as the motor runs
- treedict.py: a utility class that provides simple access to the chip register classes
- motor2.py: a sample app, built using guizero to provide a simple gui to control the chip / motor.


# Installation

- git clone this repository or download the zip file and unzip it.

- install python3-pigpio

- install guizero

# demo use
cd to the directory containing the 3 python files.

start the pigpio daemon if it is not already running I use `sudo gpiod -c 256`

At the moment the gpio pins are set in the chipdrive module around line 40. You may need to change these depending on how you wired the hardware.

run the app:

`python3 motor2.py`

Select the mode to use:
`goto target: the chip drives the motor to reach the target  -  set a target posn before ppressing ACTION!
  
