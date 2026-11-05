// SPDX-License-Identifier: GPL-3.0-or-later
// 24C32 EEPROM persistence: CV calibration, DECK_ID calibration, module table,
// hours counter. The hardware I2C transport is abstracted behind IEeprom.
#pragma once

#include <cstddef>
#include <cstdint>

#include "core/config.hpp"
#include "io/cv.hpp"

namespace bukifon {

class IEeprom {
 public:
  virtual ~IEeprom() = default;
  virtual bool read(uint16_t address, uint8_t* data, size_t length) = 0;
  virtual bool write(uint16_t address, const uint8_t* data, size_t length) = 0;
};

// Logical EEPROM image (also usable as a host-test fake).
class EepromStore {
 public:
  static constexpr size_t kModuleDescriptorBytes = 32;
  static constexpr size_t kImageBytes = 256;

  void init(IEeprom* eeprom) { eeprom_ = eeprom; }
  bool load();   // read+verify (falls back to defaults on failure)
  bool save();   // serialise+write (with CRC)

  CvCalibration& cvCalibration() { return cv_; }
  const CvCalibration& cvCalibration() const { return cv_; }

  void setDeckCalibration(float padVolts, float keysVolts);
  float deckPadVolts() const { return deckPadVolts_; }
  float deckKeysVolts() const { return deckKeysVolts_; }

  void setModuleDescriptor(int port, const uint8_t* descriptor32);
  const uint8_t* moduleDescriptor(int port) const;

  uint32_t hours() const { return hours_; }
  void addHours(uint32_t hours) { hours_ += hours; }
  bool ok() const { return ok_; }

  size_t serialize(uint8_t* out, size_t capacity) const;
  bool deserialize(const uint8_t* data, size_t length);

 private:
  IEeprom* eeprom_ = nullptr;
  bool ok_ = false;
  CvCalibration cv_;
  float deckPadVolts_ = 0.3f;
  float deckKeysVolts_ = 3.0f;
  uint8_t modules_[kNumBusPorts][kModuleDescriptorBytes] = {};
  uint32_t hours_ = 0;
};

}  // namespace bukifon
