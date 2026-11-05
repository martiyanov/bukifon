// SPDX-License-Identifier: GPL-3.0-or-later
// Bukifon host demo / screenshot tool.
//
//   ./bukifon_sim [--out DIR] [--log FILE] [--bars N] [--determinism]
//
// 1. builds the demo pattern (4 tracks x 16 steps, one p-lock),
// 2. plays N bars on the host simulator (default 16),
// 3. writes the deterministic event log and verifies it,
// 4. renders the four 800x480 UI screens + the four device-mode panels
//    (Synth / Sampler / DAW-controller / USB-keyboard) as PPM (converted to PNG
//    by tools/ppm_to_png.py).
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#include "bukifon_ui_theme.h"
#include "sim/simulator.hpp"
#include "ui/ui800.hpp"

using namespace bukifon;

namespace {

struct Args {
  std::string outDir = "artifacts/ui";
  std::string logPath = "tests/out/sim_event_log.txt";
  std::string theme;
  std::string themeConfig;  // empty: no auto-load; pass --theme-config explicitly
  int bars = 16;
  bool determinism = true;
};

Args parseArgs(int argc, char** argv) {
  Args args;
  for (int i = 1; i < argc; ++i) {
    if (std::strcmp(argv[i], "--out") == 0 && i + 1 < argc) {
      args.outDir = argv[++i];
    } else if (std::strcmp(argv[i], "--log") == 0 && i + 1 < argc) {
      args.logPath = argv[++i];
    } else if (std::strcmp(argv[i], "--bars") == 0 && i + 1 < argc) {
      args.bars = std::atoi(argv[++i]);
    } else if (std::strcmp(argv[i], "--theme") == 0 && i + 1 < argc) {
      args.theme = argv[++i];
    } else if (std::strcmp(argv[i], "--theme-config") == 0 && i + 1 < argc) {
      args.themeConfig = argv[++i];
    } else if (std::strcmp(argv[i], "--no-determinism") == 0) {
      args.determinism = false;
    } else if (std::strcmp(argv[i], "--help") == 0) {
      std::printf(
          "usage: bukifon_sim [--out DIR] [--log FILE] [--bars N] [--no-determinism]\n"
          "                   [--theme Night|Amber|Phosphor|Cream] [--theme-config PATH]\n");
      std::exit(0);
    }
  }
  if (args.bars < 1) args.bars = 1;
  if (args.bars > 64) args.bars = 64;
  return args;
}

bool writeScreens(sim::Simulator& simulator, const std::string& outDir) {
  ui::Framebuffer800 framebuffer;
  if (!framebuffer.valid()) {
    std::printf("ERROR: cannot allocate 800x480 framebuffer\n");
    return false;
  }
  const ui::Screen screens[4] = {ui::Screen::Main, ui::Screen::Sequencer, ui::Screen::Mixer,
                                 ui::Screen::Modules};
  const char* names[4] = {"main", "sequencer", "mixer", "modules"};
  bool ok = true;
  for (int i = 0; i < 4; ++i) {
    framebuffer.clear(colors::kBlack);
    const ui::UiSnapshot snapshot = simulator.snapshot(screens[i]);
    ui::drawUi800(framebuffer, snapshot);
    const std::string path = outDir + "/" + names[i] + ".ppm";
    if (!framebuffer.writePpm(path.c_str())) {
      std::printf("ERROR: cannot write %s\n", path.c_str());
      ok = false;
      continue;
    }
    std::printf("wrote %s\n", path.c_str());
  }
  // Mode-specific panels: same UI shell, different status-bar MODE + panels.
  const DeviceMode modes[4] = {DeviceMode::Synth, DeviceMode::Sampler, DeviceMode::DawController,
                               DeviceMode::UsbKeyboard};
  const char* modeNames[4] = {"synth", "sampler", "daw", "usb_kbd"};
  for (int i = 0; i < 4; ++i) {
    framebuffer.clear(colors::kBlack);
    ui::UiSnapshot snapshot = simulator.snapshot(ui::Screen::Main);
    ui::uiSnapshotForDeviceMode(&snapshot, modes[i]);
    ui::drawUi800(framebuffer, snapshot);
    const std::string path = outDir + "/" + modeNames[i] + ".ppm";
    if (!framebuffer.writePpm(path.c_str())) {
      std::printf("ERROR: cannot write %s\n", path.c_str());
      ok = false;
      continue;
    }
    std::printf("wrote %s (MODE %s)\n", path.c_str(), deviceModeShortName(modes[i]));
  }
  return ok;
}

}  // namespace

