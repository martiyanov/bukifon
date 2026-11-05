// SPDX-License-Identifier: GPL-3.0-or-later
// I2S output for PCM5102A: PIO + DMA, 48 kHz / 16 bit stereo.
//
// On RP2040 the arduino-pico "I2S" library drives BCK/LRCK/DIN from a PIO state
// machine with a DMA ring; the engine fills two 256-frame application buffers
// alternately (double buffering) and writes them to the DMA ring.
//
// HARDWARE STATUS: not verified on a real PCM5102A board in this environment.
// TODO(hw): scope-check BCK/LRCK timing and DMA underrun counter on real HW.
#pragma once

#include <cstddef>
#include <cstdint>

#include "hal/pinmap.hpp"

#if defined(ARDUINO)
#include <Arduino.h>
#if __has_include(<I2S.h>)
#include <I2S.h>
#define BUKIFON_HAVE_I2S 1
#endif
#endif

namespace bukifon {
namespace hal {

class I2sPio {
 public:
  bool begin(int sampleRate = 48000) {
#if defined(BUKIFON_HAVE_I2S)
    I2S.setBCLK(pins::kI2sBck);   // LRCK is the next GPIO (GP17)
    I2S.setDATA(pins::kI2sDin);
    I2S.setBitsPerSample(16);
    // Two DMA buffers of 256 interleaved stereo frames = the 2x256 contract.
    I2S.setBuffers(pins::kAudioBuffers, pins::kAudioBlock * 2);
    started_ = I2S.begin(sampleRate);
    return started_;
#else
    (void)sampleRate;
    return false;  // TODO(hw): core without the I2S library
#endif
  }

  // Blocking write of interleaved stereo frames into the DMA ring.
  void writeFrames(const int16_t* interleaved, size_t frames) {
#if defined(BUKIFON_HAVE_I2S)
    if (!started_) return;
    I2S.write(reinterpret_cast<const uint8_t*>(interleaved), frames * 4);
#else
    (void)interleaved;
    (void)frames;
#endif
  }

  void end() {
#if defined(BUKIFON_HAVE_I2S)
    I2S.end();
#endif
    started_ = false;
  }
  bool started() const { return started_; }

 private:
  bool started_ = false;
};

}  // namespace hal
}  // namespace bukifon
