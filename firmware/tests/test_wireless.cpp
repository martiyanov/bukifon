// SPDX-License-Identifier: GPL-3.0-or-later
#include <cstring>

#include "net/wireless.hpp"
#include "test_framework.hpp"

using namespace bukifon;
using namespace bukifon::net;

TEST(WirelessTransportSwitching) {
  WirelessManager wireless;
  wireless.init();
  CHECK(wireless.transport() == Transport::Off);
  CHECK(wireless.status() == Status::Disabled);
  CHECK(wireless.setTransport(Transport::Usb));
  CHECK(wireless.transport() == Transport::Usb);
  CHECK(wireless.status() == Status::Ready);
  CHECK(wireless.usbReady());
  CHECK(wireless.setTransport(Transport::BleMidi));
  CHECK(wireless.status() == Status::Stub);
  CHECK(!wireless.usbReady());
  CHECK(wireless.setTransport(Transport::Wifi));
  CHECK(wireless.status() == Status::Stub);
  CHECK(wireless.setTransport(Transport::Off));
  CHECK(wireless.status() == Status::Disabled);
  CHECK(!wireless.setTransport(static_cast<Transport>(99)));
  CHECK(wireless.lastError() == WirelessError::InvalidState);
  INFO("wireless: USB/BLE-MIDI/BLE-HID/Wi-Fi/Off transport switching (stubs)");
}

TEST(WirelessBleStubs) {
  WirelessManager wireless;
  wireless.init();
  CHECK(!wireless.startBleMidi());  // stub returns false, records NotImplemented
  CHECK(wireless.transport() == Transport::BleMidi);
  CHECK(wireless.status() == Status::Stub);
  CHECK(wireless.lastError() == WirelessError::NotImplemented);
  CHECK(!wireless.bleReady());
  CHECK(!wireless.startBleAdvertising());
  const uint8_t midi[3] = {0x90, 60, 100};
  CHECK(!wireless.sendBleMidi(midi, sizeof(midi)));
  CHECK(wireless.bleMidiBytesSent() == 0);
  CHECK(!wireless.startBleHid());
  CHECK(wireless.transport() == Transport::BleHid);
  CHECK(wireless.stopBle());
  CHECK(wireless.transport() == Transport::Off);
  // P4 topology: BLE via an ESP32-C6 coprocessor (SDIO/UART).
  WirelessManager p4;
  p4.init(WirelessManager::Config{"BUKIFON", "Bukifon-AP", "bukifon123", true});
  CHECK(p4.bleViaCoprocessor());
  INFO("BLE stubs: NimBLE MIDI/HID interfaces present, radio implementation TODO");
}

TEST(WirelessWifiAndOtaStubs) {
  WirelessManager wireless;
  wireless.init();
  CHECK(!wireless.startWifiAccessPoint());
  CHECK(wireless.transport() == Transport::Wifi);
  CHECK(wireless.status() == Status::Stub);
  CHECK(!wireless.wifiReady());
  const char* page = wireless.webPageHtml();
  CHECK(page != nullptr);
  CHECK(std::strstr(page, "Bukifon") != nullptr);
  CHECK(std::strstr(page, "OTA") != nullptr);
  CHECK(std::strstr(page, "/api/projects") != nullptr);
  CHECK(!wireless.otaBegin(1024 * 1024));
  CHECK(wireless.otaImageBytes() == 1024 * 1024);
  CHECK(!wireless.otaInProgress());
  const uint8_t chunk[4] = {1, 2, 3, 4};
  CHECK(!wireless.otaWrite(chunk, sizeof(chunk)));
  CHECK(!wireless.otaEnd());
  CHECK(wireless.stopWifi());
  INFO("Wi-Fi/OTA stubs: AP state machine + web page string (%zu B) + OTA API", std::strlen(page));
}

TEST(WirelessStatusNames) {
  CHECK(std::strcmp(WirelessManager().statusName(), "DISABLED") == 0);
  WirelessManager wireless;
  CHECK(std::strcmp(wireless.statusName(), "DISABLED") == 0);
  wireless.init();
  wireless.setTransport(Transport::Wifi);
  CHECK(std::strcmp(wireless.statusName(), "STUB") == 0);
  wireless.setTransport(Transport::Usb);
  CHECK(std::strcmp(wireless.statusName(), "READY") == 0);
  INFO("wireless status names: DISABLED/STUB/READY");
}
