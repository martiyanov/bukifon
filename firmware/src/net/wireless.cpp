// SPDX-License-Identifier: GPL-3.0-or-later
#include "net/wireless.hpp"

#include <cstring>

namespace bukifon {
namespace net {
namespace {

constexpr const char* kStubWebPage =
    "<!doctype html><html><head><meta charset=\"utf-8\"><title>Bukifon</title></head>"
    "<body><h1>Bukifon v0.5</h1>"
    "<p>Wireless stub: project upload, sample transfer and OTA are TODO.</p>"
    "<ul><li>Projects: /api/projects (TODO)</li>"
    "<li>Samples: /api/samples (TODO)</li>"
    "<li>OTA: /api/ota (TODO)</li></ul></body></html>";

}  // namespace

void WirelessManager::init(const Config& config) {
  config_ = config;
  transport_ = Transport::Off;
  status_ = Status::Disabled;
  lastError_ = WirelessError::None;
  bleAdvertising_ = false;
  wifiStarted_ = false;
  bleMidiBytesSent_ = 0;
  otaImageBytes_ = 0;
  otaInProgress_ = false;
}

const char* WirelessManager::statusName() const {
  switch (status_) {
    case Status::Disabled: return "DISABLED";
    case Status::Stub: return "STUB";
    case Status::Starting: return "STARTING";
    case Status::Ready: return "READY";
    case Status::Error: return "ERROR";
    default: return "?";
  }
}

void WirelessManager::stopCurrent() {
  bleAdvertising_ = false;
  wifiStarted_ = false;
  otaInProgress_ = false;
}

bool WirelessManager::setTransport(Transport transport) {
  const int index = static_cast<int>(transport);
  if (index < 0 || index >= static_cast<int>(Transport::kNumTransports)) {
    lastError_ = WirelessError::InvalidState;
    return false;
  }
  stopCurrent();
  transport_ = transport;
  lastError_ = WirelessError::None;
  switch (transport) {
    case Transport::Off:
      status_ = Status::Disabled;
      break;
    case Transport::Usb:
      status_ = Status::Ready;  // USB descriptors are built on the device
      break;
    case Transport::BleMidi:
    case Transport::BleHid:
    case Transport::Wifi:
      status_ = Status::Stub;  // radio implementation is TODO
      break;
    default:
      status_ = Status::Disabled;
      break;
  }
  return true;
}

bool WirelessManager::startBleMidi() {
  transport_ = Transport::BleMidi;
  status_ = Status::Stub;
  lastError_ = WirelessError::NotImplemented;
  return false;  // TODO(net): NimBLE MIDI service (S3) / C6 bridge (P4)
}

bool WirelessManager::startBleHid() {
  transport_ = Transport::BleHid;
  status_ = Status::Stub;
  lastError_ = WirelessError::NotImplemented;
  return false;  // TODO(net): BLE HID over GATT (keyboard report map)
}

bool WirelessManager::startBleAdvertising() {
  if (transport_ != Transport::BleMidi && transport_ != Transport::BleHid) {
    lastError_ = WirelessError::InvalidState;
    return false;
  }
  bleAdvertising_ = false;
  lastError_ = WirelessError::NotImplemented;
  return false;  // TODO(net): advertising data with BLE-MIDI service UUID
}

bool WirelessManager::stopBle() {
  bleAdvertising_ = false;
  if (transport_ == Transport::BleMidi || transport_ == Transport::BleHid) {
    transport_ = Transport::Off;
    status_ = Status::Disabled;
  }
  return true;
}

bool WirelessManager::bleReady() const {
  return (transport_ == Transport::BleMidi || transport_ == Transport::BleHid) &&
         status_ == Status::Ready;
}

bool WirelessManager::sendBleMidi(const uint8_t* data, size_t length) {
  if (!data || length == 0) return false;
  if (transport_ != Transport::BleMidi || status_ != Status::Ready) {
    lastError_ = WirelessError::NotImplemented;
    return false;  // stub: count the traffic so tests can observe the API
  }
  bleMidiBytesSent_ += static_cast<uint32_t>(length);
  return true;
}

bool WirelessManager::startWifiAccessPoint() {
  transport_ = Transport::Wifi;
  status_ = Status::Stub;
  wifiStarted_ = false;
  lastError_ = WirelessError::NotImplemented;
  return false;  // TODO(net): ESP-IDF WiFi AP + esp_http_server + OTA partition
}

bool WirelessManager::stopWifi() {
  wifiStarted_ = false;
  if (transport_ == Transport::Wifi) {
    transport_ = Transport::Off;
    status_ = Status::Disabled;
  }
  return true;
}

bool WirelessManager::wifiReady() const {
  return transport_ == Transport::Wifi && wifiStarted_ && status_ == Status::Ready;
}

const char* WirelessManager::webPageHtml() const { return kStubWebPage; }

bool WirelessManager::otaBegin(uint32_t imageBytes) {
  otaImageBytes_ = imageBytes;
  otaInProgress_ = false;
  lastError_ = WirelessError::NotImplemented;
  return false;  // TODO(net): esp_ota_begin with the reported image size
}

bool WirelessManager::otaWrite(const uint8_t* data, size_t length) {
  if (!otaInProgress_ || !data || length == 0) {
    lastError_ = WirelessError::NotImplemented;
    return false;
  }
  return false;
}

bool WirelessManager::otaEnd() {
  otaInProgress_ = false;
  lastError_ = WirelessError::NotImplemented;
  return false;
}

}  // namespace net
}  // namespace bukifon
