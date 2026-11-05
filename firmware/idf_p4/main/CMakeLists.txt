# SPDX-License-Identifier: GPL-3.0-or-later
idf_component_register(
    SRCS "app_main.cpp"
    INCLUDE_DIRS "."
    REQUIRES esp_driver_i2c esp_psram esp_timer
)
