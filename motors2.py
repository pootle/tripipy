import guizero as gz
import time
import chipdrive
import tmc5130regs
import sys

def ticker():
    el=time.time()-starttime
    elm=int(el/60)
    els=int(el-elm*60)
    elapsed.value='%2d:%2d' %(elm, els)
    motorpan.ticker()

class Ftext(gz.Text):
    """
    simple extension to Text that links it to a given motor
    """
    def __init__(self, mpanel, **kwargs):
        """
        mpanel: motorpanel this field belongs to
        """
        self.mpanel=mpanel
        ftxt=self.makeString()
        super().__init__(master=mpanel.panel, text=ftxt, **kwargs)

    def makeString(self):
        """
        generates the string to be displayed on screen
        """
        raise NotImplementedError

class FmotorName(Ftext):
    def makeString(self):
        return self.mpanel.motor.name

class Ffield(Ftext):
    def __init__(self, motorfield, format='{}', **kwargs):
        """
        the displayed value is linked to a motor field and formatted
        """
        self.motorfield=motorfield
        self.format=format
        super().__init__(**kwargs)

    def getValue(self):
        return self.mpanel.motor[self.motorfield].getCurrent()

    def makeString(self):
        return self.format.format(self.getValue())

    def update(self):
        self.value=self.makeString()

class BitField(Ftext):
    """
    The displayed value is a single bitFlag
    """
    def __init__(self, motorfield, flagbit, textOn='Y', textOff='', **kwargs):
        self.motorfield=motorfield
        self.flagbit=flagbit
        self.textOn=textOn
        self.textOff=textOff
        super().__init__(**kwargs)

    def makeString(self):
        return self.textOn if self.mpanel.motor[self.motorfield].testFlag(self.flagbit) else self.textOff

    def update(self):
        self.value=self.makeString()

class CalcField(Ffield):
    """
    like Ffield but does a conversion on the read value
    """
    def __init__(self, mpanel, converts='regtorpm', **kwargs):
        if converts=='regtorpm':
            setattr(self, 'converter', mpanel.motor.VREGtoRPM)
        else:
            raise ValueError('unknown conversion function %s' % converts)
        super().__init__(mpanel=mpanel, **kwargs)

    def getValue(self):
        return self.converter(super().getValue())

class EdText(gz.TextBox):
    """
    basic user editable field
    """
    def __init__(self, mpanel, **kwargs):
        self.mpanel=mpanel
        super().__init__(master=mpanel.panel, command=self.checker, **kwargs)

    def checker(self):
        """
        called when the user edits the field
        """
        print('I have value %s' % self.value)

class EdInt(EdText):
    """
    EdText specialised to accept integer values
    """
    def __init__(self, minval, maxval, **kwargs):
        pass

class EdFloat(EdText):
    """
    EdText specialised for floating point numbers
    """
    def __init__(self, minval, maxval, **kwargs):
        self.minval=-sys.float_info.max if minval is None else float(minval)
        self.maxval=sys.float_info.max if maxval is None else float(maxval)
        super().__init__(**kwargs)

    def checker(self):
        for ix, ch in enumerate(self.value):
            if not ch in '+-.0123456789':
                xval=self.value[:ix]+self.value[ix+1:]
                self.value=xval

    def getValue(self):
        try:
            fv=float(self.value)
            if fv < self.minval:
                return self.minval
            if fv > self.maxval:
                return self.maxval
            return fv
        except:
            return float('nan')

class EdChoice(gz.Combo):
    def __init__(self, mpanel, **kwargs):
        self.mpanel=mpanel
        super().__init__(master=mpanel.panel, **kwargs)

class Button(gz.PushButton):
    def __init__(self, mpanel, command, **kwargs):
        self.mpanel=mpanel
        if command.startswith('../'):
            cmd=getattr(mpanel, command[3:])
        else:
            cmd=getattr(self, command)
        assert callable(cmd)
        super().__init__(master=mpanel.panel, command=cmd, **kwargs)

