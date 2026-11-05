// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon firmware — global configuration (portable, no Arduino deps).
#pragma once

#include <cstdint>
#include <cstddef>

namespace bukifon {

// --- audio / control rates -------------------------------------------------
constexpr int kSampleRate = 48000;
constexpr int kControlRate = 1000;
constexpr int kBlockSize = 256;          // audio block on core1
constexpr int kFmOversampling = 2;       // FM core runs at 96 kHz
constexpr int kFmSampleRate = kSampleRate * kFmOversampling;

// --- engine topology -------------------------------------------------------
constexpr int kNumParts = 4;
constexpr int kMaxVoices = 8;
constexpr int kNumEnvs = 4;
constexpr int kNumLfos = 4;
constexpr int kModSlots = 16;
constexpr int kFmOperators = 4;
constexpr int kFmAlgorithms = 8;
constexpr int kMaxUnison = 4;
constexpr int kNumMacros = 4;

// --- wavetables ------------------------------------------------------------
constexpr int kNumWaves = 8;
constexpr int kTableSize = 2048;
constexpr int kMipLevels = 8;

// --- sequencer -------------------------------------------------------------
constexpr int kSeqSteps = 16;
constexpr int kSeqTracks = 4;            // one track per part
constexpr int kNumPatterns = 8;
constexpr int kMaxPatternChain = 16;
constexpr int kPlocksPerStep = 8;
constexpr int kStepMods = 8;

// --- io --------------------------------------------------------------------
constexpr int kNumPages = 8;
constexpr int kNumEncoders = 8;
constexpr int kNumPads = 18;
constexpr int kNumKeys = 42;
constexpr int kPanelLeds = 9;
constexpr int kPadLeds = 18;
constexpr int kKeyLeds = 42;
constexpr int kNumBusPorts = 3;
constexpr int kNumCvOut = 4;
constexpr int kNumCvIn = 4;

// --- storage ---------------------------------------------------------------
constexpr int kNumPresets = 64;
constexpr int kNumFactoryPatches = 16;
constexpr int kMaxPatchBytes = 512;

// --- FX / memory -----------------------------------------------------------
#if defined(BUKIFON_EMBEDDED)
constexpr int kDelayMaxSamples = 16000;  // 0.33 s stereo, int16 ring (64 KiB)
#else
constexpr int kDelayMaxSamples = 48000;  // 1.0 s stereo
#endif
constexpr int kChorusMaxSamples = 2048;

// --- board ----------------------------------------------------------------
namespace pins {
constexpr int kMidiTx = 0;
constexpr int kMidiRx = 1;
constexpr int kSpi0Sck = 2;
constexpr int kSpi0Mosi = 3;
constexpr int kSpi0Miso = 4;
constexpr int kMcp3208Cs = 5;
constexpr int kHc165Pl = 6;
constexpr int kLedData = 7;
constexpr int kI2c0Sda = 8;
constexpr int kI2c0Scl = 9;
constexpr int kLcdSck = 10;
constexpr int kLcdMosi = 11;
constexpr int kLcdCs = 12;
constexpr int kLcdDc = 13;
constexpr int kLcdRst = 14;
constexpr int kLcdBl = 15;
constexpr int kI2sBck = 16;
constexpr int kI2sLrck = 17;
constexpr int kI2sDin = 18;
constexpr int kPort0Cs = 19;
constexpr int kPort1Cs = 20;
constexpr int kPort2Cs = 21;
constexpr int kReserved22 = 22;
constexpr int kSysMon = 26;
constexpr int kDeckId = 27;
}  // namespace pins

// Default per-part voice allocation (sums to 8).
constexpr uint8_t kDefaultPartVoices[kNumParts] = {2, 2, 2, 2};

}  // namespace bukifon
