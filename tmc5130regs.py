#!/usr/bin/python3
"""
This defines the registers accessible via SPI for a tmc5130
"""

def bytesToSigned32(bytearr):
    """
    converts the last 4 bytes of a 5 byte array to a signed integer
    """
    unsigned=(bytearr[1]<<24)+(bytearr[2]<<16)+(bytearr[3]<<8)+bytearr[4]
    return unsigned-4294967296 if bytearr[1]&128 else unsigned

def bytesToSigned24(bytearr):
    """
    converts the last 3 bytes of a 5 byte array to a signed integer
    """
    unsigned=(bytearr[2]<<16)+(bytearr[3]<<8)+bytearr[4]
    return unsigned-16777216 if bytearr[2]&128 else unsigned


def bytesToUnsigned(bytearr):
    return (bytearr[1]<<24)+(bytearr[2]<<16)+(bytearr[3]<<8)+bytearr[4]

addr="addr"
mode="mode"
readconv="readconv"

_regset={
    "GCONF":      {addr: 0x00, mode:"RW"},
    "GSTAT":      {addr: 0x01, mode:"RC"},
    "IFCNT":      {addr: 0x02, mode:""},
    "SLAVECONF":  {addr: 0x03, mode:""},
    "INP_OUT":    {addr: 0x04, mode:"R"},
    "X_COMPARE":  {addr: 0x05, mode:"W"},

    "IHOLD_IRUN": {addr: 0x10, mode:"W"},
    "TPOWERDOWN": {addr: 0x11, mode:"W"},
    "TSTEP":      {addr: 0x12, mode:"R"},
    "TPWMTHRS":   {addr: 0x13, mode:"W"},
    "TCOOLTHRS":  {addr: 0x14, mode:"W"},
    "THIGH":      {addr: 0x15, mode:"W"},

    "RAMPMODE":   {addr: 0x20, mode:"RW"},
    "XACTUAL":    {addr: 0x21, mode:"RW"},
    "VACTUAL":    {addr: 0x22, mode:"R", readconv:bytesToSigned24},
    "VSTART":     {addr: 0x23, mode:"W"},
    "A1":         {addr: 0x24, mode:"W"},
    "V1":         {addr: 0x25, mode:"W"},
    "AMAX":       {addr: 0x26, mode:"W"},
    "VMAX":       {addr: 0x27, mode:"W"},
    "DMAX":       {addr: 0x28, mode:"W"},
    "D1":         {addr: 0x2A, mode:"W"},
    "VSTOP":      {addr: 0x2B, mode:"W"},
    "TZEROWAIT":  {addr: 0x2C, mode:"W"},
    "XTARGET":    {addr: 0x2D, mode:"RW"},

    "VDCMIN":     {addr: 0x33, mode:"W"},
    "SWMODE":     {addr: 0x34, mode:"RW"},
    "RAMPSTAT":   {addr: 0x35, mode:"RC"},
    "XLATCH":     {addr: 0x36, mode:"R"},

    "ENCMODE":    {addr: 0x38, mode:"RW"},
    "XENC":       {addr: 0x39, mode:"RW"},
    "ENC_CONST":  {addr: 0x3A, mode:"W"},
    "ENC_STATUS": {addr: 0x3B, mode:"RC"},
    "ENC_LATCH":  {addr: 0x3C, mode:"R"},

    "MSLUT0":     {addr: 0x60, mode:"W"},
    "MSLUT1":     {addr: 0x61, mode:"W"},
    "MSLUT2":     {addr: 0x62, mode:"W"},
    "MSLUT3":     {addr: 0x63, mode:"W"},
    "MSLUT4":     {addr: 0x64, mode:"W"},
    "MSLUT5":     {addr: 0x65, mode:"W"},
    "MSLUT6":     {addr: 0x66, mode:"W"},
    "MSLUT7":     {addr: 0x67, mode:"W"},
    "MSLUTSEL":   {addr: 0x68, mode:"W"},
    "MSLUTSTART": {addr: 0x69, mode:"W"},
    "MSCNT":      {addr: 0x6A, mode:"R"},
    "MSCURACT":   {addr: 0x6B, mode:"R"},

    "CHOPCONF":   {addr: 0x6C, mode:"RW"},
    "COOLCONF":   {addr: 0x6D, mode:"W"},
    "DCCTRL":     {addr: 0x6E, mode:"W"},
    "DRVSTATUS":  {addr: 0x6F, mode:"R"},
    "PWMCONF":    {addr: 0x70, mode:"W"},
    "PWMSCALE":   {addr: 0x71, mode:"R"},
    "ENCM_CTRL":  {addr: 0x72, mode:"W"},
    "LOST_STEPS": {addr: 0x73, mode:"R"},
}

