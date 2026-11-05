// SPDX-License-Identifier: GPL-3.0-or-later
#include "bench_alloc_probe.hpp"

#include <atomic>
#include <cstdlib>
#include <new>

namespace bukifon {
namespace bench {
namespace {
std::atomic<bool> g_probeActive{false};
std::atomic<uint64_t> g_allocations{0};

inline void noteAllocation() {
  if (g_probeActive.load(std::memory_order_relaxed)) {
    g_allocations.fetch_add(1, std::memory_order_relaxed);
  }
}
}  // namespace

void allocProbeBegin() {
  g_allocations.store(0, std::memory_order_relaxed);
  g_probeActive.store(true, std::memory_order_release);
}
void allocProbeEnd() { g_probeActive.store(false, std::memory_order_release); }
uint64_t allocProbeCount() { return g_allocations.load(std::memory_order_relaxed); }
void allocProbeReset() { g_allocations.store(0, std::memory_order_relaxed); }

}  // namespace bench
}  // namespace bukifon

// Replaceable global allocation functions (C++17).
void* operator new(std::size_t size) {
  bukifon::bench::noteAllocation();
  void* p = std::malloc(size ? size : 1);
  if (!p) throw std::bad_alloc();
  return p;
}
void* operator new[](std::size_t size) {
  bukifon::bench::noteAllocation();
  void* p = std::malloc(size ? size : 1);
  if (!p) throw std::bad_alloc();
  return p;
}
void* operator new(std::size_t size, const std::nothrow_t&) noexcept {
  bukifon::bench::noteAllocation();
  return std::malloc(size ? size : 1);
}
void* operator new[](std::size_t size, const std::nothrow_t&) noexcept {
  bukifon::bench::noteAllocation();
  return std::malloc(size ? size : 1);
}
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete(void* p, std::size_t) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t) noexcept { std::free(p); }
void operator delete(void* p, const std::nothrow_t&) noexcept { std::free(p); }
void operator delete[](void* p, const std::nothrow_t&) noexcept { std::free(p); }

#if defined(__cpp_aligned_new)
void* operator new(std::size_t size, std::align_val_t alignment) {
  bukifon::bench::noteAllocation();
  void* p = std::aligned_alloc(static_cast<std::size_t>(alignment), size ? size : 1);
  if (!p) throw std::bad_alloc();
  return p;
}
void* operator new[](std::size_t size, std::align_val_t alignment) {
  bukifon::bench::noteAllocation();
  void* p = std::aligned_alloc(static_cast<std::size_t>(alignment), size ? size : 1);
  if (!p) throw std::bad_alloc();
  return p;
}
void* operator new(std::size_t size, std::align_val_t alignment, const std::nothrow_t&) noexcept {
  bukifon::bench::noteAllocation();
  return std::aligned_alloc(static_cast<std::size_t>(alignment), size ? size : 1);
}
void operator delete(void* p, std::align_val_t) noexcept { std::free(p); }
void operator delete[](void* p, std::align_val_t) noexcept { std::free(p); }
void operator delete(void* p, std::size_t, std::align_val_t) noexcept { std::free(p); }
void operator delete[](void* p, std::size_t, std::align_val_t) noexcept { std::free(p); }
#endif
