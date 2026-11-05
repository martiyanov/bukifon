// SPDX-License-Identifier: GPL-3.0-or-later
#include "modules/module.hpp"

#include <cstring>

#include "dsp/effects.hpp"
#include "dsp/lfo.hpp"
#include "dsp/ensemble.hpp"
#include "io/sequencer.hpp"

namespace bukifon {

ModuleRegistry& ModuleRegistry::instance() {
  static ModuleRegistry registry;
  return registry;
}

void ModuleRegistry::add(const ModuleInfo& info, ModuleFactory factory) {
  if (count_ >= kMaxModules || !factory) return;
  entries_[count_].info = info;
  entries_[count_].factory = factory;
  ++count_;
}

const ModuleInfo* ModuleRegistry::info(int index) const {
  if (index < 0 || index >= count_) return nullptr;
  return &entries_[index].info;
}

IModule* ModuleRegistry::create(int index) const {
  if (index < 0 || index >= count_) return nullptr;
  return entries_[index].factory();
}

IModule* ModuleRegistry::createByName(const char* name) const {
  if (!name) return nullptr;
  for (int i = 0; i < count_; ++i) {
    if (std::strcmp(entries_[i].info.name, name) == 0) return entries_[i].factory();
  }
  return nullptr;
}

const char* ModuleRegistry::name(int index) const {
  const ModuleInfo* i = info(index);
  return i ? i->name : "";
}

namespace {

// --- built-in programmatic modules ----------------------------------------
class SoftDelayModule : public IEffect {
 public:
  SoftDelayModule() {
    delay_.init();
    delay_.setTime(0.25f);
    delay_.setFeedback(0.35f);
    delay_.setMix(0.3f);
  }
  const char* name() const override { return "Soft Delay"; }
  void process(float* l, float* r, size_t n) override {
    delay_.process(l, r, static_cast<int>(n));
  }

 private:
  StereoDelay delay_;
};

class SoftChorusModule : public IEffect {
 public:
  SoftChorusModule() {
    ensemble_.init();
    ensemble_.setAmount(0.5f);
    ensemble_.setRate(0.35f);
  }
  const char* name() const override { return "Soft Chorus"; }
  void process(float* l, float* r, size_t n) override {
    ensemble_.process(l, r, static_cast<int>(n));
  }

 private:
  Ensemble ensemble_;
};

class SoftDriveModule : public IEffect {
 public:
  SoftDriveModule() {
    drive_.init();
    drive_.setAmount(0.4f);
    drive_.setTone(0.6f);
    drive_.setMix(1.0f);
  }
  const char* name() const override { return "Soft Drive"; }
  void process(float* l, float* r, size_t n) override {
    drive_.process(l, r, static_cast<int>(n));
  }

 private:
  DriveFx drive_;
};

class SoftCrushModule : public IEffect {
 public:
  SoftCrushModule() {
    fx_.init();
    fx_.setBits(8.0f);
    fx_.setRate(0.5f);
    fx_.setMix(0.8f);
  }
  const char* name() const override { return "Soft Bitcrush"; }
  void process(float* l, float* r, size_t n) override {
    fx_.process(l, r, static_cast<int>(n));
  }

 private:
  BitcrushFx fx_;
};

class SoftLfoModule : public IModulator {
 public:
  SoftLfoModule() { lfo_.init(); }
  const char* name() const override { return "Soft LFO"; }
  void process(float* l, float* r, size_t n) override {
    (void)l;
    (void)r;
    (void)n;
  }
  void tick() override { lfo_.tick(); }
  float value() const { return lfo_.value(); }

 private:
  Lfo lfo_;
};

class SoftSeqModule : public ISequencer {
 public:
  SoftSeqModule() { seq_.init(); }
  const char* name() const override { return "Soft Sequencer"; }
  void process(float* l, float* r, size_t n) override {
    (void)l;
    (void)r;
    (void)n;
  }
  void tick() override { seq_.process(1); }

 private:
  Sequencer seq_;
};

ModuleInfo makeInfo(const char* name, uint8_t kind, const char* description) {
  ModuleInfo i;
  i.name = name;
  i.kind = kind;
  i.description = description;
  return i;
}

}  // namespace

void registerBuiltinModules() {
  ModuleRegistry& r = ModuleRegistry::instance();
  static bool registered = false;
  if (registered) return;
  registered = true;
  r.add(makeInfo("Soft Delay", KindEffect, "Stereo delay effect"), []() -> IModule* {
    return new SoftDelayModule();
  });
  r.add(makeInfo("Soft Chorus", KindEffect, "Ensemble / chorus effect"), []() -> IModule* {
    return new SoftChorusModule();
  });
  r.add(makeInfo("Soft Drive", KindEffect, "Soft saturation drive"), []() -> IModule* {
    return new SoftDriveModule();
  });
  r.add(makeInfo("Soft Bitcrush", KindEffect, "Bitcrusher"), []() -> IModule* {
    return new SoftCrushModule();
  });
  r.add(makeInfo("Soft LFO", KindLfo, "Free-running LFO"), []() -> IModule* {
    return new SoftLfoModule();
  });
  r.add(makeInfo("Soft Sequencer", KindSequencer, "16-step sequencer"), []() -> IModule* {
    return new SoftSeqModule();
  });
}

}  // namespace bukifon
