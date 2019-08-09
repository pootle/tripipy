#!/usr/bin/python3
"""
Generic driver for trinamic chips using the SPI interface using pigpio.

This driver is based on the SPI spec for the Trinamic tmc5130, but should work for several other Trinamic chips that support SPI.

It supports 2 motors (via 2 tmc chips) on a Raspberry Pi. (There is a second SPI interface on the Raspberry Pi that could
potentially drive 1 further 3 motors, but it does not appear to support SPI mode 3 which the trinamic chips use.)

The class sets up the SPI interface using pigpio (http://abyz.me.uk/rpi/pigpio/) and provides methods to read and write the registers
that control the chip's operation. It also manages a couple of extra gpio pins that are used by the chip.
"""
import logging
import pigpio
import time
from enum import IntFlag, auto
import treedict

class TrinamicDriver(treedict.Tree_dict):
    """
    This class supports various Trinamic chips with an SPI interface (such as the 5130 or 5160).
    
    Methods are provided to read and write the chipset registers by name, using data provided on setup. Control of the extra pins
    that enable the chip's output stage, control its clock and set the logic levels are integrated into the class.
    
    The driver uses the hierarchic Tree_dict class to provide easy access the state of the chip as follows:
    
        The driver has a name, which allows multiple chips to be given individual names.
        The driver has a child - 'chipregs' which contains info about all the registers for the chip. This allows inheriting classes
                to define further children for their own purposes.
        
        'chipregs' is a plain Tree_dict container that in turn contains a child for each register (named as in the chip's datasheet).
                There is an additional 'pseudo' register named 'SHORTSTAT' that contains the last read status byte from the chip
                (see datasheet section 4.1). It allows the last read status to be accessed in the same way as full registers.
                
        This enables any register to be addressed as <motor name>/chipregs/<register name>.
        
        Various types of register are supported (full details in their class definitions below):
            triHex: a register which is simply represented as an int with no understanding of it's meaning / structure
            
            triPosint / triSignedint: a register containing 1 integer. The classes understand the min / max values and 
                correctly handle 2's compliment values.
            
            triMixed: a register that can contain a number of bit flags (defined using a subclass of Intflag) and 0 or more
                multi-bit numeric fields that are numbers. The bit flags are defined by passing the IntFlag subclass as a parameter
                to the constructor (or None if there aren't any). Numeric sub-fields are setup as children of the register using the
                class triSubInt.

    To allow batching of access (which reduces the bandwidth / increases the speed of access on the SPI interface, a read/write multiple
    registers method is provided. The app can then issue a request to update multiple registers in a single call, and subsequently access
    any read values through the register's class instance.
    
    Register access examples (from within an instance of TrinamicDriver):   # these examples use the reg defs for a tmc5130
        self['chipregs/XACTUAL'].getCurrent()                               # the most recently read value of the XACTUAL register
        self['chipregs/RAMPSTAT'].testFlags(tmc5130regs.rampflags.vmax_reached # True if vmax_reached set in register RAMPSTAT
        
    Various levels of logging are available.

    It is written using a TMC5130, but hopefully keeping the specifics of that chip abstracted out.

    It uses pigpio (http://abyz.me.uk/rpi/pigpio/python.html)to do the detailed driving of the SPI interface. It can run multiple
    motors from a single Raspberry pi.
    """
    def __init__(self, masterspi=True, spiChannel=0, mode=3, datarate=1000000, cslow=True, datacount=32,
            resetpin=2, drvenpin=3, clockpin=4, clockfrequ=None, pigp={}, motordef=None, loglvl=logging.INFO, **kwargs):
        """
        Initialises the tmc5130
        
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
        super().__init__(**kwargs)
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
        regs=self.makeChild(_cclass=treedict.Tree_dict, name='chipregs')
        for rn, rdef in self.motordef['regNames'].items():
            rc=rdef['rclass']
            regs.makeChild(_cclass=rc, name=rn, **rdef['rargs'])
        regs['SHORTSTAT'].loadByte(0)
        if self.logger:
            self.logger.info("controller initialised using spi {spi} on channel {spich}, {clock}.".format(
                    spi='master' if self.masterspi else 'aux',
                    spich=self.spiChannel,
                    clock= 'undefined clock' if self.clockpin is None else 'internal clock' if self.clockfrequ is None else 'clock frequency {:,d}'.format(self.clockfrequ),
            ))

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
                pass
#                self.logger.debug("output drivers " + "enabled" if enabled else "disabled")
        elif self.logger:
            self.logger.warning("output driver (dis)enable requested but pigpio not availalble")

    def writeInt(self, regName, regValue):
        """
        Writes immediately to a single register in the Trinamic chip
        
        regName: Either the name of a register present in  self['chipregs']
        
        regValue: a value interpreted as a simple 32 bit integer that will be written to the chip.
        """
        if self.SPIlog:
            cstart=time.perf_counter_ns()
            cpustart=time.process_time_ns()
        ba=[0]*5
        self['chipregs/'+regName].writeBytes(ba, value=regValue)
        self.pigp.spi_write(self.spidev, ba)
        if self.SPIrawlog:
            self.SPIrawlog.debug('SPI_WRITE: ' + ':'.join("{:02x}".format(c) for c in ba))
        if self.SPIlog:
            clockns=time.perf_counter_ns()-cstart
            cpuratio=(time.process_time_ns()-cpustart)/clockns*100
            self.SPIlog.debug("WRITE" + " {regname:10s}: {regval:9d} ({regval:08x}) {clockus:6.1f}uS {cpu:4.1f}%CPU".format(
                    regname=str(regName), regval=regValue, clockus=clockns/1000, cpu=cpuratio,))

    def readInt(self, regName):
        """
        immediately reads a single register in the Trinamic chip. Records the status in SHORTSTAT register
        
        Note: if you want to read multiple registers, use readWriteMultiple.

        regName: Either the name of a register present in the register definition dictionary or an integer in the range 0 - 127
        
        returns the integer value of the register.
        """
        if self.SPIlog:
            cstart=time.perf_counter_ns()
            cpustart=time.process_time_ns()
        ba=[0]*5
        rrr=self['chipregs/'+regName]
        rrr.readBytes(ba)
        self.pigp.spi_write(self.spidev, ba)
        bblen, bytesback = self.pigp.spi_xfer(self.spidev, ba)
        assert bblen==5
        if self.SPIrawlog:
            self.SPIrawlog.debug('SPI_WRITE: ' + ':'.join("{:02x}".format(c) for c in ba))
            self.SPIrawlog.debug('SPI_XFER : ' + ':'.join("{:02x}".format(c) for c in ba) + ' returned ' + ':'.join("{:02x}".format(c) for c in bytesback))
        rrr.loadBytes(bytesback)
        resint=rrr.curval
        self['chipregs/SHORTSTAT'].loadByte(bytesback[0])
        if self.SPIlog:
            clockns=time.perf_counter_ns()-cstart
            cpuratio=(time.process_time_ns()-cpustart)/clockns*100
            self.SPIlog.log(self.loglvl," READ  {regname:10s}: {resint:9d} ({resint:08x}) status: {stat:02x} {clockus:6.1f}uS {cpu:4.1f}%CPU".format(
                    stat=bytesback[0], regname=str(regName),  resint=resint, clockus=clockns/1000, cpu=cpuratio))
        return resint

    def readWriteMultiple(self, regNameList, regActions='R'):
        """
        Immediately reads and writes multiple registers in a single pass. Records the status of the final exchange in SHORTSTAT register
        
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
        prevrr=self['chipregs/'+prevname]
        if regActions[0] == 'R':
            ba=[0]*5
            prevrr.readBytes(ba)
        else:
            ba=[0]*5
            prevrr.writeBytes(ba, value=regNameList[prevname])
            if self.SPIlog:
                self.SPIlog.log(self.loglvl,"WRITE" + " {regname:10s}: {regval:9d} ({regval:08x}) raw: {raw}".format(
                        regname=str(prevname), regval=regNameList[prevname], raw=":".join("{:02x}".format(c) for c in ba)))
        self.pigp.spi_write(self.spidev, ba)
        if self.SPIrawlog:
            self.SPIrawlog.debug('SPI_WRITE: ' + ':'.join("{:02x}".format(c) for c in ba))
        readback = not regActions[0]=='W'       # leave a flag that we want to get the value from the next response
        for i, reg in enumerate(regList[1:]):
            useindex=0 if len(regActions)==1 else i
            rrr=self['chipregs/'+reg]
            if regActions[useindex]=='R':
                rrr.readBytes(ba)
            else:
                rrr.writeBytes(ba,value=regNameList[reg])
                if self.SPIlog:
                    self.SPIlog.log(self.loglvl,"WRITE" + " {regname:10s}: {regval:9d} ({regval:08x}) raw: {raw}".format(
                        regname=str(reg), regval=regNameList[reg], raw=":".join("{:02x}".format(c) for c in ba)))
            bblen, bytesback = self.pigp.spi_xfer(self.spidev, ba)
            if self.SPIrawlog:
                self.SPIrawlog.debug('SPI_XFER : ' + ':'.join("{:02x}".format(c) for c in ba) + ' returned ' + ':'.join("{:02x}".format(c) for c in bytesback))
            if readback:
                assert bblen==5
                prevrr.loadBytes(bytesback)
                resp[prevname]=prevrr.curval
                if self.SPIlog:
                    self.SPIlog.log(self.loglvl,"READ " + " {regname:10s}: {regval:9d} ({regval:08x}) raw: {raw}".format(
                        regname=str(prevname), regval=resp[prevname], raw=":".join("{:02x}".format(c) for c in bytesback)))
            prevname=reg
            prevrr=rrr
            readback=not regActions[useindex]=='W'
        ba[0] = ba[0] & 127
        bblen, bytesback = self.pigp.spi_xfer(self.spidev, ba)
        if self.SPIrawlog:
            self.SPIrawlog.debug('SPI_XFER : ' + ':'.join("{:02x}".format(c) for c in ba) + ' returned ' + ':'.join("{:02x}".format(c) for c in bytesback))
        assert bblen==5
        self['chipregs/SHORTSTAT'].loadByte(bytesback[0])
        if readback:
            prevrr.loadBytes(bytesback)
            resp[prevname]=prevrr.curval
            if self.SPIlog:
                self.SPIlog.log(self.loglvl,"READ " + " {regname:10s}: {regval:9d} ({regval:08x}) raw: {raw}".format(
                    regname=str(prevname), regval=resp[prevname], raw=":".join("{:02x}".format(c) for c in bytesback)))
        if self.SPIlog:
            clockns=time.perf_counter_ns()-cstart
            cpuratio=(time.process_time_ns()-cpustart)/clockns*100
            self.SPIlog.log(self.loglvl,"Status: {stat:s}, SPI timing: {clockus:6.1f}uS {cpu:4.1f}%CPU".format(stat=self['chipregs/SHORTSTAT'].curval,
                    clockus=clockns/1000, cpu=cpuratio))
        return resp

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

