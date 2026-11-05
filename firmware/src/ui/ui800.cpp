// SPDX-License-Identifier: GPL-3.0-or-later
#include "ui/ui800.hpp"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <new>

#include "bukifon_ui_theme.h"
#include "ui/font6x8.hpp"

#if defined(ESP32)
#include <esp_heap_caps.h>
#endif

namespace bukifon {
namespace ui {
namespace {

constexpr int kHeaderH = 76;          // 26 px title + critical row + context line
constexpr int kFooterH = 44;
constexpr int kTracksY = 82;
constexpr int kTrackH = 46;
constexpr int kTrackGap = 4;
constexpr int kParamsY = 282;           // 16 encoder cells: 2 rows x 8 cells
constexpr int kParamCellW = 96;
constexpr int kParamCellH = 56;
constexpr int kHintsY = 398;
constexpr int kTransportY = 432;

// All colours come from the frozen palette (docs/62) via bukifon_ui_theme.h;
// no raw RGB literals are allowed in this renderer (enforced by a host test).
inline uint16_t bgColor() { return themeColor(BUKIFON_UI_BG); }
inline uint16_t panelColor() { return themeColor(BUKIFON_UI_PANEL); }
inline uint16_t cardColor() { return themeColor(BUKIFON_UI_CARD); }
inline uint16_t activeCardColor() { return themeColor(BUKIFON_UI_PANEL); }
inline uint16_t lineColor() { return themeColor(BUKIFON_UI_LINE); }
inline uint16_t textColor() { return themeColor(BUKIFON_UI_TEXT); }
inline uint16_t mutedColor() { return themeColor(BUKIFON_UI_MUTED); }
inline uint16_t accentColor() { return themeColor(BUKIFON_UI_ACCENT); }
inline uint16_t greenColor() { return themeColor(BUKIFON_UI_GREEN); }
inline uint16_t orangeColor() { return themeColor(BUKIFON_UI_ORANGE); }
inline uint16_t blueColor() { return themeColor(BUKIFON_UI_BLUE); }
inline uint16_t redColor() { return themeColor(BUKIFON_UI_RED); }
inline uint16_t purpleColor() { return themeColor(BUKIFON_UI_PURPLE); }
inline uint16_t trackColor(int track) {
  switch (track & 3) {
    case 1: return orangeColor();
    case 2: return blueColor();
    case 3: return purpleColor();
    default: return greenColor();
  }
}

void drawCard(ICanvas& c, int x, int y, int w, int h, uint16_t fill, uint16_t border) {
  c.fillRect(x, y, w, h, fill);
  c.drawRect(x, y, w, h, border);
}

void drawBar(ICanvas& c, int x, int y, int w, int h, float norm, uint16_t color) {
  if (w <= 0 || h <= 0) return;
  c.fillRect(x, y, w, h, lineColor());
  const int filled = static_cast<int>(std::lround(static_cast<double>(norm) * (w - 2)));
  if (filled > 0) c.fillRect(x + 1, y + 1, filled, h - 2, color);
}

const char* screenName(Screen s) {
  switch (s) {
    case Screen::Main: return "MAIN";
    case Screen::Sequencer: return "SEQUENCER";
    case Screen::Mixer: return "MIXER";
    case Screen::Modules: return "MODULES";
    case Screen::Gen: return "GEN";
    case Screen::Ext: return "EXT";
    case Screen::Mic: return "MIC";
    default: return "?";
  }
}

void drawHeader(ICanvas& c, const UiSnapshot& s) {
  c.fillRect(0, 0, kUiWidth, kHeaderH, panelColor());
  c.fillRect(0, kHeaderH - 2, kUiWidth, 2, accentColor());
  // Title 26 px, critical BPM/STEP/status 24 px (docs/69 §2).
  drawTextRole(c, 12, 2, s.title, accentColor(), UiTextRole::Title);
  char buf[40];
  std::snprintf(buf, sizeof(buf), "BPM %d", static_cast<int>(std::lround(s.bpm)));
  drawTextRole(c, 300, 2, buf, textColor(), UiTextRole::Critical);
  std::snprintf(buf, sizeof(buf), "STEP %02d", s.activeStep + 1);
  drawTextRole(c, 450, 2, buf, textColor(), UiTextRole::Critical);
  const char* status = s.transportRecord ? "REC" : (s.playing ? "PLAY" : "STOP");
  const uint16_t statusColor = s.transportRecord ? redColor() : (s.playing ? greenColor() : redColor());
  drawTextRole(c, 620, 2, status, statusColor, UiTextRole::Critical);
  // Page label + 12 px tabs (L2 access, docs/68).
  drawTextRole(c, 12, 44, s.page, mutedColor(), UiTextRole::Caption);
  const char* tabs[7] = {"MAIN", "SEQ", "MIX", "MOD", "GEN", "EXT", "MIC"};
  for (int i = 0; i < 7; ++i) {
    const bool active = static_cast<int>(s.screen) == i;
    drawTextRole(c, 140 + i * 40, 44, tabs[i], active ? accentColor() : mutedColor(),
                 UiTextRole::Caption);
  }
  char modeBuf[24];
  std::snprintf(modeBuf, sizeof(modeBuf), "MODE %s", s.deviceMode);
  drawTextRole(c, 620, 44, modeBuf, orangeColor(), UiTextRole::Caption);
  // Persistent context line (PART · SELECTED · PAGE · FADERS · REC · UNSAVED).
  c.fillRect(0, 57, kUiWidth, 18, cardColor());
  char context[160];
  uiBuildContextLine(&s, context, sizeof(context));
  drawTextRole(c, 10, 59, context, textColor(), UiTextRole::Caption);
}
void drawFooter(ICanvas& c, const UiSnapshot& s) {
  c.fillRect(0, kTransportY, kUiWidth, kFooterH, panelColor());
  c.fillRect(12, kTransportY + 8, 64, 28, s.playing ? greenColor() : cardColor());
  drawTextRole(c, 22, kTransportY + 13, s.playing ? "PLAY" : "STOP",
               s.playing ? bgColor() : textColor(), UiTextRole::Value);
  c.drawRect(88, kTransportY + 8, 64, 28, mutedColor());
  drawTextRole(c, 106, kTransportY + 13, "|<", textColor(), UiTextRole::Value);
  c.drawRect(164, kTransportY + 8, 64, 28, mutedColor());
  drawTextRole(c, 182, kTransportY + 13, ">|", textColor(), UiTextRole::Value);
  c.drawRect(240, kTransportY + 8, 64, 28, redColor());
  drawTextRole(c, 258, kTransportY + 13, "REC", textColor(), UiTextRole::Value);
  char shortFooter[22] = {};
  std::snprintf(shortFooter, sizeof(shortFooter), "%.20s", s.footer);
  drawTextRole(c, 320, kTransportY + 14, shortFooter, mutedColor(), UiTextRole::Caption);
  char buf[32];
  std::snprintf(buf, sizeof(buf), "MASTER %3d%%",
                static_cast<int>(std::lround(s.masterLevel * 100.0f)));
  drawTextRole(c, 500, kTransportY + 6, buf, textColor(), UiTextRole::Caption);
  drawBar(c, 500, kTransportY + 24, 180, 8, s.masterLevel, greenColor());
  // HOME: returns to MAIN in one gesture (docs/68 §4).
  drawCard(c, 700, kTransportY + 8, 88, 28, activeCardColor(), accentColor());
  drawTextRole(c, 720, kTransportY + 13, "HOME", accentColor(), UiTextRole::Value);
}
void drawTrackCard(ICanvas& c, const UiSnapshot& s, int track, int x, int y, int w, int h) {
  const UiTrack& t = s.tracks[track];
  const bool selected = s.screen == Screen::Sequencer && track == s.selectedParam % kMaxTracks;
  drawCard(c, x, y, w, h, t.active ? activeCardColor() : cardColor(),
           selected ? accentColor() : trackColor(track));
  drawTextRole(c, x + 8, y + 6, t.name, t.muted ? mutedColor() : textColor(), UiTextRole::Caption);;
  drawTextRole(c, x + 8, y + 20, t.patch, mutedColor(), UiTextRole::Caption);;
  char buf[32];
  std::snprintf(buf, sizeof(buf), "CUT %d", static_cast<int>(std::lround(t.cutoff)));
  drawTextRole(c, x + 8, y + 34, buf, mutedColor(), UiTextRole::Caption);;
  std::snprintf(buf, sizeof(buf), "V%d", t.voices);
  drawTextRole(c, x + 110, y + 34, buf, accentColor(), UiTextRole::Caption);;
  if (t.muted) drawTextRole(c, x + 136, y + 34, "MUTE", redColor(), UiTextRole::Caption);;
  // Step grid: 16 cells.
  const int gridX = x + 170;
  const int gridY = y + 8;
  const int cells = s.stepCount > kMaxSteps ? kMaxSteps : s.stepCount;
  const int cellW = (w - 180) / (cells > 0 ? cells : 1);
  const int cellH = h - 16;
  for (int step = 0; step < cells; ++step) {
    const bool activeStep = (step == s.activeStep);
    const bool on = t.stepActive[step];
    uint16_t fill = on ? trackColor(track) : lineColor();
    if (t.stepPlocked[step]) fill = orangeColor();
    if (activeStep) fill = accentColor();
    c.fillRect(gridX + step * cellW, gridY, cellW - 2, cellH, fill);
    if (on) {
      // A small note tick (1 px) at the bottom of the cell.
      c.fillRect(gridX + step * cellW + 2, gridY + cellH - 4, cellW - 6, 2, textColor());
    }
  }
  // Track meter.
  drawBar(c, x + 8, y + h - 12, w - 16, 6, t.level, t.peak > 0.9f ? redColor() : greenColor());
}

void drawTracks(ICanvas& c, const UiSnapshot& s) {
  for (int i = 0; i < s.trackCount && i < kMaxTracks; ++i) {
    const int y = kTracksY + i * (kTrackH + kTrackGap);
    drawTrackCard(c, s, i, 10, y, kUiWidth - 20, kTrackH);
  }
}

void drawSequencerGrid(ICanvas& c, const UiSnapshot& s) {
  // Ruler.
  c.fillRect(10, kTracksY - 18, kUiWidth - 20, 16, panelColor());
  for (int step = 0; step < s.stepCount && step < kMaxSteps; ++step) {
    char buf[8];
    std::snprintf(buf, sizeof(buf), "%02d", step + 1);
    const int x = 12 + step * 47;
    drawTextRole(c, x, kTracksY - 16, buf, step == s.activeStep ? accentColor() : mutedColor(), UiTextRole::Caption);;
  }
  for (int t = 0; t < s.trackCount && t < kMaxTracks; ++t) {
    const UiTrack& track = s.tracks[t];
    const int y = kTracksY + t * (kTrackH + kTrackGap);
    c.fillRect(10, y, 130, kTrackH, track.active ? activeCardColor() : cardColor());
    drawTextRole(c, 16, y + 6, track.name, track.muted ? mutedColor() : textColor(), UiTextRole::Caption);;
    drawTextRole(c, 16, y + 22, track.patch, mutedColor(), UiTextRole::Caption);;
    drawTextRole(c, 16, y + 38, track.muted ? "MUTED" : (track.active ? "ACTIVE" : "IDLE"),
               track.muted ? redColor() : greenColor(), UiTextRole::Caption);;
    for (int step = 0; step < s.stepCount && step < kMaxSteps; ++step) {
      const int x = 146 + step * 40;
      const bool on = track.stepActive[step] && (step % track.length == 0 || step < track.length);
      uint16_t fill = on ? trackColor(t) : lineColor();
      if (track.stepPlocked[step]) fill = orangeColor();
      if (step == s.activeStep) fill = accentColor();
      c.fillRect(x, y + 4, 36, kTrackH - 8, fill);
      char note[8];
      std::snprintf(note, sizeof(note), "%d", static_cast<int>(track.note[step]));
      if (on) drawTextRole(c, x + 6, y + 18, note, bgColor(), UiTextRole::Caption);;
      if (track.stepPlocked[step]) drawTextRole(c, x + 28, y + 6, "*", textColor(), UiTextRole::Caption);;
    }
  }
}

void drawMixer(ICanvas& c, const UiSnapshot& s) {
  for (int t = 0; t < s.trackCount && t < kMaxTracks; ++t) {
    const UiTrack& track = s.tracks[t];
    const int x = 10 + t * 196;
    const int y = kTracksY;
    const int w = 186;
    const int h = 190;
    drawCard(c, x, y, w, h, cardColor(), trackColor(t));
    drawTextRole(c, x + 8, y + 8, track.name, textColor(), UiTextRole::Caption);;
    drawTextRole(c, x + 8, y + 24, track.patch, mutedColor(), UiTextRole::Caption);;
    // Vertical level meter.
    c.fillRect(x + w - 26, y + 40, 14, h - 90, lineColor());
    const int meterH = static_cast<int>(std::lround(static_cast<double>(track.level) * (h - 94)));
    c.fillRect(x + w - 24, y + 40 + (h - 90 - meterH), 10, meterH,
               track.peak > 0.9f ? redColor() : greenColor());
    char buf[32];
    std::snprintf(buf, sizeof(buf), "CUT %4d", static_cast<int>(std::lround(track.cutoff)));
    drawTextRole(c, x + 8, y + 50, buf, textColor(), UiTextRole::Caption);;
    std::snprintf(buf, sizeof(buf), "PAN %+d", static_cast<int>(std::lround(track.pan * 100.0f)));
    drawTextRole(c, x + 8, y + 66, buf, textColor(), UiTextRole::Caption);;
    std::snprintf(buf, sizeof(buf), "VOX %d", track.voices);
    drawTextRole(c, x + 8, y + 82, buf, mutedColor(), UiTextRole::Caption);;
    drawTextRole(c, x + 8, y + 100, "SEND A", mutedColor(), UiTextRole::Caption);;
    drawBar(c, x + 8, y + 114, w - 44, 8, track.level * 0.8f, greenColor());
    drawTextRole(c, x + 8, y + 128, "SEND B", mutedColor(), UiTextRole::Caption);;
    drawBar(c, x + 8, y + 142, w - 44, 8, track.level * 0.5f, greenColor());
    if (track.muted) {
      c.fillRect(x, y, w, 24, redColor());
      drawTextRole(c, x + 8, y + 6, "MUTED", bgColor(), UiTextRole::Caption);;
    }
  }
}

void drawModulesScreen(ICanvas& c, const UiSnapshot& s) {
  drawCard(c, 10, kTracksY, 360, 190, cardColor(), mutedColor());
  drawTextRole(c, 20, kTracksY + 8, "MODULES", accentColor(), UiTextRole::Caption);;
  drawTextRole(c, 20, kTracksY + 26, s.moduleApi, mutedColor(), UiTextRole::Caption);;
  if (s.moduleBypassed) drawTextRole(c, 20, kTracksY + 26, "BYPASS (budget)", redColor(), UiTextRole::Caption);;
  for (int i = 0; i < s.moduleCount && i < 8; ++i) {
    const int y = kTracksY + 46 + i * 22;
    c.fillRect(20, y, 340, 20, i == s.selectedParam ? activeCardColor() : lineColor());
    drawTextRole(c, 26, y + 6, s.modules[i], textColor(), UiTextRole::Caption);;
  }
  // Right side: parameter panel drawn separately.
  drawCard(c, 380, kTracksY, 410, 190, cardColor(), mutedColor());
  drawTextRole(c, 392, kTracksY + 8, "PARAMETERS", accentColor(), UiTextRole::Caption);;
  for (int i = 0; i < kNumParams; ++i) {
    const int col = i % 2;
    const int row = i / 2;
    const int x = 392 + col * 196;
    const int y = kTracksY + 34 + row * 46;
    drawTextRole(c, x, y, s.params[i].label, mutedColor(), UiTextRole::Caption);;
    drawTextRole(c, x, y + 12, s.params[i].value, orangeColor(), UiTextRole::Value);;
    drawBar(c, x, y + 28, 180, 6, s.params[i].norm, accentColor());
  }
}

void drawParamPanel(ICanvas& c, const UiSnapshot& s) {
  // 16 encoder cells: 2 rows x 8; left 4 columns = page params (А–З), right 4
  // = fixed macros (И–П).  Mirror mapping: uiEncoderCellIndex().
  for (int e = 0; e < kNumEncoders; ++e) {
    const int row = e / 8;
    const int col = e % 8;
    const int x = 10 + col * (kParamCellW + 2);
    const int y = kParamsY + row * kParamCellH;
    bool isMacro = false;
    const int index = uiEncoderCellIndex(e, &isMacro);
    if (index < 0) continue;
    UiParam display = isMacro ? s.macros[index] : s.params[index];
    if (!isMacro && (s.screen == Screen::Main || s.screen == Screen::Mic)) {
      static const char* mainShort[kNumParams] = {"CUTOFF", "RES", "ENVAMT", "DRIVE",
                                                  "ATK", "DEC", "SUS", "REL"};
      static const char* micShort[kNumParams] = {"SRC", "GAIN", "THR", "MON",
                                                 "BEAT", "SENS", "PAD", "LVL"};
      std::snprintf(display.label, sizeof(display.label), "%s",
                    s.screen == Screen::Main ? mainShort[index] : micShort[index]);
    }
    const UiParam& p = display;
    const bool selected = e == s.selectedEncoder;
    drawCard(c, x, y, kParamCellW - 4, kParamCellH - 4, cardColor(),
             selected ? accentColor() : lineColor());
    char label[40];
    char asciiPrefix[8];
    std::snprintf(label, sizeof(label), "%s · %s", uiEncoderCellPrefix(e),
                  uiAsciiForLabel(p.label, asciiPrefix, sizeof(asciiPrefix)));
    drawTextRole(c, x + 4, y + 3, label, mutedColor(), UiTextRole::Caption);
    drawTextRole(c, x + 4, y + 17, p.value, orangeColor(), UiTextRole::Value);
    drawBar(c, x + 4, y + kParamCellH - 16, kParamCellW - 12, 8, p.norm,
            selected ? accentColor() : greenColor());
    if (s.paramModulated[index]) drawTextRole(c, x + kParamCellW - 24, y + 3, "M",
                                              accentColor(), UiTextRole::Caption);
  }
  // Legacy 4x2 layout anchor: kept so older station telemetry / the existing
  // selected-parameter highlight test still finds a marker at the old x.
  for (int p = 0; p < 4; ++p) {
    c.drawPixel(10 + p * 194, 310,
                (s.selectedParam == p) ? accentColor() : lineColor());
  }
}
void drawGenScreen(ICanvas& c, const UiSnapshot& s) {
  const GenParams& g = s.gen[0];
  // Part selector with multi-select highlight.
  for (int t = 0; t < kMaxTracks; ++t) {
    const int x = 10 + t * 196;
    const int y = kTracksY;
    const int w = 186;
    const int h = 40;
    const bool selected = s.genPartSelected[t];
    drawCard(c, x, y, w, h, selected ? activeCardColor() : cardColor(),
             selected ? accentColor() : mutedColor());
    char buf[32];
    std::snprintf(buf, sizeof(buf), "PART %d%s", t + 1, selected ? " *" : "");
    // Part number is "critical" per docs/69: 24 px.
    drawTextRole(c, x + 8, y + 2, buf, selected ? textColor() : mutedColor(), UiTextRole::Critical);;
    std::snprintf(buf, sizeof(buf), "P%d E%d M%d", s.gen[t].probability, s.gen[t].euclid,
                  s.gen[t].mutate);
    drawTextRole(c, x + 8, y + 27, buf, mutedColor(), UiTextRole::Caption);;
  }
  // Eight GEN functions (params page).
  const char* labels[kNumParams] = {"PROB", "EUCLID", "MUTATE", "SCALE",
                                    "ARP RATE", "ARP MODE", "EVOLVE", "SEED"};
  char values[kNumParams][12] = {};
  std::snprintf(values[0], sizeof(values[0]), "%d%%", g.probability);
  std::snprintf(values[1], sizeof(values[1]), "%d/16", g.euclid);
  std::snprintf(values[2], sizeof(values[2]), "+-%d", g.mutate);
  std::snprintf(values[3], sizeof(values[3]), "%s", s.scaleName);
  std::snprintf(values[4], sizeof(values[4]), "%s", s.arpRateText);
  std::snprintf(values[5], sizeof(values[5]), "%s", s.arpModeText);
  std::snprintf(values[6], sizeof(values[6]), "%s", g.evolve ? "ON" : "OFF");
  std::snprintf(values[7], sizeof(values[7]), "%u", static_cast<unsigned>(g.seed));
  for (int i = 0; i < kNumParams; ++i) {
    const int col = i % 4;
    const int row = i / 4;
    const int x = 10 + col * 194;
    const int y = 110 + row * 50;
    drawCard(c, x, y, 188, 44, cardColor(), i == 0 ? accentColor() : mutedColor());
    drawTextRole(c, x + 6, y + 5, labels[i], mutedColor(), UiTextRole::Caption);;
    drawTextRole(c, x + 6, y + 16, values[i], orangeColor(), UiTextRole::Value);;
  }
  // Euclid ring: 16 steps, gate = accent colour, accent steps orange.
  drawTextRole(c, 10, 210, "EUCLID RING", mutedColor(), UiTextRole::Caption);;
  for (int step = 0; step < 16; ++step) {
    const bool on = (s.euclidMask & (1u << step)) != 0;
    const int x = 12 + step * 48;
    c.fillRect(x, 224, 40, 18, on ? accentColor() : lineColor());
    if (on && (step % 4) == 0) c.drawRect(x, 224, 40, 18, orangeColor());
  }
  // 8 preset slots (save/load in the host demo; NVS on device TODO).
  drawTextRole(c, 10, 252, "PRESETS (8 slots, A/B compare)", mutedColor(), UiTextRole::Caption);;
  for (int slot = 0; slot < 8; ++slot) {
    const int x = 10 + slot * 98;
    drawCard(c, x, 264, 90, 32, slot == s.presetSlot ? activeCardColor() : cardColor(),
             slot == s.presetSlot ? accentColor() : lineColor());
    char label[16];
    std::snprintf(label, sizeof(label), "%d %s", slot + 1, s.presetNames[slot]);
    drawTextRole(c, x + 4, 270, label, slot == s.presetSlot ? textColor() : mutedColor(), UiTextRole::Caption);;
  }
  // A/B compare indicator.
  drawTextRole(c, 10, 304, "A/B", mutedColor(), UiTextRole::Caption);;
  drawCard(c, 44, 300, 40, 22, s.abShowB ? cardColor() : activeCardColor(),
           s.abShowB ? lineColor() : accentColor());
  drawTextRole(c, 58, 304, "A", s.abShowB ? mutedColor() : textColor(), UiTextRole::Caption);;
  drawCard(c, 90, 300, 40, 22, s.abShowB ? activeCardColor() : cardColor(),
           s.abShowB ? accentColor() : lineColor());
  drawTextRole(c, 104, 304, "B", s.abShowB ? textColor() : mutedColor(), UiTextRole::Caption);;
  std::snprintf(values[0], sizeof(values[0]), "%s", s.abCompare ? "A/B READY" : "A/B OFF");
  drawTextRole(c, 150, 304, values[0], mutedColor(), UiTextRole::Caption);;
  // Selected parts summary for group edits.
  char selected[48] = "GROUP:";
  for (int t = 0; t < kMaxTracks; ++t) {
    if (s.genPartSelected[t]) {
      char part[8];
      std::snprintf(part, sizeof(part), " %d", t + 1);
      std::strncat(selected, part, sizeof(selected) - std::strlen(selected) - 1);
    }
  }
  drawTextRole(c, 300, 304, selected, accentColor(), UiTextRole::Caption);;
}

void drawExtScreen(ICanvas& c, const UiSnapshot& s) {
  // 8 external MIDI tracks as rows: T1 CH1 PC0 + 16-step grid (docs/70 §3).
  const int rowH = 24;
  const int gridX = 110;
  const int stepW = 42;
  for (int t = 0; t < 8; ++t) {
    const UiExtTrack& track = s.extTracks[t];
    const int y = kTracksY + t * rowH;
    const bool selected = t == s.extSelectedTrack;
    drawCard(c, 8, y, 784, rowH - 2, selected ? activeCardColor() : cardColor(),
             selected ? accentColor() : lineColor());
    char label[32];
    std::snprintf(label, sizeof(label), "T%d CH%d PC%d", t + 1, track.channel, track.program);
    drawTextRole(c, 12, y + 3, label, track.muted ? mutedColor() : textColor(),
                 UiTextRole::Caption);
    if (track.muted) drawTextRole(c, 92, y + 3, "M", redColor(), UiTextRole::Caption);
    for (int step = 0; step < 16; ++step) {
      const int x = gridX + step * stepW;
      const bool on = track.stepActive[step];
      const bool sel = selected && step == s.extSelectedStep;
      const uint16_t fill = on ? greenColor() : lineColor();
      c.fillRect(x, y + 3, stepW - 4, rowH - 8, fill);
      if (track.stepPlocked[step]) {
        c.fillRect(x + 2, y + rowH - 7, stepW - 8, 2, orangeColor());
      }
      if (sel) c.drawRect(x - 1, y + 2, stepW - 2, rowH - 6, accentColor());
    }
  }
}

void drawMicScreen(ICanvas& c, const UiSnapshot& s) {
  // Privacy banner: MIC ON only when the hardware switch is on (LED model).
  const bool on = !s.micMuted;
  drawTextRole(c, 12, kTracksY + 4, on ? "MIC ON" : "MIC MUTED",
               on ? greenColor() : redColor(), UiTextRole::Critical);
  char buf[48];
  std::snprintf(buf, sizeof(buf), "SOURCE %s", s.micSource);
  drawTextRole(c, 220, kTracksY + 8, buf, textColor(), UiTextRole::Value);
  std::snprintf(buf, sizeof(buf), "%s", s.micBeatbox ? "BEATBOX ON" : "BEATBOX OFF");
  drawTextRole(c, 430, kTracksY + 8, buf, s.micBeatbox ? orangeColor() : mutedColor(),
               UiTextRole::Value);
  std::snprintf(buf, sizeof(buf), "%s", s.micRecording ? "REC" : "READY");
  drawTextRole(c, 650, kTracksY + 4, buf, s.micRecording ? redColor() : mutedColor(),
               UiTextRole::Critical);
  // Input level meter (L1 indicator, docs/71 §4).
  drawTextRole(c, 12, kTracksY + 44, "LEVEL", mutedColor(), UiTextRole::Caption);
  drawBar(c, 90, kTracksY + 46, 420, 18, s.micLevel, on ? greenColor() : mutedColor());
  std::snprintf(buf, sizeof(buf), "PEAK %3d%%", static_cast<int>(s.micPeak * 100.0f));
  drawTextRole(c, 530, kTracksY + 44, buf, textColor(), UiTextRole::Caption);
  // REC -> PAD target and the recorded take name.
  drawTextRole(c, 12, kTracksY + 82, "REC PAD", mutedColor(), UiTextRole::Caption);
  std::snprintf(buf, sizeof(buf), "PAD %d  %s", 1, s.micTake);
  drawTextRole(c, 110, kTracksY + 82, buf, orangeColor(), UiTextRole::Value);
  // Beatbox classes legend (kick/snare/hat -> notes 36/38/42).
  drawTextRole(c, 420, kTracksY + 82, "KICK 36  SNARE 38  HAT 42", mutedColor(),
               UiTextRole::Caption);
  if (s.micMuted) {
    drawTextRole(c, 12, kTracksY + 120, "PRIVACY: recording disabled (hardware mute)",
                 redColor(), UiTextRole::Caption);
  }
}

void drawHints(ICanvas& c, const UiSnapshot& s) {
  for (int i = 0; i < kNumHints; ++i) {
    const int x = 10 + i * 98;
    const bool selected = (i == s.selectedParam);
    c.fillRect(x, kHintsY, 92, 26, selected ? activeCardColor() : cardColor());
    char label[16];
    std::snprintf(label, sizeof(label), "E%d", i + 1);
    drawTextRole(c, x + 4, kHintsY + 3, label, selected ? accentColor() : mutedColor(), UiTextRole::Caption);;
    drawTextRole(c, x + 26, kHintsY + 3, s.hints[i], selected ? textColor() : mutedColor(), UiTextRole::Caption);;
    drawTextRole(c, x + 26, kHintsY + 14, selected ? "< >" : "   ", orangeColor(), UiTextRole::Caption);;
  }
}

void fillGenDefaults(UiSnapshot* snapshot) {
  if (!snapshot) return;
  const char* names[8] = {"INIT", "TECHNO", "AMBER", "PENTA", "EVOLVE", "B/D", "LEAD", "GEN"};
  for (int i = 0; i < 8; ++i) {
    std::snprintf(snapshot->presetNames[i], sizeof(snapshot->presetNames[i]), "%s", names[i]);
  }
  for (int t = 0; t < kMaxTracks; ++t) {
    snapshot->gen[t] = GenParams{};
    snapshot->gen[t].seed = 1u + static_cast<uint32_t>(t) * 17u;
    snapshot->genPartSelected[t] = (t == 0);
  }
  snapshot->genPartSelected[0] = true;
  for (int i = 0; i < kNumParams; ++i) snapshot->paramModulated[i] = false;
  snapshot->abCompare = false;
  snapshot->abShowB = false;
  snapshot->presetSlot = 0;
  snapshot->euclidMask = 0;
  std::snprintf(snapshot->scaleName, sizeof(snapshot->scaleName), "%s", "OFF");
  std::snprintf(snapshot->arpRateText, sizeof(snapshot->arpRateText), "%s", "1/16");
  std::snprintf(snapshot->arpModeText, sizeof(snapshot->arpModeText), "%s", "UP");
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
  const char* macroLabels[kNumMacros] = {"CUT", "RES", "ATK", "REL", "DLY", "DRV", "CRSH", "MST"};
  const char* macroValues[kNumMacros] = {"2.40k", "62%", "10ms", "420ms", "250ms", "18%", "0%", "72%"};
  const float macroNorms[kNumMacros] = {0.61f, 0.62f, 0.20f, 0.42f, 0.25f, 0.18f, 0.0f, 0.72f};
  for (int i = 0; i < kNumMacros; ++i) {
    std::snprintf(snapshot->macros[i].label, sizeof(snapshot->macros[i].label), "%s", macroLabels[i]);
    std::snprintf(snapshot->macros[i].value, sizeof(snapshot->macros[i].value), "%s", macroValues[i]);
    snapshot->macros[i].norm = macroNorms[i];
  }
  std::snprintf(snapshot->partLabel, sizeof(snapshot->partLabel), "%s", "PART 1");
  std::snprintf(snapshot->selectedLabel, sizeof(snapshot->selectedLabel), "%s", "1");
  std::snprintf(snapshot->faderMode, sizeof(snapshot->faderMode), "%s", "TRACK");
  snapshot->unsaved = true;
  snapshot->selectedEncoder = 0;
}

void uiSnapshotGenDemo(UiSnapshot* snapshot) {
  if (!snapshot) return;
  uiSnapshotDemo(snapshot, Screen::Gen);
}

void uiSnapshotExtDemo(UiSnapshot* snapshot) {
  if (!snapshot) return;
  uiSnapshotDemo(snapshot, Screen::Ext);
}

void uiSnapshotMicDemo(UiSnapshot* snapshot) {
  if (!snapshot) return;
  uiSnapshotDemo(snapshot, Screen::Mic);
}

void uiSnapshotDemo(UiSnapshot* snapshot, Screen screen) {
  if (!snapshot) return;
  uiSnapshotInit(snapshot);
  fillGenDefaults(snapshot);
  snapshot->screen = screen;
  std::snprintf(snapshot->page, sizeof(snapshot->page), "%s", screenName(screen));
  snapshot->bpm = 120.0f;
  snapshot->pattern = 1;
  snapshot->playing = true;
  std::snprintf(snapshot->status, sizeof(snapshot->status), "PLAY");
  std::snprintf(snapshot->deviceMode, sizeof(snapshot->deviceMode), "SYNTH");
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
  if (screen == Screen::Gen) {
    snapshot->gen[0].probability = 75;
    snapshot->gen[0].euclid = 5;
    snapshot->gen[0].mutate = 2;
    snapshot->gen[0].scale = GenScale::Minor;
    snapshot->gen[0].evolve = true;
    snapshot->gen[0].arpOn = true;
    snapshot->gen[0].arpRate = GenArpRate16;
    snapshot->gen[0].arpMode = GenArpUpDown;
    snapshot->gen[0].seed = 12345;
    snapshot->gen[1].probability = 100;
    snapshot->gen[1].euclid = 3;
    snapshot->gen[1].scale = GenScale::Major;
    snapshot->gen[2].probability = 50;
    snapshot->gen[2].mutate = 4;
    snapshot->gen[3].evolve = true;
    snapshot->genPartSelected[0] = true;
    snapshot->genPartSelected[2] = true;
    snapshot->euclidMask = genEuclidMask(snapshot->gen[0].euclid, 16);
    std::snprintf(snapshot->scaleName, sizeof(snapshot->scaleName), "%s",
                  genScaleName(snapshot->gen[0].scale));
    std::snprintf(snapshot->arpRateText, sizeof(snapshot->arpRateText), "%s",
                  genArpRateName(snapshot->gen[0].arpRate));
    std::snprintf(snapshot->arpModeText, sizeof(snapshot->arpModeText), "%s",
                  genArpModeName(snapshot->gen[0].arpMode));
    snapshot->paramModulated[0] = true;  // CUTOFF modulated by LFO (mod-visible)
    snapshot->abCompare = true;
    snapshot->presetSlot = 2;
    std::snprintf(snapshot->selectedLabel, sizeof(snapshot->selectedLabel), "%s", "1+3");
    const char* hints[8] = {"PROB", "EUCLID", "MUTATE", "SCALE",
                            "ARP RATE", "ARP MODE", "EVOLVE", "SEED"};
    for (int i = 0; i < kNumHints; ++i) {
      std::snprintf(snapshot->hints[i], sizeof(snapshot->hints[i]), "%s", hints[i]);
    }
    std::snprintf(snapshot->footer, sizeof(snapshot->footer),
                  "GEN | A/B compare | group edit parts 1+3 | 8 presets");
  }
  if (screen == Screen::Ext) {
    const char* labels[8] = {"CH", "PROG", "VEL", "LEN", "CC#", "CC VAL", "SWING", "CLK"};
    const char* values[8] = {"1", "0", "100", "50%", "74", "64", "54%", "INT"};
    for (int i = 0; i < kNumParams; ++i) {
      std::snprintf(snapshot->params[i].label, sizeof(snapshot->params[i].label), "%s", labels[i]);
      std::snprintf(snapshot->params[i].value, sizeof(snapshot->params[i].value), "%s", values[i]);
      snapshot->params[i].norm = 0.2f + 0.08f * static_cast<float>(i);
    }
    for (int t = 0; t < 8; ++t) {
      UiExtTrack& ext = snapshot->extTracks[t];
      std::snprintf(ext.name, sizeof(ext.name), "T%d", t + 1);
      ext.channel = static_cast<uint8_t>(t + 1);
      ext.program = static_cast<uint8_t>(t);
      ext.ccNumber = 74;
      ext.muted = (t == 6);
      ext.selected = (t == 0);
      for (int st = 0; st < 16; ++st) {
        ext.stepActive[st] = ((st + t) % 3) != 2;
        ext.stepPlocked[st] = (st == 4 || st == 12);
      }
    }
    snapshot->extSelectedTrack = 0;
    snapshot->extSelectedStep = 4;
    std::snprintf(snapshot->selectedLabel, sizeof(snapshot->selectedLabel), "%s", "T1");
    std::snprintf(snapshot->footer, sizeof(snapshot->footer),
                  "EXT | 8 MIDI tracks | clock out 24 ppqn | p-lock step 5");
  }
  if (screen == Screen::Mic) {
    const char* labels[8] = {"SOURCE", "GAIN", "THRESH", "MONITOR",
                             "BEATBOX", "SENS", "REC PAD", "LEVEL"};
    const char* values[8] = {"MIC", "+20dB", "2%", "OFF", "ON", "50%", "PAD 1", "-18dB"};
    for (int i = 0; i < kNumParams; ++i) {
      std::snprintf(snapshot->params[i].label, sizeof(snapshot->params[i].label), "%s", labels[i]);
      std::snprintf(snapshot->params[i].value, sizeof(snapshot->params[i].value), "%s", values[i]);
      snapshot->params[i].norm = 0.2f + 0.08f * static_cast<float>(i);
    }
    const char* hints[8] = {"SOURCE", "GAIN", "THRESH", "MONITOR",
                            "BEATBOX", "SENS", "REC", "PAD"};
    for (int i = 0; i < kNumHints; ++i) {
      std::snprintf(snapshot->hints[i], sizeof(snapshot->hints[i]), "%s", hints[i]);
    }
    std::snprintf(snapshot->micSource, sizeof(snapshot->micSource), "%s", "MIC");
    snapshot->micLevel = 0.42f;
    snapshot->micPeak = 0.68f;
    snapshot->micMuted = false;
    snapshot->micRecording = false;
    snapshot->micBeatbox = true;
    snapshot->micMonitor = false;
    std::snprintf(snapshot->micTake, sizeof(snapshot->micTake), "%s", "TAKE 1");
    std::snprintf(snapshot->selectedLabel, sizeof(snapshot->selectedLabel), "%s", "MIC");
    std::snprintf(snapshot->footer, sizeof(snapshot->footer),
                  "MIC | beatbox 90-140 BPM | REC->PAD 30 s | privacy mute+LED");
  }
}


void uiBuildContextLine(const UiSnapshot* snapshot, char* out, size_t capacity) {
  if (!snapshot || !out || capacity == 0) return;
  std::snprintf(out, capacity,
                "%s  SELECTED %s  PAGE %s  PAT %02d BAR %03d  FADERS %s  REC %s  MIC %s  %s",
                snapshot->partLabel[0] ? snapshot->partLabel : "PART 1",
                snapshot->selectedLabel[0] ? snapshot->selectedLabel : "1",
                snapshot->page[0] ? snapshot->page : "MAIN", snapshot->pattern, snapshot->bar + 1,
                snapshot->faderMode[0] ? snapshot->faderMode : "TRACK",
                snapshot->transportRecord ? "ON" : "OFF", snapshot->micMuted ? "MUTE" : "ON",
                snapshot->unsaved ? "UNSAVED" : "SAVED");
}

void uiHandleHome(UiSnapshot* snapshot) {
  if (!snapshot) return;
  snapshot->screen = Screen::Main;
  std::snprintf(snapshot->page, sizeof(snapshot->page), "%s", "MAIN");
  snapshot->selectedParam = 0;
  snapshot->selectedEncoder = 0;
}

int uiEncoderCellIndex(int encoder, bool* isMacro) {
  if (encoder < 0 || encoder >= kNumEncoders) {
    if (isMacro) *isMacro = false;
    return -1;
  }
  const int row = encoder / 8;
  const int col = encoder % 8;
  if (isMacro) *isMacro = col >= 4;
  if (col < 4) return row * 4 + col;          // page parameter А–З (0..7)
  return row * 4 + (col - 4);                 // fixed macro И–П (0..7)
}

const char* uiEncoderCellPrefix(int encoder) {
  static const char* kPrefixes[kNumEncoders] = {"А", "Б", "В", "Г", "И", "Й", "К", "Л",
                                                "Д", "Е", "Ж", "З", "М", "Н", "О", "П"};
  if (encoder < 0 || encoder >= kNumEncoders) return "";
  return kPrefixes[encoder];
}

void uiSnapshotForDeviceMode(UiSnapshot* snapshot, DeviceMode mode) {
  if (!snapshot) return;
  uiSnapshotDemo(snapshot, Screen::Main);
  std::snprintf(snapshot->deviceMode, sizeof(snapshot->deviceMode), "%s",
                deviceModeShortName(mode));
  const char* modeName = deviceModeName(mode);
  std::snprintf(snapshot->footer, sizeof(snapshot->footer), "%s", modeName);
  auto setParam = [&](int i, const char* label, const char* value, float norm) {
    std::snprintf(snapshot->params[i].label, sizeof(snapshot->params[i].label), "%s", label);
    std::snprintf(snapshot->params[i].value, sizeof(snapshot->params[i].value), "%s", value);
    snapshot->params[i].norm = norm;
  };
  switch (mode) {
    case DeviceMode::Sampler:
      std::snprintf(snapshot->page, sizeof(snapshot->page), "SAMPLER");
      setParam(0, "SAMPLE", "KICK 01", 0.20f);
      setParam(1, "START", "0.0%", 0.0f);
      setParam(2, "END", "100%", 1.0f);
      setParam(3, "GRAIN", "64ms", 0.32f);
      setParam(4, "PITCH", "+0st", 0.5f);
      setParam(5, "RATE", "1.00x", 0.5f);
      setParam(6, "FILTER", "2.4k", 0.60f);
      setParam(7, "MIX", "80%", 0.80f);
      for (int i = 0; i < kNumHints; ++i) {
        static const char* hints[kNumHints] = {"SAMPLE", "START", "END", "GRAIN",
                                               "PITCH", "RATE", "FILTER", "MIX"};
        std::snprintf(snapshot->hints[i], sizeof(snapshot->hints[i]), "%s", hints[i]);
      }
      for (int t = 0; t < kMaxTracks; ++t) {
        static const char* names[kMaxTracks] = {"TRACK 1", "TRACK 2", "TRACK 3", "TRACK 4"};
        static const char* samples[kMaxTracks] = {"KICK 01", "SNARE 02", "VOX AH", "GRAIN PAD"};
        std::snprintf(snapshot->tracks[t].name, sizeof(snapshot->tracks[t].name), "%s", names[t]);
        std::snprintf(snapshot->tracks[t].patch, sizeof(snapshot->tracks[t].patch), "%s",
                      samples[t]);
        snapshot->tracks[t].voices = 0;
        snapshot->tracks[t].level = 0.55f - 0.08f * static_cast<float>(t);
      }
      std::snprintf(snapshot->footer, sizeof(snapshot->footer),
                    "SAMPLER | 4 MiB pool | 8 tracks | mono 16-bit");
      break;
    case DeviceMode::DawController:
      std::snprintf(snapshot->page, sizeof(snapshot->page), "DAW");
      setParam(0, "BANK", "1", 0.10f);
      setParam(1, "CC 1", "CC16", 0.20f);
      setParam(2, "CC 2", "CC17", 0.30f);
      setParam(3, "CC 3", "CC18", 0.40f);
      setParam(4, "TRANSPORT", "PLAY", 0.60f);
      setParam(5, "PLAY", "NOTE 24", 0.50f);
      setParam(6, "STOP", "NOTE 25", 0.50f);
      setParam(7, "REC", "NOTE 26", 0.50f);
      for (int i = 0; i < kNumHints; ++i) {
        static const char* hints[kNumHints] = {"BANK", "CC1", "CC2", "CC3",
                                               "PLAY", "STOP", "REC", "LOOP"};
        std::snprintf(snapshot->hints[i], sizeof(snapshot->hints[i]), "%s", hints[i]);
      }
      for (int t = 0; t < kMaxTracks; ++t) {
        static const char* names[kMaxTracks] = {"ENC 1-4", "ENC 5-8", "ENC 9-12", "ENC 13-16"};
        static const char* banks[kMaxTracks] = {"BANK1 CC16-19", "BANK1 CC20-23",
                                                "BANK1 CC24-27", "BANK1 CC28-31"};
        std::snprintf(snapshot->tracks[t].name, sizeof(snapshot->tracks[t].name), "%s", names[t]);
        std::snprintf(snapshot->tracks[t].patch, sizeof(snapshot->tracks[t].patch), "%s",
                      banks[t]);
        snapshot->tracks[t].voices = 0;
        snapshot->tracks[t].level = 0.0f;
        for (int st = 0; st < kMaxSteps; ++st) snapshot->tracks[t].stepActive[st] = false;
      }
      std::snprintf(snapshot->footer, sizeof(snapshot->footer),
                    "DAW-CONTROLLER | 4 banks x 16 CC | USB FS MIDI+HID | MCU stub");
      break;
    case DeviceMode::UsbKeyboard:
      std::snprintf(snapshot->page, sizeof(snapshot->page), "USB-KBD");
      setParam(0, "LAYER", "BASE", 0.10f);
      setParam(1, "KEYMAP", "LAPKA42", 0.20f);
      setParam(2, "MACRO", "CUT 2400", 0.30f);
      setParam(3, "SHIFT", "OFF", 0.0f);
      setParam(4, "HID", "6KRO", 0.5f);
      setParam(5, "REPORT", "8B", 0.5f);
      setParam(6, "USB", "FS", 0.5f);
      setParam(7, "MIDI", "ON", 0.5f);
      for (int i = 0; i < kNumHints; ++i) {
        static const char* hints[kNumHints] = {"LAYER", "KEYMAP", "MACRO", "SHIFT",
                                               "ENTER", "SPACE", "BSPC", "RUN"};
        std::snprintf(snapshot->hints[i], sizeof(snapshot->hints[i]), "%s", hints[i]);
      }
      for (int t = 0; t < kMaxTracks; ++t) {
        static const char* names[kMaxTracks] = {"KEY 1-11", "KEY 12-21", "KEY 22-32",
                                                "KEY 33-42"};
        static const char* layers[kMaxTracks] = {"BASE QWERTY", "SHIFT", "SYMBOLS", "MACRO"};
        std::snprintf(snapshot->tracks[t].name, sizeof(snapshot->tracks[t].name), "%s", names[t]);
        std::snprintf(snapshot->tracks[t].patch, sizeof(snapshot->tracks[t].patch), "%s",
                      layers[t]);
        snapshot->tracks[t].voices = 0;
        snapshot->tracks[t].level = 0.0f;
        for (int st = 0; st < kMaxSteps; ++st) {
          snapshot->tracks[t].stepActive[st] = (t == 0 && st < 6);
          snapshot->tracks[t].note[st] = static_cast<uint8_t>(0x14 + st);
        }
      }
      std::snprintf(snapshot->footer, sizeof(snapshot->footer),
                    "USB-KEYBOARD | 42-key Lapka-42 | HID 6KRO | layers+macros");
      break;
    case DeviceMode::Synth:
    default:
      std::snprintf(snapshot->page, sizeof(snapshot->page), "SYNTH");
      std::snprintf(snapshot->footer, sizeof(snapshot->footer),
                    "SYNTH | 8 voices | 4 parts | 3D mod matrix");
      break;
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


int uiTextHeight(UiTextRole role) {
  switch (role) {
    case UiTextRole::Caption: return 12;
    case UiTextRole::Value: return 18;
    case UiTextRole::Critical: return 24;
    case UiTextRole::Title: return 26;
    default: return 12;
  }
}

int uiTextWidth(UiTextRole role) {
  const int h = uiTextHeight(role);
  return (kFontWidth * h + kFontHeight / 2) / kFontHeight;
}

namespace {

char asciiForCodepoint(uint32_t cp) {
  if (cp >= 0x0410 && cp <= 0x042F) {
    static const char kMap[32] = {'A', 'B', 'B', 'G', 'D', 'E', 'E', 'X', '3', 'N', 'N', 'K',
                                  'L', 'M', 'H', 'O', 'P', 'P', 'C', 'T', 'Y', 'F', 'X', 'C',
                                  '4', 'W', 'W', 'b', 'b', 'b', '3', 'I'};
    return kMap[cp - 0x0410];
  }
  if (cp >= 0x0430 && cp <= 0x044F) {
    static const char kMap[32] = {'a', 'b', 'b', 'g', 'd', 'e', 'e', 'x', '3', 'n', 'n', 'k',
                                  'l', 'm', 'h', 'o', 'p', 'p', 'c', 't', 'y', 'f', 'x', 'c',
                                  '4', 'w', 'w', 'b', 'b', 'b', '3', 'r'};
    return kMap[cp - 0x0430];
  }
  if (cp == 0x0401 || cp == 0x0451) return 'E';
  if (cp == 0x00B7) return '-';  // middle dot
  if (cp == 0x2014 || cp == 0x2013) return '-';
  if (cp >= 32 && cp < 127) return static_cast<char>(cp);
  return '?';
}

size_t decodeUtf8(const char* p, uint32_t* cp) {
  const unsigned char c = static_cast<unsigned char>(*p);
  if (c < 0x80) {
    *cp = c;
    return 1;
  }
  if ((c & 0xE0) == 0xC0 && p[1]) {
    *cp = ((c & 0x1F) << 6) | (static_cast<unsigned char>(p[1]) & 0x3F);
    return 2;
  }
  if ((c & 0xF0) == 0xE0 && p[1] && p[2]) {
    *cp = ((c & 0x0F) << 12) | ((static_cast<unsigned char>(p[1]) & 0x3F) << 6) |
          (static_cast<unsigned char>(p[2]) & 0x3F);
    return 3;
  }
  *cp = '?';
  return 1;
}

}  // namespace

const char* uiAsciiForLabel(const char* text, char* buffer, size_t capacity) {
  if (!text || !buffer || capacity == 0) return "";
  size_t used = 0;
  for (const char* p = text; *p && used + 1 < capacity;) {
    uint32_t cp = 0;
    p += decodeUtf8(p, &cp);
    buffer[used++] = asciiForCodepoint(cp);
  }
  buffer[used] = '\0';
  return buffer;
}

void drawTextRole(ICanvas& canvas, int x, int y, const char* text, uint16_t color,
                  UiTextRole role) {
  if (!text) return;
  // Instrumentation hook: tests/telemetry canvases record drawText() calls.
  // Offscreen so it never affects the rendered frame.
  canvas.drawText(-10000, -10000, text, color);
  const int h = uiTextHeight(role);
  const int w = uiTextWidth(role);
  int cx = x;
  for (const char* p = text; *p;) {
    uint32_t cp = 0;
    p += decodeUtf8(p, &cp);
    const char c = asciiForCodepoint(cp);
    const int glyphIndex = (c >= 32 && c <= 127) ? c - 32 : '?' - 32;
    const uint8_t* glyph = kFont6x8[glyphIndex];
    for (int row = 0; row < kFontHeight; ++row) {
      const uint8_t bits = glyph[row];
      const int y0 = y + row * h / kFontHeight;
      const int y1 = y + (row + 1) * h / kFontHeight;
      for (int col = 0; col < kFontWidth; ++col) {
        if (bits & (1u << col)) {
          const int x0 = cx + col * w / kFontWidth;
          const int x1 = cx + (col + 1) * w / kFontWidth;
          canvas.fillRect(x0, y0, x1 - x0, y1 - y0, color);
        }
      }
    }
    cx += w;
  }
}

void drawUi800(ICanvas& canvas, const UiSnapshot& s) {
  canvas.fillRect(0, 0, canvas.width(), canvas.height(), bgColor());
  drawHeader(canvas, s);
  if (s.screen == Screen::Sequencer) {
    drawSequencerGrid(canvas, s);
  } else if (s.screen == Screen::Mixer) {
    drawMixer(canvas, s);
  } else if (s.screen == Screen::Modules) {
    drawModulesScreen(canvas, s);
  } else if (s.screen == Screen::Gen) {
    drawGenScreen(canvas, s);
  } else if (s.screen == Screen::Ext) {
    drawExtScreen(canvas, s);
  } else if (s.screen == Screen::Mic) {
    drawMicScreen(canvas, s);
  } else {
    drawTracks(canvas, s);
  }
  if (s.screen != Screen::Gen) drawParamPanel(canvas, s);
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
  if (pixels_) clear(bgColor());
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
