"""Allow only measurement integration; freeze proven motor behavior and video/IO."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def check():
 a=Path(json.loads(read(R/'region_probe_lineage.json'))['archive']);old=a/'snapshot'
 manifest=json.loads(read(a/'manifest.json'))['files']
 for rel,h in manifest.items():assert sha(a/rel)==h,'archive changed '+rel
 allowed={'build.ps1','compose.py','rtl/vision_monitor.v','rtl/vision_monitor_all.v','rtl/vision_servo_core.v','rtl/vision_cascade_control.v','rtl/vision_cascade_diag.v','user_source/hdl_source/design_top_wrapper.v'}
 for rel,h in json.loads(read(old/'build_sources.json')).items():
  if rel not in allowed:assert sha(R/rel)==h,'unapproved baseline edit '+rel
 core=read(R/'rtl/vision_servo_core.v');before=read(old/'rtl/vision_servo_core.v')
 core=core.replace(',\n output wire [7:0] diag_pending,output wire signed [15:0] diag_commands,diag_delta,\n output wire diag_consistent,diag_wrong','')
 start=core.index(' wire manual_pending=');end=core.index(' assign position=',start);core=core[:start]+core[end:]
 assert core==before,'servo mutation beyond read-only diagnostic taps'
 control=read(R/'rtl/vision_cascade_control.v').replace('output wire diagnostic_quiescing,\n ','').replace(' assign diagnostic_quiescing=quiescing;\n','')
 assert control==read(old/'rtl/vision_cascade_control.v'),'continuous controller changed'
 diag=read(R/'rtl/vision_cascade_diag.v').replace('MS_CYCLES=50000,PERIOD_MS=20','MS_CYCLES=50000').replace('MS_CYCLES*PERIOD_MS-1','MS_CYCLES*20-1')
 assert diag==read(old/'rtl/vision_cascade_diag.v'),'D1 layout/serializer changed'
 top=read(old/'user_source/hdl_source/design_top_wrapper.v').replace('.CASCADE_DEFAULT(1),.CASCADE_PRESET(1)) u_vision_monitor(','.CASCADE_DEFAULT(0),.CASCADE_PRESET(0),.REGION_PROBE(1)) u_vision_monitor(')
 assert top==read(R/'user_source/hdl_source/design_top_wrapper.v'),'top changed outside probe selection'
 for rel in ('host/vision_panel_cn.ps1','host/cascade_controls.ps1','host/cascade_protocol.ps1','host/cascade_protocol.py','diagnostic_schema.json'):
  assert sha(R/rel)==sha(old/rel),'old panel/protocol changed '+rel
 print('REGION_CONTRACT_PASS: archived easy3, exact motor FSM/guards, video/IO/clocks and old protocols')
if __name__=='__main__':check()
