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

# ==========================
def si5351_set_freq(clknum,fout) :
    # Method by Jerry Gaffke KE7ER. All 32-bit integer math.
    # Error <2Hz, good enough for VCO, but maybe not for FT8 modulation.
    msa = vco_f // fout  # Integer part of vco/fout
    msb = vco_f % fout  # init value of the numerator of the fractional part of vco/fout 
    msc = fout          # init value of denominator
    while (msc & 0xffff0000) :  # Divide by 2 until denominator fits in 20 bits
        msb=msb>>1
        msc=msc>>1
#    print(msb,msc,1.0*msb/msc)

# Multisynth parameter calc, AN619 section 4.1.2
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

    i2cWriten(42+(clknum*8), regs)

def si5351_output_en(en_bits) :
# Use bits 0,1,2 to enable the corresponding clock outputs.
# en = 0b000  : all 3 outputs are disabled
# en = 0b001  : CLK0 enabled
# ...
# en = 0b111  : all 3 outputs enabled
    i2cWrite(3, 0xff & ~en_bits)

#---------------------- Main program ----------------------------------

device = 0x60             # Si5351a I2C slave address in 7-bit format
xtal_f = 25_001_850       # in Hz. Put the actual freq here, with correction included
msna_p1 = 32              # PLLA  around 25M*32=800MHz
rdiv = 0                  # output divider , 0 means no div, 1 - div/2,...

vco_f = xtal_f * msna_p1

#---------- init --------------
i2c = I2C(0, scl=Pin(9), sda=Pin(8), freq=400000) # This works with Raspberry Pi Pico boards

i2cWrite(149, 0)                   # SpreadSpectrum off
si5351_output_en(0b000)            # Disable all CLK output drivers
i2cWrite(183, 2<<6)                # Set 25mhz crystal load capacitance to 8pF
msxp1 = (msna_p1<<7) - 512         # and msna_p2=0, msna_p3=1, PLL feedback MS not fractional
regs = bytearray([0, 1, BB2(msxp1), BB1(msxp1), BB0(msxp1), 0, 0, 0])
i2cWriten(26, regs)                # Write to 8 PLLA msynth regs
i2cWrite(177, 0x20)                # Reset PLLA  (0x80 resets PLLB)

i2cWrite(16, 0x0c)    # 2mA drive, MS0 as the source for CLK0, PLLA as the src for MS0, frac mode, CLK0 powerup
si5351_output_en(0b001)     # enable CLK0 out

#fout = int(input("Enter F, Hz.> "))
while(True) :
    for fout in range (7_070_000,7_080_000,10) :
        si5351_set_freq(0,fout)
    #sleep(0.01)
