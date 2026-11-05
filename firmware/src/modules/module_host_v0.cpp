// SPDX-License-Identifier: GPL-3.0-or-later
#include "modules/module_host_v0.hpp"

#include <chrono>
#include <cstddef>
#include <cstring>

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
}

uint32_t ModuleHostV0::measureCost(uint32_t frames) {
  if (costProvider_) return costProvider_(frames);
  const auto start = std::chrono::steady_clock::now();
  // The caller has already executed the module; this hook is only kept for the
  // injected-cost tests.  With no provider the measured cost is reported by the
  // process() timing path below (0 here means "use wall clock").
  (void)start;
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
    // Interleave into the ABI buffer.
    for (uint32_t i = 0; i < chunk; ++i) {
      scratchIn_[i * 2 + 0] = inL ? inL[offset + static_cast<int>(i)] : 0.0f;
      scratchIn_[i * 2 + 1] = inR ? inR[offset + static_cast<int>(i)] : 0.0f;
      scratchOut_[i * 2 + 0] = 0.0f;
      scratchOut_[i * 2 + 1] = 0.0f;
    }
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
