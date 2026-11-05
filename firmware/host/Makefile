# SPDX-License-Identifier: GPL-3.0-or-later
# Host build of the portable Bukifon engine (no Arduino dependencies).
#
#   make            -> build/bukifon_tests and build/bukifon_render
#   make test       -> build + run the unit tests
#   make render     -> build + render the WAV files
#   make clean

CXX      ?= /usr/bin/g++
PYTHON   ?= /opt/homebrew/bin/python3
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra
CPPFLAGS := -I../src -I../include -I../app -I../bench/lib -I. -MMD -MP
LDFLAGS  ?=

SRC_DIR   := ../src
TEST_DIR  := ../tests
BUILD     := build

SRC_FILES := $(wildcard $(SRC_DIR)/*/*.cpp)
OBJ       := $(patsubst $(SRC_DIR)/%.cpp,$(BUILD)/obj/%.o,$(SRC_FILES))

TEST_FILES := $(wildcard $(TEST_DIR)/*.cpp)
TEST_OBJ   := $(patsubst $(TEST_DIR)/%.cpp,$(BUILD)/test_obj/%.o,$(TEST_FILES))

RENDER_OBJ := $(BUILD)/host/render_wav.o
SIM_OBJ    := $(BUILD)/app/sim_main.o

EXAMPLE_FILES := $(wildcard ../modules/examples/*.cpp)
EXAMPLE_OBJ   := $(patsubst ../modules/examples/%.cpp,$(BUILD)/examples/%.o,$(EXAMPLE_FILES))

BENCH_DIR   := ../bench/lib
BENCH_FILES := $(wildcard $(BENCH_DIR)/*.cpp)
BENCH_OBJ   := $(patsubst $(BENCH_DIR)/%.cpp,$(BUILD)/bench_obj/%.o,$(BENCH_FILES))

TEST_BIN   := $(BUILD)/bukifon_tests
RENDER_BIN := $(BUILD)/bukifon_render
FACTORY_BIN := $(BUILD)/bukifon_factory
USB_DUMP_BIN := $(BUILD)/usb_dump
SIM_BIN    := $(BUILD)/bukifon_sim

.PHONY: all test render sim demo clean

all: $(TEST_BIN) $(RENDER_BIN)

$(BUILD)/obj/%.o: $(SRC_DIR)/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

$(BUILD)/test_obj/%.o: $(TEST_DIR)/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

$(BUILD)/host/%.o: %.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

$(BUILD)/app/%.o: ../app/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

$(BUILD)/examples/%.o: ../modules/examples/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

$(BUILD)/bench_obj/%.o: $(BENCH_DIR)/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

-include $(shell find $(BUILD) -name '*.d' 2>/dev/null)

$(TEST_BIN): $(OBJ) $(TEST_OBJ) $(EXAMPLE_OBJ) $(BENCH_OBJ)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LDFLAGS)

$(BUILD)/factory_main.o: ../app/factory_main.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

$(BUILD)/usb_dump_main.o: ../app/usb_dump_main.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

$(USB_DUMP_BIN): $(OBJ) $(BUILD)/usb_dump_main.o
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $^ -o $@

usbdump: $(USB_DUMP_BIN)
	@mkdir -p ../artifacts/usb
	./$(USB_DUMP_BIN)

$(FACTORY_BIN): $(OBJ) $(BUILD)/factory_main.o
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $^ -o $@

factory: $(FACTORY_BIN)
	@mkdir -p ../tests/out
	./$(FACTORY_BIN) --json --out ../tests/out/factory_report.json

$(RENDER_BIN): $(OBJ) $(RENDER_OBJ) $(EXAMPLE_OBJ)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LDFLAGS)

$(SIM_BIN): $(OBJ) $(SIM_OBJ) $(EXAMPLE_OBJ)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LDFLAGS)

test: $(TEST_BIN)
	@mkdir -p ../tests/out
	cd . && ./$(TEST_BIN)

render: $(RENDER_BIN)
	mkdir -p ../tests/out
	./$(RENDER_BIN) ../tests/out

sim: $(SIM_BIN)
	@mkdir -p ../artifacts/ui ../artifacts/sim ../tests/out
	./$(SIM_BIN) --out ../artifacts/ui --log ../artifacts/sim/event_log.txt

demo: sim
	$(PYTHON) ../tools/ppm_to_png.py ../artifacts/ui

clean:
	rm -rf $(BUILD)
