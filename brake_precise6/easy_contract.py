"""Preset change: preserve the entire passing cascade motion algorithm and IO."""
from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def check_easy():
 v=json.loads((r/'easy_lineage.json').read_text(encoding='utf-8-sig'));a=Path(v['archive'])
 for p,h in json.loads((a/'manifest.json').read_text())['files'].items():assert sha(a/p)==h,'Archive changed '+p
 assert sha(r/'output/vision_follow_20261022_cascade.bit')==v['parent_bit_sha256'],'Parent cascade overwritten'
 # Locate packaged manifest; its neighboring files are the paired compiled sources.
 parent=next((a/'published').rglob('delivery_manifest.json')).parent
 old=json.loads((parent/'build_sources.json').read_text())
 allowed={'build.ps1','rtl/vision_monitor.v','rtl/vision_monitor_all.v','rtl/vision_cascade_config.v','user_source/hdl_source/design_top_wrapper.v'}
 for p,h in old.items():
  if p not in allowed:assert sha(r/p)==h,'Preset unexpectedly changed compiled logic '+p
 # The RGB fixture uses no C UART and default CASCADE_PRESET=0/CASCADE_DEFAULT=0.
 # Prove the monitor edits are confined to preset-only readiness/configuration.
 def read(p):
  raw=p.read_bytes()
  return (raw.decode('utf-16') if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else raw.decode('utf-8-sig')).replace('\r\n','\n')
 expected=read(parent/'rtl/vision_monitor.v')
 expected=expected.replace('DEFAULT_RUNTIME=60,CASCADE_DEFAULT=0,','DEFAULT_RUNTIME=60,CASCADE_DEFAULT=0,CASCADE_PRESET=0,')
 expected=expected.replace('reg c_fresh=0,c_profile_ready=0;','reg c_fresh=0,c_profile_ready=CASCADE_PRESET,c_builtin=CASCADE_PRESET;')
 expected=expected.replace('if(!rst_n || applied || center_request || settings_busy)c_profile_ready<=0;\n      else if(c_applied)c_profile_ready<=c_selection==1 && (c_kp!=0 || c_kv!=0);',
 'if(!rst_n)begin c_profile_ready<=CASCADE_PRESET;c_builtin<=CASCADE_PRESET;end\n      else begin\n        if(c_applied)begin c_builtin<=0;c_profile_ready<=c_selection==1 && (c_kp!=0 || c_kv!=0);end\n        else if(applied || center_request || settings_busy)c_profile_ready<=c_builtin;\n      end')
 expected=expected.replace('.DEFAULT_SELECTION(CASCADE_DEFAULT)) cascade_config(','.DEFAULT_SELECTION(CASCADE_DEFAULT),.DEFAULT_PRESET(CASCADE_PRESET)) cascade_config(')
 assert read(r/'rtl/vision_monitor.v')==expected,'Monitor edits exceeded preset-only scope'
 fixture=read(parent/'sim/tb_rgb.v')
 assert read(r/'sim/tb_rgb.v')==fixture and 'CASCADE_PRESET' not in fixture and 'CASCADE_DEFAULT' not in fixture
 previous=json.loads(read(parent/'verification.json'))
 assert 'tb_rgb' in previous['simulations'] and previous['sha256']==v['parent_bit_sha256']
 rgb_log=read(parent/'sim/results/tb_rgb.log')
 assert 'RGB_INTEGRATION_PASS' in rgb_log and 'FATAL' not in rgb_log
 for i in range(18):assert f'RGB_FRAME_PASS frame={i}' in rgb_log
 assert v['preset']==dict(kp=819,kv=40,ki=131,inner_kp=8192,feedforward=200,max_hz=100,slew_rate=102,delay_ms=20,polarity=0,deadzone=3,relative_limit=32,runtime=0)
if __name__=='__main__':check_easy();print('EASY_CONTRACT_PASS: immutable cascade,all motion algorithms/camera/pins/clocks frozen')
