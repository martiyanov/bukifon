// SPDX-License-Identifier: GPL-3.0-or-later
// Lua scripting layer — STUB with instruction/memory limits (no interpreter).
//
// The real Lua 5.4 runtime is not linked in v0.  This layer exists so that the
// module system, the UI and the tests already use the final sandbox contract:
//   * scripts are size-limited before being accepted;
//   * execution is metered in instructions and stopped when the budget is hit;
//   * there is no filesystem, no allocation and no blocking call exposed.
//
// TODO(lua): embed Lua 5.4 with lua_sethook(LUA_MASKCOUNT) counting instructions
// and a custom allocator capped at kMaxMemoryBytes; panic on limit.  Until then
// this stub models the limit behaviour deterministically so the integration
// points and tests exist.
#pragma once

#include <cstddef>
#include <cstdint>

namespace bukifon {

class LuaLayer {
 public:
  enum class Status : uint8_t {
    Disabled = 0,     // interpreter not linked (v0 default)
    Idle,             // loaded and ready
    Running,
    InstructionLimit, // budget exhausted, script disabled
    ScriptTooLarge,
    Error
  };

  struct Limits {
    uint32_t maxInstructions;
    uint32_t maxScriptBytes;
    uint32_t maxMemoryBytes;
    uint32_t instructionsPerTick;
    explicit Limits(uint32_t instructions = 10000, uint32_t scriptBytes = 4096,
                    uint32_t memoryBytes = 16384, uint32_t perTick = 512)
        : maxInstructions(instructions),
          maxScriptBytes(scriptBytes),
          maxMemoryBytes(memoryBytes),
          instructionsPerTick(perTick) {}
  };

  void init(const Limits& limits = Limits{});
  void reset();

  // Accepts a script and computes its (simulated) instruction count.
  bool load(const char* script, size_t length);
  bool loaded() const { return status_ == Status::Idle || status_ == Status::Running; }

  // Runs up to `budget` instructions (default: limits.instructionsPerTick).
  Status tick(uint32_t budget = 0);
  Status runToCompletion(uint32_t budgetPerTick = 0);

  Status status() const { return status_; }
  const char* statusName() const;
  uint32_t instructionsExecuted() const { return executed_; }
  uint32_t instructionLimit() const { return limits_.maxInstructions; }
  uint32_t scriptBytes() const { return scriptBytes_; }
  uint32_t estimatedInstructions() const { return estimatedInstructions_; }
  const Limits& limits() const { return limits_; }

  // True only when a real interpreter is linked.  Always false in v0.
  static bool interpreterAvailable() { return false; }

 private:
  Limits limits_{};
  Status status_ = Status::Disabled;
  uint32_t executed_ = 0;
  uint32_t scriptBytes_ = 0;
  uint32_t estimatedInstructions_ = 0;
};

}  // namespace bukifon
