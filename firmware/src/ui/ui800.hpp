// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon 800x480 UI shell (host simulator + ESP32-P4/S3 skeleton).
//
// The UI is a pure function of a UiSnapshot: it owns no state and never talks
// to the engine.  Snapshots are produced by the host simulator / the device
// control loop.  Screens: MAIN, SEQUENCER, MIXER, MODULES.
#pragma once

#include <cstddef>
#include <cstdint>

#include "core/device_mode.hpp"
#include "io/gen.hpp"
#include "ui/canvas.hpp"

namespace bukifon {
namespace ui {

enum class Screen : uint8_t {
  Main = 0,
  Sequencer,
  Mixer,
  Modules,
  Gen,  // 5th tab: generative functions (PROB/EUCLID/MUTATE/SCALE/ARP/...)
  Ext,  // 6th tab: 8 external MIDI tracks (docs/70)
  kNumScreens
};

constexpr int kUiWidth = 800;
constexpr int kUiHeight = 480;
constexpr int kMaxTracks = 4;   // display/transport rows (architecture allows 8)
constexpr int kMaxSteps = 16;
constexpr int kNumParams = 8;   // page parameters (left half, А–З)
constexpr int kNumMacros = 8;   // fixed macros (right half, И–П)
constexpr int kNumEncoders = 16;  // mirror of the panel encoders
constexpr int kNumHints = 8;

// Typography scale from docs/69 (pixels of glyph height).  Nothing smaller than
// Caption is allowed in the 800x480 renderer.
enum class UiTextRole : uint8_t {
  Caption = 0,  // 12 px — parameter/team/tab labels (minimum)
  Value,        // 18 px — main parameter/macro values
  Critical,     // 24 px — BPM, STEP, REC, part number, mode
  Title         // 26 px — screen title
};
int uiTextHeight(UiTextRole role);
int uiTextWidth(UiTextRole role);
void drawTextRole(ICanvas& canvas, int x, int y, const char* text, uint16_t color,
                  UiTextRole role);
// Latin transliteration of Cyrillic labels (the 6x8 font is ASCII only):
// "А · CUTOFF" renders as "A · CUTOFF" while snapshots keep the real labels.
const char* uiAsciiForLabel(const char* text, char* buffer, size_t capacity);

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

struct UiExtTrack {
  char name[8] = "T1";
  uint8_t channel = 1;
  uint8_t program = 0;
  uint8_t ccNumber = 74;
  bool muted = false;
  bool selected = false;
  bool stepActive[kMaxSteps] = {};
  bool stepPlocked[kMaxSteps] = {};
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
  UiParam macros[kNumMacros];
  char hints[kNumHints][12] = {};
  int selectedParam = 0;   // page parameter 0..7
  int selectedEncoder = 0; // 0..15 (mirror of the physical encoder)
  // Persistent context line (docs/68 §2): PART · SELECTED · PAGE · FADERS · REC · UNSAVED.
  char partLabel[8] = "PART 1";
  char selectedLabel[16] = "1";
  char faderMode[10] = "TRACK";
  bool unsaved = false;
  int moduleCount = 0;
  char modules[8][24] = {};
  char moduleApi[24] = "API v0";
  bool moduleBypassed = false;
  char footer[80] = "";
  int activeVoices = 0;
  float masterLevel = 0.0f;
  bool transportRecord = false;
  // --- GEN page / UX patterns (docs/65) -----------------------------------
  GenParams gen[kMaxTracks];
  bool genPartSelected[kMaxTracks] = {};  // multi-select for group edits
  bool paramModulated[kNumParams] = {};   // "M" marker (LFO etc.)
  bool abCompare = false;                 // A/B compare available
  bool abShowB = false;                   // currently showing B
  uint8_t presetSlot = 0;
  char presetNames[8][16] = {};
  char scaleName[10] = "OFF";
  char arpRateText[8] = "1/16";
  char arpModeText[8] = "UP";
  uint16_t euclidMask = 0;
  // --- EXT page: 8 external MIDI tracks (docs/70) -------------------------
  UiExtTrack extTracks[8];
  int extSelectedTrack = 0;
  int extSelectedStep = 0;
};

// Fill a snapshot with deterministic, screen-appropriate demo content.
void uiSnapshotDemo(UiSnapshot* snapshot, Screen screen);
// Mode-specific panels for the 4 device modes (Synth / Sampler / DAW /
// USB-keyboard).  The shell stays the same; status bar MODE and the panels differ.
void uiSnapshotForDeviceMode(UiSnapshot* snapshot, DeviceMode mode);
// GEN page demo content (5th tab) + presets/A-B/multi-select/mod markers.
void uiSnapshotGenDemo(UiSnapshot* snapshot);
// EXT page demo content: 8 external tracks / 16 steps / CH,PC,VEL,LEN,CC,...
void uiSnapshotExtDemo(UiSnapshot* snapshot);

// UX helpers (docs/68/69):
// Build the always-visible context line (PART · SELECTED · PAGE · FADERS · REC · UNSAVED).
void uiBuildContextLine(const UiSnapshot* snapshot, char* out, size_t capacity);
// HOME one-gesture return to MAIN (docs/68 §4).
void uiHandleHome(UiSnapshot* snapshot);
// Mirror mapping: encoder 0..15 -> page parameter or macro cell.
// col<4 are page parameters (returned index 0..7, isMacro=false),
// col>=4 are macros (returned index 0..7, isMacro=true).
int uiEncoderCellIndex(int encoder, bool* isMacro);
const char* uiEncoderCellPrefix(int encoder);  // "А".."П" (Cyrillic, transliterated when drawn)
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
