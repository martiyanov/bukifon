// SPDX-License-Identifier: GPL-3.0-or-later
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "test_framework.hpp"
#include "ui/ui800.hpp"

using namespace bukifon;

namespace {

class RecordingCanvas : public ui::Framebuffer800 {
 public:
  void drawText(int x, int y, const char* text, uint16_t color, uint16_t bg = 0xFFFF) override {
    texts.emplace_back(text ? text : "");
    ui::Framebuffer800::drawText(x, y, text, color, bg);
  }
  bool has(const char* needle) const {
    for (const std::string& t : texts) {
      if (t.find(needle) != std::string::npos) return true;
    }
    return false;
  }
  int nonBlack(int step = 8) const {
    int count = 0;
    for (int y = 0; y < height(); y += step) {
      for (int x = 0; x < width(); x += step) {
        if (at(x, y) != colors::kBlack) ++count;
      }
    }
    return count;
  }
  std::vector<std::string> texts;
};

}  // namespace

TEST(Ui800FramebufferBasics) {
  ui::Framebuffer800 fb;
  CHECK(fb.valid());
  CHECK(fb.width() == 800);
  CHECK(fb.height() == 480);
  fb.clear(colors::kBlack);
  CHECK(fb.at(0, 0) == colors::kBlack);
  fb.fillRect(10, 10, 100, 50, colors::kRed);
  CHECK(fb.at(10, 10) == colors::kRed);
  CHECK(fb.at(109, 59) == colors::kRed);
  CHECK(fb.at(110, 10) == colors::kBlack);
  // Out-of-bounds operations must be clipped, never crash.
  fb.fillRect(-50, -50, 10000, 10000, colors::kGreen);
  fb.drawPixel(-1, -1, colors::kWhite);
  fb.drawPixel(800, 480, colors::kWhite);
  CHECK(fb.at(0, 0) == colors::kGreen);
  const char* path = "../tests/out/ui_test.ppm";
  CHECK(fb.writePpm(path));
  FILE* f = std::fopen(path, "rb");
  CHECK(f != nullptr);
  if (f) {
    char header[32] = {};
    const size_t n = std::fread(header, 1, 15, f);
    std::fclose(f);
    CHECK(n == 15);
    CHECK(std::strncmp(header, "P6\n800 480\n255", 14) == 0);
  }
  std::remove(path);
  INFO("ui800 framebuffer: 800x480 RGB565, PPM export OK");
}

TEST(Ui800AllScreens) {
  const ui::Screen screens[4] = {ui::Screen::Main, ui::Screen::Sequencer, ui::Screen::Mixer,
                                 ui::Screen::Modules};
  const char* pages[4] = {"MAIN", "SEQUENCER", "MIXER", "MODULES"};
  for (int i = 0; i < 4; ++i) {
    ui::UiSnapshot snapshot;
    ui::uiSnapshotDemo(&snapshot, screens[i]);
    RecordingCanvas canvas;
    ui::drawUi800(canvas, snapshot);
    CHECK(canvas.nonBlack(6) > 3000);
    CHECK(canvas.has("BPM"));
    CHECK(canvas.has("PAT"));
    CHECK(canvas.has("PLAY"));
    CHECK(canvas.has(pages[i]));
    CHECK(canvas.has("MASTER"));
    CHECK(canvas.texts.size() > 8);
    // Four track strips must have been drawn in the upper area.
    int trackPixels = 0;
    for (int t = 0; t < 4; ++t) {
      const int y = 70 + t * 60;
      for (int x = 20; x < 780; x += 4) {
        if (canvas.at(x, y) != colors::kBlack && canvas.at(x, y) != colors::kPanel) ++trackPixels;
      }
    }
    CHECK(trackPixels > 100);
    INFO("ui800 screen %s: %zu text runs, %d sampled pixels", pages[i], canvas.texts.size(),
         canvas.nonBlack(6));
  }
}

TEST(Ui800SnapshotDriven) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
  snapshot.bpm = 140.0f;
  snapshot.playing = false;
  std::snprintf(snapshot.status, sizeof(snapshot.status), "STOP");
  snapshot.tracks[0].muted = true;
  snapshot.activeStep = 3;
  RecordingCanvas canvas;
  ui::drawUi800(canvas, snapshot);
  CHECK(canvas.has("BPM 140"));
  CHECK(canvas.has("STOP"));
  CHECK(canvas.has("MUTE"));
  INFO("ui800 snapshot-driven: bpm/status/mute reflected in the frame");
}

TEST(Ui800SelectedParamHighlight) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
  snapshot.selectedParam = 0;
  ui::Framebuffer800 a;
  ui::drawUi800(a, snapshot);
  snapshot.selectedParam = 3;
  ui::Framebuffer800 b;
  ui::drawUi800(b, snapshot);
  // The highlighted encoder hint box changes colour.
  CHECK(a.at(20, 408) != b.at(20, 408));
  // And the parameter panel border of the selected cell changes too.
  CHECK(a.at(12, 310) != b.at(12, 310) || a.at(400, 310) != b.at(400, 310));
  INFO("ui800: selected parameter highlight is visible");
}

TEST(Ui800EdgeCases) {
  ui::UiSnapshot snapshot;
  ui::uiSnapshotInit(&snapshot);
  snapshot.trackCount = 0;
  snapshot.stepCount = 0;
  ui::Framebuffer800 fb;
  ui::drawUi800(fb, snapshot);  // must not crash or write out of bounds
  CHECK(fb.valid());
  ui::drawTextScaled(fb, -100, -100, "CLIPPED", colors::kWhite, 3);
  ui::drawTextScaled(fb, 790, 470, "X", colors::kWhite, 4);
  INFO("ui800: empty/edge snapshots are safe");
}
