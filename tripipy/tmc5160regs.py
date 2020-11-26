#!/usr/bin/python3
"""
This defines the registers accessible via SPI for a tmc5160

This is based on the TMC5160A DATASHEET (Rev. 1.13 / 2019-NOV-19)
"""

from enum import Enum, IntFlag
from tripipy.trinamicDriver import triHex, triByteFlags, triSignedint, triPosint, triMixed, triSubInt, triEnum

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
    right_stop  =128

class GSTATflags(IntFlag):
    """
    Flags in the GSTAT register
    """
    NONE        = 0
    reset       = 1
    drv_err     = 2
    uv_cp       = 4

class rampFlags(IntFlag):
    """
    the flag bits in the ramp status register 
    """
    NONE                = 0
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
    recalibrate         = 1
    fast_stand_still    = 2
    en_pwm_mode         = 4
    multistep_filt      = 8
    shaft               = 2**4      # reverses motor rotation
    diag0_error         = 2**5      # only with SD_MODE=1
    diag0_otpw          = 2**6
    diag0_stall         = 2**7      # with SD_MODE=1
    diag0_step          = 2**7      # with SD_MODE=0
    diag1_stall         = 2**8      # with SD_MODE=1
    diag1_dir           = 2**8      # with SD_MODE=0
    diag1_index         = 2**9      # only with SD_MODE=1
    diag1_onstate       = 2**10     # only with SD_MODE=1
    diag1_steps_skipped = 2**11     # only with SD_MODE=1
    diag0_int_pushpull  = 2**12
    diag1_poscomp_pushpull=2**13
    small_hysteresis    = 2**14
    stop_enable         = 2**15
    direct_mode         = 2**16
    test_mode           = 2**17

class IOINflags(IntFlag):
    NONE                = 0
    REFL_STEP           = 1
    REFR_DIR            = 2
    ENCB_DCEN_CFG4      = 4
    ENCA_DCIN_CFG5      = 8
    DRV_ENN             = 16
    ENC_N_DCO_CFG6      = 32
    SD_MODE             = 64
    SWCOMP_IN           = 128

class RAMPmode(Enum):
    POSITION        = 0
    VELOCITY_FWD    = 1
    VELOCITY_REV    = 2
    VOLICITY_HOLD   = 3

class SWMODEflags(IntFlag):
    NONE            = 0
    stop_l_enable   = 2**0
    stop_r_enable   = 2**1
    pol_stop_l      = 2**2
    pol_stop_r      = 2**3
    swap_lr         = 2**4
    latch_l_active  = 2**5
    latch_l_inactive= 2**6
    latch_r_active  = 2**7
    latch_r_inactive= 2**8
    en_latch_encoder= 2**9
    sg_stop         = 2**10
    en_softstop     = 2**11

class DRVSTATflags(IntFlag):
    fsactive            = 2**15
    stallGuard          = 2**24
    ot                  = 2**25
    otpw                = 2**26
    s2ga                = 2**27
    s2gb                = 2**28
    ola                 = 2**29
    olb                 = 2**30
    stst                = 2**31

