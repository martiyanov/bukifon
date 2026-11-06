// SPDX-License-Identifier: GPL-3.0-or-later
// Example module: tape delay (audio effect). Host model for SDK v0.2 tests.
#pragma once
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace bukifon {
namespace examples {

class TapeDelayModel {
 public:
  bool init(float sampleRate = 48000.0f) {
    sampleRate_ = sampleRate;
    const size_t n = static_cast<size_t>(sampleRate) * 2 + 1;
    buffer_.assign(n, 0.0f);
    write_ = 0;
    setDelayMs(250.0f);
    setFeedback(0.35f);
    setMix(0.30f);
    return true;
  }
  void reset() {
    for (float& s : buffer_) s = 0.0f;
    write_ = 0;
  }
  void setDelayMs(float ms) {
    float samples = ms * 0.001f * sampleRate_;
    if (samples < 1.0f) samples = 1.0f;
    if (samples > static_cast<float>(buffer_.size() - 1)) samples = static_cast<float>(buffer_.size() - 1);
    delaySamples_ = static_cast<int>(samples);
  }
  void setFeedback(float feedback) { feedback_ = feedback < 0.0f ? 0.0f : (feedback > 0.95f ? 0.95f : feedback); }
  void setMix(float mix) { mix_ = mix < 0.0f ? 0.0f : (mix > 1.0f ? 1.0f : mix); }
  float process(float input) {
    const int read = (write_ - delaySamples_ + static_cast<int>(buffer_.size())) %
                     static_cast<int>(buffer_.size());
    const float delayed = buffer_[read];
    buffer_[write_] = input + delayed * feedback_;
    write_ = (write_ + 1) % static_cast<int>(buffer_.size());
    return input * (1.0f - mix_) + delayed * mix_;
  }
  void render(const float* in, float* out, size_t frames) {
    for (size_t i = 0; i < frames; ++i) out[i] = process(in[i]);
  }
  int delaySamples() const { return delaySamples_; }
  float feedback() const { return feedback_; }

 private:
  float sampleRate_ = 48000.0f;
  std::vector<float> buffer_;
  int write_ = 0;
  int delaySamples_ = 12000;
  float feedback_ = 0.35f;
  float mix_ = 0.3f;
};

}  // namespace examples
}  // namespace bukifon
