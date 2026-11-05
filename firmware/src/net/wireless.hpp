// SPDX-License-Identifier: GPL-3.0-or-later
// Wireless transport skeleton: BLE-MIDI / BLE-HID (NimBLE on S3; on P4 via an
// ESP32-C6 coprocessor over SDIO/UART) and Wi-Fi AP + web page + OTA stubs.
//
// Nothing here talks to a radio in v0.5: the API, state machine and limits are
// in place so the host demo and tests can exercise mode switching, while the
// device implementation is explicitly marked TODO.
#pragma once

#include <cstddef>
#include <cstdint>

namespace bukifon {
namespace net {

enum class Transport : uint8_t {
  Off = 0,
  Usb,
  BleMidi,
  BleHid,
  Wifi,
  kNumTransports
};

enum class Status : uint8_t {
  Disabled = 0,
  Stub,       // interface exists, no radio implementation in v0.5
  Starting,
  Ready,
  Error
};

enum class WirelessError : uint8_t {
  None = 0,
  NotImplemented,
  NotInitialized,
  InvalidState,
  NoRadio
};

constexpr size_t kMaxBleMidiPacket = 64;

class WirelessManager {
 public:
  struct Config {
    const char* bleName;
    const char* wifiSsid;
    const char* wifiPassword;  // WPA2 minimum length
    bool preferCoprocessor;    // P4: BLE via ESP32-C6
    explicit Config(const char* ble = "BUKIFON", const char* ssid = "Bukifon-AP",
                    const char* password = "bukifon123", bool coprocessor = false)
        : bleName(ble),
          wifiSsid(ssid),
          wifiPassword(password),
          preferCoprocessor(coprocessor) {}
  };

  void init(const Config& config = Config{});
  bool setTransport(Transport transport);  // no reboot; stops the previous one
  Transport transport() const { return transport_; }
  Status status() const { return status_; }
  WirelessError lastError() const { return lastError_; }
  const char* statusName() const;

  // BLE (NimBLE or coprocessor) — stubs.
  bool startBleMidi();
  bool startBleHid();
  bool startBleAdvertising();
  bool stopBle();
  bool bleReady() const;
  bool bleViaCoprocessor() const { return config_.preferCoprocessor; }
  bool sendBleMidi(const uint8_t* data, size_t length);
  uint32_t bleMidiBytesSent() const { return bleMidiBytesSent_; }

  // Wi-Fi AP + web/OTA stubs.
  bool startWifiAccessPoint();
  bool stopWifi();
  bool wifiReady() const;
  const char* webPageHtml() const;
  bool otaBegin(uint32_t imageBytes);
  bool otaWrite(const uint8_t* data, size_t length);
  bool otaEnd();
  uint32_t otaImageBytes() const { return otaImageBytes_; }
  bool otaInProgress() const { return otaInProgress_; }

  // USB side (descriptor building lives in usb/usb_descriptors).
  bool usbReady() const { return transport_ == Transport::Usb && status_ == Status::Ready; }

 private:
  void stopCurrent();
  Config config_{};
  Transport transport_ = Transport::Off;
  Status status_ = Status::Disabled;
  WirelessError lastError_ = WirelessError::None;
  bool bleAdvertising_ = false;
  bool wifiStarted_ = false;
  uint32_t bleMidiBytesSent_ = 0;
  uint32_t otaImageBytes_ = 0;
  bool otaInProgress_ = false;
};

}  // namespace net
}  // namespace bukifon
