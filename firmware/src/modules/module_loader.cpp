// SPDX-License-Identifier: GPL-3.0-or-later
#include "modules/module_loader.hpp"

#include <cstdio>
#include <cstring>
#include <vector>

namespace bukifon {
namespace {

bool readFile(const char* path, std::vector<uint8_t>* out) {
  if (!path || !out) return false;
  std::FILE* file = std::fopen(path, "rb");
  if (!file) return false;
  std::fseek(file, 0, SEEK_END);
  const long size = std::ftell(file);
  std::fseek(file, 0, SEEK_SET);
  if (size < 0) {
    std::fclose(file);
    return false;
  }
  out->resize(static_cast<size_t>(size));
  const size_t read = size > 0 ? std::fread(out->data(), 1, out->size(), file) : 0;
  std::fclose(file);
  return read == out->size();
}

}  // namespace

void ModuleLoader::clear() {
  count_ = 0;
  attempts_ = 0;
  rejected_ = 0;
  executedAnything_ = false;
  lastError_[0] = '\0';
  for (int i = 0; i < kMaxInstalledModules; ++i) modules_[i] = InstalledModule{};
}

const InstalledModule* ModuleLoader::at(int index) const {
  if (index < 0 || index >= count_) return nullptr;
  return &modules_[index];
}

const InstalledModule* ModuleLoader::find(const char* id) const {
  if (!id) return nullptr;
  for (int i = 0; i < count_; ++i) {
    if (std::strcmp(modules_[i].id, id) == 0) return &modules_[i];
  }
  return nullptr;
}

bool ModuleLoader::load(const char* manifestJson, const uint8_t* payload, size_t payloadSize,
                        char* error, size_t errorLen) {
  ++attempts_;
  if (error && errorLen) error[0] = '\0';
  ModuleManifest manifest;
  if (!moduleManifestParse(manifestJson, &manifest, error, errorLen)) {
    ++rejected_;
    if (error && errorLen) {
      std::snprintf(lastError_, sizeof(lastError_), "%s", error);
    }
    return false;
  }
  if (!moduleAbiAccepted(manifest.abi) ||
      (std::strcmp(manifest.abi, "host") != 0 && std::strcmp(manifest.abi, "any") != 0 &&
       std::strcmp(manifest.abi, "p4") != 0 && std::strcmp(manifest.abi, "s3") != 0)) {
    ++rejected_;
    std::snprintf(error, errorLen, "ABI target '%s' not accepted", manifest.abi);
    std::snprintf(lastError_, sizeof(lastError_), "%s", error);
    return false;
  }
  if (!payload) {
    ++rejected_;
    std::snprintf(error, errorLen, "DSP payload missing");
    std::snprintf(lastError_, sizeof(lastError_), "%s", error);
    return false;
  }
  if (manifest.size != payloadSize) {
    ++rejected_;
    std::snprintf(error, errorLen, "payload size %u != manifest size %u",
                  static_cast<unsigned>(payloadSize), static_cast<unsigned>(manifest.size));
    std::snprintf(lastError_, sizeof(lastError_), "%s", error);
    return false;
  }
  char actualSha[65];
  moduleSha256(payload, payloadSize, actualSha);
  if (std::strcmp(actualSha, manifest.sha256) != 0) {
    ++rejected_;
    std::snprintf(error, errorLen, "sha256 mismatch (payload %s, manifest %s)", actualSha,
                  manifest.sha256);
    std::snprintf(lastError_, sizeof(lastError_), "%s", error);
    return false;
  }
  if (count_ >= kMaxInstalledModules) {
    ++rejected_;
    std::snprintf(error, errorLen, "installed list full (%d)", kMaxInstalledModules);
    std::snprintf(lastError_, sizeof(lastError_), "%s", error);
    return false;
  }
  InstalledModule& slot = modules_[count_++];
  std::snprintf(slot.id, sizeof(slot.id), "%s", manifest.id);
  std::snprintf(slot.version, sizeof(slot.version), "%s", manifest.version);
  std::snprintf(slot.sha256, sizeof(slot.sha256), "%s", manifest.sha256);
  slot.size = manifest.size;
  slot.permissions = manifest.permissions;
  // Deliberately no callback/execution here: validation is complete, but the
  // module is only exposed as an installed entry (sandboxed ABI boundary).
  executedAnything_ = false;
  if (error && errorLen) {
    std::snprintf(error, errorLen, "installed %s %s", manifest.id, manifest.version);
  }
  return true;
}

bool ModuleLoader::loadFiles(const char* manifestPath, const char* dspPath, char* error,
                             size_t errorLen) {
  std::vector<uint8_t> manifestBytes;
  std::vector<uint8_t> payload;
  if (!readFile(manifestPath, &manifestBytes) || !readFile(dspPath, &payload)) {
    ++attempts_;
    ++rejected_;
    std::snprintf(error, errorLen, "cannot read manifest or DSP file");
    std::snprintf(lastError_, sizeof(lastError_), "%s", error);
    return false;
  }
  manifestBytes.push_back(0);
  return load(reinterpret_cast<const char*>(manifestBytes.data()), payload.data(),
              payload.size(), error, errorLen);
}

}  // namespace bukifon
