// SPDX-License-Identifier: GPL-3.0-or-later
#include "modules/lua_layer.hpp"

#include <cstring>

namespace bukifon {
namespace {

// Deterministic estimate used by the stub: one instruction per 2 non-whitespace
// bytes, at least 1.  The real interpreter will use the Lua instruction hook.
uint32_t estimateInstructions(const char* script, size_t length) {
  if (!script) return 0;
  uint32_t executable = 0;
  for (size_t i = 0; i < length; ++i) {
    const unsigned char c = static_cast<unsigned char>(script[i]);
    if (c != ' ' && c != '\n' && c != '\r' && c != '\t') ++executable;
  }
  return (executable + 1) / 2;
}

}  // namespace

void LuaLayer::init(const Limits& limits) {
  limits_ = limits;
  if (limits_.maxInstructions == 0) limits_.maxInstructions = 10000;
  if (limits_.maxScriptBytes == 0) limits_.maxScriptBytes = 4096;
  if (limits_.maxMemoryBytes == 0) limits_.maxMemoryBytes = 16384;
  if (limits_.instructionsPerTick == 0) limits_.instructionsPerTick = 512;
  reset();
}

void LuaLayer::reset() {
  status_ = Status::Disabled;  // interpreter is not linked in v0
  executed_ = 0;
  scriptBytes_ = 0;
  estimatedInstructions_ = 0;
}

bool LuaLayer::load(const char* script, size_t length) {
  if (!script) {
    status_ = Status::Error;
    return false;
  }
  if (length > limits_.maxScriptBytes) {
    status_ = Status::ScriptTooLarge;
    return false;
  }
  estimatedInstructions_ = estimateInstructions(script, length);
  scriptBytes_ = static_cast<uint32_t>(length);
  if (estimatedInstructions_ > limits_.maxInstructions) {
    status_ = Status::InstructionLimit;
    return false;
  }
  executed_ = 0;
  status_ = Status::Idle;
  return true;
}

LuaLayer::Status LuaLayer::tick(uint32_t budget) {
  if (status_ == Status::Disabled) return status_;
  if (status_ == Status::ScriptTooLarge || status_ == Status::Error ||
      status_ == Status::InstructionLimit) {
    return status_;
  }
  const uint32_t step = budget == 0 ? limits_.instructionsPerTick : budget;
  const uint32_t remaining = estimatedInstructions_ > executed_ ? estimatedInstructions_ - executed_ : 0;
  const uint32_t run = step < remaining ? step : remaining;
  executed_ += run;
  if (executed_ >= limits_.maxInstructions) {
    status_ = Status::InstructionLimit;
    return status_;
  }
  status_ = executed_ >= estimatedInstructions_ ? Status::Idle : Status::Running;
  return status_;
}

LuaLayer::Status LuaLayer::runToCompletion(uint32_t budgetPerTick) {
  uint32_t guard = 0;
  while (status_ == Status::Running || status_ == Status::Idle) {
    const Status before = status_;
    tick(budgetPerTick);
    if (status_ == before) break;  // no progress
    if (++guard > 100000) {
      status_ = Status::InstructionLimit;
      break;
    }
  }
  return status_;
}

const char* LuaLayer::statusName() const {
  switch (status_) {
    case Status::Disabled: return "DISABLED";
    case Status::Idle: return "IDLE";
    case Status::Running: return "RUNNING";
    case Status::InstructionLimit: return "INSTRUCTION_LIMIT";
    case Status::ScriptTooLarge: return "SCRIPT_TOO_LARGE";
    case Status::Error: return "ERROR";
    default: return "?";
  }
}

}  // namespace bukifon
