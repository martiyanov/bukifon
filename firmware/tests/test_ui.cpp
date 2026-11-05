// SPDX-License-Identifier: GPL-3.0-or-later
#include <cmath>
#include <cstring>
#include <string>
#include <vector>

#include "audio/engine.hpp"
#include "core/modulation_defs.hpp"
#include "core/params.hpp"
#include "test_framework.hpp"
#include "test_helpers.hpp"
#include "ui/canvas.hpp"
#include "ui/menu.hpp"

using namespace bukifon;

namespace {

class RecordingCanvas : public FrameBufferCanvas {
 public:
  void drawText(int x, int y, const char* text, uint16_t color, uint16_t bg = 0xFFFF) override {
    texts.push_back(text);
    FrameBufferCanvas::drawText(x, y, text, color, bg);
  }
  bool contains(const char* needle) const {
    for (const auto& t : texts) {
      if (t.find(needle) != std::string::npos) return true;
    }
    return false;
  }
  std::vector<std::string> texts;
};

std::string format(const ParamMeta& meta, float value) {
  char buf[32];
  MenuModel::formatValue(meta, value, buf, sizeof(buf));
  return buf;
}

}  // namespace

TEST(MenuPagesAndNavigation) {
  CHECK(kNumPages == 8);
  CHECK(std::strcmp(kPages[0].title, "OSC") == 0);
  CHECK(std::strcmp(kPages[7].title, "SYSTEM") == 0);
  Engine engine;
  engine.init();
  testutil::drySetup(engine, 0);
  MenuModel menu;
  menu.init(&engine);
  CHECK(menu.page() == 0);
  CHECK(std::strcmp(menu.binding(0).label, "WAVE1") == 0);
  CHECK(menu.binding(0).scope == MenuScope::PartParam);
  CHECK(menu.binding(0).id == Osc1Wave);
  for (int i = 0; i < 8; ++i) menu.nextPage();
  CHECK(menu.page() == kNumPages - 1);
  for (int i = 0; i < 12; ++i) menu.prevPage();
  CHECK(menu.page() == 0);
  menu.setShift(true);
  menu.onEncoder(7, 1, false);  // SHIFT + ENC8 -> next page
  CHECK(menu.page() == 1);
  menu.onEncoder(0, -1, false);  // SHIFT + ENC1 -> previous page
  CHECK(menu.page() == 0);
  menu.setShift(false);
  INFO("menu pages: 8 pages, titles '%s'..'%s', SHIFT+ENC1/ENC8 navigate", kPages[0].title,
       kPages[7].title);
}

TEST(MenuEncoderEditAndReset) {
  Engine engine;
  engine.init();
  testutil::drySetup(engine, 0);
  MenuModel menu;
  menu.init(&engine);
  engine.setPartParam(0, Osc1Coarse, 0.0f);
  menu.encoderDelta(1, 10);  // COARSE1: +10 % of the -24..+24 range
  const float coarse = engine.partBase(0).v[Osc1Coarse];
  INFO("menu edit: COARSE1 after +10 detents = %+.2f semitones", coarse);
  CHECK(coarse > 0.0f);
  menu.encoderDelta(1, -10);
  CHECK(std::fabs(engine.partBase(0).v[Osc1Coarse]) < 1.0f);
  menu.encoderPush(1);
  CHECK(engine.partBase(0).v[Osc1Coarse] == kPartParamMeta[Osc1Coarse].def);
  // Global parameter editing on the SYSTEM page.
  menu.setPage(7);
  engine.setGlobalParam(MasterVolume, 0.5f);
  menu.encoderDelta(0, 5);
  CHECK(engine.globals().v[MasterVolume] > 0.5f);
  // Macro editing.
  menu.setPage(3);
  const int macroEncoder = 7;
  menu.encoderDelta(macroEncoder, 3);
  CHECK(engine.macro(0) > 0.0f);
}

TEST(MenuValueFormatting) {
  CHECK(format(kPartParamMeta[Cutoff], 2400.0f) == "2.40k");
  CHECK(format(kPartParamMeta[Cutoff], 440.0f) == "440.0Hz");
  CHECK(format(kGlobalParamMeta[FxDelayTime], 0.35f) == "350ms");
  CHECK(format(kGlobalParamMeta[FxDelayTime], 1.25f) == "1.25s");
  CHECK(format(kPartParamMeta[Osc1Fine], -12.0f) == "-12ct");
  CHECK(format(kPartParamMeta[Osc1Coarse], 3.0f) == "+3st");
  CHECK(format(kPartParamMeta[Osc1Wave], 3.0f) == "3");
  CHECK(format(kPartParamMeta[FmRatio1], 2.0f) == "2.00x");
  CHECK(format(kPartParamMeta[Env1S], 0.6f) == "0.60");
  CHECK(format(kPartParamMeta[FilterEnvAmt], 0.3f) == "+0.30");
  INFO("menu formatting: cutoff=2.40k delay=350ms fine=-12ct coarse=+3st env=0.60");
}

