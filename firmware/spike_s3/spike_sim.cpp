// SPDX-License-Identifier: GPL-3.0-or-later
// Host simulation of the S3 spike (no hardware): runs the same buffers, metric
// accumulation and pass/fail logic that the devkit firmware uses.
//
//   g++ -std=c++17 -O2 -I. spike_sim.cpp -o /tmp/spike_sim && /tmp/spike_sim
//   (or: bash run_host_spike.sh)
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "spike_core.hpp"

using namespace bukifon::spike;

int main(int argc, char** argv) {
  uint32_t blocks = 2000;
  uint64_t seed = 0xB0C0FFEEull;
  const char* outPath = nullptr;
  for (int i = 1; i < argc; ++i) {
    if (std::strcmp(argv[i], "--blocks") == 0 && i + 1 < argc) {
      blocks = static_cast<uint32_t>(std::strtoul(argv[++i], nullptr, 10));
    } else if (std::strcmp(argv[i], "--seed") == 0 && i + 1 < argc) {
      seed = std::strtoull(argv[++i], nullptr, 0);
    } else if (std::strcmp(argv[i], "--out") == 0 && i + 1 < argc) {
      outPath = argv[++i];
    }
  }
  std::printf("S3 spike host simulation (lite concept; P4 is primary SKU)\n");
  std::printf("blocks=%u seed=0x%llx\n", blocks, static_cast<unsigned long long>(seed));
  SpikeMetrics metrics;
  char report[512];
  const bool ok = runHostSpikeSimulation(blocks, seed, &metrics, report, sizeof(report));
  char line[512];
  metrics.logLine(line, sizeof(line));
  std::printf("%s\n", line);
  std::printf("%s\n", report);
  std::printf("SPIKE_RESULT pass=%d reason=%s\n", ok ? 1 : 0, ok ? "PASS" : "FAIL");
  if (outPath) {
    FILE* file = std::fopen(outPath, "wb");
    if (file) {
      std::fprintf(file, "%s\n%s\n", line, report);
      std::fclose(file);
    }
  }
  return ok ? 0 : 1;
}
