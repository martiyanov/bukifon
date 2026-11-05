// SPDX-License-Identifier: GPL-3.0-or-later
// Host-side wrapper for Bukifon module API v0.
//
// Enforces the ABI limits: API version, frame size (<= 64), declared stack and
// state size, real-time budget (overruns are counted and the module is bypassed
// after BUKIFON_MODULE_MAX_OVERRUNS), and exposes state save/load.  The audio
// path is portable C++ (host tests + ESP32 builds); the embedded build should
// feed it the cycle counter instead of the host clock (TODO(hw)).
#pragma once

#include <cstdint>
#include <functional>
#include <vector>

#include "bukifon_module.h"

namespace bukifon {

class ModuleHostV0 {
 public:
  using CostProvider = std::function<uint32_t(uint32_t frames)>;

  ModuleHostV0() = default;
  ~ModuleHostV0();
  ModuleHostV0(const ModuleHostV0&) = delete;
  ModuleHostV0& operator=(const ModuleHostV0&) = delete;

  // Validates the ABI and creates one instance.  Returns false on any ABI limit
  // violation (leaves the host detached).
  bool attach(const bukifon_module_v0_t* module);
  void detach();
  bool attached() const { return module_ != nullptr && instance_ != nullptr; }

  bool prepare(uint32_t sampleRate);
  void reset();

  // Renders interleaved stereo (frames may be > 64: split into ABI-sized calls).
  void process(const float* inL, const float* inR, float* outL, float* outR, int frames);

  bool setParam(uint16_t id, float value);
  uint32_t paramCount() const;
  const bukifon_param_desc_t* paramDesc(uint32_t index) const;

  uint32_t stateSize() const;
  bool saveState(uint8_t* out, uint32_t capacity);
  bool loadState(const uint8_t* data, uint32_t size);

  const bukifon_module_desc_t* descriptor() const { return descriptor_; }
  const bukifon_module_v0_t* module() const { return module_; }
  bool bypassed() const { return bypassed_; }
  uint32_t overrunCount() const { return overruns_; }
  void clearBypass();

  // Test hook: deterministic cost injection (microseconds per ABI call).
  void setCostProvider(CostProvider provider) { costProvider_ = std::move(provider); }
  // Host default = real wall clock (microseconds); embedded uses cycles (TODO).
  static uint32_t defaultBudgetUs() { return BUKIFON_MODULE_BUDGET_US; }
  void setBudgetUs(uint32_t budgetUs) { budgetUs_ = budgetUs; }
  uint32_t budgetUs() const { return budgetUs_; }

 private:
  uint32_t measureCost(uint32_t frames);
  bool validate(const bukifon_module_v0_t* module);

  const bukifon_module_v0_t* module_ = nullptr;
  const bukifon_module_desc_t* descriptor_ = nullptr;
  void* instance_ = nullptr;
  uint32_t sampleRate_ = 48000;
  uint32_t budgetUs_ = BUKIFON_MODULE_BUDGET_US;
  uint32_t overruns_ = 0;
  bool bypassed_ = false;
  bool prepared_ = false;
  CostProvider costProvider_;
  float scratchIn_[BUKIFON_MODULE_MAX_FRAMES * 2] = {};
  float scratchOut_[BUKIFON_MODULE_MAX_FRAMES * 2] = {};
};

}  // namespace bukifon
