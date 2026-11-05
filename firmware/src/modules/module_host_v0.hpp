// SPDX-License-Identifier: GPL-3.0-or-later
// Host-side wrapper for Bukifon module API v0.1.
//
// Enforces the ABI limits: API version, frame size (<= 64), declared stack and
// state size, real-time budget (overruns are counted and the module is bypassed
// after BUKIFON_MODULE_MAX_OVERRUNS).  v0.1 adds:
//   * host services (monotonic time, log) attached via attach_host();
//   * event delivery (note/gate/transport/...) via on_event();
//   * lock-free-ish host-side parameter smoothing (setParamSmoothed).
//
// Log rules: log() is allowed outside the audio path only.  Calls made while
// process() runs are counted as violations and the message is dropped (no I/O
// from the audio thread).
#pragma once

#include <cstdint>
#include <functional>

#include "bukifon_module.h"

namespace bukifon {

class ModuleHostV0 {
 public:
  using CostProvider = std::function<uint32_t(uint32_t frames)>;

  ModuleHostV0() = default;
  ~ModuleHostV0();
  ModuleHostV0(const ModuleHostV0&) = delete;
  ModuleHostV0& operator=(const ModuleHostV0&) = delete;

  bool attach(const bukifon_module_v0_t* module);
  void detach();
  bool attached() const { return module_ != nullptr && instance_ != nullptr; }

  bool prepare(uint32_t sampleRate);
  void reset();
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

  void setCostProvider(CostProvider provider) { costProvider_ = std::move(provider); }
  static uint32_t defaultBudgetUs() { return BUKIFON_MODULE_BUDGET_US; }
  void setBudgetUs(uint32_t budgetUs) { budgetUs_ = budgetUs; }
  uint32_t budgetUs() const { return budgetUs_; }

  // --- v0.1 host services ------------------------------------------------
  bool hostServicesAttached() const { return hostServicesAttached_; }
  uint64_t hostNowUs() const;
  uint32_t logMessages() const { return logCount_; }
  uint32_t logViolations() const { return logViolations_; }
  const char* lastLogMessage() const { return lastLog_; }

  // --- v0.1 events -------------------------------------------------------
  bool sendEvent(const bukifon_event_t& event);
  bool acceptsEvents() const { return module_ != nullptr && module_->on_event != nullptr; }
  uint32_t eventsSent() const { return eventsSent_; }

  // --- v0.1 parameter smoothing -----------------------------------------
  // timeMs <= 0: immediate set.  Otherwise the host ramps the value and calls
  // module->set_param() at ABI block boundaries (max one update per <=64 frames).
  void setParamSmoothed(uint16_t id, float value, float timeMs);
  float smoothedValue(uint16_t id) const;
  bool smoothingActive(uint16_t id) const;

 private:
  static constexpr int kMaxSmoothers = BUKIFON_MODULE_MAX_PARAMS;
  struct Smoother {
    float target = 0.0f;
    float current = 0.0f;
    float timeMs = 0.0f;
    bool active = false;
    bool initialized = false;
  };

  uint32_t measureCost(uint32_t frames);
  bool validate(const bukifon_module_v0_t* module);
  void applySmoothing(uint32_t frames);
  void handleLog(int level, const char* message);
  static uint64_t hostNowUsThunk(void* context);
  static void hostLogThunk(void* context, int level, const char* message);
  void resetV01State();

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

  Smoother smoothers_[kMaxSmoothers];
  float lastSentParam_[kMaxSmoothers] = {};
  // Persistent storage for the services table: the module may keep the pointer
  // for its whole lifetime, so it must outlive attach().
  bukifon_host_services_t hostServices_{};
  bool hostServicesAttached_ = false;
  bool inProcess_ = false;
  uint32_t logCount_ = 0;
  uint32_t logViolations_ = 0;
  uint32_t eventsSent_ = 0;
  char lastLog_[160] = {};
};

}  // namespace bukifon
