from pathlib import Path
import hashlib,json,re,subprocess,sys
from region100_contract import check,read
R=Path(__file__).resolve().parent;run=R/'vision_follow_20261022_Runs/phy_1'
sys.path.insert(0,str(R/'host'))
from region_probe import parse_event
from asym_protocol import parse_diag
from asym_protocol import parse_record
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def text(p):
 raw=p.read_bytes();return raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig').replace('\r\n','\n')
def require(ok,why):
 if not ok:raise RuntimeError(why)
check();subprocess.run([sys.executable,'source_manifest.py','--check'],cwd=R,check=True)
bit=R/'output/vision_follow_20261022_region100.bit'
require(sha(bit)==sha(run/'vision_follow_20261022.bit'),'routed bit alias mismatch')
require(b'# Package: PH1P35MDG324' in bit.read_bytes()[:500],'wrong device')
require('VISION_FOLLOW_20261022_BUILD_COMPLETE' in text(R/'build.log'),'build incomplete')
for line in text(R/'build.log').splitlines():
 if 'CRITICAL-WARNING' in line:
  require(bool(re.match(r'^PHY-5060 CRITICAL-WARNING: Clock net candidate (u_uicfgcs500/uii2c_inst/scl_clk|O_cam_24m_syn_\d+) has mixed fanouts',line) or re.match(r'^PHY-5079 CRITICAL-WARNING: Marked \d+ clock net\(s\) utilize the local routing resources',line)),'unreviewed critical: '+line)
require(not re.search(r'Undriven net:.*(?:u_camera_control|u_vision_monitor|S_roi_|S_detect_rst)',text(R/'build.log')),'undriven integration net')
timing=text(run/'vision_follow_20261022_phy.ts')
slack={k:float(re.search(k+r':\s*([-\d.]+)ns',timing)[1]) for k in ('SWNS','STNS','HWNS','HTNS')}
require(all(v>=0 for v in slack.values()),'negative timing')
old=Path(json.loads(read(R/'asym_range_lineage.json'))['archive'])/'snapshot'
def pins(p):
 d={}
 for line in text(p).splitlines():
  f=line.split()
  if len(f)>=8 and f[1] in ('INPUT','OUTPUT','INOUT'):d[f[0]]=f[1:8]
 return d
area=run/'vision_follow_20261022_phy.area';routed=pins(area)
baseline=json.loads(read(R/'asym_range_lineage.json'))['baseline_area'];baseline_area=R/baseline['path'];require(sha(baseline_area)==baseline['sha256'],'baseline routed pins artifact changed')
parent_pins=pins(baseline_area)
require(set(routed)==set(parent_pins),'routed ports changed')
for port,fields in parent_pins.items():require(routed[port][:3]==fields[:3] and routed[port][5]==fields[5],'baseline routed pin changed '+port)
def adc(p):
 d={}
 for line in text(p).splitlines():
  if line.lstrip().startswith('#'):continue
  m=re.search(r'set_pin_assignment\s*\{\s*(.*?)\s*\}\s*\{(.*?)\}',line)
  if m:d[m[1]]={k.strip():v.strip() for k,v in re.findall(r'(\w+)\s*=\s*([^;]+);',m[2])}
 return d
constraints=adc(R/'user_source/constraints_source/pin.adc')
for port,v in constraints.items():
 require(port in routed and routed[port][1]==v['LOCATION'] and routed[port][2]==v['IOSTANDARD'] and routed[port][5]==v['PULLTYPE'],'routed pin/electrical mismatch '+port)
reference=R.parents[1]/'2_Example/32_cs500_mipi_hdmi/pin/pin.adc'
for port,v in adc(reference).items():
 port={'I_sys_clk_25m':'I_sys_clk','O_clk_24m':'O_cam_24m'}.get(port,port)
 require(all(constraints[port][k]==v[k] for k in ('LOCATION','IOSTANDARD')),'official reference pin '+port)
