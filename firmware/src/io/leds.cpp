// SPDX-License-Identifier: GPL-3.0-or-later
#include "io/leds.hpp"

#include <cmath>

namespace bukifon {

Rgb LedChain::hsv(float h, float s, float v) {
  h = h - std::floor(h);
  s = s < 0.0f ? 0.0f : (s > 1.0f ? 1.0f : s);
  v = v < 0.0f ? 0.0f : (v > 1.0f ? 1.0f : v);
  const float hue = h * 6.0f;
  const int i = static_cast<int>(hue) % 6;
  const float f = hue - std::floor(hue);
  const float p = v * (1.0f - s);
  const float q = v * (1.0f - s * f);
  const float t = v * (1.0f - s * (1.0f - f));
  float r = 0.0f, g = 0.0f, b = 0.0f;
  switch (i) {
    case 0: r = v; g = t; b = p; break;
    case 1: r = q; g = v; b = p; break;
    case 2: r = p; g = v; b = t; break;
    case 3: r = p; g = q; b = v; break;
    case 4: r = t; g = p; b = v; break;
    default: r = v; g = p; b = q; break;
  }
  return Rgb{static_cast<uint8_t>(r * 255.0f + 0.5f), static_cast<uint8_t>(g * 255.0f + 0.5f),
             static_cast<uint8_t>(b * 255.0f + 0.5f)};
}

Rgb LedChain::levelColor(float level) {
  level = level < 0.0f ? 0.0f : (level > 1.0f ? 1.0f : level);
  if (level < 0.5f) {
    const float t = level * 2.0f;
    return Rgb{static_cast<uint8_t>(255.0f * t), 255, 0};
  }
  const float t = (level - 0.5f) * 2.0f;
  return Rgb{255, static_cast<uint8_t>(255.0f * (1.0f - t)), 0};
}

Rgb LedChain::noteColor(int midiNote) {
  const float h = static_cast<float>(midiNote % 48) / 48.0f;
  return hsv(h, 0.85f, 0.9f);
}

Rgb LedChain::dim(Rgb c, float scale) {
  scale = scale < 0.0f ? 0.0f : (scale > 1.0f ? 1.0f : scale);
  return Rgb{static_cast<uint8_t>(c.r * scale), static_cast<uint8_t>(c.g * scale),
             static_cast<uint8_t>(c.b * scale)};
}

void buildLedFrame(const LedState& state, DeckType deckType, LedChain* chain) {
  if (!chain) return;
  const bool keys = deckType == DeckType::Keys;
  chain->setLength(kPanelLeds + (keys ? kKeyLeds : kPadLeds));
  chain->clear();
  // Panel: 8 encoder rings (value as hue) + status LED.
  for (int i = 0; i < kNumEncoders; ++i) {
    const float v = state.encoderValue[i];
    chain->set(i, LedChain::hsv(0.55f - 0.45f * v, 0.8f, 0.15f + 0.75f * v));
  }
  // Status LED: green when playing, orange when stopped, magenta in shift layer.
  if (state.shift) {
    chain->set(8, Rgb{255, 0, 200});
  } else if (state.playing) {
    chain->set(8, Rgb{0, 255, 40});
  } else {
    chain->set(8, Rgb{255, 100, 0});
  }

  const int deckOffset = kPanelLeds;
  if (keys) {
    for (int k = 0; k < kKeyLeds; ++k) {
      const bool pressed = (state.keyPressedMask & (1u << k)) != 0;
      if (pressed) {
        chain->set(deckOffset + k, Rgb{255, 255, 255});
      } else {
        // Show the active sequencer step across the key row for orientation.
        const bool stepLit = (k % kSeqSteps) == (state.activeStep % kSeqSteps);
        chain->set(deckOffset + k, stepLit ? LedChain::hsv(0.15f, 0.9f, 0.7f)
                                           : Rgb{0, 0, 12});
      }
    }
  } else {
    for (int p = 0; p < kPadLeds; ++p) {
      const bool pressed = (state.padPressedMask & (1u << p)) != 0;
      const bool stepLit = (p % kSeqSteps) == (state.activeStep % kSeqSteps);
      chain->set(deckOffset + p, pressed ? Rgb{255, 255, 255}
                                         : (stepLit ? LedChain::levelColor(state.masterLevel)
                                                    : Rgb{0, 0, 10}));
    }
  }
}

}  // namespace bukifon
