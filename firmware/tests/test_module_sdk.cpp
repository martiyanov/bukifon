// SPDX-License-Identifier: GPL-3.0-or-later
// Module SDK v0.2 tests: manifest validation, API/ABI compatibility, SHA-256,
// loader accept/reject/list, permissions, and the two example modules.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "modules/module_loader.hpp"
#include "modules/module_manifest.hpp"
#include "modules/examples/mod_euclid_arp/model.hpp"
#include "modules/examples/mod_tape_delay/model.hpp"
#include "test_framework.hpp"

using namespace bukifon;

namespace {

std::string readFileText(const char* path) {
  std::FILE* file = std::fopen(path, "rb");
  if (!file) return {};
  std::string out;
  char buffer[2048];
  size_t n = 0;
  while ((n = std::fread(buffer, 1, sizeof(buffer), file)) > 0) out.append(buffer, n);
  std::fclose(file);
  return out;
}

std::string makeManifest(const char* sha = nullptr) {
  char hash[65];
  if (sha) {
    std::snprintf(hash, sizeof(hash), "%s", sha);
  } else {
    moduleSha256(reinterpret_cast<const uint8_t*>("dsp"), 3, hash);
  }
  char json[1400];
  std::snprintf(json, sizeof(json),
                "{\"schema\":\"bukifon.module.v2\",\"id\":\"vendor.test_mod\","
                "\"name\":\"Test Mod\",\"version\":\"0.2.0\",\"api\":\"0.2.0\","
                "\"author\":\"tester\",\"abi\":\"host\","
                "\"permissions\":[\"audio\",\"params\"],"
                "\"params\":[{\"id\":0,\"name\":\"GAIN\",\"type\":\"float\","
                "\"min\":0.0,\"max\":1.0,\"default\":0.5}],"
                "\"dsp\":\"model.hpp\",\"size\":3,\"sha256\":\"%s\","
                "\"license\":\"GPL-3.0-or-later\",\"description\":\"test\"}",
                hash);
  return json;
}

}  // namespace

TEST(ModuleManifestValidTapeDelay) {
  const std::string json = readFileText("../modules/examples/mod_tape_delay/module.json");
  CHECK(!json.empty());
  ModuleManifest m;
  char error[192];
  CHECK(moduleManifestParse(json.c_str(), &m, error, sizeof(error)));
  CHECK(std::strcmp(m.schema, "bukifon.module.v2") == 0);
  CHECK(std::strcmp(m.id, "bukifon.mod_tape_delay") == 0);
  CHECK(std::strcmp(m.version, "0.2.0") == 0);
  CHECK(std::strcmp(m.abi, "any") == 0);
  CHECK(m.apiMajor == 0 && m.apiMinor == 2);
  CHECK(m.paramCount == 3);
  CHECK((m.permissions & kPermAudio) != 0);
  CHECK((m.permissions & kPermParams) != 0);
  CHECK((m.permissions & kPermIo) == 0);
  CHECK(m.size > 0 && std::strlen(m.sha256) == 64);
  INFO("manifest v2: tape delay fields/params/permissions/API parsed");
}

TEST(ModuleManifestValidEuclidArp) {
  const std::string json = readFileText("../modules/examples/mod_euclid_arp/module.json");
  ModuleManifest m;
  char error[192];
  CHECK(moduleManifestParse(json.c_str(), &m, error, sizeof(error)));
  CHECK(std::strcmp(m.id, "bukifon.mod_euclid_arp") == 0);
  CHECK(m.paramCount == 4);
  CHECK((m.permissions & kPermSeq) != 0);
  INFO("manifest v2: euclid arp permissions include seq");
}

TEST(ModuleManifestRejectsSchema) {
  ModuleManifest m;
  char error[192];
  std::string json = makeManifest();
  const size_t pos = json.find("bukifon.module.v2");
  json.replace(pos, std::strlen("bukifon.module.v2"), "bukifon.module.v1");
  CHECK(!moduleManifestParse(json.c_str(), &m, error, sizeof(error)));
  CHECK(std::strstr(error, "schema") != nullptr);
  INFO("manifest rejects wrong schema with a readable error");
}

TEST(ModuleManifestRejectsFields) {
  ModuleManifest m;
  char error[192];
  std::string json = makeManifest();
  json.replace(json.find("\"id\":"), 5, "\"nope\":");  // removes id key
  json.insert(json.find("\"nope\":"), "\"zz\":");
  CHECK(!moduleManifestParse(json.c_str(), &m, error, sizeof(error)));
  CHECK(std::strstr(error, "id") != nullptr);
  INFO("manifest rejects missing id");
}

