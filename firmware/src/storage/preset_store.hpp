// SPDX-License-Identifier: GPL-3.0-or-later
// 64 presets in LittleFS (flash) with a RAM cache of Patch structures.
#pragma once

#include <cstddef>
#include <cstdint>

#include "core/config.hpp"
#include "core/patch.hpp"

namespace bukifon {

// Abstraction over LittleFS on the device and an in-memory FS in host tests.
class IFileSystem {
 public:
  virtual ~IFileSystem() = default;
  virtual bool writeFile(const char* path, const uint8_t* data, size_t length) = 0;
  virtual bool readFile(const char* path, uint8_t* data, size_t maxLength, size_t* outLength) = 0;
  virtual bool exists(const char* path) = 0;
  virtual bool remove(const char* path) = 0;
};

class PresetStore {
 public:
  void init(IFileSystem* fs) { fs_ = fs; }
  bool save(int index, const Patch& patch);
  bool load(int index, Patch* out);
  bool exists(int index) const;
  bool erase(int index);
  const Patch* cached(int index) const;
  void putInCache(int index, const Patch& patch);
  void loadFactoryBank();
  int cachedCount() const;
  static void presetPath(int index, char* out, size_t size);

 private:
  IFileSystem* fs_ = nullptr;
  Patch cache_[kNumPresets] = {};
  bool valid_[kNumPresets] = {};
};

}  // namespace bukifon
