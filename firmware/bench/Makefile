# SPDX-License-Identifier: GPL-3.0-or-later
# Bukifon P1 benchmark — host build/run.
#
#   make -C firmware/bench host     # build + run, writes results/host.{json,csv}
#   make -C firmware/bench clean
#
# Portable scenario code (firmware/bench/lib) is also compiled into the
# firmware/tests suite (determinism / no-allocation / criteria tests).

CXX      ?= /usr/bin/g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra
CPPFLAGS := -I../src -I../include -Ilib -MMD -MP

BUILD := build

SRC_FILES   := $(wildcard ../src/*/*.cpp)
SRC_OBJ     := $(patsubst ../src/%.cpp,$(BUILD)/obj/%.o,$(SRC_FILES))
BENCH_FILES := $(wildcard lib/*.cpp)
BENCH_OBJ   := $(patsubst lib/%.cpp,$(BUILD)/bench/%.o,$(BENCH_FILES))
MAIN_OBJ    := $(BUILD)/bench_main.o
BENCH_BIN   := $(BUILD)/bukifon_bench

.PHONY: all host host_s3 bench clean

all: $(BENCH_BIN)

$(BUILD)/obj/%.o: ../src/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

$(BUILD)/bench/%.o: lib/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

$(BUILD)/bench_main.o: bench_main.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

$(BENCH_BIN): $(SRC_OBJ) $(BENCH_OBJ) $(MAIN_OBJ)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $^ -o $@

-include $(shell find $(BUILD) -name '*.d' 2>/dev/null)

host: $(BENCH_BIN)
	@mkdir -p results
	./$(BENCH_BIN) --json results/host.json --csv results/host.csv

host_s3: $(BENCH_BIN)
	@mkdir -p results
	./$(BENCH_BIN) --scenario s3_profile --json results/host_s3.json --csv results/host_s3.csv

bench: host

clean:
	rm -rf $(BUILD)
