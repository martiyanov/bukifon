// SPDX-License-Identifier: GPL-3.0-or-later
// Unity translation unit for the PlatformIO build.
//
// The portable engine lives outside the sketch project (firmware/src) so the
// host tests can build it without Arduino; PlatformIO only compiles sources
// below this project, therefore the engine .cpp files are included here.
// Keep this list in sync with the directories in firmware/src.
#include "../src/core/params.cpp"
#include "../src/core/patch.cpp"
#include "../src/core/modulation_defs.cpp"
#include "../src/dsp/wavetable.cpp"
#include "../src/dsp/wavetable_data.cpp"
#include "../src/dsp/oscillator.cpp"
#include "../src/dsp/fm.cpp"
#include "../src/dsp/filter.cpp"
#include "../src/dsp/ensemble.cpp"
#include "../src/dsp/envelope.cpp"
#include "../src/dsp/lfo.cpp"
#include "../src/dsp/effects.cpp"
#include "../src/audio/part.cpp"
#include "../src/audio/voice.cpp"
#include "../src/audio/engine.cpp"
#include "../src/io/midi_parser.cpp"
#include "../src/io/midi_router.cpp"
#include "../src/io/deck.cpp"
#include "../src/io/cv.cpp"
#include "../src/io/leds.cpp"
#include "../src/io/sequencer.cpp"
#include "../src/io/arp.cpp"
#include "../src/modules/module_registry.cpp"
#include "../src/modules/hw_module.cpp"
#include "../src/storage/preset_store.cpp"
#include "../src/storage/eeprom.cpp"
#include "../src/ui/font6x8.cpp"
#include "../src/ui/menu.cpp"
