// SPDX-License-Identifier: GPL-3.0-or-later
// GEN page (5th tab), mod-visible marker, multi-select and A/B/preset visuals.
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

TEST(UiGenSnapshotFields) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotGenDemo(&snapshot);
  CHECK(snapshot.screen == ui::Screen::Gen);
  CHECK(std::strcmp(snapshot.page, "GEN") == 0);
  CHECK(snapshot.gen[0].probability == 75);
  CHECK(snapshot.gen[0].euclid == 5);
  CHECK(snapshot.gen[0].mutate == 2);
  CHECK(snapshot.gen[0].scale == GenScale::Minor);
  CHECK(snapshot.gen[0].evolve);
  CHECK(snapshot.gen[0].arpOn);
  CHECK(snapshot.gen[0].seed == 12345);
  CHECK(snapshot.genPartSelected[0]);
  CHECK(snapshot.genPartSelected[2]);
  CHECK(!snapshot.genPartSelected[1]);
  CHECK(snapshot.euclidMask == genEuclidMask(5, 16));
  CHECK(std::strcmp(snapshot.scaleName, "MINOR") == 0);
  CHECK(std::strcmp(snapshot.arpRateText, "1/16") == 0);
  CHECK(std::strcmp(snapshot.arpModeText, "UPDOWN") == 0);
  CHECK(snapshot.abCompare);
  CHECK(snapshot.presetSlot == 2);
  CHECK(std::strlen(snapshot.presetNames[2]) > 0);
  CHECK(snapshot.paramModulated[0]);  // CUTOFF modulated by LFO
  INFO("GEN snapshot: PROB/EUCLID/MUTATE/SCALE/ARP/EVOLVE/SEED + presets/A-B/multi-select");
}

TEST(UiGenScreenRendersAllThemes) {
  uint64_t hashes[4] = {};
  for (int theme = 0; theme < 4; ++theme) {
    CHECK(bukifon_ui_theme_set(bukifon_ui_theme_name(theme)));
    ui::Framebuffer800 fb;
    CHECK(fb.valid());
    ui::UiSnapshot snapshot;
    ui::uiSnapshotGenDemo(&snapshot);
    ui::drawUi800(fb, snapshot);
    CHECK(nonBlack(fb) > 2000);
    hashes[theme] = checksum(fb);
  }
  CHECK(hashes[0] != hashes[1]);
  CHECK(hashes[2] != hashes[3]);
  bukifon_ui_theme_set("Night");
  INFO("GEN page renders in all 4 themes (5th tab visible, distinct palettes)");
}

TEST(UiGenModMarkerAndMultiSelectAffectPixels) {
  ui::Framebuffer800 plain;
  ui::UiSnapshot snapshot;
  ui::uiSnapshotGenDemo(&snapshot);
  snapshot.paramModulated[0] = false;
  snapshot.genPartSelected[0] = true;
  snapshot.genPartSelected[2] = false;
  ui::drawUi800(plain, snapshot);
  const uint64_t plainHash = checksum(plain);

  ui::Framebuffer800 marked;
  snapshot.paramModulated[0] = true;  // LFO M marker
  snapshot.genPartSelected[2] = true; // multi-select highlight
  ui::drawUi800(marked, snapshot);
  CHECK(checksum(marked) != plainHash);
  CHECK(nonBlack(marked) > 2000);
  INFO("mod-visible 'M' marker and multi-select highlight change the rendered frame");
}

TEST(UiGenPresetsAndAbCompare) {
  ui::Framebuffer800 a;
  ui::UiSnapshot snapshot;
  ui::uiSnapshotGenDemo(&snapshot);
  snapshot.presetSlot = 0;
  snapshot.abShowB = false;
  ui::drawUi800(a, snapshot);
  ui::Framebuffer800 b;
  snapshot.presetSlot = 6;
  snapshot.abShowB = true;  // show B side of A/B compare
  ui::drawUi800(b, snapshot);
  CHECK(checksum(a) != checksum(b));
  CHECK(nonBlack(b) > 2000);
  CHECK(std::strlen(snapshot.presetNames[6]) > 0);
  INFO("GEN page: 8 preset slot row, selected slot highlight and A/B B-state");
}

TEST(UiGenTabDispatch) {
  ui::Framebuffer800 gen;
  ui::Framebuffer800 main;
  ui::UiSnapshot snapshot;
  ui::uiSnapshotGenDemo(&snapshot);
  ui::drawUi800(gen, snapshot);
  snapshot.screen = ui::Screen::Main;
  std::snprintf(snapshot.page, sizeof(snapshot.page), "%s", "MAIN");
  ui::drawUi800(main, snapshot);
  CHECK(checksum(gen) != checksum(main));
  CHECK(static_cast<int>(ui::Screen::Gen) == 4);  // 5th tab (0-based 4)
  CHECK(static_cast<int>(ui::Screen::kNumScreens) == 6);
  INFO("GEN is the 5th screen/tab and dispatches to drawGenScreen");
}
