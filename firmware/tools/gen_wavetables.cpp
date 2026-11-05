// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon offline wavetable generator.
//
// Builds the band-limited wavetable bank consumed by the firmware:
//   8 waveforms x 8 mip levels x 2048 samples, int16 (flash-resident on RP2040).
//
// Mip level L keeps harmonics 1..(1023 >> L), so a table level is always
// band-limited below its own Nyquist; the oscillator picks the level from the
// note frequency.  Run from the repository root:
//
//   g++ -std=c++17 -O2 firmware/tools/gen_wavetables.cpp -o /tmp/gen_wavetables
//   /tmp/gen_wavetables firmware/src/dsp/wavetable_data.cpp \
//                       firmware/src/dsp/wavetable_data.hpp
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace {

constexpr int kWaves = 8;
constexpr int kMips = 8;
constexpr int kSize = 2048;
constexpr int kMaxHarm = kSize / 2 - 1;  // 1023 representable harmonics

const char* const kNames[kWaves] = {"SAW",  "SQUARE", "PULSE25", "TRI",
                                    "SINE", "ORGAN",  "DIGITAL", "VOX"};

// Harmonic amplitude for waveform `wave`, harmonic `n` (1-based).
double amplitude(int wave, int n) {
  switch (wave) {
    case 0:  // saw
      return 1.0 / n;
    case 1:  // square
      return (n & 1) ? 1.0 / n : 0.0;
    case 2:  // 25% pulse
      return (2.0 / (n * M_PI)) * std::sin(n * M_PI * 0.25);
    case 3: {  // triangle
      if ((n & 1) == 0) return 0.0;
      const double sign = ((n - 1) / 2) % 2 == 0 ? 1.0 : -1.0;
      return sign * 8.0 / (M_PI * M_PI * n * n);
    }
    case 4:  // sine
      return n == 1 ? 1.0 : 0.0;
    case 5: {  // organ: 1,2,3,4,6,8
      const int partials[6] = {1, 2, 3, 4, 6, 8};
      const double amps[6] = {1.0, 0.5, 0.33, 0.2, 0.12, 0.08};
      for (int i = 0; i < 6; ++i)
        if (n == partials[i]) return amps[i];
      return 0.0;
    }
    case 6: {  // digital/bell
      const int partials[8] = {1, 2, 3, 4, 5, 7, 9, 11};
      const double amps[8] = {1.0, 0.15, 0.5, 0.1, 0.35, 0.25, 0.15, 0.1};
      for (int i = 0; i < 8; ++i)
        if (n == partials[i]) return amps[i];
      return 0.0;
    }
    case 7: {  // voice-ish: 1/n with two formant bumps
      const double f1 = std::exp(-std::pow((n - 3.5) / 1.2, 2.0));
      const double f2 = std::exp(-std::pow((n - 8.0) / 1.5, 2.0));
      return (1.0 / n) * (1.0 + 2.0 * f1 + 1.5 * f2);
    }
    default:
      return 0.0;
  }
}

std::vector<int16_t> renderLevel(int wave, int mip) {
  const int maxHarm = std::max(1, kMaxHarm >> mip);
  std::vector<double> buf(kSize, 0.0);
  for (int n = 1; n <= maxHarm; ++n) {
    const double a = amplitude(wave, n);
    if (a == 0.0) continue;
    for (int i = 0; i < kSize; ++i) {
      buf[i] += a * std::sin(2.0 * M_PI * n * i / kSize);
    }
  }
  double peak = 1e-12;
  for (double v : buf) peak = std::max(peak, std::fabs(v));
  std::vector<int16_t> out(kSize);
  const double scale = 32767.0 * 0.98 / peak;
  for (int i = 0; i < kSize; ++i) {
    out[i] = static_cast<int16_t>(std::lround(buf[i] * scale));
  }
  return out;
}

bool writeFile(const char* path, const std::string& text) {
  FILE* f = std::fopen(path, "wb");
  if (!f) return false;
  std::fwrite(text.data(), 1, text.size(), f);
  std::fclose(f);
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  const char* cppPath = argc > 1 ? argv[1] : "wavetable_data.cpp";
  const char* hppPath = argc > 2 ? argv[2] : "wavetable_data.hpp";

  std::vector<std::vector<std::vector<int16_t>>> data(
      kWaves, std::vector<std::vector<int16_t>>(kMips));
  for (int w = 0; w < kWaves; ++w) {
    for (int m = 0; m < kMips; ++m) {
      data[w][m] = renderLevel(w, m);
      const int maxHarm = std::max(1, kMaxHarm >> m);
      std::printf("wave %d (%s) mip %d: harmonics 1..%d\n", w, kNames[w], m, maxHarm);
    }
  }

  std::string hpp;
  hpp += "// SPDX-License-Identifier: GPL-3.0-or-later\n";
  hpp += "// GENERATED FILE — do not edit. Generator: firmware/tools/gen_wavetables.cpp\n";
  hpp += "#pragma once\n\n#include <cstdint>\n\nnamespace bukifon {\n\n";
  hpp += "constexpr int kWaveCount = " + std::to_string(kWaves) + ";\n";
  hpp += "// Waveform names for the UI (index == table index).\n";
  hpp += "extern const char* const kWaveNames[kWaveCount];\n";
  hpp += "// Data[w][mip][sample], int16 full scale ~32767.\n";
  hpp += "extern const int16_t kWavetableData[kWaveCount][kMipLevels][kTableSize];\n\n";
  hpp += "}  // namespace bukifon\n";
  if (!writeFile(hppPath, hpp)) {
    std::fprintf(stderr, "cannot write %s\n", hppPath);
    return 1;
  }

  std::string cpp;
  cpp += "// SPDX-License-Identifier: GPL-3.0-or-later\n";
  cpp += "// GENERATED FILE — do not edit. Generator: firmware/tools/gen_wavetables.cpp\n";
  cpp += "#include \"dsp/wavetable_data.hpp\"\n\nnamespace bukifon {\n\n";
  cpp += "const char* const kWaveNames[kWaveCount] = {\"SAW\", \"SQUARE\", \"PULSE25\", \"TRI\",\n";
  cpp += "    \"SINE\", \"ORGAN\", \"DIGITAL\", \"VOX\"};\n\n";
  cpp += "const int16_t kWavetableData[kWaveCount][kMipLevels][kTableSize] = {\n";
  for (int w = 0; w < kWaves; ++w) {
    cpp += "  {  // " + std::string(kNames[w]) + "\n";
    for (int m = 0; m < kMips; ++m) {
      cpp += "    {\n";
      const auto& lev = data[w][m];
      for (int i = 0; i < kSize; i += 16) {
        cpp += "      ";
        for (int j = 0; j < 16 && i + j < kSize; ++j) {
          cpp += std::to_string(static_cast<int>(lev[i + j]));
          cpp += (i + j + 1 < kSize) ? "," : "";
          if (j != 15 && i + j + 1 < kSize) cpp += " ";
        }
        cpp += "\n";
      }
      cpp += "    },\n";
    }
    cpp += "  },\n";
  }
  cpp += "};\n\n}  // namespace bukifon\n";
  if (!writeFile(cppPath, cpp)) {
    std::fprintf(stderr, "cannot write %s\n", cppPath);
    return 1;
  }
  std::printf("wrote %s and %s\n", cppPath, hppPath);
  return 0;
}