class regFlags(IntFlag):
    """
    flags associated with every register indicating if the register can be read and / or can be written. Used to check access.
    """
    NONE        =0
    readable    =auto()
    writeable   =auto()

class triRegister(treedict.Tree_dict):
    """
    Every register uses an instance of (a derived version) of this class. This class records basic info about the register
    and provides some common methods.
    
    Registers inherit from Tree_dict so we can easily address them from the motor level and can subdivide them for bit 
    fields. The actual value of the register is held at this level for full registers and for bit field registers.
    
    """
    def __init__(self, addr, access, logacts=[], **kwargs):
        """
        sets up basic info on the register
        
        addr:   The address of the register
        access: a string containing 'W' if register can be written to the chip and 'R' if the register can be read from the chip
        """
        assert 0 <= int(addr) < 128
        self.addr=int(addr)
        self.rflags = regFlags.readable if 'R' in access else regFlags.NONE
        if 'W' in access:
            self.rflags |= regFlags.writeable
        try:
            super().__init__(**kwargs)
        except:
            print('exception in reg setup', kwargs)
            raise

    def getCurrent(self):
        """
        returns the current value in the register - the last (or about to be) written value for write only regs, or the last
        read value if the register is readable.
        
        readint or readwriteMultiple must be called before this to get an up to date value if appropriate.
        
        The returned type depends on the type of register (i.e. not necessarily an int)
        """
        raise NotImplementedError()

    def readBytes(self, ba):
        """
        puts the register number in the first byte of the given buffer
        """
        ba[0]=self.addr

    def writeVal(self, value):
        """
        called to set a new value to be written to the chip register 
        """
        pass

    def packBytes(self, ba, rawval):
        if regFlags.writeable in self.rflags:
            ba[0]=self.addr | 128
            ba[1]=(rawval>>24) & 255
            ba[2]=(rawval>>16) & 255
            ba[3]=(rawval>>8) & 255
            ba[4]=rawval & 255
        else:
            raise ValueError('register %s does not allow write' % self.name)

    def unpackBytes(self, ba):
        return ((ba[1]<<24) | (ba[2]<<16) | (ba[3]<<8) | ba[4])

