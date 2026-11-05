// SPDX-License-Identifier: GPL-3.0-or-later
// Factory identity: serial/date validation, CRC, JSON, two-slot store, CLI.
#include <cstdio>
#include <cstring>
#include <string>

#include "factory/identity.hpp"
#include "factory/mock_hardware.hpp"
#include "factory/selftest.hpp"
#include "test_framework.hpp"

using namespace bukifon::factory;

namespace {

Identity makeIdentity(const char* serial = "BKS3-26A-0001") {
  Identity identity;
  std::snprintf(identity.serial, sizeof(identity.serial), "%s", serial);
  std::snprintf(identity.product, sizeof(identity.product), "%s", "BUKIFON");
  std::snprintf(identity.coreRev, sizeof(identity.coreRev), "%s", "2.p4");
  std::snprintf(identity.panelRev, sizeof(identity.panelRev), "%s", "2");
  std::snprintf(identity.pwrRev, sizeof(identity.pwrRev), "%s", "1");
  std::snprintf(identity.date, sizeof(identity.date), "%s", "2026-11-05");
  std::snprintf(identity.batch, sizeof(identity.batch), "%s", "26A");
  identity.mac[0] = 0x24;
  identity.mac[1] = 0x0A;
  identity.mac[2] = 0xC4;
  identity.mac[3] = 0x11;
  identity.mac[4] = 0x22;
  identity.mac[5] = 0x33;
  std::snprintf(identity.calibrationVersion, sizeof(identity.calibrationVersion), "%s", "cal1");
  std::snprintf(identity.testResult, sizeof(identity.testResult), "%s", "PASS");
  identitySeal(&identity);
  return identity;
}

bool writeFile(const char* path, const std::string& text) {
  std::FILE* file = std::fopen(path, "wb");
  if (!file) return false;
  const bool ok = std::fwrite(text.data(), 1, text.size(), file) == text.size();
  std::fclose(file);
  return ok;
}

std::string readFile(FILE* file) {
  std::fflush(file);
  std::fseek(file, 0, SEEK_END);
  const long size = std::ftell(file);
  std::fseek(file, 0, SEEK_SET);
  std::string out(static_cast<size_t>(size), '\0');
  std::fread(&out[0], 1, static_cast<size_t>(size), file);
  return out;
}

}  // namespace

TEST(IdentitySerialFormat) {
  char error[96];
  CHECK(identitySerialValid("BKS3-26A-0001", error, sizeof(error)));
  CHECK(identitySerialValid("BKS3-26Z-9999"));
  CHECK(!identitySerialValid("BKS2-26A-0001"));
  CHECK(!identitySerialValid("BKS3-26A-001"));
  CHECK(!identitySerialValid("BKS3-26a-0001"));
  CHECK(!identitySerialValid("BKS3-26AA-0001"));
  CHECK(!identitySerialValid("BKS3-26A-ABCD"));
  CHECK(strstr(error, "four digits") != nullptr || error[0] == '\0');
  INFO("SN format: BKS3-YYA-NNNN (product-gen, batch, 4 digits) strictly validated");
}

TEST(IdentityDateFormat) {
  CHECK(identityDateValid("2026-11-05"));
  CHECK(!identityDateValid("26-11-05"));
  CHECK(!identityDateValid("2026-13-05"));
  CHECK(!identityDateValid("2026-00-10"));
  CHECK(!identityDateValid("2026-11-32"));
  CHECK(!identityDateValid("abcd-ef-gh"));
  INFO("date format: YYYY-MM-DD with month/day range check");
}

TEST(IdentityValidation) {
  Identity identity = makeIdentity();
  char error[96];
  CHECK(identityValidate(identity, error, sizeof(error)));
  CHECK(identityVerifyCrc(identity));
  identity.magic = 0x12345678;
  CHECK(!identityValidate(identity, error, sizeof(error)));
  identity = makeIdentity();
  identity.version = 99;
  CHECK(!identityValidate(identity, error, sizeof(error)));
  identity = makeIdentity();
  std::snprintf(identity.product, sizeof(identity.product), "%s", "OTHER");
  CHECK(!identityValidate(identity, error, sizeof(error)));
  identity = makeIdentity();
  std::snprintf(identity.batch, sizeof(identity.batch), "%s", "26B");
  CHECK(!identityValidate(identity, error, sizeof(error)));
  CHECK(strstr(error, "batch") != nullptr);
  identity = makeIdentity();
  memset(identity.mac, 0, sizeof(identity.mac));
  CHECK(!identityValidate(identity, error, sizeof(error)));
  INFO("identity validation: magic/version/product/serial/batch/date/MAC/CRC contract");
}

