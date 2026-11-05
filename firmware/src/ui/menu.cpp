// SPDX-License-Identifier: GPL-3.0-or-later
#include "ui/menu.hpp"

#include "bukifon_ui_theme.h"

#include <cmath>
#include <cstdio>
#include <cstring>

#include "core/math.hpp"

namespace bukifon {
namespace {

EncoderBinding bind(const char* label, MenuScope scope, uint8_t id) {
  EncoderBinding b;
  b.label = label;
  b.scope = scope;
  b.id = id;
  return b;
}

EncoderBinding empty() { return EncoderBinding{}; }

}  // namespace

const PageDef kPages[kNumPages] = {
    // 1. OSC
    {"OSC",
     {bind("WAVE1", MenuScope::PartParam, Osc1Wave), bind("COARSE1", MenuScope::PartParam, Osc1Coarse),
      bind("FINE1", MenuScope::PartParam, Osc1Fine), bind("WAVE2", MenuScope::PartParam, Osc2Wave),
      bind("COARSE2", MenuScope::PartParam, Osc2Coarse), bind("FINE2", MenuScope::PartParam, Osc2Fine),
      bind("LEVEL1", MenuScope::PartParam, Osc1Level),
      bind("LEVEL2", MenuScope::PartParam, Osc2Level)}},
    // 2. FILTER / ENV
    {"FILTER/ENV",
     {bind("CUTOFF", MenuScope::PartParam, Cutoff), bind("RES", MenuScope::PartParam, Resonance),
      bind("DRIVE", MenuScope::PartParam, FilterDrive), bind("ENV AMT", MenuScope::PartParam, FilterEnvAmt),
      bind("ATK1", MenuScope::PartParam, Env1A), bind("DEC1", MenuScope::PartParam, Env1D),
      bind("SUS1", MenuScope::PartParam, Env1S), bind("REL1", MenuScope::PartParam, Env1R)}},
    // 3. LFO / MOD (matrix slot editor)
    {"LFO/MOD",
     {bind("SLOT", MenuScope::ModSlot, 0), bind("SOURCE", MenuScope::ModSlot, 1),
      bind("TARGET", MenuScope::ModSlot, 2), bind("DEPTH", MenuScope::ModSlot, 3),
      bind("CURVE", MenuScope::ModSlot, 4), bind("PART", MenuScope::ModSlot, 5),
      bind("COND", MenuScope::ModSlot, 6), bind("LFO1", MenuScope::PartParam, Lfo1Rate)}},
    // 4. SEQ / ARP
    {"SEQ",
     {bind("MODE", MenuScope::GlobalParam, SeqMode), bind("LEN", MenuScope::GlobalParam, SeqLength),
      bind("SWING", MenuScope::GlobalParam, SeqSwing), bind("TRANSP", MenuScope::GlobalParam, SeqTranspose),
      bind("ARP", MenuScope::GlobalParam, ArpMode), bind("ARP OCT", MenuScope::GlobalParam, ArpOctaves),
      bind("TEMPO", MenuScope::GlobalParam, Bpm), bind("MACRO1", MenuScope::Macro, 0)}},
    // 5. CV / GATE
    {"CV/GATE",
     {bind("CV1", MenuScope::GlobalParam, Cv1Amount), bind("CV2", MenuScope::GlobalParam, Cv2Amount),
      bind("CV3", MenuScope::GlobalParam, Cv3Amount), bind("CV4", MenuScope::GlobalParam, Cv4Amount),
      bind("G1 TIME", MenuScope::GlobalParam, Gate1Time), bind("G2 TIME", MenuScope::GlobalParam, Gate2Time),
      bind("G1 MODE", MenuScope::GlobalParam, Gate1Mode),
      bind("G2 MODE", MenuScope::GlobalParam, Gate2Mode)}},
    // 6. MODULES (hardware bus)
    {"MODULES",
     {bind("SLOT", MenuScope::ModuleSlot, 0), bind("PARAM", MenuScope::ModuleSlot, 1),
      bind("VALUE", MenuScope::ModuleSlot, 2), empty(), empty(), empty(), empty(), empty()}},
    // 7. FX
    {"FX",
     {bind("DLY TIME", MenuScope::GlobalParam, FxDelayTime),
      bind("DLY FB", MenuScope::GlobalParam, FxDelayFb), bind("DLY MIX", MenuScope::GlobalParam, FxDelayMix),
      bind("CH RATE", MenuScope::GlobalParam, FxChorusRate),
      bind("CH DEPTH", MenuScope::GlobalParam, FxChorusDepth),
      bind("CH MIX", MenuScope::GlobalParam, FxChorusMix), bind("DRIVE", MenuScope::GlobalParam, FxDrive),
      bind("LIMIT", MenuScope::GlobalParam, FxLimiterThreshold)}},
    // 8. SYSTEM
    {"SYSTEM",
     {bind("MASTER", MenuScope::GlobalParam, MasterVolume), bind("TEMPO", MenuScope::GlobalParam, Bpm),
      bind("VOICE", MenuScope::GlobalParam, PolyMode), bind("GLIDE", MenuScope::GlobalParam, Glide),
      bind("BEND", MenuScope::GlobalParam, BendRange),
      bind("LIM REL", MenuScope::GlobalParam, FxLimiterRelease), bind("MACRO1", MenuScope::Macro, 0),
      bind("MACRO2", MenuScope::Macro, 1)}},
};

void MenuModel::init(Engine* engine) {
  engine_ = engine;
  page_ = 0;
  part_ = 0;
  shift_ = false;
  selectedEncoder_ = 0;
  editedSlotIndex_ = 0;
  if (engine_) {
    editedSlot_ = engine_->modSlot(part_, editedSlotIndex_);
  }
}

void MenuModel::setPage(int page) {
  page_ = math::clampInt(page, 0, kNumPages - 1);
  loadEditedSlot();
}

void MenuModel::nextPage() { setPage(page_ + 1); }
void MenuModel::prevPage() { setPage(page_ - 1); }

void MenuModel::setPart(int part) {
  part_ = math::clampInt(part, 0, kNumParts - 1);
  loadEditedSlot();
}

void MenuModel::loadEditedSlot() {
  if (engine_) editedSlot_ = engine_->modSlot(part_, editedSlotIndex_);
}

void MenuModel::writeEditedSlot() {
  if (engine_) engine_->setModSlot(part_, editedSlotIndex_, editedSlot_);
}

const EncoderBinding& MenuModel::binding(int encoder) const {
  static const EncoderBinding kEmpty{};
  if (encoder < 0 || encoder >= kNumEncoders) return kEmpty;
  return kPages[page_].encoders[encoder];
}

int MenuModel::paramNormToDelta(const ParamMeta& meta, float value, int delta) const {
  (void)value;
  (void)delta;
  (void)meta;
  return 0;
}

int MenuModel::encoderDelta(int encoder, int delta) {
  if (!engine_ || encoder < 0 || encoder >= kNumEncoders || delta == 0) return 0;
  const EncoderBinding& b = kPages[page_].encoders[encoder];
  switch (b.scope) {
    case MenuScope::PartParam: {
      const int id = b.id;
      const ParamMeta& meta = kPartParamMeta[id];
      const float norm = paramToNorm(meta, engine_->partBase(part_).v[id]);
      const float newNorm = math::clamp(norm + static_cast<float>(delta) * 0.01f, 0.0f, 1.0f);
      engine_->setPartParam(part_, id, paramFromNorm(meta, newNorm));
      return delta;
    }
    case MenuScope::GlobalParam: {
      const int id = b.id;
      const ParamMeta& meta = kGlobalParamMeta[id];
      const float norm = paramToNorm(meta, engine_->globals().v[id]);
      const float newNorm = math::clamp(norm + static_cast<float>(delta) * 0.01f, 0.0f, 1.0f);
      engine_->setGlobalParam(id, paramFromNorm(meta, newNorm));
      return delta;
    }
    case MenuScope::Macro: {
      const float value = math::clamp(engine_->macro(b.id) + static_cast<float>(delta) * 0.02f, 0.0f, 1.0f);
      engine_->setMacro(b.id, value);
      return delta;
    }
    case MenuScope::ModSlot: {
      if (page_ != 2) return 0;
      switch (b.id) {
        case 0:  // slot selector
          editedSlotIndex_ = (editedSlotIndex_ + delta + kModSlots) % kModSlots;
          loadEditedSlot();
          return delta;
        case 1: {  // source
          const int count = static_cast<int>(kNumModSources);
          editedSlot_.source = static_cast<uint8_t>((editedSlot_.source + delta + count) % count);
          writeEditedSlot();
          return delta;
        }
        case 2: {  // target
          const int count = static_cast<int>(kNumModTargets);
          editedSlot_.target = static_cast<uint8_t>((editedSlot_.target + delta + count) % count);
          writeEditedSlot();
          return delta;
        }
        case 3:  // depth -100..100
          editedSlot_.depth = static_cast<int8_t>(
              math::clampInt(static_cast<int>(editedSlot_.depth) + delta * 2, -100, 100));
          writeEditedSlot();
          return delta;
        case 4: {  // curve
          const int c = (static_cast<int>(modSlotCurve(editedSlot_)) + delta + 4) % 4;
          modSlotSetCurve(editedSlot_, static_cast<ModCurve>(c));
          writeEditedSlot();
          return delta;
        }
        case 5: {  // receiver part
          const int p = (static_cast<int>(modSlotPart(editedSlot_)) + delta + kNumParts) % kNumParts;
          modSlotSetPart(editedSlot_, static_cast<uint8_t>(p));
          writeEditedSlot();
          return delta;
        }
        case 6: {  // trig condition
          const int c = (static_cast<int>(modSlotCondition(editedSlot_)) + delta +
                         static_cast<int>(kNumModConditions)) %
                        static_cast<int>(kNumModConditions);
          modSlotSetCondition(editedSlot_, static_cast<ModCondition>(c));
          writeEditedSlot();
          return delta;
        }
        default:
          return 0;
      }
    }
    case MenuScope::ModuleSlot: {
      if (page_ != 5) return 0;
      switch (b.id) {
        case 0:
          moduleSlot_ = math::clampInt(moduleSlot_ + delta, 0, kNumBusPorts - 1);
          return delta;
        case 1:
          moduleParam_ = math::clampInt(moduleParam_ + delta, 0, 15);
          return delta;
        case 2: {
          moduleValue_ = math::clamp(moduleValue_ + static_cast<float>(delta) * 0.02f, 0.0f, 1.0f);
          if (modules_) {
            HwModuleProxy* proxy = modules_->proxy(moduleSlot_);
            if (proxy && !proxy->passive()) proxy->setParam(moduleParam_, moduleValue_);
          }
          return delta;
        }
        default:
          return 0;
      }
    }
    case MenuScope::None:
    default:
      return 0;
  }
}

void MenuModel::encoderPush(int encoder) {
  if (!engine_ || encoder < 0 || encoder >= kNumEncoders) return;
  const EncoderBinding& b = kPages[page_].encoders[encoder];
  if (b.scope == MenuScope::PartParam) {
    engine_->setPartParam(part_, b.id, kPartParamMeta[b.id].def);
  } else if (b.scope == MenuScope::GlobalParam) {
    engine_->setGlobalParam(b.id, kGlobalParamMeta[b.id].def);
  } else if (b.scope == MenuScope::Macro) {
    engine_->setMacro(b.id, 0.5f);
  } else if (b.scope == MenuScope::ModSlot && page_ == 2) {
    if (b.id <= 6) {
      editedSlot_ = ModSlotData{};
      writeEditedSlot();
    }
  }
}

void MenuModel::onEncoder(int encoder, int delta, bool push) {
  if (push) {
    encoderPush(encoder);
    return;
  }
  if (delta == 0) return;
  // SHIFT + ENC1 / ENC8 switch pages (spec/10-panel-ui.md §4).
  if (shift_ && (encoder == 0 || encoder == 7)) {
    if (encoder == 0) {
      prevPage();
    } else {
      nextPage();
    }
    return;
  }
  encoderDelta(encoder, delta);
}

void MenuModel::formatValue(const ParamMeta& meta, float value, char* out, size_t capacity) {
  if (!out || capacity == 0) return;
  if (meta.flags & PF_DISCRETE) {
    std::snprintf(out, capacity, "%d", static_cast<int>(std::lround(value)));
    return;
  }
  if (meta.flags & PF_HZ) {
    if (value >= 1000.0f) {
      std::snprintf(out, capacity, "%.2fk", value / 1000.0f);
    } else {
      std::snprintf(out, capacity, "%.1fHz", value);
    }
    return;
  }
  if (meta.flags & PF_SECONDS) {
    if (value < 1.0f) {
      std::snprintf(out, capacity, "%.0fms", value * 1000.0f);
    } else {
      std::snprintf(out, capacity, "%.2fs", value);
    }
    return;
  }
  if (meta.flags & PF_CENTS) {
    std::snprintf(out, capacity, "%+.0fct", value);
    return;
  }
  if (meta.flags & PF_SEMITONES) {
    std::snprintf(out, capacity, "%+.0fst", value);
    return;
  }
  if (meta.flags & PF_RATIO) {
    std::snprintf(out, capacity, "%.2fx", value);
    return;
  }
  if (meta.flags & PF_PERCENT) {
    std::snprintf(out, capacity, "%.0f%%", value * 100.0f);
    return;
  }
  if (meta.flags & PF_BIPOLAR) {
    std::snprintf(out, capacity, "%+.2f", value);
    return;
  }
  std::snprintf(out, capacity, "%.2f", value);
}

float MenuModel::displayValue(int encoder) const {
  const EncoderBinding& b = kPages[page_].encoders[encoder];
  if (!engine_) return 0.0f;
  if (b.scope == MenuScope::PartParam) return engine_->modulatedPartParams(part_).v[b.id];
  if (b.scope == MenuScope::GlobalParam) return engine_->modulatedGlobals().v[b.id];
  if (b.scope == MenuScope::Macro) return engine_->macro(b.id);
  return 0.0f;
}

void MenuModel::valueText(int encoder, char* out, size_t capacity) const {
  if (!out || capacity == 0) return;
  out[0] = '\0';
  const EncoderBinding& b = kPages[page_].encoders[encoder];
  switch (b.scope) {
    case MenuScope::PartParam:
      formatValue(kPartParamMeta[b.id], displayValue(encoder), out, capacity);
      break;
    case MenuScope::GlobalParam:
      formatValue(kGlobalParamMeta[b.id], displayValue(encoder), out, capacity);
      break;
    case MenuScope::Macro:
      std::snprintf(out, capacity, "%d%%", static_cast<int>(displayValue(encoder) * 100.0f + 0.5f));
      break;
    case MenuScope::ModSlot:
      if (encoder == 0) {
        std::snprintf(out, capacity, "S%d", editedSlotIndex_ + 1);
      } else if (encoder == 1) {
        std::snprintf(out, capacity, "%s", modSourceName(static_cast<ModSource>(editedSlot_.source)));
      } else if (encoder == 2) {
        std::snprintf(out, capacity, "%s",
                      modTargetName(static_cast<ModTarget>(editedSlot_.target)));
      } else if (encoder == 3) {
        std::snprintf(out, capacity, "%+d%%", static_cast<int>(editedSlot_.depth));
      } else if (encoder == 4) {
        std::snprintf(out, capacity, "%s", modCurveName(modSlotCurve(editedSlot_)));
      } else if (encoder == 5) {
        std::snprintf(out, capacity, "P%d", modSlotPart(editedSlot_) + 1);
      } else if (encoder == 6) {
        std::snprintf(out, capacity, "%s", modConditionName(modSlotCondition(editedSlot_)));
      }
      break;
    case MenuScope::ModuleSlot:
      if (encoder == 0) {
        if (modules_ && modules_->present(moduleSlot_)) {
          std::snprintf(out, capacity, "%s", modules_->descriptor(moduleSlot_)->name);
        } else {
          std::snprintf(out, capacity, "EMPTY");
        }
      } else if (encoder == 1) {
        std::snprintf(out, capacity, "P%d", moduleParam_);
      } else if (encoder == 2) {
        std::snprintf(out, capacity, "%.2f", moduleValue_);
      }
      break;
    case MenuScope::None:
    default:
      std::snprintf(out, capacity, "-");
      break;
  }
}

void MenuModel::draw(ICanvas& canvas) const {
  canvas.fillRect(0, 0, canvas.width(), canvas.height(), ui::themeColor(BUKIFON_UI_PANEL));
  // Header.
  canvas.fillRect(0, 0, canvas.width(), 22, ui::themeColor(BUKIFON_UI_PANEL));
  canvas.drawText(6, 7, "Bukifon", ui::themeColor(BUKIFON_UI_ACCENT));
  canvas.drawText(80, 7, kPages[page_].title, ui::themeColor(BUKIFON_UI_TEXT));
  char buf[32];
  std::snprintf(buf, sizeof(buf), "PART %d", part_ + 1);
  canvas.drawText(200, 7, buf, ui::themeColor(BUKIFON_UI_MUTED));
  if (shift_) canvas.drawText(280, 7, "SHIFT", ui::themeColor(BUKIFON_UI_RED));

  // Two columns of four encoders with label + modulated value.
  for (int i = 0; i < kNumEncoders; ++i) {
    const int col = i / 4;
    const int row = i % 4;
    const int x = 8 + col * 160;
    const int y = 34 + row * 44;
    const EncoderBinding& b = kPages[page_].encoders[i];
    canvas.fillRect(x, y, 148, 38, ui::themeColor(BUKIFON_UI_CARD));
    canvas.drawRect(x, y, 148, 38, ui::themeColor(BUKIFON_UI_MUTED));
    canvas.drawText(x + 5, y + 5, b.label, ui::themeColor(BUKIFON_UI_MUTED));
    valueText(i, buf, sizeof(buf));
    canvas.drawText(x + 5, y + 20, buf, ui::themeColor(BUKIFON_UI_ORANGE));
  }

  // Footer: transport and voices.
  canvas.fillRect(0, canvas.height() - 34, canvas.width(), 34, ui::themeColor(BUKIFON_UI_PANEL));
  std::snprintf(buf, sizeof(buf), "TEMPO %d", static_cast<int>(engine_ ? engine_->globals().v[Bpm] : 120));
  canvas.drawText(8, canvas.height() - 26, buf, ui::themeColor(BUKIFON_UI_TEXT));
  std::snprintf(buf, sizeof(buf), "VOICES %d", engine_ ? engine_->activeVoices() : 0);
  canvas.drawText(130, canvas.height() - 26, buf, ui::themeColor(BUKIFON_UI_GREEN));
  std::snprintf(buf, sizeof(buf), "PART %d", part_ + 1);
  canvas.drawText(240, canvas.height() - 26, buf, ui::themeColor(BUKIFON_UI_ACCENT));
  // Step bar.
  for (int s = 0; s < kSeqSteps; ++s) {
    const int x = 8 + s * 18;
    canvas.fillRect(x, canvas.height() - 10, 16, 6, s == 7 ? ui::themeColor(BUKIFON_UI_ACCENT) : ui::themeColor(BUKIFON_UI_MUTED));
  }
}

}  // namespace bukifon
