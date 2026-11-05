import json,os,glob,subprocess,sys
K="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
pro={"meta":{"filename":"","version":1},
 "erc":{"rule_severities":{
   "pin_not_driven":"warning","power_pin_not_driven":"warning",
   "lib_symbol_mismatch":"ignore","lib_symbol_issues":"ignore",
   "isolated_pin_label":"warning","unconnected_wire_endpoint":"warning",
   "endpoint_off_grid":"warning","label_dangling":"error",
   "pin_not_connected":"error","no_connect_dangling":"error"}}}
for f in sorted(glob.glob("MOD-*.kicad_sch")):
    base=f[:-10]
    p=dict(pro); p["meta"]=dict(pro["meta"]); p["meta"]["filename"]=base+".kicad_pro"
    json.dump(p, open(base+".kicad_pro","w"), indent=1)
    r=subprocess.run([K,"sch","erc",f,"-o","erc/"+base+".rpt"],capture_output=True,text=True)
    out=r.stdout+r.stderr
    print("="*60); print(base)
    print([l for l in out.splitlines() if "нарушен" in l or "violation" in l])
    rpt=open("erc/"+base+".rpt").read()
    errs=[l for l in rpt.splitlines() if "error" in l]
    print("errors:",len(errs))
    for l in rpt.splitlines():
        if l.startswith("[") or "error" in l or "warning" in l: print("  ",l.strip())
