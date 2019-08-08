#!/usr/bin/python3
"""
This defines the registers accessible via SPI for a tmc5130

This is based on the TMC5130A DATASHEET (Rev. 1.15 / 2018-JUL-11)
"""

from enum import IntFlag

addr="addr"
mode="mode"
readconv="readconv"
rclass='rclass'
rargs='rargs'
sigbits='sigbits'
maxval='maxval'
access='access'

class statusFlags(IntFlag):
    """
    The flags returned in the status byte on each spi transfer
    """
    NONE        =  0
    reset       =  1
    driver_error=  2
    stallguard  =  4
    stationary  =  8
    at_VMAX     = 16
    at_position = 32
    left_stop   = 64
    rightstop   =128

class rampFlags(IntFlag):
    """
    the flag bits in the ramp status register 
    """
    limit_left          = 1
    limit_right         = 2
    latch_left          = 4
    latch_right         = 8
    stop_left           = 0x0010
    stop_right          = 0x0020
    stalled             = 0x0040
    pos_reached_event   = 0x0080
    vmax_reached        = 0x0100
    pos_reached         = 0x0200
    speed_zero          = 0x0400
    zero_transit_wait   = 0x0800
    reversed_dir        = 0x1000
    stall_guard_active  = 0x2000

class GCONFflags(IntFlag):
    """
    The flag bits in register GCONF
    """
    NONE                = 0
    I_scale_analog      = 1
    internal_Rsense     = 2
    en_pwm_mode         = 4
    enc_commutation     = 8
    shaft               = 2**4      # reverses motor rotation
    diag0_error         = 2**5
    diag0_otpw          = 2**6
    diag0_stall         = 2**7
    diag1_stall         = 2**8
    diag1_index         = 2**9
    diag1_onstate       = 2**10
    diag1_steps_skipped = 2**11
    diag0_int_pushpull  = 2**12
    diag1_poscomp_pushpull=2**13
    small_hysteresis    = 2**14
    stop_enable         = 2**15
    direct_mode         = 2**16
    test_mode           = 2**17

