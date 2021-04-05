# ESP8266 Now Playing

## Spotify album art on a 64x64 LED matrix

### Materials

* 64x64 LED matrix
* ESP8266
* 16x2 LCD display
* 5V 2A+ power supply. I got mine from [Amazon](https://www.amazon.com/gp/product/B01LZF6NK6/) (though the link is dead, and honestly, while it has the ability to output a lot, it was slightly suspicious for the price, smelled a little funny when I plugged it in initially, and came slightly warped, which was concerning. Might want to save yourself the worry and get an actual Meanwell. Also, this thing doesn't have a power _switch_, so I literally power it off by unplugging it. Saving on electricity bills, I guess...

### HW Setup

1. Connect your pins according to [PxMatrix](https://github.com/2dom/PxMatrix/).
2. You'll need to add a backpack to the LCD display so you can go from a large number of IO pins to 2 + VCC + GND. Connect those two to GPIO 1 and 3. (after flashing, if you need those pins, I guess. I'm using a development board so a lot of things is just plug and play)
3. Tie all grounds together to the power supply. Very important. I spent a lot of time trying to figure out why there was flickering and random pixels lit up so you don't have to.

### 3D prints

* Stuff in `pcbs` is a board that simplifies connecting the LCD, LED matrix, and ESP8266.
  * Stuff in `pcbs/gerbers` is what you can provide to your favorite PCB fab to get a PCB from them.
* Stuff in `3d-prints` are modifiable designs to print for mounting the matrix.

### SW Setup

#### Server

`server.py` will do the following:

* Get the user's currently playing track (track name + artist, album art, and remaining playtime) from the Spotify API
* Convert the image into a set of bytes that the ESP will display
* Expose this data at `/user/<user>/`, `/user/<user>/track`, `/user/<user>/art` for consumption

##### Notes

* `/user/<user>/art?mode={565,888}` defines which mode you'll receive images in. `/user/<user>/?mode=` has the same options.
* `/user/<user>/?mode=565&debug=true` will batch 2 bytes into a short/uint16_t and render that. These would be what you pass into the `display.drawPixelRGB565(x, y, color)` call. Use this to double check your bitshifts are what you expect them to be.

#### Client

`esp8266_nowplaying.ino` is the client. It'll make a request to `track` and write that to the write to LCD, then `art` and write those bytes to the LED matrix.

I've separated out the credentials to `secrets.c` and added it to `.gitignore`, so you'll need to define your own. The variables you need to define are in `secrets.h` (they're wifi credentials, etc.).

##### Notes

* Make sure your `IMAGE_MODE` in `secrets.h` matches up with the URL in `secrets.c`
