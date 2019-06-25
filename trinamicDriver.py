#!/usr/bin/python3
"""
Generic driver for trinamic chips using the SPI interface using pigpio.

This driver is based on the SPI spec for the Trinamic tmc5130, but should work for several other Trinamic chips that support SPI.

It should support 2 motors (via 2 tmc chips) on a Raspberry Pi. (There is a second SPI interface on the Raspberry Pi that could
potentially drive 1 further 3 motors, but it does not appear to support SPI mode 3 which the trinamic chips use.)

The class sets up the SPI interface using pigpio (http://abyz.me.uk/rpi/pigpio/) and provides methods to read and write the registers
that control the chip's operation. It also manages a couple of extra gpio pins that are used by the chip.
"""
import logging
import pigpio
import time

class TrinamicDriver():
    """
    This class supports various Trinamic chips with an SPI interface (such as the 5130 or 5160.
    
    Methods are provided to read and write the chipset registers by name, using tables provided on setup. Control of the extra pins
    that enable the chip's output stage, control its clock and set the logic levels are integrated into the class. 

    Various levels of logging are available.

    It is written using a TMC5130, but hopefully keeping the specifics of that chip abstracted out.

    It uses pigpio (http://abyz.me.uk/rpi/pigpio/python.html)to do the detailed driving of the SPI interface. It should enable multiple
    motors to be run from a single Raspberry pi.
    """
    def __init__(self, name='motor', masterspi=True, spiChannel=0, mode=3, datarate=1000000, cslow=True, datacount=32,
            resetpin=2, drvenpin=3, clockpin=4, clockfrequ=None, pigp={}, motordef=None, loglvl=logging.INFO):
        """
        Initialises the tmc5130

        name:       for logging purposes, a name for this motor
        
        masterspi:  uses main SPI interface, otherwise uses auxiliary interface
        
        spiChannel: which chip select to use - 0 or 1 for main, 0, 1 or 2 for auxiliary
        
        mode:       spi mode (0..3)
        
        datarate:   (or baud rate), defaults to 1MHz
        
        cslow:      chip select is active low if True (else active high)
        
        datacount:  this is the number of bits of data, rounded up to bytes for main SPI interface, or word length
                    for the aux interface

        resetpin:   gpio pin connected to VCC_IO that is also used for reset

        drvenpin:   gpio pin number to enable chip output stage - low is enabled, high is disabled. If None, we assume
                    the drivers are permanently enabled outwith our control.
        
        clockpin:   gpio pin with the clock for the chip. If None we assume the clock input is handled elsewhere
                    (e.g. shared with another device)
        
        clockfrequ: If None the clock pin is set low so the chip uses its internal clock, otherwise the frequency in Hz (10000000 is good)
        
        pigp:       instance of pigpio to use

        motordef:   Definitions of the the various registers and other motor information
        
        loglvl:     controls the logging from. 
                    loglvl is None, no logging is performed (apart from a critical warning if pigpio is broken)
                    loglvl integer >= logging.DEBUG, logging of most activity to logger <classname>.<name> using various levels
                    loglvl string 'rawspi'  uses logging.DEBUG, logging of ALL SPI activity to logger <classname>.<name>.<SPI>
                    loglvl string 'commands' uses logging DEBUG logging logical activity in SPI interface to logger <classname>.<name>.<SPI>
                    loglvl string 'all' does both rawspi and commands logging
        """
        self.pigp=pigp
        if not self.pigp.connected:
            logging.getLogger().critical("pigpio daemon does not appear to be running")
            self.pigp=None          # this is used as a master control to enable / disable all functionality
            raise RuntimeError("pigpio daemon does not appear to be running")
        self.name=name
        self.loglvl = loglvl if loglvl is None or isinstance(loglvl,int) else logging.DEBUG
        self.logger=None if self.loglvl is None else logging.getLogger(type(self).__name__ + '.' + self.name)
        self.SPIlog=logging.getLogger(type(self).__name__ + '.' + self.name + '.SPI') if loglvl in ('commands', 'all') else None
        self.SPIrawlog=logging.getLogger(type(self).__name__ + '.' + self.name + '.SPI') if loglvl in ('rawspi', 'all') else None
        assert isinstance(masterspi,bool)
        assert isinstance(spiChannel,int) and 0<=spiChannel<=2
        assert isinstance(mode,int) and 0<=mode<=3
        assert 32767 < datarate < 10000000
        assert isinstance(cslow,bool)
        assert isinstance(resetpin,int) and 0<=resetpin<=53
        assert isinstance(drvenpin,int) and 0<=drvenpin<=53
        assert clockpin is None or (isinstance(clockpin,int) and 0<=clockpin<=53)
        assert isinstance(motordef, dict)       # testing for dict is a bit strict but will do for now
        self.vccio=resetpin                       
        self.drvenable=drvenpin
        self.clockpin=clockpin
        self.clockfrequ=clockfrequ
        self.spiChannel=spiChannel
        self.spimode=mode
        self.datarate=datarate
        self.cslow=cslow
        self.masterspi=masterspi
        self.resetChip()
        self.setupIO()
        self.motordef=motordef
        self.regdefs=self.motordef['regNames']
        self.status=0
        self.lastwritten={}     # a dict of the last value written to each register
        if self.logger:
            self.logger.info("controller initialised using spi {spi} on channel {spich}, {clock}.".format(
                    spi='master' if self.masterspi else 'aux'
                   ,spich=self.spiChannel
                   ,clock= 'undefined clock' if self.clockpin is None else 'internal clock' if self.clockfrequ is None else 'clock frequency {:,d}'.format(self.clockfrequ))
            )
        
    def setupIO(self):
        """
        initialises all the io needed to control the chip
        """
        self.pigp.set_mode(self.vccio,pigpio.OUTPUT)
        self.pigp.write(self.vccio,1)
        self.pigp.set_mode(self.drvenable,pigpio.OUTPUT)
        self.enableOutput(False)
        if not self.clockpin is None:
            self.pigp.set_mode(self.clockpin,pigpio.OUTPUT)
            if self.clockfrequ is None:
                self.pigp.write(self.clockpin, 0)
            else:
                self.pigp.hardware_clock(self.clockpin, self.clockfrequ)
        self.spidev=self.pigp.spi_open(self.spiChannel,baud=self.datarate,
                spi_flags=self.spimode + 0 if self.cslow else self.spiChannel<<4 + 0 if self.masterspi else 256)

    def resetChip(self):
        """
        This should reset the chip
        """
        self.pigp.set_mode(self.vccio, pigpio.OUTPUT)
        self.pigp.set_mode(self.drvenable, pigpio.OUTPUT)
        self.pigp.write(self.drvenable,0)
        self.pigp.write(self.vccio,0)
        time.sleep(.1)
        self.pigp.write(self.vccio,1)
        self.pigp.write(self.drvenable,1)
        if self.logger:
            self.logger.info("chip reset attempted")

    def enableOutput(self, enabled):
        """
        use this to enable or disable the mosfet output drivers
        """
        if not self.pigp is None and self.pigp.connected:
            self.pigp.write(self.drvenable, 0 if enabled is True else 1)
            if self.logger:
                self.logger.debug("output drivers " + "enabled" if enabled else "disabled")
        elif self.logger:
            self.logger.warning("output driver (dis)enable requested but pigpio not availalble")

    def writeInt(self, regName, regValue):
        """
        Writes to a single register in the Trinamic chip
        
        regName: Either the name of a register present in the register definition dictionary or an integer in the range 0 - 127
        
        regValue: a value interpreted as a simple 32 bit integer that will be written to the chip.
        """
        if self.SPIlog:
            cstart=time.perf_counter_ns()
            cpustart=time.process_time_ns()
        regint, _ = self._checkRegName(regName, 'W')
        valueint=regValue
        ba = bytes([regint|128
            , (valueint>>24) & 255
            , (valueint>>16) & 255
            , (valueint>>8) & 255
            , valueint & 255])
        self.pigp.spi_write(self.spidev, ba)
        self.lastwritten[regName]=regValue
        if self.SPIrawlog:
            self.SPIrawlog.debug('SPI_WRITE: ' + ':'.join("{:02x}".format(c) for c in ba))
        if self.SPIlog:
            clockns=time.perf_counter_ns()-cstart
            cpuratio=(time.process_time_ns()-cpustart)/clockns*100
            self.SPIlog.debug("WRITE" + " {regname:10s}: {regval:9d} ({regval:08x}) {clockus:6.1f}uS {cpu:4.1f}%CPU".format(
                    regname=str(regName), regval=valueint, clockus=clockns/1000, cpu=cpuratio,))

    def readInt(self, regName):
        """
        reads a single register in the Trinamic chip. Records the status in self.status
        
        Note: if you want to read multiple registers, use readWriteMultiple.

        regName: Either the name of a register present in the register definition dictionary or an integer in the range 0 - 127
        
        returns the integer value of the register.
        """
        if self.SPIlog:
            cstart=time.perf_counter_ns()
            cpustart=time.process_time_ns()
        regint, regdef = self._checkRegName(regName, 'R')
        ba = bytes([regint
            , 0, 0, 0, 0])
        self.pigp.spi_write(self.spidev, ba)
        bblen, bytesback = self.pigp.spi_xfer(self.spidev, ba)
        if self.SPIrawlog:
            self.SPIrawlog.debug('SPI_WRITE: ' + ':'.join("{:02x}".format(c) for c in ba))
            self.SPIrawlog.debug('SPI_XFER : ' + ':'.join("{:02x}".format(c) for c in ba) + ' returned ' + ':'.join("{:02x}".format(c) for c in bytesback))
        assert bblen==5
        if 'readconv' in regdef:
            resint=regdef['readconv'](bytesback)
        else:
            resint=(bytesback[1]<<24)+(bytesback[2]<<16)+(bytesback[3]<<8)+bytesback[4]
        self.status=bytesback[0]
        if self.SPIlog:
            clockns=time.perf_counter_ns()-cstart
            cpuratio=(time.process_time_ns()-cpustart)/clockns*100
            self.SPIlog.log(self.loglvl," READ  {regname:10s}: {resint:9d} ({resint:08x}) status: {stat:02x} {clockus:6.1f}uS {cpu:4.1f}%CPU".format(
                    stat=bytesback[0], regname=str(regName),  clockus=clockns/1000, cpu=cpuratio))
        return resint

    def readWriteMultiple(self, regNameList, regActions='R'):
        """
        Reads and writes multiple registers in a single pass. Records the status of the final exchange in self.status.
        
        Somewhat more efficient than reading / writing 1 at a time due to the way the chip interface works.

        regNameList: can be a list or a dict, if a dict then the values are updated (for registers marked as 'R'ead - see below)
                     otherwise a new dict is returned with a key for each reg name marked as 'R'ead, with the value read, also 
                     note if regActions is not a single character, the dict should be ordered to match regActions below (python3.7 dict or an ordered dict 
                     for earlier versions).
                     Note it must be a dict if any registers are written.
        
        regActions: a string or an array of single characters that define the action for each register, if the array or string is length 1, then all
                    registers are treated the same way
                        'R' - read the register
                        'W' - write the register
                        'U' - write the register and read back the value
        """
        if self.SPIlog:
            cstart=time.perf_counter_ns()
            cpustart=time.process_time_ns()
        if isinstance(regNameList, dict):
            resp=regNameList
            regList=list(regNameList.keys())
        else:
            resp={}
            regList=regNameList
        assert len(regActions)==1 or len(regActions)==len(regNameList)
        prevname=regList[0]
        # check the first action - if read use dummy data, otherwise put the value in the buffer
        if regActions[0] == 'R':
            regint, prevdef = self._checkRegName(prevname, 'R')
            ba = [regint
            , 0, 0, 0, 0]
        else:
            regint, prevdef = self._checkRegName(prevname, 'W')
            valueint = regNameList[prevname]
            ba = [regint|128
                , (valueint>>24) & 255
                , (valueint>>16) & 255
                , (valueint>>8) & 255
                , valueint & 255]
            self.lastwritten[prevname]=valueint
            if self.SPIlog:
                self.SPIlog.log(self.loglvl,"WRITE" + " {regname:10s}: {regval:9d} ({regval:08x}) raw: {raw}".format(
                    regname=str(prevname), regval=valueint, raw=":".join("{:02x}".format(c) for c in ba)))
        self.pigp.spi_write(self.spidev, ba)
        if self.SPIrawlog:
            self.SPIrawlog.debug('SPI_WRITE: ' + ':'.join("{:02x}".format(c) for c in ba))
        readback = not regActions[0]=='W'       # leave a flag that we want to get the value from the next response
        for i, reg in enumerate(regList[1:]):
            useindex=0 if len(regActions)==1 else i
            if regActions[useindex]=='R':
                regint, nextdef = self._checkRegName(reg, 'R')
                ba[0] = regint
            else:
                regint, nextdef = self._checkRegName(reg, 'W')
                valueint=regNameList[reg]
                ba[0] = 128 | regint
                ba[1] = (valueint>>24) & 255
                ba[2] = (valueint>>16) & 255
                ba[3] = (valueint>>8) & 255
                ba[4] = valueint & 255
                self.lastwritten[reg]=valueint
                if self.SPIlog:
                    self.SPIlog.log(self.loglvl,"WRITE" + " {regname:10s}: {regval:9d} ({regval:08x}) raw: {raw}".format(
                        regname=str(reg), regval=valueint, raw=":".join("{:02x}".format(c) for c in ba)))
            bblen, bytesback = self.pigp.spi_xfer(self.spidev, ba)
            if self.SPIrawlog:
                self.SPIrawlog.debug('SPI_XFER : ' + ':'.join("{:02x}".format(c) for c in ba) + ' returned ' + ':'.join("{:02x}".format(c) for c in bytesback))
            if readback:
                assert bblen==5
                if 'readconv' in prevdef:
                    resp[prevname]=prevdef['readconv'](bytesback)
                else:
                    resp[prevname]=(bytesback[1]<<24)+(bytesback[2]<<16)+(bytesback[3]<<8)+bytesback[4]
                if self.SPIlog:
                    self.SPIlog.log(self.loglvl,"READ " + " {regname:10s}: {regval:9d} ({regval:08x}) raw: {raw}".format(
                        regname=str(prevname), regval=resp[prevname], raw=":".join("{:02x}".format(c) for c in bytesback)))
            prevname=reg
            prevdef=nextdef
            readback=not regActions[useindex]=='W'
        ba[0] = ba[0] & 127
        bblen, bytesback = self.pigp.spi_xfer(self.spidev, ba)
        if self.SPIrawlog:
            self.SPIrawlog.debug('SPI_XFER : ' + ':'.join("{:02x}".format(c) for c in ba) + ' returned ' + ':'.join("{:02x}".format(c) for c in bytesback))
        assert bblen==5
        self.status=bytesback[0]
        if readback:
            if 'readconv' in prevdef:
                resp[prevname]=prevdef['readconv'](bytesback)
            else:
                resp[prevname]=(bytesback[1]<<24)+(bytesback[2]<<16)+(bytesback[3]<<8)+bytesback[4]
            if self.SPIlog:
                self.SPIlog.log(self.loglvl,"READ " + " {regname:10s}: {regval:9d} ({regval:08x}) raw: {raw}".format(
                    regname=str(prevname), regval=resp[prevname], raw=":".join("{:02x}".format(c) for c in bytesback)))
        if self.SPIlog:
            clockns=time.perf_counter_ns()-cstart
            cpuratio=(time.process_time_ns()-cpustart)/clockns*100
            self.SPIlog.log(self.loglvl,"Status: {stat:02x}, SPI timing: {clockus:6.1f}uS {cpu:4.1f}%CPU".format(stat=self.status, clockus=clockns/1000, cpu=cpuratio))
        return resp

    def flagsToText(self, flags, lookup):
        return [txt for fbit, txt in self.motordef[lookup].items() if fbit & flags ]

    def close(self):
        if not self.pigp is None and self.pigp.connected:
            self.pigp.write(self.drvenable,1)   # if we still have a working pigpio, set the enable pin high to 
                                                # stop current flowing (disable the chip output stage)
        try:
            if not self.spidev is None:
                self.pigp.spi_close(self.spidev)
                self.spidev=None
        except:
            pass
        if not self.clockpin is None:
            if not self.clockfrequ is None:
                self.pigp.hardware_clock(self.clockpin, 0)            
        self.pigp=None
        if self.logger:
            self.logger.info("controller shut down")

    def _checkRegName(self, regName, checkFlag):
        """
        used by readReg and writeReg. to validate and convert the register name or number

        regName     : name of register or integer value of register
        
        checkFlag   : if not None and regName is in regdefs then check the flag is present in the regdef 'mode'
        
        returns a tuple of register number, register definition if regName is not a number otherwise None
        """
        if not self.regdefs is None and regName in self.regdefs:
            rdef=self.regdefs[regName]
            if checkFlag is None or checkFlag in rdef['mode']:
                return rdef['addr'], rdef
            else:
                if self.logger:
                    self.logger.error("The register %s is not writable" % str(regName))
                raise RuntimeError("The register %s is not writable" % str(regName))
        else:
            regint=int(regName)
            if 0<regint<128:
                return regint, None
            else:
                if self.logger:
                    self.logger.error("The register number given (%d) is not in the range 0..127" % rval)
                raise ValueError("The register number given (%d) is not in the range 0..127" % rval)