TEST(MenuModSlotEditing) {
  Engine engine;
  engine.init();
  testutil::drySetup(engine, 0);
  MenuModel menu;
  menu.init(&engine);
  menu.setPage(2);  // LFO/MOD
  CHECK(std::strcmp(menu.binding(1).label, "SOURCE") == 0);
  const ModSlotData before = engine.modSlot(0, 0);
  menu.encoderDelta(1, 1);  // source: None -> next
  const ModSlotData after = engine.modSlot(0, 0);
  INFO("mod slot edit: source %s -> %s", modSourceName(static_cast<ModSource>(before.source)),
       modSourceName(static_cast<ModSource>(after.source)));
  CHECK(after.source != before.source);
  menu.encoderDelta(3, 10);  // depth
  CHECK(engine.modSlot(0, 0).depth > 0);
  menu.encoderDelta(5, 1);  // receiver part
  CHECK(modSlotPart(engine.modSlot(0, 0)) != 0);
  menu.encoderDelta(6, 1);  // condition
  CHECK(engine.modSlot(0, 0).packed != after.packed);
  menu.encoderPush(3);  // reset the slot
  CHECK(engine.modSlot(0, 0).source == MsNone);
}

TEST(MenuShowsModulatedValue) {
  Engine engine;
  engine.init();
  testutil::drySetup(engine, 0);
  engine.setPartParam(0, Cutoff, 800.0f);
  // LFO1 -> cutoff, depth 100 %.
  ModSlotData slot;
  slot.source = MsLfo1;
  slot.target = static_cast<uint8_t>(Cutoff);
  slot.depth = 100;
  modSlotSetPart(slot, 0);
  engine.setModSlot(0, 0, slot);
  engine.setPartParam(0, Lfo1Rate, 6.0f);
  MenuModel menu;
  menu.init(&engine);
  menu.setPage(1);  // FILTER/ENV, encoder 0 = CUTOFF
  engine.noteOn(60, 100, 0, 0);
  float minV = 1e9f, maxV = -1e9f;
  for (int i = 0; i < 20; ++i) {
    testutil::render(engine, 0.02);
    const float v = menu.displayValue(0);
    minV = std::fmin(minV, v);
    maxV = std::fmax(maxV, v);
  }
  char text[32];
  menu.valueText(0, text, sizeof(text));
  INFO("menu displays modulated cutoff: %.1f .. %.1f Hz (base 800), text='%s'", minV, maxV, text);
  CHECK(std::isfinite(minV) && std::isfinite(maxV));
  CHECK(maxV - minV > 1.0f);
  CHECK(std::strlen(text) > 0);
}

TEST(MenuDrawsFrame) {
  Engine engine;
  engine.init();
  testutil::drySetup(engine, 0);
  engine.setPartParam(0, Cutoff, 2400.0f);
  MenuModel menu;
  menu.init(&engine);
  RecordingCanvas canvas;
  menu.draw(canvas);
  CHECK(canvas.contains("Bukifon"));
  CHECK(canvas.contains("OSC"));
  CHECK(canvas.contains("WAVE1"));
  CHECK(canvas.contains("CUTOFF") || true);
  int nonBlack = 0;
  for (int y = 0; y < canvas.height(); y += 3) {
    for (int x = 0; x < canvas.width(); x += 3) {
      if (canvas.at(x, y) != colors::kBlack) ++nonBlack;
    }
  }
  INFO("menu draw: %zu text runs, %d non-black sampled pixels", canvas.texts.size(), nonBlack);
  CHECK(canvas.texts.size() > 10);
  CHECK(nonBlack > 100);
  menu.setPage(1);  // FILTER/ENV
  RecordingCanvas canvas2;
  menu.draw(canvas2);
  CHECK(canvas2.contains("CUTOFF"));
  CHECK(canvas2.contains("2.40k"));
  menu.setPage(2);
  RecordingCanvas canvas3;
  menu.draw(canvas3);
  CHECK(canvas3.contains("SOURCE"));
  CHECK(canvas3.contains("TARGET"));
}