TEST(IdentitySerializeRoundtrip) {
  const Identity identity = makeIdentity();
  uint8_t blob[kIdentitySerializedSize];
  size_t written = 0;
  CHECK(identitySerialize(identity, blob, sizeof(blob), &written));
  CHECK(written == kIdentitySerializedSize);
  CHECK(kIdentitySerializedSize == 114);
  Identity decoded;
  char error[96];
  CHECK(identityDeserialize(blob, written, &decoded, error, sizeof(error)));
  CHECK(std::strcmp(decoded.serial, identity.serial) == 0);
  CHECK(std::strcmp(decoded.coreRev, identity.coreRev) == 0);
  CHECK(std::strcmp(decoded.panelRev, identity.panelRev) == 0);
  CHECK(std::strcmp(decoded.batch, identity.batch) == 0);
  CHECK(std::strcmp(decoded.date, identity.date) == 0);
  CHECK(decoded.crc32 == identity.crc32);
  CHECK(identityVerifyCrc(decoded));
  uint8_t small[16];
  CHECK(!identitySerialize(identity, small, sizeof(small)));
  CHECK(!identityDeserialize(blob, 10, &decoded, error, sizeof(error)));
  INFO("serialize/deserialize: %u-byte little-endian blob, fixed size, bounds checked",
       static_cast<unsigned>(kIdentitySerializedSize));
}

TEST(IdentityCrcDetectsCorruption) {
  Identity identity = makeIdentity();
  uint8_t blob[kIdentitySerializedSize];
  CHECK(identitySerialize(identity, blob, sizeof(blob)));
  const uint32_t originalCrc = identity.crc32;
  blob[84] ^= 0x01;  // MAC byte (still a valid MAC, so CRC is the failure)
  Identity decoded;
  char error[96];
  CHECK(!identityDeserialize(blob, sizeof(blob), &decoded, error, sizeof(error)));
  CHECK(strstr(error, "CRC") != nullptr);
  identity = makeIdentity();
  identity.serial[12] = '2';
  CHECK(identityComputeCrc(identity) != originalCrc);
  INFO("CRC32 catches a single corrupted byte in the identity blob");
}

TEST(IdentityJsonRoundtrip) {
  const Identity identity = makeIdentity();
  const std::string json = identityToJson(identity);
  CHECK(json.find("\"serial\":\"BKS3-26A-0001\"") != std::string::npos);
  CHECK(json.find("\"core_rev\":\"2.p4\"") != std::string::npos);
  CHECK(json.find("\"mac\":\"24:0A:C4:11:22:33\"") != std::string::npos);
  Identity decoded;
  char error[96];
  CHECK(identityFromJson(json.c_str(), &decoded, error, sizeof(error)));
  CHECK(std::strcmp(decoded.serial, identity.serial) == 0);
  CHECK(decoded.crc32 == identity.crc32);
  CHECK(!identityFromJson("{}", &decoded, error, sizeof(error)));
  CHECK(error[0] != '\0');
  std::string bad = json;
  const std::string needle = "\"serial\":\"BKS3-26A-0001\"";
  const size_t pos = bad.find(needle);
  CHECK(pos != std::string::npos);
  bad.replace(pos, needle.size(), "\"serial\":\"BAD\"");
  CHECK(!identityFromJson(bad.c_str(), &decoded, error, sizeof(error)));
  INFO("bad serial JSON error: %s", error);
  CHECK(strstr(error, "serial") != nullptr);
  INFO("JSON identity roundtrip; malformed serial rejected");
}

TEST(IdentityMacValidation) {
  Identity identity = makeIdentity();
  CHECK(identityValidate(identity));
  char macText[] = "AA:BB:CC:DD:EE:FF";
  CHECK(std::strlen(macText) == 17);
  identity.mac[0] = 0xAA;
  identitySeal(&identity);
  CHECK(identityVerifyCrc(identity));
  identity.mac[1] = 0x00;
  CHECK(!identityVerifyCrc(identity));
  INFO("MAC is part of the CRC'd identity; eFuse anchor documented");
}

TEST(IdentityStoreWriteRead) {
  IdentityStore store;
  CHECK(store.count() == 0);
  Identity first = makeIdentity("BKS3-26A-0001");
  char error[96];
  CHECK(store.write(first, error, sizeof(error)));
  CHECK(store.count() == 1);
  Identity second = makeIdentity("BKS3-26A-0002");
  CHECK(store.write(second, error, sizeof(error)));
  CHECK(store.count() == 2);
  CHECK(store.hasSerial("BKS3-26A-0001"));
  CHECK(store.hasSerial("BKS3-26A-0002"));
  Identity read;
  int slot = -1;
  CHECK(store.read(&read, &slot));
  CHECK(std::strcmp(read.serial, "BKS3-26A-0002") == 0);
  CHECK(slot == 1);  // alternating two-copy layout
  INFO("store: two alternating copies, latest valid read, duplicate check");
}

