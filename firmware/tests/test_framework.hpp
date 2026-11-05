// SPDX-License-Identifier: GPL-3.0-or-later
// Tiny dependency-free unit test framework for the Bukifon host tests.
#pragma once

#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <string>
#include <vector>

namespace testfw {

struct TestCase {
  const char* name;
  void (*fn)();
};

inline std::vector<TestCase>& registry() {
  static std::vector<TestCase> r;
  return r;
}

struct Registrar {
  Registrar(const char* name, void (*fn)()) { registry().push_back({name, fn}); }
};

inline int& failureCount() {
  static int f = 0;
  return f;
}

inline void check(bool ok, const char* expr, const char* file, int line) {
  if (!ok) {
    std::printf("    FAIL: %s (%s:%d)\n", expr, file, line);
    ++failureCount();
  }
}

inline void checkNear(double a, double b, double tol, const char* expr, const char* file, int line) {
  const bool ok = std::fabs(a - b) <= tol;
  if (!ok) {
    std::printf("    FAIL: %s = %.6f, expected %.6f +/- %.6f (%s:%d)\n", expr, a, b, tol, file,
                line);
    ++failureCount();
  }
}

inline void info(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  std::vprintf(fmt, args);
  va_end(args);
  std::printf("\n");
}

}  // namespace testfw

#define TEST(name)                              \
  static void name();                           \
  static testfw::Registrar test_reg_##name(#name, name); \
  static void name()

#define CHECK(cond) testfw::check((cond), #cond, __FILE__, __LINE__)
#define CHECK_CLOSE(a, b, tol) testfw::checkNear((a), (b), (tol), #a " ~ " #b, __FILE__, __LINE__)
#define INFO(...) testfw::info(__VA_ARGS__)
