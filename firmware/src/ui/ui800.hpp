// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon 800x480 UI shell (host simulator + ESP32-P4/S3 skeleton).
//
// The UI is a pure function of a UiSnapshot: it owns no state and never talks
// to the engine.  Snapshots are produced by the host simulator / the device
// control loop.  Screens: MAIN, SEQUENCER, MIXER, MODULES.
#pragma once

#include <cstdint>

#include "ui/canvas.hpp"

namespace bukifon {
namespace ui {

enum class Screen : uint8_t {
  Main = 0,
  Sequencer,
  Mixer,
  Modules,
  kNumScreens
};

constexpr int kUiWidth = 800;
constexpr int kUiHeight = 480;
constexpr int kMaxTracks = 4;   // display/transport rows (architecture allows 8)
constexpr int kMaxSteps = 16;
constexpr int kNumParams = 8;   // parameter panel rows/encoders
constexpr int kNumHints = 8;

struct UiTrack {
  char name[10] = "PART";
  char patch[16] = "Init";
  bool muted = false;
  bool active = false;
  int voices = 0;
  int currentStep = 0;
  int length = kMaxSteps;
  float level = 0.0f;   // 0..1 meter
  float peak = 0.0f;
  float cutoff = 2000.0f;
  float pan = 0.0f;     // -1..1
  uint8_t note[kMaxSteps] = {};
  bool stepActive[kMaxSteps] = {};
  bool stepPlocked[kMaxSteps] = {};
};

struct UiParam {
  char label[14] = "";
  char value[12] = "";
  float norm = 0.0f;
};

struct UiSnapshot {
  Screen screen = Screen::Main;
  char title[12] = "BUKIFON";
  char page[16] = "MAIN";
  float bpm = 120.0f;
  int pattern = 1;
  bool playing = false;
  char status[10] = "STOP";
  char deviceMode[16] = "SYNTH";
  int bar = 0;
  int activeStep = 0;
  bool fill = false;
  int trackCount = kMaxTracks;
  int stepCount = kMaxSteps;
  UiTrack tracks[kMaxTracks];
  UiParam params[kNumParams];
  char hints[kNumHints][12] = {};
  int selectedParam = 0;
  int moduleCount = 0;
  char modules[8][24] = {};
  char moduleApi[24] = "API v0";
  bool moduleBypassed = false;
  char footer[80] = "";
  int activeVoices = 0;
  float masterLevel = 0.0f;
  bool transportRecord = false;
};

// Fill a snapshot with deterministic, screen-appropriate demo content.
void uiSnapshotDemo(UiSnapshot* snapshot, Screen screen);
void uiSnapshotInit(UiSnapshot* snapshot);

void drawUi800(ICanvas& canvas, const UiSnapshot& snapshot);

// 6x8 font drawn with an integer scale (1 = 6x8, 2 = 12x16, 3 = 18x24).
void drawTextScaled(ICanvas& canvas, int x, int y, const char* text, uint16_t color, int scale);

// 800x480 RGB565 framebuffer.  On ESP32 the buffer is allocated in PSRAM when
// available (750 KiB); on the host it is a normal heap allocation.
class Framebuffer800 : public ICanvas {
 public:
  Framebuffer800();
  ~Framebuffer800();
  Framebuffer800(const Framebuffer800&) = delete;
  Framebuffer800& operator=(const Framebuffer800&) = delete;

  int width() const override { return kUiWidth; }
  int height() const override { return kUiHeight; }
  void fillRect(int x, int y, int w, int h, uint16_t color) override;
  void drawPixel(int x, int y, uint16_t color) override;
  void drawChar(int x, int y, char c, uint16_t color) override;
  void clear(uint16_t color);

  bool valid() const { return pixels_ != nullptr; }
  uint16_t at(int x, int y) const;
  const uint16_t* data() const { return pixels_; }

  // Binary PPM (P6, RGB888) — converted to PNG with tools/ppm_to_png.py.
  bool writePpm(const char* path) const;

 private:
  uint16_t* pixels_ = nullptr;
};

}  // namespace ui
}  // namespace bukifon
