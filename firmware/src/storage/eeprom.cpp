// SPDX-License-Identifier: GPL-3.0-or-later
#include "storage/eeprom.hpp"

#include <cstring>

#include "core/patch.hpp"

namespace bukifon {
namespace {
constexpr uint8_t kMagic[4] = {'P', 'M', 'E', '1'};
}  // namespace

void EepromStore::setDeckCalibration(float padVolts, float keysVolts) {
  deckPadVolts_ = padVolts;
  deckKeysVolts_ = keysVolts;
}

void EepromStore::setModuleDescriptor(int port, const uint8_t* descriptor32) {
  if (port < 0 || port >= kNumBusPorts || !descriptor32) return;
  std::memcpy(modules_[port], descriptor32, kModuleDescriptorBytes);
}

const uint8_t* EepromStore::moduleDescriptor(int port) const {
  static const uint8_t kEmpty[kModuleDescriptorBytes] = {};
  if (port < 0 || port >= kNumBusPorts) return kEmpty;
  return modules_[port];
}

size_t EepromStore::serialize(uint8_t* out, size_t capacity) const {
  if (!out || capacity < kImageBytes) return 0;
  size_t o = 0;
  std::memcpy(out + o, kMagic, 4);
  o += 4;
  out[o++] = 1;  // version
  out[o++] = 0;  // flags
  const size_t lengthPos = o;
  o += 2;  // total record length (filled in below)
  uint8_t cvBlock[CvCalibration::kSerializedBytes];
  const size_t cvLen = cv_.serialize(cvBlock, sizeof(cvBlock));
  out[o++] = static_cast<uint8_t>(cvLen);
  std::memcpy(out + o, cvBlock, cvLen);
  o += cvLen;
  const int16_t padMv = static_cast<int16_t>(deckPadVolts_ * 1000.0f + 0.5f);
  const int16_t keysMv = static_cast<int16_t>(deckKeysVolts_ * 1000.0f + 0.5f);
  out[o++] = static_cast<uint8_t>(padMv & 0xFF);
  out[o++] = static_cast<uint8_t>((padMv >> 8) & 0xFF);
  out[o++] = static_cast<uint8_t>(keysMv & 0xFF);
  out[o++] = static_cast<uint8_t>((keysMv >> 8) & 0xFF);
  std::memcpy(out + o, modules_, sizeof(modules_));
  o += sizeof(modules_);
  for (int i = 0; i < 4; ++i) out[o++] = static_cast<uint8_t>((hours_ >> (8 * i)) & 0xFF);
  const size_t payloadEnd = o;
  const size_t total = payloadEnd + 2;
  // The length field is part of the CRC-protected payload, so write it first.
  out[lengthPos] = static_cast<uint8_t>(total & 0xFF);
  out[lengthPos + 1] = static_cast<uint8_t>((total >> 8) & 0xFF);
  const uint16_t crc = crc16Ccitt(out, payloadEnd);
  out[payloadEnd] = static_cast<uint8_t>(crc & 0xFF);
  out[payloadEnd + 1] = static_cast<uint8_t>(crc >> 8);
  return total;
}

bool EepromStore::deserialize(const uint8_t* data, size_t length) {
  if (!data || length < 12) return false;
  if (std::memcmp(data, kMagic, 4) != 0) return false;
  const size_t total = static_cast<size_t>(data[6]) | (static_cast<size_t>(data[7]) << 8);
  if (total < 12 || total > length) return false;
  const size_t payloadEnd = total - 2;
  const uint16_t stored = static_cast<uint16_t>(data[payloadEnd]) |
                          (static_cast<uint16_t>(data[payloadEnd + 1]) << 8);
  if (crc16Ccitt(data, payloadEnd) != stored) return false;
  size_t o = 8;  // magic + version + flags + length
  const uint8_t cvLen = data[o++];
  if (cvLen != CvCalibration::kSerializedBytes ||
      o + cvLen + 4 + sizeof(modules_) + 4 > payloadEnd) {
    return false;
  }
  CvCalibration cal;
  if (!cal.deserialize(data + o, cvLen)) return false;
  cv_ = cal;
  o += cvLen;
  const int16_t padMv = static_cast<int16_t>(data[o] | (data[o + 1] << 8));
  const int16_t keysMv = static_cast<int16_t>(data[o + 2] | (data[o + 3] << 8));
  o += 4;
  deckPadVolts_ = static_cast<float>(padMv) / 1000.0f;
  deckKeysVolts_ = static_cast<float>(keysMv) / 1000.0f;
  std::memcpy(modules_, data + o, sizeof(modules_));
  o += sizeof(modules_);
  uint32_t hours = 0;
  for (int i = 0; i < 4; ++i) hours |= static_cast<uint32_t>(data[o++]) << (8 * i);
  hours_ = hours;
  return true;
}

bool EepromStore::load() {
  if (!eeprom_) return false;
  uint8_t image[kImageBytes] = {};
  if (!eeprom_->read(0, image, sizeof(image))) {
    cv_.reset();
    ok_ = false;
    return false;
  }
  const size_t total = static_cast<size_t>(image[6]) | (static_cast<size_t>(image[7]) << 8);
  if (!deserialize(image, total)) {
    cv_.reset();
    ok_ = false;
    return false;
  }
  ok_ = true;
  return true;
}

bool EepromStore::save() {
  if (!eeprom_) return false;
  uint8_t image[kImageBytes] = {};
  const size_t length = serialize(image, sizeof(image));
  if (length == 0) return false;
  ok_ = eeprom_->write(0, image, length);
  return ok_;
}

}  // namespace bukifon
