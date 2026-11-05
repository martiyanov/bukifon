// SPDX-License-Identifier: GPL-3.0-or-later
// Lock-free single-producer / single-consumer ring buffer used for core0<->core1
// communication on RP2040 and for host tests.
#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <type_traits>

namespace bukifon {

// Capacity must be a power of two. Producer calls push(), consumer calls pop().
template <typename T, size_t Capacity>
class SpscQueue {
 public:
  static_assert((Capacity & (Capacity - 1)) == 0, "Capacity must be a power of two");
  static_assert(std::is_trivially_copyable<T>::value, "T must be trivially copyable");

  SpscQueue() = default;
  SpscQueue(const SpscQueue&) = delete;
  SpscQueue& operator=(const SpscQueue&) = delete;

  bool push(const T& item) {
    const size_t head = head_.load(std::memory_order_relaxed);
    const size_t next = (head + 1) & kMask;
    if (next == tail_.load(std::memory_order_acquire)) return false;  // full
    buffer_[head] = item;
    head_.store(next, std::memory_order_release);
    return true;
  }

  bool pop(T* out) {
    const size_t tail = tail_.load(std::memory_order_relaxed);
    if (tail == head_.load(std::memory_order_acquire)) return false;  // empty
    *out = buffer_[tail];
    tail_.store((tail + 1) & kMask, std::memory_order_release);
    return true;
  }

  bool empty() const {
    return tail_.load(std::memory_order_acquire) == head_.load(std::memory_order_acquire);
  }

  size_t size() const {
    const size_t h = head_.load(std::memory_order_acquire);
    const size_t t = tail_.load(std::memory_order_acquire);
    return (h - t) & kMask;
  }

  static constexpr size_t capacity() { return Capacity - 1; }
  void reset() { head_.store(0); tail_.store(0); }

 private:
  static constexpr size_t kMask = Capacity - 1;
  alignas(64) std::atomic<size_t> head_{0};
  alignas(64) std::atomic<size_t> tail_{0};
  T buffer_[Capacity]{};
};

}  // namespace bukifon
