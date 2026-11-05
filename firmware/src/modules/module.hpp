// SPDX-License-Identifier: GPL-3.0-or-later
// Programmatic module API (spec/40-firmware.md §9) and the static registry.
#pragma once

#include <cstddef>
#include <cstdint>

namespace bukifon {

struct IModule {
  virtual ~IModule() = default;
  virtual const char* name() const = 0;
  virtual void process(float* l, float* r, size_t n) = 0;  // effects
  virtual void tick() {}                                   // 1 kHz, UI modules
};

struct IOscillator : IModule {};
struct IFilter : IModule {};
struct IEffect : IModule {};
struct IModulator : IModule {};
struct ISequencer : IModule {};

enum ModuleKind : uint8_t {
  KindOscillator = 1,
  KindFilter = 2,
  KindVca = 3,
  KindLfo = 4,
  KindEffect = 5,
  KindSequencer = 6,
  KindCustom = 0xFF
};

struct ModuleInfo {
  const char* name = "";
  uint8_t kind = KindCustom;
  const char* description = "";
};

using ModuleFactory = IModule* (*)();

class ModuleRegistry {
 public:
  static ModuleRegistry& instance();
  void add(const ModuleInfo& info, ModuleFactory factory);
  int count() const { return count_; }
  const ModuleInfo* info(int index) const;
  IModule* create(int index) const;
  IModule* createByName(const char* name) const;
  const char* name(int index) const;

 private:
  static constexpr int kMaxModules = 24;
  struct Entry {
    ModuleInfo info;
    ModuleFactory factory;
  };
  Entry entries_[kMaxModules] = {};
  int count_ = 0;
};

// Registration helper used by MOD_REGISTER().
struct ModuleRegistrar {
  ModuleRegistrar(const ModuleInfo& info, ModuleFactory factory) {
    ModuleRegistry::instance().add(info, factory);
  }
};

#define MOD_REGISTER(ClassName, Kind, Description)                                      \
  namespace {                                                                            \
  IModule* bukifon_make_##ClassName() { return new ClassName(); }                        \
  const ModuleRegistrar bukifon_reg_##ClassName(                                         \
      ModuleInfo{#ClassName, Kind, Description}, bukifon_make_##ClassName);              \
  }  // namespace

// Built-in programmatic modules (declared here, implemented in modules/builtin.cpp).
void registerBuiltinModules();

}  // namespace bukifon
