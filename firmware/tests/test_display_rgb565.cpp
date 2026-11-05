// SPDX-License-Identifier: GPL-3.0-or-later
// RGB565 display backend tests: init/flush/full/partial/dirty-rects/fps model.
#include <cmath>
#include <cstdint>
#include <cstring>

#include "bench_alloc_probe.hpp"
#include "hal/display_rgb565.hpp"
#include "test_framework.hpp"

using namespace bukifon::hal;

namespace {

uint16_t* allocateFramebuffer(int width, int height) {
  return new uint16_t[static_cast<size_t>(width) * height];
}

}  // namespace

TEST(DisplayRgb565InitAndAttach) {
  DisplayRgb565 display;
  Rgb565Config config;
  config.width = 800;
  config.height = 480;
  config.bounceRows = 16;
  CHECK(display.init(config));
  CHECK(display.config().width == 800);
  CHECK(display.metrics().modeledFullFps > 50.0);
  CHECK(std::strstr(DisplayRgb565::backendName(), "TODO") != nullptr);
  Rgb565Config bad = config;
  bad.bounceRows = 17;
  CHECK(!display.init(bad));
  bad = config;
  bad.width = 0;
  CHECK(!display.init(bad));
  uint16_t* fb = allocateFramebuffer(800, 480);
  CHECK(display.attachFramebuffer(fb));
  CHECK(display.framebuffer() == fb);
  delete[] fb;
  INFO("display init: 800x480, 20 MHz pixel clock, 16-row bounce, host-sim backend");
}

TEST(DisplayRgb565FullFlushMetrics) {
  DisplayRgb565 display;
  Rgb565Config config;
  CHECK(display.init(config));
  uint16_t* fb = allocateFramebuffer(config.width, config.height);
  CHECK(display.attachFramebuffer(fb));
  display.clear(0x0000);
  display.fillRect(0, 0, 800, 2, 0xFFFF);
  CHECK(display.checksum() != 0);
  const uint32_t us = display.flushFull();
  CHECK(us == display.modeledFullFrameUs());
  CHECK(us > 15000 && us < 25000);  // ~19.2 ms at 20 MHz
  CHECK(display.metrics().fullFrames == 1);
  CHECK(display.metrics().bytesFlushed == 800u * 480u * 2u);
  CHECK(std::fabs(display.metrics().modeledFullFps - 52.083) < 0.1);
  delete[] fb;
  INFO("full flush: %u us, %llu bytes, modelled %.2f fps", us,
       static_cast<unsigned long long>(display.metrics().bytesFlushed),
       display.metrics().modeledFullFps);
}

TEST(DisplayRgb565DirtyRectsAndPartial) {
  DisplayRgb565 display;
  CHECK(display.init(Rgb565Config{}));
  uint16_t* fb = allocateFramebuffer(800, 480);
  CHECK(display.attachFramebuffer(fb));
  display.beginFrame();
  CHECK(display.addDirtyRect(10, 300, 300, 40));
  CHECK(display.addDirtyRect(0, 0, 800, 56));
  CHECK(display.dirtyRectCount() == 2);
  CHECK(display.dirtyRect(0).w == 300);
  CHECK(display.dirtyRect(1).h == 56);
  // Out-of-bounds rect is clamped; degenerate rect is dropped.
  CHECK(display.addDirtyRect(790, 470, 100, 100));
  CHECK(display.dirtyRect(2).w == 10);
  CHECK(display.dirtyRect(2).h == 10);
  CHECK(!display.addDirtyRect(0, 0, 0, 5));
  CHECK(display.metrics().droppedBands == 1);
  // Capacity is bounded: no allocations in the audio/display path.
  for (int i = 0; i < 10; ++i) display.addDirtyRect(0, 0, 1, 1);
  CHECK(display.dirtyRectCount() <= DisplayRgb565::kMaxDirtyRects);
  const uint32_t us = display.flushPartial(display.dirtyRect(0));
  CHECK(us > 0);
  CHECK(display.metrics().partialUpdates == 1);
  display.beginFrame();
  CHECK(display.dirtyRectCount() == 0);
  delete[] fb;
  INFO("dirty rects: clamping, capacity %d, partial flush %u us", DisplayRgb565::kMaxDirtyRects, us);
}

TEST(DisplayRgb565HostFrameSimulation) {
  DisplayRgb565 display;
  CHECK(display.init(Rgb565Config{}));
  uint16_t* fb = allocateFramebuffer(800, 480);
  CHECK(display.attachFramebuffer(fb));
  display.clear(0x1234);
  display.beginFrame();
  display.addDirtyRect(10, 300, 300, 40);
  display.hostSimulateFrame(false);
  CHECK(display.metrics().partialUpdates == 1);
  CHECK(std::fabs(display.metrics().modeledPartialFps - 130.208) < 0.5);
  display.hostSimulateFrame(true);
  CHECK(display.metrics().fullFrames == 1);
  CHECK(std::fabs(display.metrics().modeledFullFps - 52.083) < 0.1);
  delete[] fb;
  INFO("host frame sim matches host_p4 model: 52.08 full fps / 130.21 partial fps");
}

TEST(DisplayRgb565FlushNoAllocations) {
  DisplayRgb565 display;
  CHECK(display.init(Rgb565Config{}));
  uint16_t* fb = allocateFramebuffer(800, 480);
  CHECK(display.attachFramebuffer(fb));
  display.clear(0);
  bukifon::bench::allocProbeBegin();
  display.flushFull();
  display.beginFrame();
  display.addDirtyRect(10, 300, 300, 40);
  display.flushPartial(display.dirtyRect(0));
  display.hostSimulateFrame(true);
  bukifon::bench::allocProbeEnd();
  const uint64_t allocations = bukifon::bench::allocProbeCount();
  CHECK(allocations == 0);
  delete[] fb;
  INFO("display flush path: %llu allocations (must be 0)", static_cast<unsigned long long>(allocations));
}
