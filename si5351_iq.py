from machine import Pin,I2C
from  time import sleep

# ----------------I2C functions------------------
def i2cWrite(reg_adr, reg_data) :
    cmd_data = bytearray([reg_adr,reg_data])
    i2c.writeto(device, cmd_data)

def i2cWriten(reg_adr, reg_data) :
    cmd_data = bytearray([reg_adr]) + reg_data  # reg_data is already bytearray
    i2c.writeto(device, cmd_data)

def i2cRead(reg_adr) :
    cmd_data = bytearray([reg_adr])
    i2c.writeto(device,cmd_data)
    data_in = i2c.readfrom(device, 1)
#    i2c.stop()
    return data_in[0]

# ***********functions to split 24-bit integer into 3 bytes**************
def BB0 (int3b) :
    return (int3b & 0x0000ff)
def BB1 (int3b) :
    return ((int3b & 0x00ff00)>>8)
def BB2 (int3b) :
    return ((int3b & 0xff0000)>>16)

# ***********==========================
# Use PLLA for CLK0 and CLK1 outputs
def si5351_set_freq_iq(fout) :
    # Calculate output divisor, so that PLL freq is below 900M
    # divisor can be even integer in  8..126 range (citation needed)
    vco_f = 900_000_000
    int_div = vco_f // fout
    even_div = int_div - (int_div % 2)
    if (even_div > 126) :
        even_div = 126  # whatever it is, but clean signal not guaranteed below 4.7MHz

    vco_f = fout * even_div

    if (debug) : print("vco_f = {:.2f}MHz even_div = {:d}".format(vco_f/1e6, even_div))
    
    # calculate feedback multisynth (fractional divider) parameters
    msa = vco_f // xtal_f  # Integer part of vco_f/xtal_f
    msb = vco_f % xtal_f  # init value of the numerator of the fractional part
    msc = xtal_f          # init value of denominator
    while (msc & 0xfff00000) :  # Divide by 2 until denominator fits in 20 bits
        msb=msb>>1
        msc=msc>>1
    if (debug) : print(msa,msb,msc,1.0*msb/msc)

# Multisynth parameter calc, AN619 section 3.2
    frac_x128 = (msb<<7)//msc
    msxp1 = ((msa<<7) + frac_x128 - 512) | (rdiv<<20)
    msxp2 = (msb<<7) - msc*frac_x128
    #msxp3 = msc
    msxp3p2top = (((msc & 0x0F0000) <<4) | (msxp2 & 0x0F0000))      # 2 top nibbles

    regs = bytearray([BB1(msc),
                      BB0(msc),
                      BB2(msxp1),
                      BB1(msxp1), 
                      BB0(msxp1),
                      BB2(msxp3p2top),
                      BB1(msxp2),
                      BB0(msxp2)])

    i2cWriten(26, regs) # PLLA base register address is 26
# Output dividers
    ms0p1 = (even_div<<7) - 512         # 
    regs = bytearray([0, 1, BB2(ms0p1), BB1(ms0p1), BB0(ms0p1), 0, 0, 0])
    i2cWriten(42, regs)                # Write to 8 MS0 regs
    i2cWriten(50, regs)                # Write to 8 MS1 regs
    i2cWrite(165,0) # CLK0 phase
    i2cWrite(166,even_div) # CLK1 phase
#TODO write only when even_divisor changes

def si5351_output_en(en_bits) :
# Use bits 0,1,2 to enable the corresponding clock outputs.
# en = 0b000  : all 3 outputs are disabled
# en = 0b001  : CLK0 enabled
# ...
# en = 0b111  : all 3 outputs enabled
    i2cWrite(3, 0xff & ~en_bits)

def si5351_clk_ctrl(clknum,ctl_byte) :
# 7 CLK0_PDN Clock 0 Power Down.
# This bit allows powering down the CLK0 output driver to conserve power when the output
# is unused.
# 0: CLK0 is powered up.
# 1: CLK0 is powered down.

# 6 MS0_INT MultiSynth 0 Integer Mode.
# This bit can be used to force MS0 into Integer mode to improve jitter performance. Note
# that the fractional mode is necessary when a delay offset is specified for CLK0.
# 0: MS0 operates in fractional division mode.
# 1: MS0 operates in integer mode.

# 5 MS0_SRC MultiSynth Source Select for CLK0.
# 0: Select PLLA as the source for MultiSynth0.
# 1: Select PLLB (Si5351A/C only) or VCXO (Si5351B only) for MultiSynth0.

# 4 CLK0_INV Output Clock 0 Invert.
# 0: Output Clock 0 is not inverted.
# 1: Output Clock 0 is inverted.

# 3:2 CLK0_SRC[1:0] Output Clock 0 Input Source.
# These bits determine the input source for CLK0.
# 00: Select the XTAL as the clock source for CLK0. This option by-passes both synthesis
# stages (PLL/VCXO & MultiSynth) and connects CLK0 directly to the oscillator which
# generates an output frequency determined by the XTAL frequency.
# 01: Select CLKIN as the clock source for CLK0. This by-passes both synthesis stages
# (PLL/VCXO & MultiSynth) and connects CLK0 directly to the CLKIN input. This essentially
# creates a buffered output of the CLKIN input.
# 10: Reserved. Do not select this option.
# 11: Select MultiSynth 0 as the source for CLK0. Select this option when using the
# Si5351 to generate free-running or synchronous clocks.

# 1:0 CLK0_IDRV[1:0] CLK0 Output Rise and Fall time / Drive Strength Control.
# 00: 2 mA
# 01: 4 mA
# 10: 6 mA
# 11: 8 mA

#examples :
# 0x80 : clock off
# 0x0c :  2mA drive, MSx as the source for CLKx, no inv, PLLA as the src for MSx, frac mode, CLK0 powerup
# 0x0f :  same, but 8mA drive
    i2cWrite(16+clknum, ctl_byte)

#---------------------- Main program ----------------------------------

device = 0x60             # Si5351a I2C slave address in 7-bit format
xtal_f = 25_002_230       # in Hz. Put the actual freq here, with correction included
rdiv = 0                  # output divider , 0 means no div, 1 - div/2,...
debug = 1


#---------- init --------------
i2c = I2C(0, scl=Pin(9), sda=Pin(8), freq=100000)

i2cWrite(149, 0)                   # SpreadSpectrum off
si5351_output_en(0b000)            # Disable all CLK output drivers
i2cWrite(183, 2<<6)                # Set 25mhz crystal load capacitance to 8pF

i2cWrite(177, 0x20)                # Reset PLLA  (0x80 resets PLLB)

si5351_clk_ctrl(0, 0x4d)    # 4mA drive, MS0 as the source for CLK0, PLLA as the src for MS0, integer mode, CLK0 powerup
si5351_clk_ctrl(1, 0x4d)    # same for CLK1, except MS1 as the source (same code for CLK_SRC)
si5351_clk_ctrl(2, 0x0f)    # CLK2 off

fout = int(input("Enter F, Hz.> "))

si5351_set_freq_iq(fout)
i2cWrite(177, 0x20)                # Reset PLLA  (0x80 resets PLLB)
si5351_output_en(0b011)     # enable CLK0 and CLK1 out
