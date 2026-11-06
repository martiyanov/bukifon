#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write .kicad_pro with netclasses/impedance/DRC severities for rev.1 scaffolds."""
import json, os
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','..'))
JOBS=[('CORE-2','hardware/core2/rev1/CORE-2-rev1'),
      ('PANEL-2-left','hardware/panel2/rev1/PANEL-2-left-rev1'),
      ('PANEL-2-right','hardware/panel2/rev1/PANEL-2-right-rev1'),
      ('PWR-2','hardware/power2/rev1/PWR-2-rev1')]
IGNORE={'silk_over_copper':'ignore','silk_overlap':'ignore','courtyards_overlap':'ignore',
        'lib_footprint_mismatch':'ignore','footprint_type_mismatch':'ignore','pads_overlap':'ignore',
        'solder_mask_bridge':'ignore','lib_footprint_issues':'ignore','silk_edge_clearance':'ignore',
        'pth_inside_courtyard':'ignore','npth_inside_courtyard':'ignore','courtyards_overlap':'ignore'}
def pro(name, diff=False):
    classes=[
     {'name':'Default','clearance':0.2,'track_width':0.2,'via_diameter':0.6,'via_drill':0.3,'wire_width':6,'bus_width':12},
     {'name':'Power','clearance':0.25,'track_width':1.0,'via_diameter':0.8,'via_drill':0.45,'wire_width':6,'bus_width':12,
      'nets':['VSYS','VBAT','BATT_P','+12V','-12V','12V','5V','5V_EXT','5V_LED','N12_EXT','+3V3','3V3_MCU','3V3_C6','BL_20V','12V_EXT']},
     {'name':'USB_HS','clearance':0.15,'track_width':0.2,'via_diameter':0.6,'via_drill':0.3,'wire_width':6,'bus_width':12,
      'diff_pair_width':0.2,'diff_pair_gap':0.2,'nets':['USB_HS_DP','USB_HS_DM']},
     {'name':'Audio','clearance':0.2,'track_width':0.25,'via_diameter':0.6,'via_drill':0.3,'wire_width':6,'bus_width':12,
      'nets':['AUDOUT_L','AUDOUT_R','AUDIN_L','AUDIN_R','PHONES_L','PHONES_R','I2S_MCLK','I2S_BCK','I2S_LRCK','I2S_DAC_DIN','I2S_ADC_DOUT','MIC_DATA','MIC_BCK','MIC_WS']},
     {'name':'RF','clearance':0.2,'track_width':0.25,'via_diameter':0.6,'via_drill':0.3,'wire_width':6,'bus_width':12,
      'nets':['C6_CS','C6_HS','C6_DR','C6_RST']},
    ]
    if not diff:
        pass
    return {'board':{'design_settings':{
        'rule_severities':IGNORE,
        'net_settings':{'classes':classes,'meta':{'version':3}},
        'track_widths':[0.2,0.25,0.5,1.0,2.0],
        'via_dimensions':[{'diameter':0.6,'drill':0.3},{'diameter':0.8,'drill':0.45}],
        'diff_pair_dimensions':[{'width':0.2,'gap':0.2,'via_gap':0.2}],
        'allow_soldermask_bridges_in_footprints':False,
    }},'meta':{'filename':name+'.kicad_pro','version':1}}
for bid,base in JOBS:
    p=os.path.join(ROOT,base+'.kicad_pro')
    json.dump(pro(os.path.basename(base)), open(p,'w'), indent=1)
    print('wrote',p)
