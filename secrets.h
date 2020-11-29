#pragma once
#include <Arduino.h>

#define DISPLAY_WIDTH 64
#define DISPLAY_HEIGHT 64
#define IMAGE_MODE 888

extern const char *ssid;
extern const char *password;
extern const char *track_url;
extern const char *art_url;
extern uint8_t buf[3 * DISPLAY_WIDTH * DISPLAY_HEIGHT];