TEST(IdentityStoreDuplicateSerialRejected) {
  IdentityStore store;
  char error[96];
  Identity first = makeIdentity("BKS3-26A-0001");
  CHECK(store.write(first, error, sizeof(error)));
  Identity duplicate = makeIdentity("BKS3-26A-0001");
  CHECK(!store.write(duplicate, error, sizeof(error)));
  CHECK(strstr(error, "duplicate") != nullptr);
  CHECK(store.count() == 1);
  INFO("duplicate SN rejected by the identity store");
}

TEST(IdentityStoreCorruptSlotFallback) {
  IdentityStore store;
  char error[96];
  CHECK(store.write(makeIdentity("BKS3-26A-0001"), error, sizeof(error)));
  CHECK(store.write(makeIdentity("BKS3-26A-0002"), error, sizeof(error)));
  // Corrupt the older copy (slot 0); the newer slot 1 is still valid.
  Identity corrupt = makeIdentity("BKS3-26A-0001");
  corrupt.magic = 0xDEADBEEF;
  CHECK(store.writeRaw(0, corrupt));
  Identity read;
  CHECK(store.read(&read));
  CHECK(std::strcmp(read.serial, "BKS3-26A-0002") == 0);
  corrupt = makeIdentity("BKS3-26A-0002");
  corrupt.crc32 ^= 0xFF;
  CHECK(store.writeRaw(1, corrupt));
  CHECK(!store.read(&read));  // no valid copy left
  INFO("two-copy fallback: corrupt slot rejected, latest valid copy used");
}

TEST(IdentityStoreThirdWriteRotates) {
  IdentityStore store;
  char error[96];
  CHECK(store.write(makeIdentity("BKS3-26A-0001"), error, sizeof(error)));
  CHECK(store.write(makeIdentity("BKS3-26A-0002"), error, sizeof(error)));
  CHECK(store.write(makeIdentity("BKS3-26A-0003"), error, sizeof(error)));
  CHECK(store.count() == 2);  // two physical slots
  Identity read;
  CHECK(store.read(&read));
  CHECK(std::strcmp(read.serial, "BKS3-26A-0003") == 0);
  CHECK(!store.hasSerial("BKS3-26A-0001"));  // overwritten slot
  INFO("third write rotates the two-slot flash layout (oldest copy replaced)");
}

TEST(IdentityCliWriteAndPrint) {
  IdentityStore store;
  MockHardware hardware;
  const char* path = "../tests/out/identity_cli.json";
  const Identity identity = makeIdentity("BKS3-26A-0042");
  CHECK(writeFile(path, identityToJson(identity)));
  std::FILE* tmp = std::tmpfile();
  CHECK(tmp != nullptr);
  char a0[] = "factory";
  char a1[] = "--identity";
  char a2[] = "../tests/out/identity_cli.json";
  char* argv[] = {a0, a1, a2, nullptr};
  const int rc = factoryCliMain(3, argv, hardware, tmp, &store);
  CHECK(rc == 0);
  const std::string outText = readFile(tmp);
  CHECK(outText.find("IDENTITY OK") != std::string::npos);
  CHECK(outText.find("BKS3-26A-0042") != std::string::npos);
  CHECK(store.count() == 1);
  std::fclose(tmp);
  std::remove(path);

  std::FILE* printTmp = std::tmpfile();
  char b0[] = "factory";
  char b1[] = "--print-identity";
  char* printArgv[] = {b0, b1, nullptr};
  CHECK(factoryCliMain(2, printArgv, hardware, printTmp, &store) == 0);
  const std::string printed = readFile(printTmp);
  CHECK(printed.find("\"serial\":\"BKS3-26A-0042\"") != std::string::npos);
  std::fclose(printTmp);
  INFO("CLI: --identity writes/validates, --print-identity reads the store");
}

TEST(IdentityCliRejectsInvalidAndEmpty) {
  IdentityStore emptyStore;
  MockHardware hardware;
  std::FILE* tmp = std::tmpfile();
  char p0[] = "factory";
  char p1[] = "--print-identity";
  char* printArgv[] = {p0, p1, nullptr};
  CHECK(factoryCliMain(2, printArgv, hardware, tmp, &emptyStore) == 3);
  std::fclose(tmp);

  const char* path = "../tests/out/identity_bad.json";
  CHECK(writeFile(path, "{\"product\":\"BUKIFON\",\"serial\":\"BAD\"}"));
  std::FILE* tmp2 = std::tmpfile();
  char a0[] = "factory";
  char a1[] = "--identity";
  char a2[] = "../tests/out/identity_bad.json";
  char* argv[] = {a0, a1, a2, nullptr};
  IdentityStore store;
  CHECK(factoryCliMain(3, argv, hardware, tmp2, &store) == 1);
  const std::string outText = readFile(tmp2);
  CHECK(outText.find("IDENTITY FAIL") != std::string::npos);
  std::fclose(tmp2);
  std::remove(path);
  INFO("CLI: empty store -> exit 3, invalid identity JSON -> exit 1");
}
