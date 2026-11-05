// SPDX-License-Identifier: GPL-3.0-or-later
#include "io/daw_controller.hpp"

#include "core/math.hpp"

namespace bukifon {
namespace {
// CC layout: encoders occupy CC 16..79 in four banks of 16; transport uses the
// Mackie-ish CC 118..121 range (values 127 = pressed).
constexpr uint8_t kFirstEncoderCc = 16;
constexpr uint8_t kTransportCcPlay = 118;
constexpr uint8_t kTransportCcStop = 117;
constexpr uint8_t kTransportCcRecord = 119;
constexpr uint8_t kTransportCcLoop = 120;

// Note-mode transport notes: C-1.. = 24..27 (kept out of the synth range).
constexpr uint8_t kTransportNoteBase = 24;
}  // namespace

void DawController::init() {
  bank_ = 0;
  for (int i = 0; i < kEncoderCount; ++i) encoderValues_[i] = 64;
  lastTransportCc_ = 0xFF;
  lastTransportValue_ = 0;
  lastWasNote_ = false;
  lastTransportNote_ = 0;
  transportNotes_ = false;
  keyMode_ = KeyMode::Notes;
}

bool DawController::setBank(int bank) {
  if (bank < 0 || bank >= kBankCount) return false;
  bank_ = bank;
  return true;
}

int DawController::nextBank() {
  bank_ = (bank_ + 1) % kBankCount;
  return bank_;
}

uint8_t DawController::ccForEncoder(int encoder) const {
  if (encoder < 0 || encoder >= kEncoderCount) return 0xFF;
  return static_cast<uint8_t>(kFirstEncoderCc + bank_ * kCcPerBank + encoder);
}

uint8_t DawController::valueForEncoder(int encoder) const {
  if (encoder < 0 || encoder >= kEncoderCount) return 0;
  return encoderValues_[encoder];
}

void DawController::setEncoderValue(int encoder, float normalized) {
  if (encoder < 0 || encoder >= kEncoderCount) return;
  const float clamped = math::clamp(normalized, 0.0f, 1.0f);
  encoderValues_[encoder] = static_cast<uint8_t>(clamped * 127.0f + 0.5f);
}

uint8_t DawController::applyEncoderDelta(int encoder, int delta, int stepsPerTurn) {
  if (encoder < 0 || encoder >= kEncoderCount) return 0xFF;
  if (stepsPerTurn <= 0) stepsPerTurn = 100;
  const int value = static_cast<int>(encoderValues_[encoder]) * stepsPerTurn / 127 + delta;
  const int clamped = math::clampInt(value, 0, stepsPerTurn);
  encoderValues_[encoder] = static_cast<uint8_t>(clamped * 127 / stepsPerTurn);
  return ccForEncoder(encoder);
}

uint8_t DawController::transportAction(DawTransport action) {
  static const uint8_t kCc[static_cast<int>(DawTransport::kNumActions)] = {
      kTransportCcPlay, kTransportCcStop, kTransportCcRecord, kTransportCcLoop};
  const int index = static_cast<int>(action);
  if (index < 0 || index >= static_cast<int>(DawTransport::kNumActions)) return 0xFF;
  lastTransportCc_ = kCc[index];
  lastTransportValue_ = 127;
  lastWasNote_ = transportNotes_;
  lastTransportNote_ = transportNotes_
                           ? static_cast<uint8_t>(kTransportNoteBase + static_cast<uint8_t>(index))
                           : 0;
  return lastTransportCc_;
}

uint8_t DawController::noteForKey(int keyIndex) const {
  const int note = 48 + math::clampInt(keyIndex, 0, kNumKeys - 1);
  return static_cast<uint8_t>(note > 127 ? 127 : note);
}

uint8_t DawController::hotkeyCcForKey(int keyIndex) const {
  return static_cast<uint8_t>(100 + (math::clampInt(keyIndex, 0, kNumKeys - 1) % 20));
}

}  // namespace bukifon