_regset={
    "SHORTSTAT":  {rclass: 'triByteFlags',  rargs: {'flagClass': statusFlags}},
#    "GCONF":      {rclass: 'triHex',        rargs: {addr: 0x00, access: "RW", 'logacts': ('constructors', 'resolve', 'content')}},
    "GCONF":      {rclass: 'triFlags',      rargs: {addr: 0x00, access: "RW", 'flagClass': rampFlags}}, 
    "GSTAT":      {rclass: 'triHex',        rargs: {addr: 0x01, access: "R",  'logacts': ('constructors', 'resolve', 'content')}},
    "IFCNT":      {rclass: 'triHex',        rargs: {addr: 0x02, access: "",   'logacts': ('constructors', 'resolve', 'content')}},
    "SLAVECONF":  {rclass: 'triHex',        rargs: {addr: 0x03, access: "",   'logacts': ('constructors', 'resolve', 'content')}},
    "INP_OUT":    {rclass: 'triHex',        rargs: {addr: 0x04, access: "R",  'logacts': ('constructors', 'resolve', 'content')}},
    "X_COMPARE":  {rclass: 'triHex',        rargs: {addr: 0x05, access: "W",  'logacts': ('constructors', 'resolve', 'content')}},

    "IHOLD_IRUN": {rclass: 'triHex',        rargs: {addr: 0x10, access: "W",  'logacts': ('constructors', 'resolve', 'content')}},
    "TPOWERDOWN": {rclass: 'triHex',        rargs: {addr: 0x11, access: "W",  'logacts': ('constructors', 'resolve', 'content')}},
    "TSTEP":      {rclass: 'triHex',        rargs: {addr: 0x12, access: "R",  'logacts': ('constructors', 'resolve', 'content')}},
    "TPWMTHRS":   {rclass: 'triHex',        rargs: {addr: 0x13, access: "W",  'logacts': ('constructors', 'resolve', 'content')}},
    "TCOOLTHRS":  {rclass: 'triHex',        rargs: {addr: 0x14, access: "W",  'logacts': ('constructors', 'resolve', 'content')}},
    "THIGH":      {rclass: 'triHex',        rargs: {addr: 0x15, access: "W",  'logacts': ('constructors', 'resolve', 'content')}},

    "RAMPMODE":   {rclass: 'triHex',        rargs: {addr: 0x20, access: "RW", 'logacts': ('constructors', 'resolve', 'content')}},
    "XACTUAL":    {rclass: 'triSignedint',  rargs: {addr: 0x21, access: "RW"  ,sigbits: 32, 'logacts': ('constructors', 'resolve', 'content')}},
    "VACTUAL":    {rclass: 'triSignedint',  rargs: {addr: 0x22, access: "RW",  sigbits: 24, 'logacts': ('constructors', 'resolve', 'content')}},
    "VSTART":     {rclass: 'triPosint',     rargs: {addr: 0x23, access: "W",   sigbits: 18, 'logacts': ('constructors', 'resolve', 'content')}},
    "A1":         {rclass: 'triPosint',     rargs: {addr: 0x24, access: "W",   sigbits: 16, 'logacts': ('constructors', 'resolve', 'content')}},
    "V1":         {rclass: 'triPosint',     rargs: {addr: 0x25, access: "W", sigbits: 20, 'logacts': ('constructors', 'resolve', 'content')}},
    "AMAX":       {rclass: 'triPosint',     rargs: {addr: 0x26, access: "W", sigbits: 16, 'logacts': ('constructors', 'resolve', 'content')}},
    "VMAX":       {rclass: 'triPosint',     rargs: {addr: 0x27, access: "W", sigbits: 23, maxval: 2**23-512, 'logacts': ('constructors', 'resolve', 'content')}},
    "DMAX":       {rclass: 'triPosint',     rargs: {addr: 0x28, access: "W", sigbits: 16, 'logacts': ('constructors', 'resolve', 'content')}},
    "D1":         {rclass: 'triPosint',     rargs: {addr: 0x2A, access: "W", sigbits: 16, 'logacts': ('constructors', 'resolve', 'content')}},
    "VSTOP":      {rclass: 'triPosint',     rargs: {addr: 0x2B, access: "W", sigbits: 18, 'logacts': ('constructors', 'resolve', 'content')}},
    "TZEROWAIT":  {rclass: 'triPosint',     rargs: {addr: 0x2C, access: "W", sigbits: 16, 'logacts': ('constructors', 'resolve', 'content')}},
    "XTARGET":    {rclass: 'triSignedint',  rargs: {addr: 0x2D, access: "RW", sigbits: 32, 'logacts': ('constructors', 'resolve', 'content')}},

    "VDCMIN":     {rclass: 'triHex',        rargs: {addr: 0x33, access: "W",  'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x33, mode:"W"},
    "SWMODE":     {rclass: 'triHex',        rargs: {addr: 0x34, access: "RW", 'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x34, mode:"RW"},
#    "RAMPSTAT":   {addr: 0x35, mode:"RC"},
    'RAMPSTAT':   {rclass: 'triFlags',      rargs: {addr: 0x35, access: "R",  'flagClass': rampFlags}},
    "XLATCH":     {rclass: 'triHex',        rargs: {addr: 0x36, access: "R",  'logacts': ('constructors', 'resolve', 'content')}},# {addr: 0x36, mode:"R"},

    "ENCMODE":    {rclass: 'triHex',        rargs: {addr: 0x38, access: "RW", 'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x38, mode:"RW"},
    "XENC":       {rclass: 'triHex',        rargs: {addr: 0x39, access: "RW", 'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x39, mode:"RW"},
    "ENC_CONST":  {rclass: 'triHex',        rargs: {addr: 0x3A, access: "W",  'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x3A, mode:"W"},
    "ENC_STATUS": {rclass: 'triHex',        rargs: {addr: 0x3B, access: "R",  'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x3B, mode:"RC"},
    "ENC_LATCH":  {rclass: 'triHex',        rargs: {addr: 0x3C, access: "R",  'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x3C, mode:"R"},

#    "MSLUT0":     {addr: 0x60, mode:"W"},
#    "MSLUT1":     {addr: 0x61, mode:"W"},
#    "MSLUT2":     {addr: 0x62, mode:"W"},
#    "MSLUT3":     {addr: 0x63, mode:"W"},
#    "MSLUT4":     {addr: 0x64, mode:"W"},
#    "MSLUT5":     {addr: 0x65, mode:"W"},
#    "MSLUT6":     {addr: 0x66, mode:"W"},
#    "MSLUT7":     {addr: 0x67, mode:"W"},
#    "MSLUTSEL":   {addr: 0x68, mode:"W"},
#    "MSLUTSTART": {addr: 0x69, mode:"W"},
#    "MSCNT":      {addr: 0x6A, mode:"R"},
#    "MSCURACT":   {addr: 0x6B, mode:"R"},

    "CHOPCONF":   {rclass: 'triHex',        rargs: {addr: 0x6C, access: "RW", 'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x6C, mode:"RW"},
    "COOLCONF":   {rclass: 'triHex',        rargs: {addr: 0x6D, access: "W",  'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x6D, mode:"W"},
    "DCCTRL":     {rclass: 'triHex',        rargs: {addr: 0x6E, access: "W",  'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x6E, mode:"W"},
    "DRVSTATUS":  {rclass: 'triHex',        rargs: {addr: 0x6F, access: "R",  'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x6F, mode:"R"},
    "PWMCONF":    {rclass: 'triHex',        rargs: {addr: 0x70, access: "W",  'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x70, mode:"W"},
    "PWMSCALE":   {rclass: 'triHex',        rargs: {addr: 0x71, access: "R",  'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x71, mode:"R"},
    "ENCM_CTRL":  {rclass: 'triHex',        rargs: {addr: 0x72, access: "W",  'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x72, mode:"W"},
    "LOST_STEPS": {rclass: 'triHex',        rargs: {addr: 0x73, access: "R",  'logacts': ('constructors', 'resolve', 'content')}},#{addr: 0x73, mode:"R"},
}

tmc5130={
    'regNames'     : _regset,
#    'statusClass'  : statusFlags,
}
"""	stuff that might be useful later
    // ramp modes (Register TMC5130_RAMPMODE)
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
