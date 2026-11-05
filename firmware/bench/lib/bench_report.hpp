// SPDX-License-Identifier: GPL-3.0-or-later
// JSON / CSV / table output for benchmark results.
#pragma once

#include <cstddef>
#include <string>

#include "bench_types.hpp"

namespace bukifon {
namespace bench {

struct BenchMeta {
  const char* tool = "bukifon-bench";
  const char* platform = "";
  const char* host = "";
  const char* compiler = "";
  const char* timestamp = "";
  const char* build = "";
  const char* notes = "";
};

std::string resultsToJson(const BenchMeta& meta, const ScenarioResult* results, int count);
std::string resultsToCsv(const ScenarioResult* results, int count);
std::string resultsToTable(const ScenarioResult* results, int count, bool allPass);
bool writeTextFile(const char* path, const std::string& text);

}  // namespace bench
}  // namespace bukifon