class triHex(triRegister):
    """
    basic class where we just do it in hex. Used as a backstop for registers we don't care about yet.
    """
    def getCurrent(self):
        return self.curval

    def setVal(self, value):
        """
        called when a new value read from the chip: updates the last known chip value
        """
        self.curval=value

    def writeBytes(self, ba, value=None):
        """
        fills the given 5 byte buffer with the bytes to write to the chip.
        """
        
        if not value is None:
            self.setVal(value)
        self.packBytes(ba, self.getCurrent())

    def loadBytes(self, ba):
        """
        extracts the value from the final bytes of the passed buffer
        """
        self.setVal(self.unpackBytes(ba))

class triInt(triHex):
    """
    Registers that hold a single integer in the low order bits
    """
    def setVal(self, value):
        """
        called when a new value read from the chip: updates the last known chip value
        """
        if self.minval <= value <= self.maxval:
            super().setVal(value)
        else:
            raise ValueError('%s is not a legal value for register %s' % (value, self.name))

    def writeBytes(self, ba, value=None):
        """
        fills the given 5 byte buffer with the bytes to write to the chip. Note that the mask is applied to strip off
        high order bits in case the value is negative
        """
        if not value is None:
            self.setVal(value)
        self.packBytes(ba, self.getCurrent() & self.mask)