"""
defines the fields setup for each motor. Each entry a list of 4.
The  are used by the app to setup the labels for the fields:
0: Name of the field - used by the motor class to identify each field

The next 2 are used to setup the label for the field
1: class used for the label for the row ( 1 column per motor)
2: keyword args for the label cell, the grid position is added when the constructor is called

The last 2 are used by the motor class to setup its values for each field
3: class used for cell displaying this motor's value for the field
4: keyword args for the value cell.
"""
motorfields=(
    ('motor',    gz.Text, {'text': 'motor:',     'align': 'right'}, FmotorName,  {}),
    ('runtype',  gz.Text, {'text': 'run type:',  'align': 'right'}, EdChoice,    {'options': ['goto target', 'run forward', 'run reverse']}),
    ('speed',    gz.Text, {'text': 'speed:',     'align': 'right'}, EdChoice,    {'options': ['max rpm', 'real time', 'reverse time', 'double speed', 'target']}),
    ('userpm',   gz.Text, {'text': 'target rpm:','align': 'right'}, EdFloat,     {'minval': -100000, 'maxval': 1000000, 'align': 'left'}),
    ('targetpos',gz.Text, {'text': 'target posn:','align': 'right'}, EdFloat,    {'minval':None, 'maxval': None, 'align': 'left'}),
    ('action',   gz.Text, {'text': 'do it NOW!', 'align': 'right'}, Button,      {'text': 'ACTION!', 'command': '../actionButton'}),
    ('stat_atpos',gz.Text,{'text': 'at posn'},                      BitField,    {'motorfield': 'chipregs/SHORTSTAT', 'flagbit': tmc5130regs.statusFlags.at_position,}),
    ('stat_atmax',gz.Text,{'text': 'at max rpm'},                   BitField,    {'motorfield': 'chipregs/SHORTSTAT', 'flagbit': tmc5130regs.statusFlags.at_VMAX,}),
    ('posn',     gz.Text, {'text': 'current posn:','align': 'right'}, Ffield,    {'motorfield':'settings/posn', 'format': '{:5.2f}', 'align':'left'}),
    ('XACTUAL',  gz.Text, {'text': 'XACTUAL:',   'align': 'right'}, Ffield,      {'motorfield': 'chipregs/XACTUAL', 'format': '{:7d}', 'align': 'left'}),
    ('XTARGET',  gz.Text, {'text': 'XTARGET:',   'align': 'right'}, Ffield,      {'motorfield': 'chipregs/XTARGET', 'format': '{:7d}', 'align': 'left'}),
    ('currpm',   gz.Text, {'text': 'current rpm:','align':'right'}, Ffield,      {'motorfield': 'settings/rpmnow', 'format': '{:5.2f}', 'align': 'left'}),
    ('VACTUAL',  gz.Text, {'text': 'VACTUAL',    'align': 'right'}, Ffield,      {'motorfield': 'chipregs/VACTUAL', 'format': '{:7d}', 'align': 'left'}),
    ('maxrpm',   gz.Text, {'text': 'max rpm:',   'align': 'right'}, Ffield,      {'motorfield': 'settings/maxrpm', 'format': '{:5.2f}'}),
    ('startrpm', gz.Text, {'text': 'start rpm:', 'align': 'right'}, CalcField,   {'motorfield': 'chipregs/VSTART', 'format': '{:5.2f}'}),
    ('VMAX',     gz.Text, {'text': 'VMAX:',      'align': 'right'}, Ffield,      {'motorfield': 'chipregs/VMAX', 'format': '{:d}'}),
    ('VSTART',   gz.Text, {'text': 'VSTART:',    'align': 'right'}, Ffield,      {'motorfield': 'chipregs/VSTART', 'format': '{:d}'}),
    ('v1rpm',    gz.Text, {'text': 'V1 rpm:',    'align': 'right'}, CalcField,   {'motorfield': 'chipregs/V1', 'format': '{:5.2f}'}),
    ('stoprpm',  gz.Text, {'text': 'stop rpm:',  'align': 'right'}, CalcField,   {'motorfield': 'chipregs/VSTOP', 'format': '{:5.2f}'}),
    ('VSTOP',    gz.Text, {'text': 'VSTOP:',     'align': 'right'}, Ffield,      {'motorfield': 'chipregs/VSTOP', 'format': '{:d}'})
)

class motorPanel():
    def __init__(self, motor, gridx, pfields, panel):
        self.motor=motor
        self.panel=panel
        self.mfields={}
        for k,v in pfields.items():
            if not v['class'] is None:
                self.mfields[k]=v['class'](mpanel=self, grid=[gridx,v['y']], **v['kwargs'])

    def ticker(self):
        reads={'VACTUAL':0, 'XACTUAL':0, 'XTARGET':0, 'VACTUAL': 0, 'GSTAT':0}
        self.motor.readWriteMultiple(reads, 'R')
        self.mfields['XACTUAL'].update()
        self.mfields['posn'].update()
        self.mfields['VACTUAL'].update()
        self.mfields['currpm'].update()
        self.mfields['XTARGET'].update()
        self.mfields['VMAX'].update()
        self.mfields['stat_atpos'].update()
        self.mfields['stat_atmax'].update()

    def close(self):
        self.motor.close()

    def actionButton(self):
        rtype=self.mfields['runtype'].value
        rspeed=self.mfields['speed'].value
        if rspeed=='max rpm':
            speed=self.mfields['maxrpm'].getValue()
        elif rspeed=='real time':
            speed=1
        elif rspeed=='reverse time':
            speed=1
        elif rspeed=='double speed':
            speed=2
        elif rspeed=='target':
            speed=self.mfields['userpm'].getValue()      
        else:
            raise ValueError("speed oops " + rspeed)

        if rtype=='goto target':
            posn=self.mfields['targetpos'].getValue()
            print('doit', rtype, posn, speed)
            self.motor.goto(targetpos=posn, speed=speed)
        elif rtype in ('run forward','run reverse'):
            self.motor.setspeed(speed=speed if rtype=='run forward' else -speed)
        else:
            raise ValueError('rtype oops '+ rtype)


app = gz.App(title="Motor testing")
starttime=time.time()
header=gz.Box(app, align='top', width='fill')
elapsed = gz.Text(header, text="clock here", align='right')
mpanel=gz.Box(app, align='left', layout='grid')

pfields={}
for y, field in enumerate(motorfields):
    l=field[1](mpanel, grid=[0,y], **field[2])
    pfields[field[0]]={'y':y, 'class': field[3], 'kwargs': field[4],}
motorpan=motorPanel(motor=chipdrive.tmc5130(), gridx=1, pfields=pfields, panel=mpanel) #loglvl='rawspi'
app.repeat(1000, ticker)
app.display()
print('shutting down')
motorpan.close()