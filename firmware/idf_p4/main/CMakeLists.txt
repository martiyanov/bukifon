# SPDX-License-Identifier: GPL-3.0-or-later
idf_component_register(
    SRCS "app_main.cpp" "nvs_storage_backend.cpp"
    INCLUDE_DIRS "."
    REQUIRES esp_driver_i2c esp_driver_i2s esp_driver_ledc esp_driver_gpio
             esp_driver_uart esp_lcd esp_psram esp_timer esp_system
             nvs_flash
)
