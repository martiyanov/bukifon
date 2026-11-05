// SPDX-License-Identifier: GPL-3.0-or-later
// MIC page (docs/71): source/gain/threshold/monitor/beatbox/rec->pad/meter,
// privacy banner/context, 4 themes and mirrored 8+8 fields.
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

TEST(UiMicSnapshotFields) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotMicDemo(&snapshot);
  CHECK(snapshot.screen == ui::Screen::Mic);
  CHECK(std::strcmp(snapshot.page, "MIC") == 0);
  CHECK(static_cast<int>(ui::Screen::Mic) == 6);
  CHECK(static_cast<int>(ui::Screen::kNumScreens) == 7);
  CHECK(std::strcmp(snapshot.micSource, "MIC") == 0);
  CHECK(!snapshot.micMuted);
  CHECK(snapshot.micBeatbox);
  CHECK(snapshot.micLevel > 0.0f);
  CHECK(std::strlen(snapshot.micTake) > 0);
  CHECK(std::strcmp(snapshot.params[0].label, "SOURCE") == 0);
  CHECK(std::strcmp(snapshot.params[1].label, "GAIN") == 0);
  CHECK(std::strcmp(snapshot.params[2].label, "THRESH") == 0);
  CHECK(std::strcmp(snapshot.params[3].label, "MONITOR") == 0);
  CHECK(std::strcmp(snapshot.params[4].label, "BEATBOX") == 0);
  CHECK(std::strcmp(snapshot.params[5].label, "SENS") == 0);
  CHECK(std::strcmp(snapshot.params[6].label, "REC PAD") == 0);
  CHECK(std::strcmp(snapshot.params[7].label, "LEVEL") == 0);
  INFO("MIC snapshot: SOURCE/GAIN/THRESH/MONITOR/BEATBOX/SENS/REC PAD/LEVEL");
}

TEST(UiMicRendersAllThemes) {
  uint64_t hashes[4] = {};
  for (int theme = 0; theme < 4; ++theme) {
    CHECK(bukifon_ui_theme_set(bukifon_ui_theme_name(theme)));
    ui::Framebuffer800 fb;
    ui::UiSnapshot snapshot;
    ui::uiSnapshotMicDemo(&snapshot);
    ui::drawUi800(fb, snapshot);
    CHECK(nonBlack(fb) > 2000);
    hashes[theme] = checksum(fb);
  }
  CHECK(hashes[0] != hashes[1]);
  CHECK(hashes[2] != hashes[3]);
  bukifon_ui_theme_set("Night");
  INFO("MIC page renders in all 4 themes");
}

TEST(UiMicPrivacyBannerAndContext) {
  ui::UiSnapshot on;
  ui::uiSnapshotMicDemo(&on);
  on.micMuted = false;
  on.micRecording = true;
  char lineOn[192];
  ui::uiBuildContextLine(&on, lineOn, sizeof(lineOn));
  CHECK(std::strstr(lineOn, "MIC ON") != nullptr);
  ui::Framebuffer800 a;
  ui::drawUi800(a, on);

  ui::UiSnapshot muted = on;
  muted.micMuted = true;
  muted.micRecording = false;
  char lineMuted[192];
  ui::uiBuildContextLine(&muted, lineMuted, sizeof(lineMuted));
  CHECK(std::strstr(lineMuted, "MIC MUTE") != nullptr);
  ui::Framebuffer800 b;
  ui::drawUi800(b, muted);
  CHECK(checksum(a) != checksum(b));
  INFO("MIC ON/MUTE privacy banner and context line are rendered and distinct");
}

TEST(UiMicBeatboxAndMeterVisuals) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotMicDemo(&snapshot);
  ui::Framebuffer800 a;
  ui::drawUi800(a, snapshot);
  snapshot.micBeatbox = false;
  snapshot.micLevel = 0.05f;
  snapshot.micPeak = 0.1f;
  ui::Framebuffer800 b;
  ui::drawUi800(b, snapshot);
  CHECK(checksum(a) != checksum(b));
  CHECK(nonBlack(b) > 2000);
  INFO("beatbox state and input level meter change the MIC frame");
}

TEST(UiMicMirrorFields) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotMicDemo(&snapshot);
  CHECK(ui::kNumEncoders == 16);
  CHECK(ui::kNumParams == 8);
  CHECK(ui::kNumMacros == 8);
  bool isMacro = false;
  CHECK(ui::uiEncoderCellIndex(0, &isMacro) == 0 && !isMacro);
  CHECK(ui::uiEncoderCellIndex(4, &isMacro) == 0 && isMacro);
  CHECK(ui::uiEncoderCellIndex(15, &isMacro) == 7 && isMacro);
  CHECK(std::strcmp(ui::uiEncoderCellPrefix(0), "А") == 0);
  CHECK(std::strcmp(ui::uiEncoderCellPrefix(15), "П") == 0);
  INFO("MIC uses the same 16-cell mirror (8 page fields + 8 macros И–П)");
}