class triPosint(triInt):
    def __init__(self, sigbits, maxval=None, initialval=0, **kwargs):
        super().__init__(**kwargs)
        self.maxval=2**sigbits-1 if maxval is None else maxval
        self.minval=0
        self.mask=2**sigbits-1
        self.setVal(initialval)

    def loadBytes(self, ba):
        """
        extracts the value from the final bytes of the passed buffer
        """
        self.setVal(self.unpackBytes(ba)) & self.mask

class triSignedint(triInt):
    def __init__(self, sigbits, initialval=0, **kwargs):
        super().__init__(**kwargs)
        self.maxval=2**(sigbits-1)-1
        self.minval=-self.maxval-1
        self.mask=2**sigbits-1
        self.setVal(initialval)

    def loadBytes(self, ba):
        """
        extracts the value from the final bytes of the passed buffer
        """
        bbval=self.unpackBytes(ba) & self.mask
        if bbval & -self.minval:
            self.setVal(self.minval*2+bbval)
        else:
            self.setVal(bbval)

class triByteFlags(treedict.Tree_dict):
    """
    a special version for the status byte returned on every spi transfer - makes it look like another register to the app
    """
    def __init__(self, flagClass, **kwargs):
        self.flagClass=flagClass
        self.curval=self.flagClass.NONE
        super().__init__(**kwargs)

    def loadByte(self, abyte):
        self.curval=self.flagClass(abyte)

    def testFlag(self, flagbits):
        """
        test for 1 or more bits set (all must be set to return true)
        """
        return self.curval & flagbits == flagbits

