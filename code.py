import os
import sys
import time
#import alarm
import board
import busio
import digitalio
import displayio
import microcontroller
import neopixel
import adafruit_dotstar as dotstar
import socketpool
import ssl
import wifi
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError, AdafruitIO_ThrottleError
import terminalio
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import adafruit_scd4x


#TODO: Add CO2 reading from SCD4x, display on screen, along with time (from adafruit IO)

## I2C: Blue 7, Orange 6
## DOTSTARS: Yellow 5, white 4

MAX_BRIGHTNESS = os.getenv("LIGHT_BRIGHTNESS", 0.4)
DOTSTAR_CLOCK_PIN = board.IO5
DOTSTAR_DATA_PIN = board.IO4
DOTSTAR_PIXEL_COUNT = 24
SCL = board.IO6  #i2c
SDA = board.IO7


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


dots = dotstar.DotStar(DOTSTAR_CLOCK_PIN, DOTSTAR_DATA_PIN, DOTSTAR_PIXEL_COUNT, brightness=0)
dots.fill((255, 255, 255))
display=None
io_client = None
scd4x = None
try:
    i2c = busio.I2C(SCL,SDA) #board.I2C()  # uses board.SCL and board.SDA
    # i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
except Exception as e:
    print(f"Failed to set up I2C: {e}")
    print(sys.print_exception(e))
    print("Resetting in 6seconds")
    time.sleep(6)
    microcontroller.reset()

def setup_io():
    """Set up the IO"""
    global io_client

    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
    io_client = IO_HTTP(os.getenv("CIRCUITPY_AIO_USERNAME"), os.getenv("CIRCUITPY_AIO_KEY"), requests)

def get_io_feed(feed_key):
    """Get the IO feed"""
    global io_client
    feed = None
    try:
        feed = io_client.get_feed(feed_key)
    except AdafruitIO_RequestError:
        try:
            if feed_key.find(".") > 0:
                # create group or get existing group then create feed in group
                group_key = feed_key.split(".")[0]
                group = None
                try:
                    group = io_client.get_group(group_key)
                except AdafruitIO_RequestError:
                    # create group
                    group = io_client.create_new_group(group_key, "SLO Plants")
                except AdafruitIO_ThrottleError:
                    print("Throttle error creating group, sleeping for 30 seconds")
                    time.sleep(30)
                    return get_io_feed(feed_key)
                feed = io_client.create_feed_in_group(group_key, feed_key.split(".")[1])
                # feed = io_client.create_new_feed(feed_key)
            else:
                feed = io_client.create_and_get_feed(feed_key)
        except AdafruitIO_RequestError as e:
            print(f"Failed to create feed {feed_key}: {e}")
    return feed


def publish_new_feed_value(feed_key, value):
    """Publish a new feed value

    Args:
        feed_key (string): The feed key
        value (string): The value to publish
    """
    global io_client, FEED_KEY
    try:
        feed = get_io_feed(feed_key)
        if feed:
            print(f"Publishing new value ({value}) to feed {feed_key}")
            io_client.send_data(feed_key, value)
    except Exception as e:
        print(f"Failed to publish new value ({value}) to feed {feed_key}: {e}")
        print(sys.print_exception(e))

scd4x_last_update = 0
def update_feed_values():
    """Update the feed values"""
    global io_client, scd4x, scd4x_last_update
    if scd4x is None:
        print("SCD4x not set up, attempting reset and skipping update")
        setup_scd4x()
        return
    try:
        if scd4x_last_update==0 or time.monotonic_ns() - scd4x_last_update > 5*1000*1000:
            scd4x_last_update = time.monotonic_ns()
        else:
            print("Skipping update, less than 5 seconds since last sensor update")
            return
        mac = "".join(str(hex(x)) for x in wifi.radio.mac_address)
        board_id = board.board_id.lower()  # now clean up the board_id to just a-z0-9 and - for _ etc
        board_id = "".join([c if c.isalpha() or c.isdigit() else "-" for c in board_id])
        group_key = f"sloplants-{mac}-{board_id}"
        co2 = scd4x.CO2
        print(f"CO2: {co2}")
        if co2 is not None:
            publish_new_feed_value(f"{group_key}.co2", co2)
        temp_c = scd4x.temperature
        print(f"Temperature: {temp_c}c")
        if temp_c is not None:
            publish_new_feed_value(f"{group_key}.temperature", temp_c)
        humidity = scd4x.relative_humidity
        print(f"Humidity: {humidity}%")
        if humidity is not None:
            publish_new_feed_value(f"{group_key}.humidity", humidity)
    except Exception as e:
        print(f"Failed to update feed values: {e}")
        print(sys.print_exception(e))


def setup_scd4x():
    """Set up the SCD4x"""
    global scd4x
    try:
        scd4x = adafruit_scd4x.SCD4X(i2c)
        scd4x.reinit()
        scd4x.start_periodic_measurement()
    except Exception as e:
        print(f"Failed to set up SCD4x: {e}")
        print(sys.print_exception(e))


def setup_display():
    """Set up the display"""
    global display, i2c
    displayio.release_displays()
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

def fadeLights():
    """Fade the lights"""
    global dots, MAX_BRIGHTNESS
    if dots.brightness < MAX_BRIGHTNESS:
        dots.brightness = dots.brightness + 0.01
        print(f"brightness: {dots.brightness}")
    else:
        print("Brightness max")

setup_display()
setup_scd4x()
setup_io()
while True:
    time.sleep(1)
    fadeLights()
    update_feed_values()
