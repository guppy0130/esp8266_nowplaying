import gc
import os
import time
from io import BytesIO

import adafruit_imageload
import board
import busio
import displayio
import framebufferio
import rgbmatrix
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
from digitalio import DigitalInOut
from microcontroller import watchdog
from neopixel import NeoPixel
from watchdog import WatchDogMode

displayio.release_displays()

url = f"http://{os.getenv('SERVER_URL', 'esp8266-nowplaying.k3s.home')}/user/{os.getenv('SPOTIFY_USERNAME')}/art"

matrix = rgbmatrix.RGBMatrix(
    width=64,
    height=64,
    bit_depth=3,
    rgb_pins=[
        board.MTX_R1,
        board.MTX_G1,
        board.MTX_B1,
        board.MTX_R2,
        board.MTX_G2,
        board.MTX_B2,
    ],
    addr_pins=[
        board.MTX_ADDRA,
        board.MTX_ADDRB,
        board.MTX_ADDRC,
        board.MTX_ADDRD,
        board.MTX_ADDRE,
    ],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
    doublebuffer=False
)
display = framebufferio.FramebufferDisplay(matrix, rotation=270)
group = displayio.Group()
display.root_group = group

esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

status_pixel = NeoPixel(board.NEOPIXEL, 1)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(
    esp,
    {
        "ssid": os.getenv("CIRCUITPY_WIFI_SSID"),
        "password": os.getenv("CIRCUITPY_WIFI_PASSWORD"),
    },
    status_pixel=status_pixel,
)
wifi.debug = True
wifi.connect()
print(wifi.ip_address(), wifi.ssid, wifi.signal_strength())

if watchdog is not None:
    watchdog.timeout = 15  # miss up to three
    watchdog.mode = WatchDogMode.RESET

while True:
    gc.collect()

    try:
        resp = wifi.get(url=url)
        bytes_img = BytesIO(resp.content)
        image, palette = adafruit_imageload.load(bytes_img)

        # must pop + del here instead of before allocation because not doing so
        # will cause the display to flash empty images
        while len(group) > 0:
            i = group.pop(0)
            del i

        group.append(displayio.TileGrid(image, pixel_shader=palette))
        print("OK!")
        if watchdog is not None:
            watchdog.feed()
    except MemoryError:
        print(gc.mem_free(), gc.mem_alloc())
    except Exception as e:
        print(e)

    time.sleep(5)
