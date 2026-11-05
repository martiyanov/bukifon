#!/usr/bin/env bash
# Создать каркас модуля: bash tools/new_module.sh <handle> <name> <audio|control>
set -euo pipefail
cd "$(dirname "$0")/.."
handle="${1:?handle}"; name="${2:?name}"; kind="${3:-audio}"
slug=$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')
dir="modules/$handle/$slug"
[ -d "$dir" ] && { echo "уже есть: $dir"; exit 1; }
mkdir -p "$dir/src"
python3 - "$dir" "$handle" "$slug" "$name" "$kind" <<'PY'
import json,os,sys
dir,handle,slug,name,kind=sys.argv[1:6]
lang = "lua" if kind=="control" else "cpp"
mod={"schema":"bukifon.module.v1","id":f"{handle}.{slug}","name":name,"version":"0.1.0",
     "abi":0,"kind":"control" if kind=="control" else "audio","language":lang,
     "license":"GPL-3.0-or-later","author":handle,"description":"TODO: описание",
     "params":[{"id":0,"name":"Param","type":"float","min":0,"max":1,"default":0.5}],
     "files":([f"src/{slug}.lua"] if lang=="lua" else [f"src/{slug}.cpp"])+["README.md","LICENSE"],
     "limits":{"stack_bytes":8192,"state_bytes":4096,"max_frames":64}}
json.dump(mod,open(os.path.join(dir,"module.json"),"w"),ensure_ascii=False,indent=1)
open(os.path.join(dir,"README.md"),"w").write(f"# {name}\n\nОписание, параметры, лицензия.\n")
open(os.path.join(dir,"LICENSE"),"w").write("GPL-3.0-or-later\n")
if lang=="lua":
    open(os.path.join(dir,f"src/{slug}.lua"),"w").write("function init(sr) return true end\nfunction process_control(dt_ms) return 0 end\n")
else:
    open(os.path.join(dir,f"src/{slug}.cpp"),"w").write(
        "// SPDX-License-Identifier: GPL-3.0-or-later\n#include \\\"bukifon_module.h\\\"\n// TODO: descriptor/create/process\n")
print("создано:",dir)
PY
python3 tools/validate_module.py "$dir"