TEST(ModuleApiCompatibility) {
  CHECK(moduleApiCompatible(0, 0));
  CHECK(moduleApiCompatible(0, 1));
  CHECK(moduleApiCompatible(0, 2));
  CHECK(!moduleApiCompatible(0, 3));   // host minor too old
  CHECK(!moduleApiCompatible(1, 0));   // major mismatch
  ModuleManifest m;
  char error[192];
  std::string json = makeManifest();
  const size_t apiPos = json.find("\"api\":\"0.2.0\"");
  json.replace(apiPos, std::strlen("\"api\":\"0.2.0\""), "\"api\":\"1.0.0\"");
  CHECK(!moduleManifestParse(json.c_str(), &m, error, sizeof(error)));
  CHECK(std::strstr(error, "API") != nullptr);
  INFO("API compatibility: same major and host minor >= module minor");
}

TEST(ModuleAbiTargets) {
  CHECK(moduleAbiAccepted("host"));
  CHECK(moduleAbiAccepted("p4"));
  CHECK(moduleAbiAccepted("s3"));
  CHECK(moduleAbiAccepted("any"));
  CHECK(!moduleAbiAccepted(""));
  CHECK(!moduleAbiAccepted("rp2040"));
  INFO("ABI targets: host/p4/s3/any accepted, others rejected");
}

TEST(ModulePermissionsParsed) {
  ModuleManifest m;
  char error[192];
  std::string json = makeManifest();
  const size_t p = json.find("\"permissions\":[\"audio\",\"params\"]");
  json.replace(p, std::strlen("\"permissions\":[\"audio\",\"params\"]"),
               "\"permissions\":[\"audio\",\"params\",\"seq\",\"io\"]");
  CHECK(moduleManifestParse(json.c_str(), &m, error, sizeof(error)));
  CHECK(m.permissions == kPermAll);
  json.replace(json.find("\"permissions\":[\"audio\",\"params\",\"seq\",\"io\"]"),
               std::strlen("\"permissions\":[\"audio\",\"params\",\"seq\",\"io\"]"),
               "\"permissions\":[]");
  CHECK(!moduleManifestParse(json.c_str(), &m, error, sizeof(error)));
  INFO("permissions: audio/params/seq/io bits; empty list rejected");
}

TEST(ModuleParamsValidation) {
  ModuleManifest m;
  char error[192];
  std::string json = makeManifest();
  const size_t paramsPos = json.find("\"params\":[");
  const size_t paramsEnd = json.find("],", paramsPos);
  const std::string good = json.substr(paramsPos, paramsEnd - paramsPos + 2);
  // duplicate id
  json.replace(paramsPos, good.size(),
               "\"params\":[{\"id\":0,\"name\":\"A\",\"min\":0,\"max\":1,\"default\":0.5},"
               "{\"id\":0,\"name\":\"B\",\"min\":0,\"max\":1,\"default\":0.5}],");
  CHECK(!moduleManifestParse(json.c_str(), &m, error, sizeof(error)));
  CHECK(std::strstr(error, "duplicate") != nullptr);
  // default outside
  json.replace(paramsPos, strlen("\"params\":[{\"id\":0,\"name\":\"A\",\"min\":0,\"max\":1,\"default\":0.5},{\"id\":0,\"name\":\"B\",\"min\":0,\"max\":1,\"default\":0.5}],"),
               "\"params\":[{\"id\":0,\"name\":\"A\",\"min\":0,\"max\":1,\"default\":2}],");
  CHECK(!moduleManifestParse(json.c_str(), &m, error, sizeof(error)));
  CHECK(std::strstr(error, "default") != nullptr);
  INFO("params: 1..16, unique ids, min<max, default inside range");
}

