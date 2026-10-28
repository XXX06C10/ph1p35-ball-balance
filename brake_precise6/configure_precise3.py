from pathlib import Path
import json
R=Path(__file__).resolve().parent
def edit(n,a,b):
 p=R/n;s=p.read_text(encoding='utf-8-sig');assert a in s,(n,a);p.write_text(s.replace(a,b),encoding='utf8')
edit('build.ps1',"'brake_precise2')","'brake_precise2','brake_precise3')")
edit('run_sim.ps1',"'tb_core_fallback')","'tb_core_fallback','tb_reversal_recovery','tb_precise3_policy')")
edit('run_sim.ps1',"$taskMarkers=@{","$taskMarkers=@{tb_reversal_recovery='REVERSAL_RECOVERY_PASS';tb_precise3_policy='PRECISE3_POLICY_PASS';")
roster=json.loads((R/'brake_fast_required_suites.json').read_text())+['tb_reversal_recovery','tb_precise3_policy']
(R/'brake_precise3_required_suites.json').write_text(json.dumps(roster,indent=2))
for old,new in [('run_brake_fast_regression.ps1','run_brake_precise3_regression.ps1'),('verify_brake_precise2.py','verify_brake_precise3.py'),('publish_brake_precise2.py','publish_brake_precise3.py')]:
 s=(R/old).read_text(encoding='utf-8-sig').replace('brake_precise2','brake_precise3').replace('BRAKE_PRECISE2','BRAKE_PRECISE3').replace('brake_fast_contract','brake_precise3_contract').replace('brake_fast_required_suites','brake_precise3_required_suites').replace('==19','==21')
 if old.startswith('verify'):
  s=s.replace("markers={'tb_full'","markers={'tb_reversal_recovery':'REVERSAL_RECOVERY_PASS','tb_precise3_policy':'PRECISE3_POLICY_PASS','tb_full'")
  s=s.replace("'core_check_retry':'independent20ms CHECK retry;original64pulse,5s,realfeedback,F1/F2unchanged'","'core_check_retry':'bounded40ms old-DIR feedback recovery;3 actual no-response pulses F1; original budget and timeout'")
  s=s.replace("'stiction_escape':'after16 consecutive valid frames at <=4px_s beyond35px;bounded tilt toward K3 neutral;motion immediately returns to speed braking'","'stiction_escape':'16 genuine frames coordinate excursion<=4px and speed<=24px/s;8/16/24counts near100;far32/40/48;motion cancels'")
  s=s.replace("'D2_reserved_bit14':","'D2_reserved_bit15':'pending old-direction feedback/recovery setup;MS10 recovery setup','D2_reserved_bit14':")
 if old.startswith('publish'):
  s=s.replace("parents={'output/brake_precise.bit'","parents={'output/brake_precise2.bit':'bb0844ff70ea6b50eaf363b488435dbc6ad0f0167449f97e86751ac60ecb3560','output/brake_precise.bit'")
  s=s.replace("'brake_precise.bit','vision_follow", "'brake_precise2.bit','brake_precise.bit','vision_follow")
  s=s.replace('精准回中2_测试说明','精准回中3_测试说明')
 (R/new).write_text(s,encoding='utf8')
for n in ['start_brake_precise2.cmd','brake_precise2_panel_cn.ps1','brake_precise2_controls.ps1']:
 p=R/'host'/n;s=p.read_text(encoding='utf-8-sig').replace('brake_precise2','brake_precise3').replace('BRAKE_PRECISE2','BRAKE_PRECISE3')
 if n.endswith('controls.ps1'):
  s=s.replace(" $angle=($D.position-$D.limit_anchor)*360.0/4096", " if(($D.flags -band 32768) -and !$D.fault){$state='换向前反馈确认：有限补步，等待编码器响应'}\n $angle=($D.position-$D.limit_anchor)*360.0/4096")
 (R/'host'/n.replace('precise2','precise3')).write_text(s,encoding='utf-8-sig')
edit('sim/tb_brake_fast_policy.v','for(i=0;i<20;i=i+1)sample(-375,0)','for(i=0;i<72;i=i+1)sample(-375,0)')
print('PRECISE3_CONFIGURED')
