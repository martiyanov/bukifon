// SPDX-License-Identifier: GPL-3.0-or-later
#include "io/arp.hpp"

#include <algorithm>
#include <cmath>

namespace bukifon {

void Arpeggiator::init(float sampleRate) {
  sampleRate_ = sampleRate;
  reset();
}

void Arpeggiator::reset() {
  heldCount_ = 0;
  orderCount_ = 0;
  orderPos_ = 0;
  direction_ = 1;
  untilNext_ = 0.0;
  noteOffCountdown_ = 0.0;
  pendingNote_ = -1;
  for (auto& h : held_) h = HeldNote{};
}

void Arpeggiator::setParams(int mode, int octaves, float gate, bool latch) {
  mode_ = mode;
  octaves_ = octaves < 1 ? 1 : (octaves > 4 ? 4 : octaves);
  gate_ = gate < 0.05f ? 0.05f : (gate > 1.0f ? 1.0f : gate);
  latch_ = latch;
  rebuildOrder();
}

void Arpeggiator::noteOn(int note, int velocity) {
  if (latch_ && latchArmed_) {
    // Starting a new chord clears the latched notes.
    heldCount_ = 0;
    for (auto& h : held_) h = HeldNote{};
    latchArmed_ = false;
  }
  for (auto& h : held_) {
    if (h.active && h.note == note) {
      h.velocity = static_cast<uint8_t>(velocity);
      rebuildOrder();
      return;
    }
  }
  if (heldCount_ < 16) {
    for (auto& h : held_) {
      if (!h.active) {
        h.active = true;
        h.note = static_cast<uint8_t>(note);
        h.velocity = static_cast<uint8_t>(velocity);
        ++heldCount_;
        break;
      }
    }
  }
  rebuildOrder();
}

void Arpeggiator::noteOff(int note) {
  if (latch_) {
    latchArmed_ = true;
    return;  // latched notes keep playing
  }
  for (auto& h : held_) {
    if (h.active && h.note == note) {
      h.active = false;
      h.velocity = 0;
      --heldCount_;
      break;
    }
  }
  rebuildOrder();
}

void Arpeggiator::allNotesOff() {
  heldCount_ = 0;
  for (auto& h : held_) h = HeldNote{};
  rebuildOrder();
}

void Arpeggiator::rebuildOrder() {
  // Collect active notes sorted ascending (up pattern source).
  int notes[16];
  int velocities[16];
  int n = 0;
  for (const auto& h : held_) {
    if (!h.active) continue;
    notes[n] = h.note;
    velocities[n] = h.velocity;
    ++n;
  }
  for (int i = 1; i < n; ++i) {
    for (int j = i; j > 0 && notes[j - 1] > notes[j]; --j) {
      std::swap(notes[j - 1], notes[j]);
      std::swap(velocities[j - 1], velocities[j]);
    }
  }
  orderCount_ = 0;
  for (int oct = 0; oct < octaves_; ++oct) {
    for (int i = 0; i < n; ++i) {
      if (orderCount_ >= static_cast<int>(sizeof(order_) / sizeof(order_[0]))) break;
      order_[orderCount_++] = notes[i] + oct * 12;
    }
  }
  if (orderPos_ >= orderCount_) orderPos_ = 0;
  (void)velocities;
}

int Arpeggiator::noteAt(int stepIndex) const {
  if (orderCount_ == 0) return -1;
  return order_[stepIndex % orderCount_];
}

uint32_t Arpeggiator::nextRandom() {
  rng_ ^= rng_ << 13;
  rng_ ^= rng_ >> 17;
  rng_ ^= rng_ << 5;
  return rng_;
}

void Arpeggiator::stepTrigger(int part) {
  if (orderCount_ == 0 || pendingNote_ >= 0) return;
  int note = -1;
  switch (mode_) {
    case ArpDown:
      note = order_[orderCount_ - 1 - (orderPos_ % orderCount_)];
      ++orderPos_;
      break;
    case ArpUpDown: {
      note = noteAt(orderPos_);
      if (direction_ > 0) {
        ++orderPos_;
        if (orderPos_ >= orderCount_) {
          orderPos_ = orderCount_ - 2;
          direction_ = -1;
          if (orderPos_ < 0) orderPos_ = 0;
        }
      } else {
        --orderPos_;
        if (orderPos_ < 0) {
          orderPos_ = 1;
          direction_ = 1;
          if (orderPos_ >= orderCount_) orderPos_ = 0;
        }
      }
      break;
    }
    case ArpRandom:
      note = order_[static_cast<int>(nextRandom()) % orderCount_];
      break;
    case ArpUp:
    case ArpOff:
    default:
      note = orderPos_ % orderCount_;
      note = order_[note];
      ++orderPos_;
      break;
  }
  if (note < 0) return;
  int velocity = 100;
  // Find the velocity of the base note (ignore octave transposition).
  for (const auto& h : held_) {
    if (h.active && (note - h.note) % 12 == 0) {
      velocity = h.velocity;
      break;
    }
  }
  if (sink_) sink_->onArpNoteOn(part, note, velocity);
  pendingNote_ = note;
  noteOffCountdown_ = stepSamples_ * gate_;
}

void Arpeggiator::process(int samples, float bpm, int part) {
  bpm_ = bpm;
  stepSamples_ = (60.0 / bpm_) / 4.0 * sampleRate_;  // 16th notes
  if (!enabled() || heldCount_ == 0) {
    if (pendingNote_ >= 0 && sink_) {
      sink_->onArpNoteOff(part, pendingNote_);
      pendingNote_ = -1;
    }
    return;
  }
  for (int i = 0; i < samples; ++i) {
    if (pendingNote_ >= 0) {
      noteOffCountdown_ -= 1.0;
      if (noteOffCountdown_ <= 0.0) {
        if (sink_) sink_->onArpNoteOff(part, pendingNote_);
        pendingNote_ = -1;
      }
    }
    untilNext_ -= 1.0;
    if (untilNext_ <= 0.0) {
      stepTrigger(part);
      untilNext_ += stepSamples_;
    }
  }
}

}  // namespace bukifon