TEST(ModuleSha256KnownVector) {
  char hex[65];
  moduleSha256(reinterpret_cast<const uint8_t*>("abc"), 3, hex);
  CHECK(std::strcmp(hex, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") == 0);
  CHECK(moduleSha256Matches(reinterpret_cast<const uint8_t*>("abc"), 3, hex));
  CHECK(!moduleSha256Matches(reinterpret_cast<const uint8_t*>("abd"), 3, hex));
  INFO("SHA-256 matches the standard 'abc' test vector");
}

TEST(ModuleLoaderLoadsExamples) {
  ModuleLoader loader;
  char error[192];
  CHECK(loader.loadFiles("../modules/examples/mod_tape_delay/module.json",
                         "../modules/examples/mod_tape_delay/model.hpp", error, sizeof(error)));
  CHECK(loader.loadFiles("../modules/examples/mod_euclid_arp/module.json",
                         "../modules/examples/mod_euclid_arp/model.hpp", error, sizeof(error)));
  CHECK(loader.count() == 2);
  CHECK(loader.find("bukifon.mod_tape_delay") != nullptr);
  CHECK(loader.find("bukifon.mod_euclid_arp") != nullptr);
  CHECK(std::strcmp(loader.find("bukifon.mod_euclid_arp")->version, "0.2.0") == 0);
  CHECK(std::strlen(loader.find("bukifon.mod_tape_delay")->sha256) == 64);
  CHECK(!loader.executedAnything());
  CHECK(loader.attempts() == 2);
  CHECK(loader.rejected() == 0);
  INFO("loader installs both examples with id/version/sha256; executes nothing");
}

TEST(ModuleLoaderRejectsShaMismatch) {
  ModuleLoader loader;
  char error[192];
  const uint8_t payload[4] = {'d', 's', 'p', '!'};
  std::string json = makeManifest();  // hash of "dsp", size 3
  CHECK(!loader.load(json.c_str(), payload, sizeof(payload), error, sizeof(error)));
  CHECK(loader.count() == 0);
  CHECK(loader.rejected() == 1);
  CHECK(std::strstr(error, "size") != nullptr || std::strstr(error, "sha") != nullptr);
  CHECK(!loader.executedAnything());
  INFO("loader rejects payload with wrong size/hash, never installs/executes");
}

TEST(ModuleLoaderRejectsApiAndAbi) {
  ModuleLoader loader;
  char error[192];
  const uint8_t payload[3] = {'d', 's', 'p'};
  std::string json = makeManifest();
  const size_t api = json.find("\"api\":\"0.2.0\"");
  json.replace(api, std::strlen("\"api\":\"0.2.0\""), "\"api\":\"2.0.0\"");
  CHECK(!loader.load(json.c_str(), payload, sizeof(payload), error, sizeof(error)));
  CHECK(loader.count() == 0);
  const size_t abi = json.find("\"abi\":\"host\"");
  json.replace(abi, std::strlen("\"abi\":\"host\""), "\"abi\":\"unknown\"");
  CHECK(!loader.load(json.c_str(), payload, sizeof(payload), error, sizeof(error)));
  CHECK(loader.count() == 0);
  INFO("loader rejects incompatible API major and unknown ABI target");
}

TEST(ModuleLoaderListAndAttempts) {
  ModuleLoader loader;
  char error[192];
  const uint8_t payload[3] = {'d', 's', 'p'};
  std::string json = makeManifest();
  CHECK(loader.load(json.c_str(), payload, sizeof(payload), error, sizeof(error)));
  CHECK(loader.load(json.c_str(), payload, sizeof(payload), error, sizeof(error)));  // duplicate entry allowed
  CHECK(loader.count() == 2);
  CHECK(loader.at(1) != nullptr);
  CHECK(loader.at(2) == nullptr);
  CHECK(loader.find("missing") == nullptr);
  std::string bad = json;
  bad.replace(bad.find("\"sha256\":\""), 9, "\"sha256\":\"00000000");
  CHECK(!loader.load(bad.c_str(), payload, sizeof(payload), error, sizeof(error)));
  CHECK(loader.count() == 2);
  CHECK(loader.attempts() == 3);
  CHECK(loader.rejected() >= 1);
  INFO("loader list/find/count and rejection counters are consistent");
}

TEST(ModuleExampleTapeDelayImpulse) {
  examples::TapeDelayModel delay;
  CHECK(delay.init(48000.0f));
  delay.setDelayMs(100.0f);
  delay.setFeedback(0.0f);
  delay.setMix(1.0f);
  const int delaySamples = delay.delaySamples();
  CHECK(delaySamples == 4800);
  float out = 0.0f;
  for (int i = 0; i < delaySamples - 1; ++i) out = delay.process(0.0f);
  CHECK(std::fabs(out) < 1e-6f);
  out = delay.process(1.0f);  // impulse enters the buffer
  for (int i = 0; i < delaySamples; ++i) out = delay.process(0.0f);
  CHECK(out > 0.9f);  // echo one delay later
  INFO("tape delay example: impulse returns after 100 ms");
}

TEST(ModuleExampleTapeDelayDeterministic) {
  examples::TapeDelayModel a;
  examples::TapeDelayModel b;
  a.init(48000.0f);
  b.init(48000.0f);
  a.setFeedback(0.5f);
  b.setFeedback(0.5f);
  for (int i = 0; i < 1000; ++i) {
    const float x = std::sin(static_cast<float>(i) * 0.01f);
    CHECK(a.process(x) == b.process(x));
  }
  INFO("tape delay example is deterministic for identical state");
}

TEST(ModuleExampleEuclidArp) {
  examples::EuclidArpModel arp;
  arp.init(1234);
  CHECK(arp.mask() == genEuclidMask(5, 16));
  uint8_t steps[16] = {};
  uint8_t vels[16] = {};
  int count = 0;
  CHECK(arp.renderBar(steps, vels, &count) == 5);
  CHECK(count == 5);
  for (int i = 0; i < count; ++i) CHECK(arp.triggerAt(steps[i]));
  examples::EuclidArpModel same;
  same.init(1234);
  uint8_t steps2[16] = {};
  uint8_t vels2[16] = {};
  int count2 = 0;
  same.renderBar(steps2, vels2, &count2);
  CHECK(count == count2);
  CHECK(std::memcmp(steps, steps2, sizeof(steps)) == 0);
  CHECK(std::memcmp(vels, vels2, sizeof(vels)) == 0);
  const uint8_t held[3] = {60, 64, 67};
  CHECK(arp.noteForStep(held, 3, 0) == 60);
  CHECK(arp.noteForStep(held, 3, 2) == 64);
  CHECK(arp.noteForStep(held, 3, 4) == 67);
  INFO("euclid arp example: 5/16 deterministic steps/velocities and ARP notes");
}

TEST(ModuleExampleManifestsPackageConsistency) {
  const std::string json = readFileText("../modules/examples/mod_tape_delay/module.json");
  ModuleManifest m;
  char error[192];
  CHECK(moduleManifestParse(json.c_str(), &m, error, sizeof(error)));
  const std::string payload = readFileText("../modules/examples/mod_tape_delay/model.hpp");
  CHECK(payload.size() == m.size);
  CHECK(moduleSha256Matches(reinterpret_cast<const uint8_t*>(payload.data()), payload.size(),
                            m.sha256));
  CHECK(std::strcmp(m.dsp, "model.hpp") == 0);
  INFO("example manifest size/sha256 match the DSP payload (package integrity)");
}

TEST(ModuleLoaderRejectsBadManifestWithoutExecution) {
  ModuleLoader loader;
  char error[192];
  const uint8_t payload[3] = {'d', 's', 'p'};
  CHECK(!loader.load("not json", payload, sizeof(payload), error, sizeof(error)));
  CHECK(loader.count() == 0);
  CHECK(loader.rejected() == 1);
  CHECK(!loader.executedAnything());
  CHECK(loader.lastError()[0] != '\0');
  INFO("invalid manifest: readable error, no install, no execution");
}

TEST(ModuleManifestRejectsShaFormat) {
  ModuleManifest m;
  char error[192];
  std::string json = makeManifest();
  const size_t p = json.find("\"sha256\":\"");
  json.replace(p, std::strlen("\"sha256\":\""), "\"sha256\":\"xyz");
  CHECK(!moduleManifestParse(json.c_str(), &m, error, sizeof(error)));
  CHECK(std::strstr(error, "sha256") != nullptr);
  INFO("manifest rejects non-hex/short sha256 with a readable error");
}

TEST(ModuleLoaderRejectsUnknownAbi) {
  ModuleLoader loader;
  char error[192];
  const uint8_t payload[3] = {'d', 's', 'p'};
  std::string json = makeManifest();
  const size_t abi = json.find("\"abi\":\"host\"");
  json.replace(abi, std::strlen("\"abi\":\"host\""), "\"abi\":\"rp2040\"");
  CHECK(!loader.load(json.c_str(), payload, sizeof(payload), error, sizeof(error)));
  CHECK(loader.count() == 0);
  CHECK(std::strstr(error, "ABI") != nullptr || std::strstr(error, "abi") != nullptr);
  INFO("loader rejects an unknown ABI target before installing anything");
}
