// SPDX-License-Identifier: GPL-3.0-or-later
#include "bench_report.hpp"

#include <cstdarg>
#include <cstdio>
#include <cstring>

namespace bukifon {
namespace bench {
namespace {

void appendf(std::string& out, const char* format, ...) {
  char buffer[512];
  va_list args;
  va_start(args, format);
  std::vsnprintf(buffer, sizeof(buffer), format, args);
  va_end(args);
  out += buffer;
}

}  // namespace

std::string resultsToJson(const BenchMeta& meta, const ScenarioResult* results, int count) {
  std::string out;
  out.reserve(4096);
  appendf(out, "{\n");
  appendf(out, "  \"schema\": \"bukifon-bench-v1\",\n");
  appendf(out, "  \"tool\": \"%s\",\n", meta.tool ? meta.tool : "");
  appendf(out, "  \"platform\": \"%s\",\n", meta.platform ? meta.platform : "");
  appendf(out, "  \"host\": \"%s\",\n", meta.host ? meta.host : "");
  appendf(out, "  \"compiler\": \"%s\",\n", meta.compiler ? meta.compiler : "");
  appendf(out, "  \"timestamp\": \"%s\",\n", meta.timestamp ? meta.timestamp : "");
  appendf(out, "  \"build\": \"%s\",\n", meta.build ? meta.build : "");
  appendf(out, "  \"notes\": \"%s\",\n", meta.notes ? meta.notes : "");
  appendf(out, "  \"block_frames\": %d,\n", kBlockFrames);
  appendf(out, "  \"sample_rate\": %d,\n", kSampleRate);
  appendf(out, "  \"deadline_us\": %.4f,\n", kDeadlineUs);
  appendf(out, "  \"audio_max_block_us\": %.4f,\n", kMaxBlockTimeUs);
  bool allPass = true;
  for (int i = 0; i < count; ++i) allPass = allPass && results[i].pass;
  appendf(out, "  \"all_pass\": %s,\n", allPass ? "true" : "false");
  appendf(out, "  \"scenarios\": [\n");
  for (int i = 0; i < count; ++i) {
    const ScenarioResult& r = results[i];
    appendf(out, "    {\n");
    appendf(out, "      \"name\": \"%s\",\n", r.name ? r.name : "");
    appendf(out, "      \"description\": \"%s\",\n", r.description ? r.description : "");
    appendf(out, "      \"blocks\": %u,\n", r.blocks);
    appendf(out, "      \"block_frames\": %u,\n", r.blockFrames);
    appendf(out, "      \"deadline_us\": %.4f,\n", r.criteria.deadlineUs);
    appendf(out, "      \"max_block_us\": %.4f,\n", r.criteria.maxBlockTimeUs);
    appendf(out, "      \"deterministic\": %s,\n", r.deterministic ? "true" : "false");
    appendf(out, "      \"pass\": %s,\n", r.pass ? "true" : "false");
    appendf(out, "      \"fail_reason\": \"%s\",\n", r.failReason ? r.failReason : "");
    appendf(out, "      \"overruns\": %u,\n", r.overruns);
    appendf(out, "      \"checksum\": %llu,\n", static_cast<unsigned long long>(r.checksum));
    appendf(out, "      \"times_us\": {\"min\": %.4f, \"max\": %.4f, \"mean\": %.4f, "
                 "\"p50\": %.4f, \"p95\": %.4f, \"p99\": %.4f},\n",
            r.stats.minUs, r.stats.maxUs, r.stats.meanUs, r.stats.p50Us, r.stats.p95Us,
            r.stats.p99Us);
    appendf(out, "      \"metrics\": [");
    for (int m = 0; m < r.metricCount; ++m) {
      appendf(out, "%s{\"name\": \"%s\", \"value\": %.4f, \"unit\": \"%s\"}",
              m == 0 ? "" : ", ", r.metrics[m].name ? r.metrics[m].name : "",
              r.metrics[m].value, r.metrics[m].unit ? r.metrics[m].unit : "");
    }
    appendf(out, "]\n");
    appendf(out, "    }%s\n", i + 1 < count ? "," : "");
  }
  appendf(out, "  ]\n}\n");
  return out;
}

std::string resultsToCsv(const ScenarioResult* results, int count) {
  std::string out;
  out +=
      "scenario,blocks,block_frames,min_us,max_us,mean_us,p50_us,p95_us,p99_us,overruns,"
      "deterministic,pass,checksum\n";
  char line[512];
  for (int i = 0; i < count; ++i) {
    const ScenarioResult& r = results[i];
    std::snprintf(line, sizeof(line),
                  "%s,%u,%u,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%u,%d,%d,%llu\n",
                  r.name ? r.name : "", r.blocks, r.blockFrames, r.stats.minUs, r.stats.maxUs,
                  r.stats.meanUs, r.stats.p50Us, r.stats.p95Us, r.stats.p99Us, r.overruns,
                  r.deterministic ? 1 : 0, r.pass ? 1 : 0,
                  static_cast<unsigned long long>(r.checksum));
    out += line;
  }
  return out;
}

std::string resultsToTable(const ScenarioResult* results, int count, bool allPass) {
  std::string out;
  out += "scenario          blocks   mean_us    max_us    p99_us  overruns  pass  det  checksum\n";
  out += "---------------------------------------------------------------------------------------\n";
  char line[256];
  for (int i = 0; i < count; ++i) {
    const ScenarioResult& r = results[i];
    std::snprintf(line, sizeof(line), "%-17s %6u %9.2f %9.2f %9.2f %9u  %4s  %3s  %llx\n",
                  r.name ? r.name : "", static_cast<unsigned>(r.blocks), r.stats.meanUs,
                  r.stats.maxUs, r.stats.p99Us, static_cast<unsigned>(r.overruns),
                  r.pass ? "PASS" : "FAIL", r.deterministic ? "yes" : "no",
                  static_cast<unsigned long long>(r.checksum));
    out += line;
  }
  out += "---------------------------------------------------------------------------------------\n";
  out += allPass ? "RESULT: ALL SCENARIOS PASS\n" : "RESULT: FAIL (see per-scenario reasons)\n";
  return out;
}

bool writeTextFile(const char* path, const std::string& text) {
  if (!path) return false;
  FILE* file = std::fopen(path, "wb");
  if (!file) return false;
  const bool ok = std::fwrite(text.data(), 1, text.size(), file) == text.size();
  std::fclose(file);
  return ok;
}

}  // namespace bench
}  // namespace bukifon