netlist=text(R/'routed_netlist.v');drivers={}
for port in ('O_motor_step','O_motor_step_v2','O_motor_dir','O_motor_dir_v1','O_motor_en','O_motor_en_u2'):
 m=re.search(r'\b'+port+r'_syn_\d+\s*\(\s*\.doq\(\{([^}]+)\}\),\s*\.opad\('+port+r'\)\);',netlist)
 require(m is not None,'missing pad '+port);drivers[port]=m[1].split(',')[-1].strip()
for p,m in (('O_motor_step','O_motor_step_v2'),('O_motor_dir','O_motor_dir_v1'),('O_motor_en','O_motor_en_u2')):require(drivers[p]==drivers[m] and drivers[p] not in ("1'b0","1'b1"),'mirror constant/mismatch')
markers={'tb_full': 'ALL_TESTS_PASS', 'tb_motion': 'MOTION_GUARDS_PASS', 'tb_fast': 'FAST_ALL_PASS', 'tb_hold': 'HOLD_ALL_PASS', 'tb_loss': 'LOSS_CONTROL_PASS', 'tb_cascade_config': 'CASCADE_CONFIG_PASS', 'tb_asym_limits': 'ASYM_LIMITS_PASS', 'tb_asym_faults': 'ASYM_FAULTS_PASS', 'tb_asym_edges': 'ASYM_EDGES_PASS', 'tb_tail_checkpoint': 'TAIL_CHECKPOINT_PASS', 'tb_smooth_policy': 'SMOOTH_POLICY_PASS', 'tb_overlay_rgb': 'OVERLAY_RGB_PASS', 'tb_region100_policy': 'REGION100_POLICY_PASS', 'tb_region100_runtime': 'REGION100_RUNTIME_PASS', 'tb_region100_plant': 'REGION100_PLANT_PASS'}
require(set(markers)==set(json.loads(read(R/'region100_required_suites.json'))),'suite roster mismatch')
combined=read(R/'rtl/vision_monitor_all.v');bench_results={}
for b,marker in markers.items():
 s=text(R/f'sim/results/{b}.log');snapshot=read(R/f'sim/results/{b}.combined.v')
 require(marker in s and not re.search('FATAL|FAIL:',s),'test failed '+b)
 require(combined in snapshot and read(R/f'sim/{b}.v') in snapshot,'stale test '+b)
 bench_results[b]=marker
for f in range(1,9):
 require(f'PASS fault {f}:' in text(R/'sim/results/tb_motion.log'),'manual fault coverage')
 require(f'FAST_FAULT_PASS code={f} ' in text(R/'sim/results/tb_fast.log'),'fast fault coverage')
 require(f'HOLD_FAULT_PASS code={f} ' in text(R/'sim/results/tb_hold.log'),'hold fault coverage')
counts={'D2':0,'VIS6':0};diags=[]
for line in text(R/'sim/results/tb_region100_runtime.log').splitlines():
 if line.startswith('ASYM_WIRE D2'):
  raw=line.split(' ',1)[1];d=parse_diag(raw);require(d is not None and len(raw)+2==148,'new region D1 wire');diags.append(d);counts['D2']+=1
 elif line.startswith('ASYM_WIRE VIS=6'):
  raw=line.split(' ',1)[1];require(parse_record(raw) is not None and len(raw)+2==441,'new region VIS5 wire');counts['VIS6']+=1
