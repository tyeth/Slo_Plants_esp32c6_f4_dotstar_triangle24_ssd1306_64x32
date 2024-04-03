#import alarm
import board
import digitalio
import neopixel
import time

print("START")
# On MagTag, enable power to NeoPixels.
# Remove these two lines on boards without board.NEOPIXEL_POWER.
# np_power = digitalio.DigitalInOut(board.NEOPIXEL_POWER)
# np_power.switch_to_output(value=False)

np = neopixel.NeoPixel(board.NEOPIXEL, 1)

np[0] = (50, 50, 50)
time.sleep(1)
np[0] = (0, 0, 0)

# Create a an alarm that will trigger 20 seconds from now.
#time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 20)
# Exit the program, and then deep sleep until the alarm wakes us.
#alarm.exit_and_deep_sleep_until_alarms(time_alarm)
# Does not return, so we never get here.
#print("SHOULDN'T REACH THIS!")

# SPDX-FileCopyrightText: 2022 David Glaude (based on 2021 ladyada for Adafruit Industries)
# SPDX-License-Identifier: MIT

# """
# This test will initialize the display using displayio and draw a solid white
# background, a smaller black rectangle, and some white text.
# Customized version of displayio_ssd1306_simpletest.py for 64x32
# """

## I2C: Blue 7, Orange 6
## DOTSTARS: Yellow 5, white 4

# import board
import displayio
import terminalio
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import busio

displayio.release_displays()

import adafruit_dotstar as dotstar
dots = dotstar.DotStar(board.IO5, board.IO4, 24, brightness=0)
dots.fill((255, 255, 255))

i2c = busio.I2C(board.IO6,board.IO7) #board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=64, height=32)

# Make the display context
splash = displayio.Group()
display.root_group = splash

color_bitmap = displayio.Bitmap(64, 32, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xFFFFFF  # White

bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
splash.append(bg_sprite)

## Draw a smaller inner rectangle
inner_bitmap = displayio.Bitmap(62, 30, 1)
inner_palette = displayio.Palette(1)
inner_palette[0] = 0x000000  # Black

inner_sprite = displayio.TileGrid(inner_bitmap, pixel_shader=inner_palette, x=1, y=1)
splash.append(inner_sprite)

TEXT1 = "Good"
text_area = label.Label(terminalio.FONT, text=TEXT1, color=0xFFFFFF, x=2, y=6)
splash.append(text_area)

TEXT2 = "Enough"
text_area = label.Label(terminalio.FONT, text=TEXT2, color=0xFFFFFF, x=27, y=12)
splash.append(text_area)

TEXT3 = "Slo Plants"
text_area = label.Label(terminalio.FONT, text=TEXT3, color=0xFFFFFF, x=2, y=24)
splash.append(text_area)

while True:
    time.sleep(1)
    if dots.brightness <0.69:
        dots.brightness = dots.brightness + 0.01
        print(f"brightness: {dots.brightness}")
    else:
        print("Brightness max")
