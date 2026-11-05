// SPDX-License-Identifier: GPL-3.0-or-later
// EXT page: 8 external MIDI tracks, 16-step grid, selected track/step,
// CH/PROG/VEL/LEN/CC#/CC VAL/SWING/CLK fields, p-lock/mute indicators.
#include <cstdint>
#include <cstring>

#include "bukifon_ui_theme.h"
#include "test_framework.hpp"
#include "ui/ui800.hpp"

using namespace bukifon;

namespace {

uint64_t checksum(const ui::Framebuffer800& fb) {
  uint64_t hash = 1469598103934665603ull;
  for (int y = 0; y < fb.height(); y += 5) {
    for (int x = 0; x < fb.width(); x += 5) {
      hash ^= fb.at(x, y);
      hash *= 1099511628211ull;
    }
  }
  return hash;
}

int nonBlack(const ui::Framebuffer800& fb) {
  int count = 0;
  for (int y = 0; y < fb.height(); y += 3) {
    for (int x = 0; x < fb.width(); x += 3) count += fb.at(x, y) != 0 ? 1 : 0;
  }
  return count;
}

}  // namespace

TEST(UiExtSnapshotTracksAndSteps) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotExtDemo(&snapshot);
  CHECK(snapshot.screen == ui::Screen::Ext);
  CHECK(std::strcmp(snapshot.page, "EXT") == 0);
  CHECK(static_cast<int>(ui::Screen::Ext) == 5);
  CHECK(static_cast<int>(ui::Screen::kNumScreens) == 7);
  for (int t = 0; t < 8; ++t) {
    CHECK(snapshot.extTracks[t].channel >= 1 && snapshot.extTracks[t].channel <= 16);
    CHECK(snapshot.extTracks[t].program <= 127);
    int active = 0;
    bool plock = false;
    for (int s = 0; s < 16; ++s) {
      active += snapshot.extTracks[t].stepActive[s] ? 1 : 0;
      plock = plock || snapshot.extTracks[t].stepPlocked[s];
    }
    CHECK(active > 0);
    CHECK(plock);
  }
  CHECK(snapshot.extSelectedTrack == 0);
  CHECK(snapshot.extSelectedStep == 4);
  CHECK(std::strcmp(snapshot.params[0].label, "CH") == 0);
  CHECK(std::strcmp(snapshot.params[7].label, "CLK") == 0);
  INFO("EXT snapshot: 8 tracks x 16 steps, CH/PROG/VEL/LEN/CC#/CC VAL/SWING/CLK");
}

TEST(UiExtRendersAllThemes) {
  uint64_t hashes[4] = {};
  for (int theme = 0; theme < 4; ++theme) {
    CHECK(bukifon_ui_theme_set(bukifon_ui_theme_name(theme)));
    ui::Framebuffer800 fb;
    ui::UiSnapshot snapshot;
    ui::uiSnapshotExtDemo(&snapshot);
    ui::drawUi800(fb, snapshot);
    CHECK(nonBlack(fb) > 2000);
    hashes[theme] = checksum(fb);
  }
  CHECK(hashes[0] != hashes[1]);
  CHECK(hashes[2] != hashes[3]);
  bukifon_ui_theme_set("Night");
  INFO("EXT page renders in all 4 themes");
}

TEST(UiExtSelectedTrackStepHighlight) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotExtDemo(&snapshot);
  ui::Framebuffer800 a;
  ui::drawUi800(a, snapshot);
  snapshot.extSelectedTrack = 4;
  snapshot.extSelectedStep = 10;
  ui::Framebuffer800 b;
  ui::drawUi800(b, snapshot);
  CHECK(checksum(a) != checksum(b));
  CHECK(a.at(20, 100) != b.at(20, 100) || a.at(300, 100) != b.at(300, 100));
  INFO("selected external track/step highlight changes the frame");
}

TEST(UiExtMirrorFieldsAndMacros) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotExtDemo(&snapshot);
  bool isMacro = false;
  CHECK(ui::uiEncoderCellIndex(0, &isMacro) == 0 && !isMacro);
  CHECK(ui::uiEncoderCellIndex(4, &isMacro) == 0 && isMacro);  // И = macro CUT
  CHECK(ui::kNumParams == 8);
  CHECK(ui::kNumMacros == 8);
  CHECK(ui::kNumEncoders == 16);
  const char* macros[8] = {"CUT", "RES", "ATK", "REL", "DLY", "DRV", "CRSH", "MST"};
  for (int i = 0; i < 8; ++i) CHECK(std::strcmp(snapshot.macros[i].label, macros[i]) == 0);
  INFO("EXT uses the 8+8 mirrored cells (CH..CLK left, macros И–П right)");
}

TEST(UiExtPLockAndMuteIndicators) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotExtDemo(&snapshot);
  ui::Framebuffer800 a;
  ui::drawUi800(a, snapshot);
  // Clear p-locks/mutes: the rendered frame must change.
  for (int t = 0; t < 8; ++t) {
    for (int s = 0; s < 16; ++s) snapshot.extTracks[t].stepPlocked[s] = false;
    snapshot.extTracks[t].muted = false;
  }
  ui::Framebuffer800 b;
  ui::drawUi800(b, snapshot);
  CHECK(checksum(a) != checksum(b));
  CHECK(nonBlack(a) > 2000 && nonBlack(b) > 2000);
  INFO("p-lock bars and mute marker are visible on the EXT grid");
}
