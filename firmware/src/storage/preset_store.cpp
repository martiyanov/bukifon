// SPDX-License-Identifier: GPL-3.0-or-later
#include "storage/preset_store.hpp"

#include <cstdio>
#include <cstring>

namespace bukifon {

void PresetStore::presetPath(int index, char* out, size_t size) {
  std::snprintf(out, size, "/presets/%02d.pmp", index % kNumPresets);
}

bool PresetStore::save(int index, const Patch& patch) {
  if (!fs_ || index < 0 || index >= kNumPresets) return false;
  uint8_t buffer[kMaxPatchBytes];
  const size_t length = patchSerialize(patch, buffer, sizeof(buffer));
  if (length == 0) return false;
  char path[32];
  presetPath(index, path, sizeof(path));
  if (!fs_->writeFile(path, buffer, length)) return false;
  cache_[index] = patch;
  valid_[index] = true;
  return true;
}

bool PresetStore::load(int index, Patch* out) {
  if (index < 0 || index >= kNumPresets) return false;
  if (valid_[index]) {
    if (out) *out = cache_[index];
    return true;
  }
  if (!fs_) return false;
  char path[32];
  presetPath(index, path, sizeof(path));
  uint8_t buffer[kMaxPatchBytes];
  size_t length = 0;
  if (!fs_->readFile(path, buffer, sizeof(buffer), &length)) return false;
  Patch patch;
  if (!patchDeserialize(buffer, length, &patch)) return false;
  cache_[index] = patch;
  valid_[index] = true;
  if (out) *out = patch;
  return true;
}

bool PresetStore::exists(int index) const {
  if (index < 0 || index >= kNumPresets) return false;
  if (valid_[index]) return true;
  if (!fs_) return false;
  char path[32];
  presetPath(index, path, sizeof(path));
  return fs_->exists(path);
}

bool PresetStore::erase(int index) {
  if (!fs_ || index < 0 || index >= kNumPresets) return false;
  char path[32];
  presetPath(index, path, sizeof(path));
  valid_[index] = false;
  return fs_->remove(path);
}

const Patch* PresetStore::cached(int index) const {
  if (index < 0 || index >= kNumPresets || !valid_[index]) return nullptr;
  return &cache_[index];
}

void PresetStore::putInCache(int index, const Patch& patch) {
  if (index < 0 || index >= kNumPresets) return;
  cache_[index] = patch;
  valid_[index] = true;
}

void PresetStore::loadFactoryBank() {
  for (int i = 0; i < kNumFactoryPatches; ++i) {
    makeFactoryPatch(i, &cache_[i]);
    valid_[i] = true;
  }
}

int PresetStore::cachedCount() const {
  int n = 0;
  for (int i = 0; i < kNumPresets; ++i) n += valid_[i] ? 1 : 0;
  return n;
}

}  // namespace bukifon
