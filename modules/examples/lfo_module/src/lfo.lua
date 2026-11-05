-- Bukifon control-rate module example (Lua): simple LFO.
-- ABI v0 (experimental): init/process_control/set_param.
local rate = 0.3
local depth = 0.5
local phase = 0.0

function init(sample_rate)
  sample_rate = sample_rate or 48000
  return true
end

function set_param(id, value)
  if id == 0 then rate = value end
  if id == 1 then depth = value end
end

function process_control(dt_ms)
  local hz = 0.05 * math.pow(100.0, rate)   -- 0.05 … 5 Hz
  phase = (phase + hz * dt_ms / 1000.0) % 1.0
  local value = math.sin(phase * 2.0 * math.pi) * depth
  return value
end

function state_size() return 16 end
