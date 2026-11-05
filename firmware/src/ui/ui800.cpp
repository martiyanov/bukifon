// SPDX-License-Identifier: GPL-3.0-or-later
#include "ui/ui800.hpp"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <new>

#include "ui/font6x8.hpp"

#if defined(ESP32)
#include <esp_heap_caps.h>
#endif

namespace bukifon {
namespace ui {
namespace {

constexpr int kHeaderH = 56;
constexpr int kFooterH = 44;
constexpr int kTracksY = 62;
constexpr int kTrackH = 56;
constexpr int kTrackGap = 4;
constexpr int kParamsY = 308;
constexpr int kParamCellW = 194;
constexpr int kParamCellH = 40;
constexpr int kHintsY = 400;
constexpr int kTransportY = 432;

const uint16_t kBg = colors::kPanel;
const uint16_t kCard = rgb565(28, 31, 40);
const uint16_t kCardActive = rgb565(40, 52, 64);
const uint16_t kGridOn = rgb565(70, 190, 120);
const uint16_t kGridOff = rgb565(38, 42, 50);
const uint16_t kGridPlock = rgb565(255, 170, 60);
const uint16_t kMeter = rgb565(90, 220, 120);
const uint16_t kMeterHot = rgb565(255, 90, 80);

void drawCard(ICanvas& c, int x, int y, int w, int h, uint16_t fill, uint16_t border) {
  c.fillRect(x, y, w, h, fill);
  c.drawRect(x, y, w, h, border);
}

void drawBar(ICanvas& c, int x, int y, int w, int h, float norm, uint16_t color) {
  if (w <= 0 || h <= 0) return;
  c.fillRect(x, y, w, h, kGridOff);
  const int filled = static_cast<int>(std::lround(static_cast<double>(norm) * (w - 2)));
  if (filled > 0) c.fillRect(x + 1, y + 1, filled, h - 2, color);
}

const char* screenName(Screen s) {
  switch (s) {
    case Screen::Main: return "MAIN";
    case Screen::Sequencer: return "SEQUENCER";
    case Screen::Mixer: return "MIXER";
    case Screen::Modules: return "MODULES";
    default: return "?";
  }
}

void drawHeader(ICanvas& c, const UiSnapshot& s) {
  c.fillRect(0, 0, kUiWidth, kHeaderH, colors::kDim);
  c.fillRect(0, kHeaderH - 2, kUiWidth, 2, colors::kAccent);
  drawTextScaled(c, 12, 8, s.title, colors::kAccent, 2);
  c.drawText(12, 38, s.page, colors::kGrey);

  char buf[32];
  std::snprintf(buf, sizeof(buf), "BPM %d", static_cast<int>(std::lround(s.bpm)));
  c.drawText(300, 10, buf, colors::kWhite);
  std::snprintf(buf, sizeof(buf), "PAT %02d", s.pattern);
  c.drawText(300, 28, buf, colors::kWhite);
  std::snprintf(buf, sizeof(buf), "BAR %03d", s.bar + 1);
  c.drawText(430, 10, buf, colors::kGrey);
  std::snprintf(buf, sizeof(buf), "STEP %02d", s.activeStep + 1);
  c.drawText(430, 28, buf, colors::kGrey);

  const uint16_t statusColor = s.playing ? colors::kGreen : colors::kRed;
  c.fillRect(560, 10, 10, 10, statusColor);
  c.drawText(578, 10, s.status, statusColor);
  if (s.fill) c.drawText(578, 28, "FILL", colors::kValue);
  if (s.transportRecord) c.drawText(650, 28, "REC", colors::kRed);

  std::snprintf(buf, sizeof(buf), "VOICES %d", s.activeVoices);
  c.drawText(650, 10, buf, colors::kAccent);
  drawTextScaled(c, 700, 34, s.moduleApi, colors::kGrey, 1);
}

void drawFooter(ICanvas& c, const UiSnapshot& s) {
  c.fillRect(0, kTransportY, kUiWidth, kFooterH, colors::kDim);
  // Transport row.
  c.fillRect(12, kTransportY + 8, 64, 28, s.playing ? colors::kGreen : kCard);
  c.drawText(24, kTransportY + 16, s.playing ? "PLAY" : "STOP", s.playing ? colors::kBlack : colors::kWhite);
  c.drawRect(88, kTransportY + 8, 64, 28, colors::kGrey);
  c.drawText(100, kTransportY + 16, "|<", colors::kWhite);
  c.drawRect(164, kTransportY + 8, 64, 28, colors::kGrey);
  c.drawText(176, kTransportY + 16, ">|", colors::kWhite);
  c.drawRect(240, kTransportY + 8, 64, 28, colors::kRed);
  c.drawText(252, kTransportY + 16, "REC", colors::kWhite);
  c.drawText(320, kTransportY + 16, s.footer, colors::kGrey);
  // Master level.
  char buf[32];
  std::snprintf(buf, sizeof(buf), "MASTER %3d%%",
                static_cast<int>(std::lround(s.masterLevel * 100.0f)));
  c.drawText(600, kTransportY + 6, buf, colors::kWhite);
  drawBar(c, 600, kTransportY + 22, 180, 10, s.masterLevel, kMeter);
  // Box for the selected encoder hint.
  if (s.selectedParam >= 0 && s.selectedParam < kNumHints) {
    c.drawText(12, kTransportY + 20, "ENC", colors::kGrey);
    c.drawText(48, kTransportY + 20, s.hints[s.selectedParam], colors::kValue);
  }
}

void drawTrackCard(ICanvas& c, const UiSnapshot& s, int track, int x, int y, int w, int h) {
  const UiTrack& t = s.tracks[track];
  const bool selected = s.screen == Screen::Sequencer && track == s.selectedParam % kMaxTracks;
  drawCard(c, x, y, w, h, t.active ? kCardActive : kCard,
           selected ? colors::kAccent : colors::kGrey);
  drawTextScaled(c, x + 8, y + 6, t.name, t.muted ? colors::kGrey : colors::kWhite, 1);
  c.drawText(x + 8, y + 20, t.patch, colors::kGrey);
  char buf[32];
  std::snprintf(buf, sizeof(buf), "CUT %d", static_cast<int>(std::lround(t.cutoff)));
  c.drawText(x + 8, y + 34, buf, colors::kGrey);
  std::snprintf(buf, sizeof(buf), "V%d", t.voices);
  c.drawText(x + 110, y + 34, buf, colors::kAccent);
  if (t.muted) c.drawText(x + 136, y + 34, "MUTE", colors::kRed);
  // Step grid: 16 cells.
  const int gridX = x + 170;
  const int gridY = y + 8;
  const int cells = s.stepCount > kMaxSteps ? kMaxSteps : s.stepCount;
  const int cellW = (w - 180) / (cells > 0 ? cells : 1);
  const int cellH = h - 16;
  for (int step = 0; step < cells; ++step) {
    const bool activeStep = (step == s.activeStep);
    const bool on = t.stepActive[step];
    uint16_t fill = on ? kGridOn : kGridOff;
    if (t.stepPlocked[step]) fill = kGridPlock;
    if (activeStep) fill = colors::kAccent;
    c.fillRect(gridX + step * cellW, gridY, cellW - 2, cellH, fill);
    if (on) {
      // A small note tick (1 px) at the bottom of the cell.
      c.fillRect(gridX + step * cellW + 2, gridY + cellH - 4, cellW - 6, 2, colors::kWhite);
    }
  }
  // Track meter.
  drawBar(c, x + 8, y + h - 12, w - 16, 6, t.level, t.peak > 0.9f ? kMeterHot : kMeter);
}

void drawTracks(ICanvas& c, const UiSnapshot& s) {
  for (int i = 0; i < s.trackCount && i < kMaxTracks; ++i) {
    const int y = kTracksY + i * (kTrackH + kTrackGap);
    drawTrackCard(c, s, i, 10, y, kUiWidth - 20, kTrackH);
  }
}

void drawSequencerGrid(ICanvas& c, const UiSnapshot& s) {
  // Ruler.
  c.fillRect(10, kTracksY - 18, kUiWidth - 20, 16, colors::kDim);
  for (int step = 0; step < s.stepCount && step < kMaxSteps; ++step) {
    char buf[8];
    std::snprintf(buf, sizeof(buf), "%02d", step + 1);
    const int x = 12 + step * 47;
    c.drawText(x, kTracksY - 16, buf, step == s.activeStep ? colors::kAccent : colors::kGrey);
  }
  for (int t = 0; t < s.trackCount && t < kMaxTracks; ++t) {
    const UiTrack& track = s.tracks[t];
    const int y = kTracksY + t * (kTrackH + kTrackGap);
    c.fillRect(10, y, 130, kTrackH, track.active ? kCardActive : kCard);
    drawTextScaled(c, 16, y + 6, track.name, track.muted ? colors::kGrey : colors::kWhite, 1);
    c.drawText(16, y + 22, track.patch, colors::kGrey);
    c.drawText(16, y + 38, track.muted ? "MUTED" : (track.active ? "ACTIVE" : "IDLE"),
               track.muted ? colors::kRed : colors::kGreen);
    for (int step = 0; step < s.stepCount && step < kMaxSteps; ++step) {
      const int x = 146 + step * 40;
      const bool on = track.stepActive[step] && (step % track.length == 0 || step < track.length);
      uint16_t fill = on ? kGridOn : kGridOff;
      if (track.stepPlocked[step]) fill = kGridPlock;
      if (step == s.activeStep) fill = colors::kAccent;
      c.fillRect(x, y + 4, 36, kTrackH - 8, fill);
      char note[8];
      std::snprintf(note, sizeof(note), "%d", static_cast<int>(track.note[step]));
      if (on) c.drawText(x + 6, y + 18, note, colors::kBlack);
      if (track.stepPlocked[step]) c.drawText(x + 28, y + 6, "*", colors::kWhite);
    }
  }
}

void drawMixer(ICanvas& c, const UiSnapshot& s) {
  for (int t = 0; t < s.trackCount && t < kMaxTracks; ++t) {
    const UiTrack& track = s.tracks[t];
    const int x = 10 + t * 196;
    const int y = kTracksY;
    const int w = 186;
    const int h = 236;
    drawCard(c, x, y, w, h, kCard, colors::kGrey);
    drawTextScaled(c, x + 8, y + 8, track.name, colors::kWhite, 1);
    c.drawText(x + 8, y + 24, track.patch, colors::kGrey);
    // Vertical level meter.
    c.fillRect(x + w - 26, y + 40, 14, h - 90, kGridOff);
    const int meterH = static_cast<int>(std::lround(static_cast<double>(track.level) * (h - 94)));
    c.fillRect(x + w - 24, y + 40 + (h - 90 - meterH), 10, meterH,
               track.peak > 0.9f ? kMeterHot : kMeter);
    char buf[32];
    std::snprintf(buf, sizeof(buf), "CUT %4d", static_cast<int>(std::lround(track.cutoff)));
    c.drawText(x + 8, y + 50, buf, colors::kWhite);
    std::snprintf(buf, sizeof(buf), "PAN %+d", static_cast<int>(std::lround(track.pan * 100.0f)));
    c.drawText(x + 8, y + 66, buf, colors::kWhite);
    std::snprintf(buf, sizeof(buf), "VOX %d", track.voices);
    c.drawText(x + 8, y + 82, buf, colors::kGrey);
    c.drawText(x + 8, y + 100, "SEND A", colors::kGrey);
    drawBar(c, x + 8, y + 114, w - 44, 8, track.level * 0.8f, kMeter);
    c.drawText(x + 8, y + 128, "SEND B", colors::kGrey);
    drawBar(c, x + 8, y + 142, w - 44, 8, track.level * 0.5f, kMeter);
    if (track.muted) {
      c.fillRect(x, y, w, 24, colors::kRed);
      c.drawText(x + 8, y + 6, "MUTED", colors::kBlack);
    }
  }
}

void drawModulesScreen(ICanvas& c, const UiSnapshot& s) {
  drawCard(c, 10, kTracksY, 360, 236, kCard, colors::kGrey);
  drawTextScaled(c, 20, kTracksY + 8, "MODULES", colors::kAccent, 1);
  c.drawText(20, kTracksY + 26, s.moduleApi, colors::kGrey);
  if (s.moduleBypassed) c.drawText(20, kTracksY + 26, "BYPASS (budget)", colors::kRed);
  for (int i = 0; i < s.moduleCount && i < 8; ++i) {
    const int y = kTracksY + 46 + i * 22;
    c.fillRect(20, y, 340, 20, i == s.selectedParam ? kCardActive : kGridOff);
    c.drawText(26, y + 6, s.modules[i], colors::kWhite);
  }
  // Right side: parameter panel drawn separately.
  drawCard(c, 380, kTracksY, 410, 236, kCard, colors::kGrey);
  drawTextScaled(c, 392, kTracksY + 8, "PARAMETERS", colors::kAccent, 1);
  for (int i = 0; i < kNumParams; ++i) {
    const int col = i % 2;
    const int row = i / 2;
    const int x = 392 + col * 196;
    const int y = kTracksY + 34 + row * 46;
    c.drawText(x, y, s.params[i].label, colors::kGrey);
    drawTextScaled(c, x, y + 12, s.params[i].value, colors::kValue, 1);
    drawBar(c, x, y + 28, 180, 6, s.params[i].norm, colors::kAccent);
  }
}

void drawParamPanel(ICanvas& c, const UiSnapshot& s) {
  for (int i = 0; i < kNumParams; ++i) {
    const int col = i % 4;
    const int row = i / 4;
    const int x = 10 + col * kParamCellW;
    const int y = kParamsY + row * kParamCellH;
    const uint16_t border = (i == s.selectedParam) ? colors::kAccent : colors::kGrey;
    drawCard(c, x, y, kParamCellW - 6, kParamCellH - 6, kCard, border);
    c.drawText(x + 6, y + 5, s.params[i].label, colors::kGrey);
    drawTextScaled(c, x + 6, y + 16, s.params[i].value, colors::kValue, 1);
    drawBar(c, x + 100, y + 18, kParamCellW - 114, 8, s.params[i].norm, colors::kAccent);
  }
}

void drawHints(ICanvas& c, const UiSnapshot& s) {
  for (int i = 0; i < kNumHints; ++i) {
    const int x = 10 + i * 98;
    const bool selected = (i == s.selectedParam);
    c.fillRect(x, kHintsY, 92, 26, selected ? kCardActive : kCard);
    char label[16];
    std::snprintf(label, sizeof(label), "E%d", i + 1);
    c.drawText(x + 4, kHintsY + 3, label, selected ? colors::kAccent : colors::kGrey);
    c.drawText(x + 20, kHintsY + 3, s.hints[i], selected ? colors::kWhite : colors::kGrey);
    c.drawText(x + 20, kHintsY + 14, selected ? "< >" : "   ", colors::kValue);
  }
}

}  // namespace

void uiSnapshotInit(UiSnapshot* snapshot) {
  if (!snapshot) return;
  *snapshot = UiSnapshot{};
  snapshot->screen = Screen::Main;
  snapshot->trackCount = kMaxTracks;
  snapshot->stepCount = kMaxSteps;
  for (int t = 0; t < kMaxTracks; ++t) {
    std::snprintf(snapshot->tracks[t].name, sizeof(snapshot->tracks[t].name), "PART %d", t + 1);
    std::snprintf(snapshot->tracks[t].patch, sizeof(snapshot->tracks[t].patch), "PATCH %d", t + 1);
    snapshot->tracks[t].length = kMaxSteps;
  }
  for (int i = 0; i < kNumHints; ++i) {
    std::snprintf(snapshot->hints[i], sizeof(snapshot->hints[i]), "P%d", i + 1);
  }
}

void uiSnapshotDemo(UiSnapshot* snapshot, Screen screen) {
  if (!snapshot) return;
  uiSnapshotInit(snapshot);
  snapshot->screen = screen;
  std::snprintf(snapshot->page, sizeof(snapshot->page), "%s", screenName(screen));
  snapshot->bpm = 120.0f;
  snapshot->pattern = 1;
  snapshot->playing = true;
  std::snprintf(snapshot->status, sizeof(snapshot->status), "PLAY");
  snapshot->bar = 3;
  snapshot->activeStep = 7;
  snapshot->activeVoices = 6;
  snapshot->masterLevel = 0.72f;
  std::snprintf(snapshot->footer, sizeof(snapshot->footer),
                "16 bars demo | track mutes | p-lock on track 1");
  const char* patches[kMaxTracks] = {"FAT SAW", "FM BELL", "POLY VOX", "LADDER LEAD"};
  const float levels[kMaxTracks] = {0.72f, 0.48f, 0.61f, 0.37f};
  for (int t = 0; t < kMaxTracks; ++t) {
    UiTrack& track = snapshot->tracks[t];
    std::snprintf(track.name, sizeof(track.name), "PART %d", t + 1);
    std::snprintf(track.patch, sizeof(track.patch), "%s", patches[t]);
    track.active = (t != 3);
    track.muted = false;
    track.voices = 2 - (t % 2);
    track.currentStep = snapshot->activeStep;
    track.level = levels[t];
    track.peak = (t == 0) ? 0.95f : 0.5f;
    track.cutoff = 400.0f + 900.0f * static_cast<float>(t);
    track.pan = (t % 2 == 0) ? -0.35f : 0.35f;
    track.length = (t == 3) ? 12 : 16;
    for (int st = 0; st < kMaxSteps; ++st) {
      track.note[st] = static_cast<uint8_t>(48 + t * 12 + (st % 4) * 2);
      track.stepActive[st] = ((st + t) % 4) != 3;
    }
    track.stepPlocked[4] = true;
    track.stepPlocked[12] = true;
  }
  // One p-lock marker on track 1 step 5 (the vertical slice's single p-lock).
  snapshot->tracks[0].stepPlocked[4] = true;
  const char* labels[kNumParams] = {"CUTOFF", "RESONANCE", "ENV AMT", "DRIVE",
                                    "ATK",    "DEC",       "SUS",     "REL"};
  const char* values[kNumParams] = {"2.40k", "62%",  "+35%", "18%",
                                    "10ms",  "340ms", "65%",  "420ms"};
  const float norms[kNumParams] = {0.61f, 0.62f, 0.35f, 0.18f, 0.2f, 0.34f, 0.65f, 0.42f};
  for (int i = 0; i < kNumParams; ++i) {
    std::snprintf(snapshot->params[i].label, sizeof(snapshot->params[i].label), "%s", labels[i]);
    std::snprintf(snapshot->params[i].value, sizeof(snapshot->params[i].value), "%s", values[i]);
    snapshot->params[i].norm = norms[i];
  }
  const char* hintLabels[kNumHints] = {"CUTOFF", "RESON", "ENVAMT", "DRIVE",
                                       "ATK",    "DEC",   "SUS",    "REL"};
  for (int i = 0; i < kNumHints; ++i) {
    std::snprintf(snapshot->hints[i], sizeof(snapshot->hints[i]), "%s", hintLabels[i]);
  }
  snapshot->selectedParam = 1;
  if (screen == Screen::Modules) {
    snapshot->moduleCount = 4;
    std::snprintf(snapshot->modules[0], sizeof(snapshot->modules[0]), "DIODE DRIVE  v0.1");
    std::snprintf(snapshot->modules[1], sizeof(snapshot->modules[1]), "LFO MOD      v0.1");
    std::snprintf(snapshot->modules[2], sizeof(snapshot->modules[2]), "SOFT DELAY   builtin");
    std::snprintf(snapshot->modules[3], sizeof(snapshot->modules[3]), "SOFT CHORUS  builtin");
    std::snprintf(snapshot->moduleApi, sizeof(snapshot->moduleApi), "MODULE API v0 (EXP)");
    snapshot->selectedParam = 0;
    std::snprintf(snapshot->params[0].label, sizeof(snapshot->params[0].label), "DRIVE");
    std::snprintf(snapshot->params[0].value, sizeof(snapshot->params[0].value), "55%%");
    snapshot->params[0].norm = 0.55f;
    std::snprintf(snapshot->params[1].label, sizeof(snapshot->params[1].label), "TONE");
    std::snprintf(snapshot->params[1].value, sizeof(snapshot->params[1].value), "45%%");
    snapshot->params[1].norm = 0.45f;
    std::snprintf(snapshot->params[2].label, sizeof(snapshot->params[2].label), "MIX");
    std::snprintf(snapshot->params[2].value, sizeof(snapshot->params[2].value), "85%%");
    snapshot->params[2].norm = 0.85f;
    std::snprintf(snapshot->params[3].label, sizeof(snapshot->params[3].label), "STATE");
    std::snprintf(snapshot->params[3].value, sizeof(snapshot->params[3].value), "32B");
    snapshot->params[3].norm = 0.1f;
    for (int i = 4; i < kNumParams; ++i) {
      std::snprintf(snapshot->params[i].label, sizeof(snapshot->params[i].label), "SPARE%d", i);
      std::snprintf(snapshot->params[i].value, sizeof(snapshot->params[i].value), "--");
      snapshot->params[i].norm = 0.0f;
    }
  }
  if (screen == Screen::Mixer) {
    for (int i = 0; i < kNumParams; ++i) {
      const char* mixLabels[kNumParams] = {"DELAY", "FEEDBACK", "CHORUS", "CH DEPTH",
                                           "DRIVE", "CRUSH",    "LIMIT",  "MASTER"};
      const char* mixValues[kNumParams] = {"250ms", "35%", "0.4Hz", "40%",
                                           "18%",   "0%",  "95%",   "80%"};
      std::snprintf(snapshot->params[i].label, sizeof(snapshot->params[i].label), "%s",
                    mixLabels[i]);
      std::snprintf(snapshot->params[i].value, sizeof(snapshot->params[i].value), "%s",
                    mixValues[i]);
      snapshot->params[i].norm = 0.25f + 0.08f * static_cast<float>(i);
    }
  }
  if (screen == Screen::Sequencer) {
    snapshot->tracks[0].stepPlocked[4] = true;
    snapshot->tracks[0].stepPlocked[12] = true;
    snapshot->tracks[2].muted = true;
    const char* seqLabels[kNumParams] = {"MODE", "LEN", "SWING", "TRANSPOSE",
                                         "PLOCK", "COND", "MICRO", "TEMPO"};
    const char* seqValues[kNumParams] = {"FWD", "16", "54%", "0",
                                         "1",   "1ST", "+0",  "120"};
    for (int i = 0; i < kNumParams; ++i) {
      std::snprintf(snapshot->params[i].label, sizeof(snapshot->params[i].label), "%s",
                    seqLabels[i]);
      std::snprintf(snapshot->params[i].value, sizeof(snapshot->params[i].value), "%s",
                    seqValues[i]);
      snapshot->params[i].norm = 0.4f + 0.05f * static_cast<float>(i);
    }
  }
}

void drawTextScaled(ICanvas& canvas, int x, int y, const char* text, uint16_t color, int scale) {
  if (!text || scale <= 0) return;
  int cx = x;
  for (const char* p = text; *p; ++p) {
    char c = *p;
    if (c < 32 || c > 127) c = '?';
    const uint8_t* glyph = kFont6x8[static_cast<int>(c) - 32];
    for (int row = 0; row < kFontHeight; ++row) {
      const uint8_t bits = glyph[row];
      for (int col = 0; col < kFontWidth; ++col) {
        if (bits & (1u << col)) {
          canvas.fillRect(cx + col * scale, y + row * scale, scale, scale, color);
        }
      }
    }
    cx += kFontWidth * scale;
  }
}

void drawUi800(ICanvas& canvas, const UiSnapshot& s) {
  canvas.fillRect(0, 0, canvas.width(), canvas.height(), kBg);
  drawHeader(canvas, s);
  if (s.screen == Screen::Sequencer) {
    drawSequencerGrid(canvas, s);
  } else if (s.screen == Screen::Mixer) {
    drawMixer(canvas, s);
  } else if (s.screen == Screen::Modules) {
    drawModulesScreen(canvas, s);
  } else {
    drawTracks(canvas, s);
  }
  drawParamPanel(canvas, s);
  drawHints(canvas, s);
  drawFooter(canvas, s);
}

// --- Framebuffer800 --------------------------------------------------------
Framebuffer800::Framebuffer800() {
#if defined(ESP32)
  pixels_ = static_cast<uint16_t*>(heap_caps_malloc(
      static_cast<size_t>(kUiWidth) * kUiHeight * sizeof(uint16_t), MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!pixels_) {
    pixels_ = static_cast<uint16_t*>(
        heap_caps_malloc(static_cast<size_t>(kUiWidth) * kUiHeight * sizeof(uint16_t), MALLOC_CAP_8BIT));
  }
#else
  pixels_ = new (std::nothrow) uint16_t[static_cast<size_t>(kUiWidth) * kUiHeight];
#endif
  if (pixels_) clear(colors::kBlack);
}

Framebuffer800::~Framebuffer800() {
#if defined(ESP32)
  if (pixels_) heap_caps_free(pixels_);
#else
  delete[] pixels_;
#endif
  pixels_ = nullptr;
}

void Framebuffer800::clear(uint16_t color) {
  if (!pixels_) return;
  const size_t count = static_cast<size_t>(kUiWidth) * kUiHeight;
  for (size_t i = 0; i < count; ++i) pixels_[i] = color;
}

void Framebuffer800::fillRect(int x, int y, int w, int h, uint16_t color) {
  if (!pixels_) return;
  int x0 = x < 0 ? 0 : x;
  int y0 = y < 0 ? 0 : y;
  int x1 = x + w;
  int y1 = y + h;
  if (x1 > kUiWidth) x1 = kUiWidth;
  if (y1 > kUiHeight) y1 = kUiHeight;
  for (int yy = y0; yy < y1; ++yy) {
    uint16_t* row = pixels_ + static_cast<size_t>(yy) * kUiWidth;
    for (int xx = x0; xx < x1; ++xx) row[xx] = color;
  }
}

void Framebuffer800::drawPixel(int x, int y, uint16_t color) {
  if (!pixels_ || x < 0 || y < 0 || x >= kUiWidth || y >= kUiHeight) return;
  pixels_[static_cast<size_t>(y) * kUiWidth + x] = color;
}

void Framebuffer800::drawChar(int x, int y, char c, uint16_t color) {
  if (c < 32 || c > 127) c = '?';
  const uint8_t* glyph = kFont6x8[static_cast<int>(c) - 32];
  for (int row = 0; row < kFontHeight; ++row) {
    for (int col = 0; col < kFontWidth; ++col) {
      if (glyph[row] & (1u << col)) drawPixel(x + col, y + row, color);
    }
  }
}

uint16_t Framebuffer800::at(int x, int y) const {
  if (!pixels_ || x < 0 || y < 0 || x >= kUiWidth || y >= kUiHeight) return 0;
  return pixels_[static_cast<size_t>(y) * kUiWidth + x];
}

bool Framebuffer800::writePpm(const char* path) const {
  if (!path || !pixels_) return false;
  FILE* f = std::fopen(path, "wb");
  if (!f) return false;
  std::fprintf(f, "P6\n%d %d\n255\n", kUiWidth, kUiHeight);
  // Buffer a row at a time to keep stack usage small on MCUs.
  uint8_t row[kUiWidth * 3];
  for (int y = 0; y < kUiHeight; ++y) {
    for (int x = 0; x < kUiWidth; ++x) {
      const uint16_t c = pixels_[static_cast<size_t>(y) * kUiWidth + x];
      const uint8_t r5 = static_cast<uint8_t>((c >> 11) & 0x1F);
      const uint8_t g6 = static_cast<uint8_t>((c >> 5) & 0x3F);
      const uint8_t b5 = static_cast<uint8_t>(c & 0x1F);
      row[x * 3 + 0] = static_cast<uint8_t>((r5 << 3) | (r5 >> 2));
      row[x * 3 + 1] = static_cast<uint8_t>((g6 << 2) | (g6 >> 4));
      row[x * 3 + 2] = static_cast<uint8_t>((b5 << 3) | (b5 >> 2));
    }
    if (std::fwrite(row, 1, sizeof(row), f) != sizeof(row)) {
      std::fclose(f);
      return false;
    }
  }
  std::fclose(f);
  return true;
}

}  // namespace ui
}  // namespace bukifon
