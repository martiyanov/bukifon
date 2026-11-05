// SPDX-License-Identifier: GPL-3.0-or-later
#include "modules/module_host_v0.hpp"

#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <cstring>

#if defined(ARDUINO)
#include <esp_timer.h>
#endif

namespace bukifon {
namespace {

bool descriptorValid(const bukifon_module_desc_t* desc) {
  if (!desc) return false;
  if (desc->api_version != BUKIFON_MODULE_API_VERSION) return false;
  if (desc->max_frames == 0 || desc->max_frames > BUKIFON_MODULE_MAX_FRAMES) return false;
  if (desc->stack_bytes > BUKIFON_MODULE_MAX_STACK) return false;
  if (desc->state_size > BUKIFON_MODULE_MAX_STATE) return false;
  if (desc->param_count > BUKIFON_MODULE_MAX_PARAMS) return false;
  if (desc->param_count > 0 && !desc->params) return false;
  if (!desc->id || !desc->name || !desc->version) return false;
  return true;
}

bool tableValid(const bukifon_module_v0_t* module) {
  if (!module) return false;
  if (module->api_version != BUKIFON_MODULE_API_VERSION) return false;
  return module->descriptor && module->create && module->prepare && module->reset &&
         module->process && module->set_param && module->state_size && module->save_state &&
         module->load_state && module->destroy;
}

}  // namespace

ModuleHostV0::~ModuleHostV0() { detach(); }

bool ModuleHostV0::validate(const bukifon_module_v0_t* module) {
  if (!tableValid(module)) return false;
  const bukifon_module_desc_t* desc = module->descriptor();
  return descriptorValid(desc);
}

void ModuleHostV0::resetV01State() {
  for (int i = 0; i < kMaxSmoothers; ++i) {
    smoothers_[i] = Smoother{};
    lastSentParam_[i] = 0.0f;
  }
  hostServicesAttached_ = false;
  inProcess_ = false;
  logCount_ = 0;
  logViolations_ = 0;
  eventsSent_ = 0;
  lastLog_[0] = '\0';
}

bool ModuleHostV0::attach(const bukifon_module_v0_t* module) {
  detach();
  if (!validate(module)) return false;
  const bukifon_module_desc_t* desc = module->descriptor();
  void* instance = module->create();
  if (!instance) return false;
  module_ = module;
  descriptor_ = desc;
  instance_ = instance;
  overruns_ = 0;
  bypassed_ = false;
  prepared_ = false;
  resetV01State();
  if (module_->attach_host) {
    hostServices_.context = this;
    hostServices_.now_us = &ModuleHostV0::hostNowUsThunk;
    hostServices_.log = &ModuleHostV0::hostLogThunk;
    if (module_->attach_host(instance_, &hostServices_) < 0) {
      module_->destroy(instance_);
      module_ = nullptr;
      descriptor_ = nullptr;
      instance_ = nullptr;
      return false;
    }
    hostServicesAttached_ = true;
  }
  return true;
}

void ModuleHostV0::detach() {
  if (module_ && instance_ && module_->destroy) module_->destroy(instance_);
  module_ = nullptr;
  descriptor_ = nullptr;
  instance_ = nullptr;
  overruns_ = 0;
  bypassed_ = false;
  prepared_ = false;
  resetV01State();
}

bool ModuleHostV0::prepare(uint32_t sampleRate) {
  if (!attached()) return false;
  const int rc = module_->prepare(instance_, sampleRate);
  if (rc != 0) return false;
  sampleRate_ = sampleRate;
  prepared_ = true;
  module_->reset(instance_);
  return true;
}

void ModuleHostV0::reset() {
  if (!attached()) return;
  module_->reset(instance_);
  overruns_ = 0;
  bypassed_ = false;
  for (int i = 0; i < kMaxSmoothers; ++i) {
    if (smoothers_[i].initialized) {
      smoothers_[i].current = smoothers_[i].target;
      smoothers_[i].active = false;
    }
  }
}

uint64_t ModuleHostV0::hostNowUs() const {
#if defined(ARDUINO)
  return static_cast<uint64_t>(esp_timer_get_time());
#else
  using namespace std::chrono;
  return static_cast<uint64_t>(
      duration_cast<microseconds>(steady_clock::now().time_since_epoch()).count());
#endif
}

uint64_t ModuleHostV0::hostNowUsThunk(void* context) {
  return context ? static_cast<ModuleHostV0*>(context)->hostNowUs() : 0;
}

void ModuleHostV0::hostLogThunk(void* context, int level, const char* message) {
  if (context) static_cast<ModuleHostV0*>(context)->handleLog(level, message);
}

void ModuleHostV0::handleLog(int level, const char* message) {
  if (inProcess_) {
    ++logViolations_;  // logging from the audio path is forbidden: drop it
    return;
  }
  ++logCount_;
  std::snprintf(lastLog_, sizeof(lastLog_), "[%d] %s", level, message ? message : "");
}

void ModuleHostV0::applySmoothing(uint32_t frames) {
  if (!module_ || !prepared_) return;
  const uint32_t count = descriptor_->param_count < static_cast<uint32_t>(kMaxSmoothers)
                             ? descriptor_->param_count
                             : static_cast<uint32_t>(kMaxSmoothers);
  for (uint32_t id = 0; id < count; ++id) {
    Smoother& s = smoothers_[id];
    if (!s.active) continue;
    const float timeSamples = s.timeMs * 0.001f * static_cast<float>(sampleRate_);
    float alpha = 1.0f;
    if (timeSamples > 1.0f) alpha = 1.0f - std::exp(-static_cast<float>(frames) / timeSamples);
    s.current += (s.target - s.current) * alpha;
    if (std::fabs(s.target - s.current) < 1e-4f) {
      s.current = s.target;
      s.active = false;
    }
    module_->set_param(instance_, static_cast<uint16_t>(id), s.current);
    lastSentParam_[id] = s.current;
  }
}

void ModuleHostV0::setParamSmoothed(uint16_t id, float value, float timeMs) {
  if (!attached()) return;
  if (id >= descriptor_->param_count || id >= kMaxSmoothers) {
    setParam(id, value);
    return;
  }
  Smoother& s = smoothers_[id];
  if (!s.initialized) {
    s.current = value;
    s.target = value;
    s.timeMs = 0.0f;
    s.active = false;
    s.initialized = true;
    module_->set_param(instance_, id, value);
    lastSentParam_[id] = value;
    return;
  }
  s.target = value;
  s.timeMs = timeMs;
  if (timeMs <= 0.0f) {
    s.current = value;
    s.active = false;
    module_->set_param(instance_, id, value);
    lastSentParam_[id] = value;
  } else {
    s.active = true;
  }
}

float ModuleHostV0::smoothedValue(uint16_t id) const {
  if (id >= static_cast<uint16_t>(kMaxSmoothers)) return 0.0f;
  if (smoothers_[id].initialized) return smoothers_[id].current;
  return 0.0f;
}

bool ModuleHostV0::smoothingActive(uint16_t id) const {
  if (id >= static_cast<uint16_t>(kMaxSmoothers)) return false;
  return smoothers_[id].active;
}

bool ModuleHostV0::sendEvent(const bukifon_event_t& event) {
  if (!attached() || !module_->on_event) return false;
  module_->on_event(instance_, &event);
  ++eventsSent_;
  return true;
}

uint32_t ModuleHostV0::measureCost(uint32_t frames) {
  (void)frames;
  return 0;
}

void ModuleHostV0::process(const float* inL, const float* inR, float* outL, float* outR,
                           int frames) {
  if (!attached() || !prepared_ || frames <= 0) return;
  const uint32_t maxFrames = descriptor_->max_frames;
  int offset = 0;
  while (offset < frames) {
    uint32_t chunk = static_cast<uint32_t>(frames - offset);
    if (chunk > maxFrames) chunk = maxFrames;
    for (uint32_t i = 0; i < chunk; ++i) {
      scratchIn_[i * 2 + 0] = inL ? inL[offset + static_cast<int>(i)] : 0.0f;
      scratchIn_[i * 2 + 1] = inR ? inR[offset + static_cast<int>(i)] : 0.0f;
      scratchOut_[i * 2 + 0] = 0.0f;
      scratchOut_[i * 2 + 1] = 0.0f;
    }
    inProcess_ = true;  // the whole ABI boundary is considered the audio path
    applySmoothing(chunk);
    uint32_t cost = 0;
    if (!bypassed_) {
      const auto start = std::chrono::steady_clock::now();
      const int rc = module_->process(instance_, scratchIn_, scratchOut_, chunk);
      if (rc == 0) {
        if (costProvider_) {
          cost = costProvider_(chunk);
        } else {
          const auto elapsed = std::chrono::steady_clock::now() - start;
          cost = static_cast<uint32_t>(
              std::chrono::duration_cast<std::chrono::microseconds>(elapsed).count());
        }
        if (cost > budgetUs_) {
          ++overruns_;
          if (overruns_ >= BUKIFON_MODULE_MAX_OVERRUNS) bypassed_ = true;
        }
      } else {
        bypassed_ = true;
      }
    }
    inProcess_ = false;
    for (uint32_t i = 0; i < chunk; ++i) {
      const float l = bypassed_ ? scratchIn_[i * 2 + 0] : scratchOut_[i * 2 + 0];
      const float r = bypassed_ ? scratchIn_[i * 2 + 1] : scratchOut_[i * 2 + 1];
      if (outL) outL[offset + static_cast<int>(i)] = l;
      if (outR) outR[offset + static_cast<int>(i)] = r;
    }
    offset += static_cast<int>(chunk);
  }
}

bool ModuleHostV0::setParam(uint16_t id, float value) {
  if (!attached()) return false;
  if (id >= descriptor_->param_count) return false;
  module_->set_param(instance_, id, value);
  if (id < static_cast<uint16_t>(kMaxSmoothers)) {
    if (smoothers_[id].initialized) {
      smoothers_[id].current = value;
      smoothers_[id].target = value;
      smoothers_[id].active = false;
    }
    lastSentParam_[id] = value;
  }
  return true;
}

uint32_t ModuleHostV0::paramCount() const {
  return descriptor_ ? descriptor_->param_count : 0;
}

const bukifon_param_desc_t* ModuleHostV0::paramDesc(uint32_t index) const {
  if (!descriptor_ || index >= descriptor_->param_count) return nullptr;
  return &descriptor_->params[index];
}

uint32_t ModuleHostV0::stateSize() const {
  if (!attached()) return 0;
  return module_->state_size(instance_);
}

bool ModuleHostV0::saveState(uint8_t* out, uint32_t capacity) {
  if (!attached() || !out) return false;
  const uint32_t size = stateSize();
  if (size == 0 || size > capacity) return false;
  return module_->save_state(instance_, out, capacity) > 0;
}

bool ModuleHostV0::loadState(const uint8_t* data, uint32_t size) {
  if (!attached() || !data || size == 0) return false;
  return module_->load_state(instance_, data, size) == 0;
}

void ModuleHostV0::clearBypass() {
  overruns_ = 0;
  bypassed_ = false;
}

}  // namespace bukifon
