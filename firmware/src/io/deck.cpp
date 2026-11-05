// SPDX-License-Identifier: GPL-3.0-or-later
#include "io/deck.hpp"

#include <cmath>
#include <cstring>

namespace bukifon {

void DeckScanner::init(DeckType type, IDeckIo* io, DeckSink* sink) {
  config_ = DeckConfig{};
  config_.type = type;
  config_.rows = (type == DeckType::Keys) ? 6 : 3;
  config_.columns = (type == DeckType::Keys) ? 7 : 6;
  config_.debounceUs = (type == DeckType::Keys) ? 3000u : 5000u;
  io_ = io;
  sink_ = sink;
  for (int i = 0; i < kNumKeys; ++i) {
    buttons_[i].stable = 0;
    buttons_[i].raw = 0;
    buttons_[i].lastChangeUs = 0;
  }
  fsrPrimed_ = false;
  fsrBaseline_ = 0;
}

void DeckScanner::updateButton(int index, bool raw, uint32_t nowUs) {
  ButtonState& b = buttons_[index];
  const uint8_t rawValue = raw ? 1 : 0;
  if (rawValue != b.raw) {
    b.raw = rawValue;
    b.lastChangeUs = nowUs;
    return;
  }
  if (b.raw != b.stable && (nowUs - b.lastChangeUs) >= config_.debounceUs) {
    b.stable = b.raw;
    const bool pressed = b.stable != 0;
    if (config_.type == DeckType::Keys) {
      if (sink_) sink_->onKey(static_cast<uint8_t>(index), pressed ? 127 : 0, pressed);
    } else {
      uint8_t velocity = 127;
      if (pressed && config_.fsrEnabled && io_) {
        const uint16_t fsr = io_->readAdc(6);
        velocity = FsrVelocity::fromForceDelta(fsrBaseline_, fsr);
      }
      if (sink_) sink_->onPad(static_cast<uint8_t>(index), velocity, pressed);
    }
  }
}

void DeckScanner::scanOnce(uint32_t nowUs) {
  if (!io_) return;
  // FSR baseline is sampled with no pad pressed (before the first event).
  if (config_.fsrEnabled && !fsrPrimed_) {
    fsrBaseline_ = io_->readAdc(6);
    fsrPrimed_ = true;
  }
  // Rows are driven low one at a time (active-low matrix + pull-ups).
  for (int row = 0; row < config_.rows; ++row) {
    const uint8_t rowMask = static_cast<uint8_t>(1u << row);
    io_->writePort(0, static_cast<uint8_t>(~rowMask));  // GPA = row drive
    const uint8_t columns = static_cast<uint8_t>(~io_->readPort(1) & 0xFF);  // GPB = columns
    for (int col = 0; col < config_.columns; ++col) {
      const int index = row * config_.columns + col;
      if (index >= kNumKeys) break;
      const bool pressed = (columns & (1u << col)) != 0;
      updateButton(index, pressed, nowUs);
    }
  }
  // Release all rows.
  io_->writePort(0, 0xFF);
}

void DeckScanner::poll(uint32_t nowUs) { scanOnce(nowUs); }

bool DeckScanner::pressed(int index) const {
  if (index < 0 || index >= kNumKeys) return false;
  return buttons_[index].stable != 0;
}

// --- keyboard mapping ------------------------------------------------------
int KeyboardMapper::keyToNote(int keyIndex, int layout, int octaveShift) {
  return keyToSemitone(keyIndex, layout) + 48 + octaveShift * 12;
}

int KeyboardMapper::keyToSemitone(int keyIndex, int layout) {
  keyIndex = (keyIndex < 0) ? 0 : (keyIndex >= kNumKeys ? kNumKeys - 1 : keyIndex);
  if (layout == 1) {
    // Isomorphic: column step = 2 semitones (major thirds), row step = 5.
    const int half = keyIndex / 21;
    const int inHalf = keyIndex % 21;
    int col, row;
    if (inHalf < 18) {
      col = inHalf % 6;
      row = inHalf / 6;
    } else {
      col = (inHalf - 18) + 4;  // thumb row sits under columns 4..6
      row = 3;
    }
    const int mirrored = (half == 0) ? col : (5 - col);
    return mirrored * 2 + row * 5 + (half ? 1 : 0);
  }
  return keyIndex;  // chromatic
}

int KeyboardMapper::noteToKey(int note, int layout) {
  for (int k = 0; k < kNumKeys; ++k) {
    if (keyToNote(k, layout) == note) return k;
  }
  return -1;
}

}  // namespace bukifon
