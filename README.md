# si5351_micropython

I couldn't find a simple library that I could use to control Si5351A from MicroPython boards in my experiments. So I've decided to write it myself.
This code is not a plug and play library (yet), it is just an example code which shows how to do it.
It is based on Arduino code by Jerry Gaffke KE7ER, published here:
https://groups.io/g/BITX20/files/KE7ER/si5351bx_0_0.ino
The code uses 32-bit integer math only, no float number math. I2C writes to the output Multisynth control registers are burst mode, 8 bytes per frequency change. When running on Raspberry Pi Pico board, the frequency update rate is about 1000 per second when using 400k I2C rate, or about 500 per second when using 100k.
The PLL frequency is constant and is an integer multiple of the crystal frequency. This is suitable for HF.

TODO: 
 - quadrature output
 - complete VFO control program, with rotary encoder and 16x2 LCD display.