class triEnum(triRegister):
    """
    for registers where each value has a distinct meaning, use an enum to make code easier to understand
    """
    def __init__(self, enumClass, **kwargs):
        self.enumClass=enumClass
        super().__init__(**kwargs)

    def loadBytes(self, ba):
        self.curval=self.enumClass(self.unpackBytes(ba))

    def writeBytes(self, ba, value=None):
        """
        fills the given 5 byte buffer with the bytes to write to the chip.
        """
        if not value is None:
            self.curval=value
        self.packBytes(ba, self.curval.value)

    def getCurrent(self):
        return self.curval

class triMixed(triRegister):
    """
    A class for registers that have a mix of 0 or more bit flags and 1 or more multi bit value fields.
    The flags can be checked in the same way as for a triFlags register, the multi bit fields are 
    children of this field that are checked dynamically. They need to be created separately after this
    has been created. (see triSubReg below).
    """
    def __init__(self, flagClass=None, **kwargs):
        if flagClass is None:
            self.flagmask=None
        else:
            fall = flagClass(0)
            for f in flagClass:
                fall |= f
            self.flagsmask=fall.value
        self.curval=0
        super().__init__(**kwargs)

    def testFlags(self, flagbits):
        """
        test for 1 or more bits set (all must be set to return True)
        """
        assert not self.flagmask is None
        return self.curval & flagbits == flagbits

    def setFlags(self, flagbits, on):
        """
        sets 1 or more flagbits on or off.
        
        flagbits: 1 or more flagbits
        
        on: If True set flagbits, else clear them
        """
        assert not self.flagmask is None
        if on:
            self.curval |= flagbits
        else:
            self.curval &= ~flagbits

    def loadBytes(self, ba):
        self.curval=self.unpackBytes(ba)

    def writeBytes(self, ba, value=None):
        """
        fills the given 5 byte buffer with the bytes to write to the chip.
        """
        if not value is None:
            raise ValueError('register %s cannot accept new value in writeBytes' % self.name)
        self.packBytes(ba, self.curval)

class triSubInt(treedict.Tree_dict):
    """
    a class for an integer that is a few bits somewhere in the register.
    
    Instances of this class must be created as children of a triMixed instance. The current value
    is always that held in the parent
    """
    def __init__(self, lowbit, bitcount, **kwargs):
        bitmask=2**bitcount-1
        self.lowbit=lowbit
        self.bitmask=bitmask << lowbit
        super().__init__(**kwargs)

    def getCurrent(self):
        return (self.parent.curval & self.bitmask) >> self.lowbit

    def set(self, value):
        shv=value<<self.lowbit
        assert shv & self.bitmask==shv
        pv=self.parent.curval & ~self.bitmask
        self.parent.curval = pv | shv

class triSubEnum(treedict.Tree_dict):
    """
    a class for an enumeration that is a few bits somewhere in the register.
    
    The register field is effectively an int, but since each value has a unique meaning, this 
    allows meaninful names to be used.
    """
    def __init__(self, lowbit, bitcount, enumClass, **kwargs):
        bitmask=2**bitcount-1
        self.lowbit=lowbit
        self.bitmask=bitmask << lowbit
        self.enumClass=enumClass
        super().__init__(**kwargs)

    def getCurrent(self):
        return self.enumClass((self.parent.curval & self.bitmask) >> self.lowbit)

    def set(self, value):
        shv=value.value<<self.lowbit
        assert shv & self.bitmask==shv
        pv=self.parent.curval & ~self.bitmask
        self.parent.curval = pv | shv