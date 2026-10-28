from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 meta=json.loads(read(R/'asym_smooth_lineage.json'));a=Path(meta['archive']);old=a/'snapshot';gold=Path(meta['trusted_asym_snapshot'])
 for rel,h in json.loads(read(a/'manifest.json'))['files'].items():assert sha(a/rel)==h,'archive changed '+rel
 assert sha(R/'output/asym_range.bit')==meta['trusted_asym_bit_sha256']
 assert sha(gold/'rtl/vision_region_hold.v')==meta['trusted_asym_region_sha256']
 allowed={'rtl/vision_region_hold.v','rtl/vision_monitor.v','rtl/vision_monitor_all.v','compose.py','build.ps1','user_source/hdl_source/design_top_wrapper.v','user_source/hdl_source/steel_ball_detect.v'}
 baseline=json.loads(read(old/'build_sources.json'))
 for rel,h in baseline.items():
  if rel not in allowed:assert sha(R/rel)==h,'unexpected compiled edit '+rel
 assert set(json.loads(read(R/'build_sources.json')))-set(baseline)=={'rtl/vision_overlay_lead.v'},'unexpected new compiled source'
 assert read(R/'build.ps1')==read(old/'build.ps1').replace("'full_range')","'full_range','asym_smooth')")
 assert read(R/'compose.py')==read(old/'compose.py').replace("parts=['vision_asym_limits.v'","parts=['vision_overlay_lead.v','vision_asym_limits.v'")
 assert '.ASYM_RANGE(1),.ASYM_SMOOTH(1)) u_vision_monitor(' in read(R/'user_source/hdl_source/design_top_wrapper.v'),'actual board mode not selected'
 assert '.RECOVER_ASYM(ASYM_SMOOTH)) region_hold(' in read(R/'rtl/vision_monitor.v'),'restored moving-law selector not wired'
 assert 'WIDE_RANGE && !RECOVER_ASYM ?' in read(R/'rtl/vision_region_hold.v'),'restored branch not selected by parameter'
 s=read(R/'rtl/vision_region_hold.v').replace('NEUTRAL_BITS=8,LIVE_ZONE=0,RECOVER_ASYM=0','NEUTRAL_BITS=8,LIVE_ZONE=0').replace('WIDE_RANGE && !RECOVER_ASYM ?','WIDE_RANGE ?').replace('WIDE_RANGE && !RECOVER_ASYM && fast_motion','WIDE_RANGE && fast_motion')
 assert s==read(old/'rtl/vision_region_hold.v'),'regional edits exceeded restored-law selector'
 s=read(R/'rtl/vision_monitor.v').replace('ASYM_RANGE=0,ASYM_SMOOTH=0,','ASYM_RANGE=0,').replace('.LIVE_ZONE(ASYM_RANGE),.RECOVER_ASYM(ASYM_SMOOTH)) region_hold(','.LIVE_ZONE(ASYM_RANGE)) region_hold(')
 assert s==read(old/'rtl/vision_monitor.v'),'monitor edits exceeded selector wiring'
 s=read(R/'user_source/hdl_source/design_top_wrapper.v')
 s=s.replace('.ASYM_RANGE(1),.ASYM_SMOOTH(1)) u_vision_monitor(','.ASYM_RANGE(1)) u_vision_monitor(')
 s=s.replace('    wire S_overlay_box_valid,S_overlay_leading;\n    wire [10:0] S_overlay_left,S_overlay_right,S_overlay_top,S_overlay_bottom;\n','')
 first=s.index('    vision_overlay_lead #');last=s.index('    steel_ball_detect #',first);s=s[:first]+s[last:]
 s=s.replace('.I_box_valid(S_overlay_box_valid)','.I_box_valid(S_detect_box_valid)').replace('.I_box_left(S_overlay_left), .I_box_right(S_overlay_right)','.I_box_left(S_fast_box_left), .I_box_right(S_fast_box_right)').replace('.I_box_top(S_overlay_top), .I_box_bottom(S_overlay_bottom)','.I_box_top(S_fast_box_top), .I_box_bottom(S_fast_box_bottom)')
 assert s==read(old/'user_source/hdl_source/design_top_wrapper.v'),'top edits exceeded display-only box wiring and selector'
 s=read(R/'user_source/hdl_source/steel_ball_detect.v')
 s=s.replace("wire [10:0] video_base_x = S_AXIS_tuser ? 11'd0 : video_x;","wire [10:0] video_base_x = (S_AXIS_tuser || line_end) ? 11'd0 : video_x;")
 s=s.replace("wire [10:0] video_base_y = S_AXIS_tuser ? 11'd0 : video_y;","wire [10:0] video_base_y = S_AXIS_tuser ? 11'd0 : line_end ? video_y+11'd1 : video_y;")
 new="            // The falling tlast word still contains the final six pixels of\n            // this row. Draw at the old x/y, then reset for the next word.\n            if(S_AXIS_tuser) video_x<=S_AXIS_tvalid ? video_count : 11'd0;\n            else if(line_end) video_x<=0;\n            else if(S_AXIS_tvalid) video_x<=video_base_x+video_count;"
 previous="            if(S_AXIS_tvalid) video_x<=video_base_x+video_count;\n            else if(S_AXIS_tuser || line_end) video_x<=0;"
 assert new in s;s=s.replace(new,previous)
 assert s==read(old/'user_source/hdl_source/steel_ball_detect.v'),'classifier/video pipeline edits exceeded overlay x/y rollover'
 assert read(R/'sim/asym_golden_region.v')==read(gold/'rtl/vision_region_hold.v').replace('module vision_region_hold','module vision_region_asym_gold')
 assert read(R/'sim/steel_ball_detect_before_overlay_fix.v')==read(old/'user_source/hdl_source/steel_ball_detect.v').replace('module steel_ball_detect #','module steel_ball_detect_before_overlay_fix #',1)
 for rel,h in json.loads(read(old/'full_range_verification.json'))['paired_host_sha256'].items():assert sha(R/rel)==h,'old paired host changed '+rel
 codec=". (Join-Path $PSScriptRoot 'asym_protocol.ps1')"
 assert read(R/'host/asym_smooth_panel_cn.ps1').split(codec)[0]==read(old/'host/full_range_panel_cn.ps1').split(codec)[0],'raw wire codecs changed'
 print('ASYM_SMOOTH_CONTRACT_PASS trustedasym golden,restored selector,display-only rollover/lead;exact raw detector/core/guards/window/pins/clocks/protocol')
if __name__=='__main__':check()
