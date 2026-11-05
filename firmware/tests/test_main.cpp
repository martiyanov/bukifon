// SPDX-License-Identifier: GPL-3.0-or-later
#include <chrono>
#include <cstdio>

#include "test_framework.hpp"

int main() {
  std::printf("Bukifon host tests\n");
  std::printf("==================\n");
  int run = 0;
  int failedTests = 0;
  const auto t0 = std::chrono::steady_clock::now();
  for (const auto& tc : testfw::registry()) {
    std::printf("[RUN ] %s\n", tc.name);
    std::fflush(stdout);
    const int before = testfw::failureCount();
    const auto start = std::chrono::steady_clock::now();
    tc.fn();
    const auto end = std::chrono::steady_clock::now();
    const double ms = std::chrono::duration<double, std::milli>(end - start).count();
    const bool ok = testfw::failureCount() == before;
    std::printf("[%s] %-34s %8.2f ms\n", ok ? " OK " : "FAIL", tc.name, ms);
    ++run;
    if (!ok) ++failedTests;
  }
  const auto t1 = std::chrono::steady_clock::now();
  const double totalMs = std::chrono::duration<double, std::milli>(t1 - t0).count();
  std::printf("------------------\n");
  std::printf("tests: %d, failed: %d, checks failed: %d, total %.1f ms\n", run, failedTests,
              testfw::failureCount(), totalMs);
  return failedTests == 0 ? 0 : 1;
}
