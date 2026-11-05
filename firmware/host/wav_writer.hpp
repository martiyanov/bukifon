// SPDX-License-Identifier: GPL-3.0-or-later
// Minimal 16-bit PCM WAV writer used by the host renderer.
#pragma once

#include <cstdint>
#include <cstdio>

#include "dsp/effects.hpp"

namespace bukifon {

class WavWriter {
 public:
  ~WavWriter() { close(); }

  bool open(const char* path, int sampleRate = 48000, int channels = 2, int bits = 16) {
    close();
    file_ = std::fopen(path, "wb");
    if (!file_) return false;
    sampleRate_ = sampleRate;
    channels_ = channels;
    bits_ = bits;
    dataBytes_ = 0;
    writeHeader(0);
    return true;
  }

  void writeStereo(const float* l, const float* r, int n, Dither* dither) {
    if (!file_) return;
    for (int i = 0; i < n; ++i) {
      const int16_t sl = dither ? dither->toPcm16(l[i]) : toPcm16(l[i]);
      const int16_t sr = dither ? dither->toPcm16(r[i]) : toPcm16(r[i]);
      std::fwrite(&sl, sizeof(int16_t), 1, file_);
      std::fwrite(&sr, sizeof(int16_t), 1, file_);
      dataBytes_ += 4;
    }
  }

  bool close() {
    if (!file_) return true;
    // Patch the RIFF/data sizes now that they are known.
    const uint32_t riffSize = 36 + dataBytes_;
    std::fseek(file_, 4, SEEK_SET);
    std::fwrite(&riffSize, sizeof(uint32_t), 1, file_);
    std::fseek(file_, 40, SEEK_SET);
    std::fwrite(&dataBytes_, sizeof(uint32_t), 1, file_);
    const bool ok = (std::fclose(file_) == 0);
    file_ = nullptr;
    return ok;
  }

  uint32_t frames() const { return dataBytes_ / (channels_ * bits_ / 8); }

 private:
  void writeHeader(uint32_t dataBytes) {
    const uint16_t channels = static_cast<uint16_t>(channels_);
    const uint16_t bits = static_cast<uint16_t>(bits_);
    const uint32_t rate = static_cast<uint32_t>(sampleRate_);
    const uint16_t blockAlign = static_cast<uint16_t>(channels * bits / 8);
    const uint32_t byteRate = rate * blockAlign;
    const uint32_t riffSize = 36 + dataBytes;
    std::fwrite("RIFF", 1, 4, file_);
    std::fwrite(&riffSize, 4, 1, file_);
    std::fwrite("WAVEfmt ", 1, 8, file_);
    const uint32_t fmtSize = 16;
    const uint16_t audioFormat = 1;
    std::fwrite(&fmtSize, 4, 1, file_);
    std::fwrite(&audioFormat, 2, 1, file_);
    std::fwrite(&channels, 2, 1, file_);
    std::fwrite(&rate, 4, 1, file_);
    std::fwrite(&byteRate, 4, 1, file_);
    std::fwrite(&blockAlign, 2, 1, file_);
    std::fwrite(&bits, 2, 1, file_);
    std::fwrite("data", 1, 4, file_);
    std::fwrite(&dataBytes, 4, 1, file_);
  }

  static int16_t toPcm16(float x) {
    const float v = x < -1.0f ? -1.0f : (x > 1.0f ? 1.0f : x);
    const float scaled = v * 32767.0f;
    const int32_t r = static_cast<int32_t>(scaled >= 0.0f ? scaled + 0.5f : scaled - 0.5f);
    return static_cast<int16_t>(r < -32768 ? -32768 : (r > 32767 ? 32767 : r));
  }

  FILE* file_ = nullptr;
  int sampleRate_ = 48000;
  int channels_ = 2;
  int bits_ = 16;
  uint32_t dataBytes_ = 0;
};

}  // namespace bukifon
