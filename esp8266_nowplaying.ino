#include "secrets.h"
/* #define double_buffer */
#include <ESP8266HTTPClient.h>
#include <ESP8266WiFi.h>
#include <LiquidCrystal_I2C.h>
#include <PxMatrix.h>
#include <Ticker.h>
#include <WiFiClient.h>
#include <Wire.h>

// lcd display setup
LiquidCrystal_I2C lcd(0x27, 16, 2);

// 64x64 led matrix
Ticker display_ticker;
#define P_LAT 16
#define P_A 5
#define P_B 4
#define P_C 15
#define P_D 12
#define P_E 0
#define P_OE 2
PxMATRIX display(DISPLAY_WIDTH, DISPLAY_HEIGHT, P_LAT, P_OE, P_A, P_B, P_C, P_D,
                 P_E);

void display_updater() { display.display(30); }

void display_update_enable(bool is_enable) {
    if (is_enable) {
        display_ticker.attach(0.004, display_updater);
    } else {
        display_ticker.detach();
    }
}

void update_display_with_buf(int mode) {
    display.clearDisplay();
    int counter = 0;
    bool printed = false;
    for (int y = 0; y < DISPLAY_HEIGHT; y++) {
        for (int x = 0; x < DISPLAY_WIDTH; x++) {
            if (mode == 565) {
                uint16_t color = (buf[counter] << 8) + buf[counter + 1];
                display.drawPixelRGB565(x, y, color);
                counter += 2;
            } else {
                display.drawPixelRGB888(x, y, buf[counter], buf[counter + 1],
                                        buf[counter + 2]);
                counter += 3;
            }
        }
    }
    display.showBuffer();
    display_update_enable(true);
}

void setup() {
    // wifi setup
    WiFi.begin(ssid, password);

    // lcd setup
    Wire.begin(1, 3);  // lcd display on 1, 3 (rx, tx)
    lcd.init();
    lcd.backlight();
    lcd.setCursor(0, 0);
    lcd.print("Wifi connecting");

    // led setup
    display.begin(32);  // 64x64 display
    display.setBrightness(20);
    display.clearDisplay();
    display.setCursor(0, 2);
    display.setTextColor(display.color565(255, 255, 255));
    display.print("hello world");
    display.showBuffer();
    display_update_enable(true);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
    }

    // connected to Wifi
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Wifi connected");
    lcd.setCursor(0, 1);
    lcd.print(ssid);

    update_display_with_buf(IMAGE_MODE);
}

void loop() {
    WiFiClient client;
    HTTPClient http;
    bool playing = false;
    long remaining_time = 100;  // if not able to connect, this value

    // get the track title, artist, time remaining
    http.begin(client, track_url);
    int response = http.GET();

    if (response == HTTP_CODE_OK) {
        String payload = http.getString();
        Serial.println(payload);
        String track_name = payload.substring(0, payload.indexOf("\n"));
        playing = strcmp(track_name.c_str(), "nothing playing");  // 0 if match
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print(track_name);
        lcd.setCursor(0, 1);
        // + 1 offset because indexing
        String artist = payload.substring(
            payload.indexOf("\n") + 1,
            payload.indexOf(
                "\n", payload.indexOf(track_name) + track_name.length() + 1));
        lcd.print(artist);
        // songs can be very long, and this is in ms anyways, so not int
        long server_suggested_time =
            payload
                .substring(payload.indexOf(
                    "\n", payload.indexOf(artist) + artist.length()))
                .toInt();
        // we don't want to spam the server
        remaining_time = std::max(remaining_time, server_suggested_time);
    }

    // get image and render
    http.begin(client, art_url);
    response = http.GET();

    if (response == HTTP_CODE_OK) {
        display.clearDisplay();
        int len = http.getSize();

        memcpy(buf, http.getString().c_str(),
               3 * DISPLAY_WIDTH * DISPLAY_HEIGHT);

        if (playing) {
            update_display_with_buf(IMAGE_MODE);
        }
    } else {
        lcd.clear();
        lcd.setCursor(0, 0);
        // debug when you forget to expose your server
        lcd.print(http.errorToString(response));
        lcd.setCursor(0, 1);
        lcd.print(remaining_time);
    }

    // delay until time remaining is up, then check for another update
    delay(remaining_time);
}