require(any(d['neutral']==200 for d in diags),'wide neutral was not transmitted')
require(all(d['work_min']==d['limit_anchor']-182 and d['work_max']==d['limit_anchor']+364 for d in diags if d['flags']&8192),'fixed bounds wire mismatch')
require(counts['VIS6']>=2,'VIS UART absent')
for code in range(1,9):require(f'FAST_FAULT_PASS code={code} ' in text(R/'sim/results/tb_asym_faults.log'),'new-enabled-tail guard missing')
for case in range(7):require(f'TAIL_CASE_PASS case={case} ' in text(R/'sim/results/tb_tail_checkpoint.log'),'tail settlement boundary not tested')
basehost=subprocess.run([sys.executable,'sim/test_cascade_host.py'],cwd=R,capture_output=True,text=True,encoding='utf-8',errors='replace')
(R/'sim/results/host_cascade_tests.txt').write_text(basehost.stdout+basehost.stderr,encoding='utf-8')
require(basehost.returncode==0 and 'Ran 7 tests' in basehost.stderr,'base host regression failure')
ah=subprocess.run([sys.executable,'sim/test_asym_host.py'],cwd=R,capture_output=True,text=True,encoding='utf-8',errors='replace')
(R/'sim/results/host_asym_tests.txt').write_text(ah.stdout+ah.stderr,encoding='utf-8')
require(ah.returncode==0,'wide host codec failed')
panel={}
for entry,st,sm in [('start_panel.cmd','HOST_SELF_TEST_PASS','HOST_UI_SMOKE_PASS'),('start_asym_range.cmd','ASYM_HOST_SELFTEST_PASS','ASYM_PANEL_SMOKE_PASS'),('start_settle30.cmd','SETTLE_HOST_SELFTEST_PASS','SETTLE_PANEL_SMOKE_PASS'),('start_full_range.cmd','FULL_RANGE_HOST_SELFTEST_PASS','FULL_RANGE_PANEL_SMOKE_PASS'),('start_asym_smooth.cmd','ASYM_SMOOTH_HOST_SELFTEST_PASS','ASYM_SMOOTH_PANEL_SMOKE_PASS'),('start_region100.cmd','REGION100_HOST_SELFTEST_PASS','REGION100_PANEL_SMOKE_PASS')]:
 for flag,marker in [('-SelfTest',st),('-SmokeTest',sm)]:
  result=subprocess.run(['cmd.exe','/c','host\\'+entry,flag],cwd=R,capture_output=True,text=True,encoding='utf-8',errors='replace')
  require(result.returncode==0 and marker in result.stdout,'panel failure '+entry+flag);panel[entry+flag]=marker
require('SMOOTH_GOLD_EQUIVALENCE_PASS 600realupdates' in text(R/'sim/results/tb_smooth_policy.log'),'trusted source comparison missing')
require('old6pixelbugreproduced' in text(R/'sim/results/tb_overlay_rgb.log'),'actual RGB old/new comparison missing')
resources={key:int(re.search(r'^#'+label+r'\s+(\d+)',text(area),re.M)[1]) for key,label in (('slice','slice'),('register','reg'),('IO','IO'),('ERAM','eram'),('DSP','dsp'))}
report={'status':'SOFTWARE_ROUTING_PASS_AWAITING_PHYSICAL_REGION100','bit':str(bit.relative_to(R)),'sha256':sha(bit),'device':'PH1P35MDG324','timing_ns':slack,'resources':resources,'suites':bench_results,'uart_frames':counts,'host_tests':10,'mirror_drivers':drivers,'panels':panel,'paired_host_sha256':{str(p.relative_to(R)):sha(p) for p in (R/'host').glob('*') if p.is_file() and (p.suffix in ('.ps1','.cmd','.py') or p.name=='asym_diag_fixture.txt')},'physical_region100':'PENDING','control_revision':'region100_20261026','capture_radius_pixels':90,'exit_radius_pixels':100,'capture_max_velocity_pixels_s':12,'velocity_frames':'2near<=120px,4far','fine_position_zero_radius':60,'fine_position_100px_counts':1.875,'fine_velocity_gain_count_per_pixels_s':0.09375,'fine_velocity_noise_deadband_pixels_s':8,'small_tilt_fine_rate_hz':20,'small_tilt_fine_slew_counts_s':12,'large_existing_tilt_return_hz':50,'target_cap_counts':None,'native_uses_fixed_work_bounds_only':True,'runtime_zone_profiles':[80,100],'qualified_hold':'K3 STEP phase with encoder neighborhood2counts; no guard or origin rebasing','working_motor_degrees':[-182*360/4096,364*360/4096],'feedback_motor_degrees':[-204*360/4096,398*360/4096],'PWM_Z_active':False,'wide_schema_sha256':{n:sha(R/n) for n in ['wide_frame_layout.json','wide_diagnostic_schema.json']},'unchanged':'detector/HDMI predictor/inner servo/core/checkpoints/F1-F8/clocks/pins/raw protocols','model_criterion':'5 assumed plants, tail abs(error)<=100px and abs(speed)<=25px/s; not physical acceptance','auto_programmed':False}
(R/'region100_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
