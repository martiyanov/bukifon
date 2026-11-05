// SPDX-License-Identifier: GPL-3.0-or-later
// Factory self-test CLI (host/mock entry point): `factory [--json] ...`.
//
// Device integration (P4FactoryHardware on first working P4 toolchain) is
// TODO(hw): call the same factoryCliMain with a Serial/USB-CDC FILE adapter.
#include <cstdio>

#include "factory/mock_hardware.hpp"
#include "factory/selftest.hpp"

int main(int argc, char** argv) {
  bukifon::factory::MockHardware hardware;
  return bukifon::factory::factoryCliMain(argc, argv, hardware, stdout);
}
