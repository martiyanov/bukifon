# SPDX-License-Identifier: GPL-3.0-or-later
# Host build of the portable Bukifon engine (no Arduino dependencies).
#
#   make            -> build/bukifon_tests and build/bukifon_render
#   make test       -> build + run the unit tests
#   make render     -> build + render the WAV files
#   make clean

CXX      ?= /usr/bin/g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra
CPPFLAGS := -I../src -I. -MMD -MP
LDFLAGS  ?=

SRC_DIR   := ../src
TEST_DIR  := ../tests
BUILD     := build

SRC_FILES := $(wildcard $(SRC_DIR)/*/*.cpp)
OBJ       := $(patsubst $(SRC_DIR)/%.cpp,$(BUILD)/obj/%.o,$(SRC_FILES))

TEST_FILES := $(wildcard $(TEST_DIR)/*.cpp)
TEST_OBJ   := $(patsubst $(TEST_DIR)/%.cpp,$(BUILD)/test_obj/%.o,$(TEST_FILES))

RENDER_OBJ := $(BUILD)/host/render_wav.o

TEST_BIN   := $(BUILD)/bukifon_tests
RENDER_BIN := $(BUILD)/bukifon_render

.PHONY: all test render clean

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

-include $(shell find $(BUILD) -name '*.d' 2>/dev/null)

$(TEST_BIN): $(OBJ) $(TEST_OBJ)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LDFLAGS)

$(RENDER_BIN): $(OBJ) $(RENDER_OBJ)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $^ -o $@ $(LDFLAGS)

test: $(TEST_BIN)
	./$(TEST_BIN)

render: $(RENDER_BIN)
	mkdir -p ../tests/out
	./$(RENDER_BIN) ../tests/out

clean:
	rm -rf $(BUILD)
