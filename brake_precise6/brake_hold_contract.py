from pathlib import Path
import hashlib,json
from asym_range_contract import check as parent_check,read
R=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 parent_check()
 meta=json.loads(read(R/'brake_hold_lineage.json'));a=Path(meta['archive']);old=a/'snapshot'
 for rel,h in json.loads(read(a/'manifest.json'))['files'].items():assert sha(a/rel)==h,'brake archive changed '+rel
 allowed={'rtl/vision_region_hold.v','rtl/vision_cascade_control.v','rtl/vision_monitor_all.v','build.ps1'}
 for rel,h in json.loads(read(old/'build_sources.json')).items():
  if rel not in allowed:assert sha(R/rel)==h,'unexpected compiled edit '+rel
 assert read(R/'build.ps1')==read(old/'build.ps1').replace("'region_return','asym_range')","'region_return','asym_range','brake_hold')")
 now=read(R/'rtl/vision_cascade_control.v');before=read(old/'rtl/vision_cascade_control.v')
 normalized=now.replace(' reg signed [31:0] neutral_command_position=0;\n','')
 first=' wire signed [31:0] encoder_error_q8=';last=' wire signed [31:0] abs_error='
 normalized=normalized[:normalized.index(first)]+' wire signed [31:0] error_q8=reference_q8-feedback_q8;\n'+normalized[normalized.index(last):]
 normalized=normalized.replace('segment_ms<=0;neutral_command_position<=0;','segment_ms<=0;').replace('quiet_ms<=20;neutral_command_position<=command_position;end','quiet_ms<=20;end')
 assert normalized==before,'controller edits exceeded STEP-phase hold error and K3 register'
 policy=read(R/'rtl/vision_region_hold.v');prior=read(old/'rtl/vision_region_hold.v')
 normalized=policy.replace(' // Reduce damping delay only in the wide-range controller.\n','').replace('assign filtered_velocity_q4=WIDE_RANGE ? $signed(pair_a)>>>1 : ($signed(pair_a)+$signed(pair_b))>>>2;','assign filtered_velocity_q4=($signed(pair_a)+$signed(pair_b))>>>2;')
 normalized=normalized.replace(' wire enter_now=distance<=15 && speed<=(WIDE_RANGE ? 128 : 240);',' wire enter_now=distance<=15 && speed<=240;')
 normalized=normalized.replace(' wire outward=(error>0 && control_velocity>0) || (error<0 && control_velocity<0);\n','').replace(' wire exit_now=distance>25 || speed>960 || (WIDE_RANGE && distance>=20 && outward && speed>=128);',' wire exit_now=distance>25 || speed>960;')
 first=' // Blend existing gains';last=' wire signed [31:0] raw_relative='
 normalized=normalized[:normalized.index(first)]+' wire signed [31:0] pd=polarity ? -(proportional+derivative) : proportional+derivative;\n'+normalized[normalized.index(last):]
 first=' reg fast_motion=0;';last=' always @(posedge clk)begin\n  if(!rst_n)begin target_q8'
 normalized=normalized[:normalized.index(first)]+" assign max_hz=holding || range_distance<=64 ? 16'd50 : (range_distance<=128 ? 16'd100 : 16'd200);\n assign slew_rate=holding || range_distance<=64 ? 16'd80 : (range_distance<=128 ? 16'd100 : 16'd160);\n"+normalized[normalized.index(last):]
 assert normalized==prior,'regional edits exceeded reviewed blend,velocity and holding policy'
 print('BRAKE_HOLD_CONTRACT_PASS exact core/guards/bounds/pins/clocks/UART; only two native controller adaptations')
if __name__=='__main__':check()
