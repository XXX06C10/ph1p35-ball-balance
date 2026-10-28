from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 meta=json.loads(read(R/'settle30_lineage.json'));a=Path(meta['archive']);old=a/'snapshot'
 for rel,h in json.loads(read(a/'manifest.json'))['files'].items():assert sha(a/rel)==h,'settle archive changed '+rel
 allowed={'rtl/vision_region_hold.v','rtl/vision_monitor.v','rtl/vision_monitor_all.v','build.ps1'}
 for rel,h in json.loads(read(old/'build_sources.json')).items():
  if rel not in allowed:assert sha(R/rel)==h,'unexpected compiled edit '+rel
 assert read(R/'build.ps1')==read(old/'build.ps1').replace("'asym_range','brake_hold')","'asym_range','brake_hold','settle30')")
 s=read(R/'rtl/vision_monitor.v').replace('.NEUTRAL_BITS(TW),.LIVE_ZONE(ASYM_RANGE)) region_hold(','.NEUTRAL_BITS(TW)) region_hold(').replace('.filtered_velocity_q4(n_region_velocity),.hold_radius_setting(deadzone));','.filtered_velocity_q4(n_region_velocity));')
 assert s==read(old/'rtl/vision_monitor.v'),'monitor exceeded live radius connection'
 s=read(R/'rtl/vision_region_hold.v')
 s=s.replace('WIDE_RANGE=0,NEUTRAL_BITS=8,LIVE_ZONE=0','WIDE_RANGE=0,NEUTRAL_BITS=8')
 s=s.replace('filtered_velocity_q4,\n input wire [15:0] hold_radius_setting\n);','filtered_velocity_q4\n);')
 first=' // Live P.DZ selects';last=' wire outward='
 s=s[:s.index(first)]+' wire enter_now=distance<=15 && speed<=(WIDE_RANGE ? 128 : 240);\n'+s[s.index(last):]
 s=s.replace('distance>hold_exit','distance>25').replace('distance>=trend_radius','distance>=20').replace('distance>escape_radius','distance>45')
 s=s.replace('$signed(smooth_d_product)>>>(LIVE_ZONE ? 5 : 4)','$signed(smooth_d_product)>>>4')
 s=s.replace("cap=LIVE_ZONE && limit>48 ? 18'sd12288 : $signed({1'b0,limit,8'b0});","cap=$signed({1'b0,limit,8'b0});").replace('relative_stage<=WIDE_RANGE && !LIVE_ZONE ? raw_stage :','relative_stage<=WIDE_RANGE ? raw_stage :')
 assert s==read(old/'rtl/vision_region_hold.v'),'regional edits exceeded target cap,damping,radius hysteresis'
 assert read(R/'sim/tb_region_policy.v')==read(old/'sim/tb_region_policy.v').replace('target,changed,holding,phase,hz,slew);',"target,changed,holding,phase,hz,slew,,16'd0);"),'legacy fixture beyond trailing port adapter'
 paired=json.loads(read(old/'brake_hold_verification.json'))['paired_host_sha256']
 for rel,h in paired.items():assert sha(R/rel)==h,'old host changed '+rel
 assert read(R/'host/settle_panel_cn.ps1').split(". (Join-Path $PSScriptRoot 'asym_protocol.ps1')")[0]==read(old/'host/asym_panel_cn.ps1').split(". (Join-Path $PSScriptRoot 'asym_protocol.ps1')")[0],'wire codecs changed'
 print('SETTLE30_CONTRACT_PASS parent archive,exact core/guards/limits/IO/clocks/UART; bounded native target/live zone only')
if __name__=='__main__':check()