_regset={
    "SHORTSTAT":  {rclass: triByteFlags,  rargs: {'flagClass': statusFlags}},
    "GCONF":      {rclass: triMixed,      rargs: {addr: 0x00, access: "RW", 'flagClass': GCONFflags}}, 
    "GSTAT":      {rclass: triMixed,      rargs: {addr: 0x01, access: "R",  'flagClass': GSTATflags}},
    "IFCNT":      {rclass: triPosint,     rargs: {addr: 0x02, access: "R",  'sigbits': 8}}, # not used in SPI mode
    "SLAVECONF":  {rclass: triHex,        rargs: {addr: 0x03, access: ""}},  # not used in SPI mode
    "IOIN":       {rclass: triMixed,      rargs: {addr: 0x04, access: "R", 'flagClass': IOINflags, 'childdefs':(
            {'_cclass': triSubInt, 'name': 'VERSION', 'lowbit':24, 'bitcount': 8},
            )}},
    "X_COMPARE":  {rclass: triSignedint,  rargs: {addr: 0x05, access: "RW", sigbits: 32}},
    "OTP_PROG": {rclass: triHex, rargs: {addr: 0x06, access: "W"}},
    "OTP_READ": {rclass: triHex, rargs: {addr: 0x07, access: "R"}},
    "FACTORY_CONF": {rclass: triPosint, rargs: {addr: 0x08, access: "RW", sigbits: 5}},
    "SHORT_CONF":   {rclass: triMixed,  rargs: {addr: 0x09, access: "W", 'childdefs': (
            {'_cclass': triSubInt, 'name': 'S2VS_LEVEL',  'lowbit':  0, 'bitcount': 4},
            {'_cclass': triSubInt, 'name': 'S2G_LEVEL',   'lowbit':  8, 'bitcount': 4},
            {'_cclass': triSubInt, 'name': 'SHORTFILTER', 'lowbit': 16, 'bitcount': 2},
            {'_cclass': triSubInt, 'name': 'SHORT_DELAY', 'lowbit': 18, 'bitcount': 1},
            )}},
    "DRV_CONF":     {rclass: triMixed,  rargs: {addr: 0x0A, access: "W", 'childdefs': (
            {'_cclass': triSubInt, 'name': 'BBMTIME',  'lowbit':  0, 'bitcount': 5},
            {'_cclass': triSubInt, 'name': 'BBMCLKS',   'lowbit':  8, 'bitcount': 4},
            {'_cclass': triSubInt, 'name': 'OTSELECT', 'lowbit': 16, 'bitcount': 2},
            {'_cclass': triSubInt, 'name': 'DRVSTRENGTH', 'lowbit': 18, 'bitcount': 2},
            {'_cclass': triSubInt, 'name': 'FILT_ISENSE', 'lowbit': 20, 'bitcount': 2},
            )}},
    "GLOBALSCALER": {rclass: triPosint, rargs: {addr: 0x0B, access: "W", sigbits: 8}},
    "OFFSET_READ": {rclass: triHex, rargs: {addr: 0x0C, access: "R"}},

    "IHOLD_IRUN": {rclass: triMixed,      rargs: {addr: 0x10, access: "W", 'childdefs':(
            {'_cclass': triSubInt, 'name': 'IHOLD',      'lowbit': 0, 'bitcount': 5},
            {'_cclass': triSubInt, 'name': 'IRUN',       'lowbit': 8, 'bitcount': 5},
            {'_cclass': triSubInt, 'name': 'IHOLDDELAY', 'lowbit':16, 'bitcount': 4},
            )}},
    "TPOWERDOWN": {rclass: triPosint,     rargs: {addr: 0x11, access: "W",  sigbits: 8}},
    "TSTEP":      {rclass: triPosint,     rargs: {addr: 0x12, access: "R",  sigbits: 20}},
    "TPWMTHRS":   {rclass: triPosint,     rargs: {addr: 0x13, access: "W",  sigbits: 20}},
    "TCOOLTHRS":  {rclass: triPosint,     rargs: {addr: 0x14, access: "W",  sigbits: 20}},
    "THIGH":      {rclass: triPosint,     rargs: {addr: 0x15, access: "W",  sigbits: 20}},

    "RAMPMODE":   {rclass: triEnum,       rargs: {addr: 0x20, access: "RW", 'enumClass': RAMPmode}},
    "XACTUAL":    {rclass: triSignedint,  rargs: {addr: 0x21, access: "RW", sigbits: 32}},
    "VACTUAL":    {rclass: triSignedint,  rargs: {addr: 0x22, access: "R", sigbits: 24}},
    "VSTART":     {rclass: triPosint,     rargs: {addr: 0x23, access: "W",  sigbits: 18}},
    "A1":         {rclass: triPosint,     rargs: {addr: 0x24, access: "W",  sigbits: 16}},
    "V1":         {rclass: triPosint,     rargs: {addr: 0x25, access: "W",  sigbits: 20}},
    "AMAX":       {rclass: triPosint,     rargs: {addr: 0x26, access: "W",  sigbits: 16}},
    "VMAX":       {rclass: triPosint,     rargs: {addr: 0x27, access: "W",  sigbits: 23, maxval: 2**23-512}},
    "DMAX":       {rclass: triPosint,     rargs: {addr: 0x28, access: "W",  sigbits: 16}},
    "D1":         {rclass: triPosint,     rargs: {addr: 0x2A, access: "W",  sigbits: 16}},
    "VSTOP":      {rclass: triPosint,     rargs: {addr: 0x2B, access: "W",  sigbits: 18}},
    "TZEROWAIT":  {rclass: triPosint,     rargs: {addr: 0x2C, access: "W",  sigbits: 16}},
    "XTARGET":    {rclass: triSignedint,  rargs: {addr: 0x2D, access: "RW", sigbits: 32}},

    "VDCMIN":     {rclass: triPosint,     rargs: {addr: 0x33, access: "W",  sigbits:23}},
    "SWMODE":     {rclass: triMixed,      rargs: {addr: 0x34, access: "RW", 'flagClass': SWMODEflags}},
    'RAMPSTAT':   {rclass: triMixed,      rargs: {addr: 0x35, access: "R",  'flagClass': rampFlags}},
    "XLATCH":     {rclass: triSignedint,  rargs: {addr: 0x36, access: "R",  sigbits: 32}},

    "ENCMODE":    {rclass: triHex,        rargs: {addr: 0x38, access: "RW"}},
    "XENC":       {rclass: triHex,        rargs: {addr: 0x39, access: "RW"}},
    "ENC_CONST":  {rclass: triHex,        rargs: {addr: 0x3A, access: "W"}},
    "ENC_STATUS": {rclass: triHex,        rargs: {addr: 0x3B, access: "R"}},
    "ENC_LATCH":  {rclass: triHex,        rargs: {addr: 0x3C, access: "R"}},
    "ENC_DEVIATION":  {rclass: triHex,    rargs: {addr: 0x3D, access: "W"}},

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

    "CHOPCONF":   {rclass: triHex,        rargs: {addr: 0x6C, access: "RW"}},
    "COOLCONF":   {rclass: triHex,        rargs: {addr: 0x6D, access: "W"}},
    "DCCTRL":     {rclass: triHex,        rargs: {addr: 0x6E, access: "W"}},
    "DRVSTATUS":  {rclass: triMixed,      rargs: {addr: 0x6F, access: "R", 'flagClass': DRVSTATflags, 'childdefs':(
            {'_cclass': triSubInt, 'name': 'SG_RESULT', 'lowbit':0, 'bitcount': 10},
            {'_cclass': triSubInt, 'name': 'CS_ACTUAL', 'lowbit':16, 'bitcount':5},
            )}},
    "PWMCONF":    {rclass: triHex,        rargs: {addr: 0x70, access: "W"}},
    "PWMSCALE":   {rclass: triHex,        rargs: {addr: 0x71, access: "R"}},
    "PWM_AUTO": {rclass: triHex, rargs: {addr: 0x72, access: "R", 'childdefs': (
        {'_cclass': triSubInt, 'name': 'PWM_OFS_AUTO', 'lowbit': 0, 'bitcount': 8},
        {'_cclass': triSubInt, 'name': 'PWM_GRAD_AUTO', 'lowbit': 16, 'bitcount': 8},
    )}},
    "LOST_STEPS": {rclass: triHex,        rargs: {addr: 0x73, access: "R"}},
}

tmc5160={
    'regNames'     : _regset,
}
"""
	//Encoderbits (Register TMC5160_ENCMODE)
    "TMC5160_EM_DECIMAL     0x0400
    "TMC5160_EM_LATCH_XACT  0x0200
    "TMC5160_EM_CLR_XENC    0x0100
    "TMC5160_EM_NEG_EDGE    0x0080
    "TMC5160_EM_POS_EDGE    0x0040
    "TMC5160_EM_CLR_ONCE    0x0020
    "TMC5160_EM_CLR_CONT    0x0010
    "TMC5160_EM_IGNORE_AB   0x0008
    "TMC5160_EM_POL_N       0x0004
    "TMC5160_EM_POL_B       0x0002
    "TMC5160_EM_POL_A       0x0001
"""
