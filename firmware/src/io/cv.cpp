// SPDX-License-Identifier: GPL-3.0-or-later
#include "io/cv.hpp"

#include <cmath>
#include <cstring>

#include "core/patch.hpp"

namespace bukifon {

void CvCalibration::reset() {
  for (int ch = 0; ch < kNumCvOut; ++ch) {
    const float volts[kPoints] = {0.0f, 2.5f, 5.0f, 10.0f};
    const uint16_t codes[kPoints] = {0, 1024, 2048, 4095};
    for (int i = 0; i < kPoints; ++i) {
      channels_[ch][i].volts = volts[i];
      channels_[ch][i].code = codes[i];
    }
  }
}

void CvCalibration::setPoint(int channel, int index, float volts, uint16_t code) {
  if (channel < 0 || channel >= kNumCvOut || index < 0 || index >= kPoints) return;
  channels_[channel][index].volts = volts;
  channels_[channel][index].code = code;
}

const CalPoint& CvCalibration::point(int channel, int index) const {
  static const CalPoint dummy{};
  if (channel < 0 || channel >= kNumCvOut || index < 0 || index >= kPoints) return dummy;
  return channels_[channel][index];
}

float CvCalibration::interpolateVolts(const Channel& ch, uint16_t code) {
  for (int i = 1; i < kPoints; ++i) {
    if (code <= ch[i].code) {
      const int c0 = ch[i - 1].code;
      const int c1 = ch[i].code;
      const float t = (c1 == c0) ? 0.0f : static_cast<float>(static_cast<int>(code) - c0) /
                                            static_cast<float>(c1 - c0);
      return ch[i - 1].volts + (ch[i].volts - ch[i - 1].volts) * t;
    }
  }
  return ch[kPoints - 1].volts;
}

float CvCalibration::interpolateCode(const Channel& ch, float volts) {
  for (int i = 1; i < kPoints; ++i) {
    if (volts <= ch[i].volts) {
      const float v0 = ch[i - 1].volts;
      const float v1 = ch[i].volts;
      const float t = (v1 == v0) ? 0.0f : (volts - v0) / (v1 - v0);
      return static_cast<float>(ch[i - 1].code) +
             static_cast<float>(static_cast<int>(ch[i].code) - static_cast<int>(ch[i - 1].code)) * t;
    }
  }
  return static_cast<float>(ch[kPoints - 1].code);
}

float CvCalibration::voltsForCode(int channel, uint16_t code) const {
  if (channel < 0 || channel >= kNumCvOut) return 0.0f;
  return interpolateVolts(channels_[channel], code);
}

uint16_t CvCalibration::codeForVolts(int channel, float volts) const {
  if (channel < 0 || channel >= kNumCvOut) return 0;
  volts = std::fmax(channels_[channel][0].volts, std::fmin(channels_[channel][3].volts, volts));
  const float code = interpolateCode(channels_[channel], volts);
  if (code < 0.0f) return 0;
  if (code > 4095.0f) return 4095;
  return static_cast<uint16_t>(code + 0.5f);
}

size_t CvCalibration::serialize(uint8_t* out, size_t capacity) const {
  if (!out || capacity < kSerializedBytes) return 0;
  size_t o = 0;
  for (int ch = 0; ch < kNumCvOut; ++ch) {
    for (int i = 0; i < kPoints; ++i) {
      const int16_t mv = static_cast<int16_t>(static_cast<int>(channels_[ch][i].volts * 1000.0f + 0.5f));
      out[o++] = static_cast<uint8_t>(mv & 0xFF);
      out[o++] = static_cast<uint8_t>((mv >> 8) & 0xFF);
      out[o++] = static_cast<uint8_t>(channels_[ch][i].code & 0xFF);
      out[o++] = static_cast<uint8_t>((channels_[ch][i].code >> 8) & 0xFF);
    }
  }
  const uint16_t crc = crc16Ccitt(out, o);
  out[o++] = static_cast<uint8_t>(crc & 0xFF);
  out[o++] = static_cast<uint8_t>(crc >> 8);
  return o;
}

bool CvCalibration::deserialize(const uint8_t* data, size_t length) {
  if (!data || length != kSerializedBytes) return false;
  const uint16_t stored = static_cast<uint16_t>(data[length - 2]) |
                          (static_cast<uint16_t>(data[length - 1]) << 8);
  if (crc16Ccitt(data, length - 2) != stored) return false;
  CvCalibration cal;
  size_t i = 0;
  for (int ch = 0; ch < kNumCvOut; ++ch) {
    for (int p = 0; p < kPoints; ++p) {
      const int16_t mv = static_cast<int16_t>(data[i] | (data[i + 1] << 8));
      const uint16_t code = static_cast<uint16_t>(data[i + 2] | (data[i + 3] << 8));
      cal.channels_[ch][p].volts = static_cast<float>(mv) / 1000.0f;
      cal.channels_[ch][p].code = code;
      i += 4;
    }
  }
  *this = cal;
  return true;
}

void CvInput::init(float sampleRate) {
  sampleRate_ = sampleRate;
  const float cutoff = 100.0f;
  coef_ = 1.0f - std::exp(-2.0f * static_cast<float>(M_PI) * cutoff / sampleRate_);
  volts_ = 0.0f;
  primed_ = false;
}

float CvInput::update(uint16_t raw) {
  const float norm = static_cast<float>(raw) / 4095.0f;
  const float target = negativeVolts_ + norm * (positiveVolts_ - negativeVolts_);
  if (!primed_) {
    volts_ = target;
    primed_ = true;
  } else {
    volts_ += (target - volts_) * coef_;
  }
  return volts_;
}

}  // namespace bukifon