int main(int argc, char** argv) {
  const Args args = parseArgs(argc, argv);
  if (!args.themeConfig.empty()) bukifon_ui_theme_load(args.themeConfig.c_str());
  if (!args.theme.empty()) {
    if (!bukifon_ui_theme_set(args.theme.c_str())) {
      std::printf("ERROR: unknown theme '%s' (Night|Amber|Phosphor|Cream)\n",
                  args.theme.c_str());
      return 2;
    }
    if (!args.themeConfig.empty()) bukifon_ui_theme_save(args.themeConfig.c_str());
  }
  std::printf("Bukifon host demo\n");
  std::printf("theme: %s\n", bukifon_ui_theme_name(bukifon_ui_theme_current()));
  std::printf("=================\n");

  sim::Simulator simulator;
  simulator.init();
  const sim::EventLog& log = simulator.runDemo(args.bars);
  const sim::EventLog::Summary summary = log.summarize();
  const sim::Simulator::Stats& stats = simulator.stats();
  const int expectedTriggers = args.bars * kSeqSteps * kSeqTracks;

  std::printf("bars: %d (%.1f s, %llu frames, %.2f s render)\n", args.bars, stats.seconds,
              static_cast<unsigned long long>(stats.frames), stats.renderSeconds);
  std::printf("events: %zu (monotonic=%s) first=%llu last=%llu\n", summary.count,
              summary.monotonic ? "yes" : "NO",
              static_cast<unsigned long long>(summary.firstFrame),
              static_cast<unsigned long long>(summary.lastFrame));
  std::printf("notes: on=%zu off=%zu plocks=%zu params=%zu mutes=%zu\n", summary.notesOn,
              summary.notesOff, summary.plocks, summary.params, summary.mutes);
  std::printf("expected triggers: %d (4 tracks x 16 steps x %d bars)\n", expectedTriggers,
              args.bars);
  std::printf("audio peak: %.3f\n", stats.peak);

  bool ok = true;
  if (!summary.monotonic) ok = false;
  if (static_cast<int>(summary.notesOn) != expectedTriggers) {
    std::printf("ERROR: note-on count mismatch: %zu != %d\n", summary.notesOn, expectedTriggers);
    ok = false;
  }
  if (summary.plocks < static_cast<size_t>(args.bars)) {
    std::printf("ERROR: expected at least one p-lock per bar, got %zu\n", summary.plocks);
    ok = false;
  }
  if (stats.peak <= 0.0f || stats.peak > 1.0f) {
    std::printf("ERROR: audio peak out of range: %.3f\n", stats.peak);
    ok = false;
  }

  const std::string logPath = args.logPath;
  if (!log.saveToFile(logPath.c_str())) {
    std::printf("ERROR: cannot write event log %s\n", logPath.c_str());
    ok = false;
  } else {
    std::printf("event log: %s\n", logPath.c_str());
  }

  if (args.determinism) {
    sim::Simulator rerun;
    rerun.init();
    const sim::EventLog& log2 = rerun.runDemo(args.bars);
    if (log.equals(log2)) {
      std::printf("determinism: PASS (two runs produced identical event logs)\n");
    } else {
      std::printf("determinism: FAIL (event logs differ)\n");
      ok = false;
    }
  }

  // Screenshots are rendered from a short, deterministic playback so the level
  // meters show live audio.
  sim::Simulator uiSim;
  uiSim.init();
  uiSim.buildDemoPattern();
  uiSim.setTrackMuted(2, true);  // show a muted track on the sequencer screen
  uiSim.play();
  uiSim.runBars(2);
  if (!writeScreens(uiSim, args.outDir)) ok = false;

  std::printf("=================\n");
  std::printf("RESULT: %s\n", ok ? "PASS" : "FAIL");
  return ok ? 0 : 1;
}
