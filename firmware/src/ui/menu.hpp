// SPDX-License-Identifier: GPL-3.0-or-later
// 8-page encoder menu (spec/10-panel-ui.md §4), page/macro/module editing and
// rendering to a 320x240 canvas. Displays the *modulated* parameter value.
#pragma once

#include <cstddef>
#include <cstdint>

#include "audio/engine.hpp"
#include "core/config.hpp"
#include "core/modulation_defs.hpp"
#include "core/params.hpp"
#include "modules/hw_module.hpp"
#include "ui/canvas.hpp"

namespace bukifon {

enum class MenuScope : uint8_t { None = 0, PartParam, GlobalParam, Macro, ModSlot, ModuleSlot };

struct EncoderBinding {
  const char* label = "";
  MenuScope scope = MenuScope::None;
  uint8_t id = 0;
};

struct PageDef {
  const char* title;
  EncoderBinding encoders[kNumEncoders];
};

extern const PageDef kPages[kNumPages];

class MenuModel {
 public:
  void init(Engine* engine = nullptr);
  void setEngine(Engine* engine) { engine_ = engine; }
  void setModuleManager(HwModuleManager* manager) { modules_ = manager; }

  void setPage(int page);
  void nextPage();
  void prevPage();
  int page() const { return page_; }
  const char* pageTitle() const { return kPages[page_].title; }

  void setShift(bool shift) { shift_ = shift; }
  bool shift() const { return shift_; }
  void setPart(int part);
  int part() const { return part_; }

  // Encoder rotation: returns the number of applied parameter steps (0 if the
  // encoder is unused on this page).
  int encoderDelta(int encoder, int delta);
  // Encoder push: resets the parameter to its default.
  void encoderPush(int encoder);

  // Menu navigation helpers used by the panel MCU.
  void onEncoder(int encoder, int delta, bool push);

  float displayValue(int encoder) const;
  void valueText(int encoder, char* out, size_t capacity) const;
  static void formatValue(const ParamMeta& meta, float value, char* out, size_t capacity);

  const EncoderBinding& binding(int encoder) const;
  const ModSlotData& editedSlot() const { return editedSlot_; }
  int editedSlotIndex() const { return editedSlotIndex_; }

  void draw(ICanvas& canvas) const;

 private:
  void loadEditedSlot();
  void writeEditedSlot();
  int paramNormToDelta(const ParamMeta& meta, float value, int delta) const;

  Engine* engine_ = nullptr;
  HwModuleManager* modules_ = nullptr;
  int page_ = 0;
  int part_ = 0;
  bool shift_ = false;
  uint8_t selectedEncoder_ = 0;

  int editedSlotIndex_ = 0;
  ModSlotData editedSlot_{};
  int moduleSlot_ = 0;
  int moduleParam_ = 0;
  float moduleValue_ = 0.0f;
};

}  // namespace bukifon