reglookup={
    v[addr]:k for k,v in _regset.items()
}

_statusBitLookup={
    1: 'reset'
   ,2: 'driver error'
   ,4: 'stallguard'
   ,8: 'stationary'
  ,16: 'at VMAX'
  ,32: 'at position'
  ,64: 'leftstop'
 ,128: 'rightstop'} 

_rampStatusBitLookup={
     0x01: 'limit left'
    ,0x02: 'limit right'
    ,0x04: 'latch left'
    ,0x08: 'latch right'
    ,0x10: 'stop left'
    ,0x20: 'stop right'
    ,0x40: 'stalled'
    ,0x80: 'pos reached event'
  ,0x0100: 'vmax reached'
  ,0x0200: 'pos reached'
  ,0x0400: 'speed zero'
  ,0x0800: 'zero transit wait'
  ,0x1000: 'reversed dir'
  ,0x2000: 'stall guard 2 active'
}

tmc5130={
    'regNames'    : _regset
   ,'statusBits'  : _statusBitLookup
   ,'statusNames' : {v: k for k,v in _statusBitLookup.items()}
   ,'rampstatBits': _rampStatusBitLookup
}
"""	// ramp modes (Register TMC5130_RAMPMODE)
    "TMC5130_MODE_POSITION  0
    "TMC5130_MODE_VELPOS    1
    "TMC5130_MODE_VELNEG    2
    "TMC5130_MODE_HOLD      3

	// limit switch mode bits (Register TMC5130_SWMODE)
    "TMC5130_SW_STOPL_ENABLE    0x0001
    "TMC5130_SW_STOPR_ENABLE    0x0002
    "TMC5130_SW STOPL_POLARITY  0x0004
    "TMC5130_SW_STOPR_POLARITY  0x0008
    "TMC5130_SW_SWAP_LR         0x0010
    "TMC5130_SW_LATCH_L_ACT     0x0020
    "TMC5130_SW_LATCH_L_INACT   0x0040
    "TMC5130_SW_LATCH_R_ACT     0x0080
    "TMC5130_SW_LATCH_R_INACT   0x0100
    "TMC5130_SW_LATCH_ENC       0x0200
    "TMC5130_SW_SG_STOP         0x0400
    "TMC5130_SW_SOFTSTOP        0x0800

	//Encoderbits (Register TMC5130_ENCMODE)
    "TMC5130_EM_DECIMAL     0x0400
    "TMC5130_EM_LATCH_XACT  0x0200
    "TMC5130_EM_CLR_XENC    0x0100
    "TMC5130_EM_NEG_EDGE    0x0080
    "TMC5130_EM_POS_EDGE    0x0040
    "TMC5130_EM_CLR_ONCE    0x0020
    "TMC5130_EM_CLR_CONT    0x0010
    "TMC5130_EM_IGNORE_AB   0x0008
    "TMC5130_EM_POL_N       0x0004
    "TMC5130_EM_POL_B       0x0002
    "TMC5130_EM_POL_A       0x0001
"""
