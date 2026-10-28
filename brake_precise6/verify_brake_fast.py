from pathlib import Path
import hashlib,json,re,subprocess,sys
from brake_fast_contract import check,read
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
bit=R/'output/vision_follow_20261022_brake_fast.bit'
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
markers={'tb_full': 'ALL_TESTS_PASS', 'tb_motion': 'MOTION_GUARDS_PASS', 'tb_fast': 'FAST_ALL_PASS', 'tb_hold': 'HOLD_ALL_PASS', 'tb_loss': 'LOSS_CONTROL_PASS', 'tb_cascade_config': 'CASCADE_CONFIG_PASS', 'tb_asym_limits': 'ASYM_LIMITS_PASS', 'tb_asym_faults': 'ASYM_FAULTS_PASS', 'tb_asym_edges': 'ASYM_EDGES_PASS', 'tb_tail_checkpoint': 'TAIL_CHECKPOINT_PASS', 'tb_smooth_policy': 'SMOOTH_POLICY_PASS', 'tb_overlay_rgb': 'OVERLAY_RGB_PASS', 'tb_region100_policy': 'REGION100_POLICY_PASS', 'tb_brake_fast_policy': 'BRAKE_FAST_POLICY_PASS', 'tb_brake_fast_runtime': 'BRAKE_FAST_RUNTIME_PASS', 'tb_checkpoint_finish': 'CHECKPOINT_FINISH_PASS', 'tb_brake_fast_plant': 'BRAKE_FAST_PLANT_PASS', 'tb_brake_fast_clock50':'BRAKE_FAST_CLOCK50_PASS', 'tb_brake_fast_clock50':'BRAKE_FAST_CLOCK50_PASS'}
require(set(markers)==set(json.loads(read(R/'brake_fast_required_suites.json'))),'suite roster mismatch')
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
for line in text(R/'sim/results/tb_brake_fast_runtime.log').splitlines():
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
for entry,st,sm in [('start_panel.cmd','HOST_SELF_TEST_PASS','HOST_UI_SMOKE_PASS'),('start_asym_range.cmd','ASYM_HOST_SELFTEST_PASS','ASYM_PANEL_SMOKE_PASS'),('start_settle30.cmd','SETTLE_HOST_SELFTEST_PASS','SETTLE_PANEL_SMOKE_PASS'),('start_full_range.cmd','FULL_RANGE_HOST_SELFTEST_PASS','FULL_RANGE_PANEL_SMOKE_PASS'),('start_asym_smooth.cmd','ASYM_SMOOTH_HOST_SELFTEST_PASS','ASYM_SMOOTH_PANEL_SMOKE_PASS'),('start_region100.cmd','REGION100_HOST_SELFTEST_PASS','REGION100_PANEL_SMOKE_PASS'),('start_brake_fast.cmd','BRAKE_FAST_HOST_SELFTEST_PASS','BRAKE_FAST_PANEL_SMOKE_PASS')]:
 for flag,marker in [('-SelfTest',st),('-SmokeTest',sm)]:
  result=subprocess.run(['cmd.exe','/c','host\\'+entry,flag],cwd=R,capture_output=True,text=True,encoding='utf-8',errors='replace')
  require(result.returncode==0 and marker in result.stdout,'panel failure '+entry+flag);panel[entry+flag]=marker
require('SMOOTH_GOLD_EQUIVALENCE_PASS 600realupdates' in text(R/'sim/results/tb_smooth_policy.log'),'trusted source comparison missing')
require('old6pixelbugreproduced' in text(R/'sim/results/tb_overlay_rgb.log'),'actual RGB old/new comparison missing')
resources={key:int(re.search(r'^#'+label+r'\s+(\d+)',text(area),re.M)[1]) for key,label in (('slice','slice'),('register','reg'),('IO','IO'),('ERAM','eram'),('DSP','dsp'))}
cp_log=text(R/'sim/results/tb_checkpoint_finish.log')
for marker in ['CHECKPOINT_LEGACY_REPRO_PASS','CHECKPOINT_FINISH_RECOVERY_PASS','failure=1 fault=1','failure=2 fault=2']:
 require(marker in cp_log,'checkpoint recovery/guard coverage missing '+marker)
require('maxspent=56' in cp_log,'bounded recovery budget not reproduced')
require('BRAKE_FAST_REPLAY_PASS' in text(R/'sim/results/tb_brake_fast_policy.log'),'highspeed replay missing')
plog=text(R/'sim/results/tb_brake_fast_plant.log')
for i in range(20,28):require(f'BRAKE_FAST_PLANT_CASE_PASS id={i} ' in plog,'plant case missing')
for i in [30,31]:require(f'BRAKE_FAST_PLANT_CASE_PASS id={i} ' in text(R/'sim/results/tb_brake_fast_clock50.log'),'50clock crosscheck missing')
for i in [30,31]:require(f'BRAKE_FAST_PLANT_CASE_PASS id={i} ' in text(R/'sim/results/tb_brake_fast_clock50.log'),'50clock crosscheck missing')
require(any(d['flags']&16384 for d in diags),'D2 checkpoint diagnostic14 never exercised')
report={'status':'SOFTWARE_ROUTING_PASS_AWAITING_PHYSICAL_BRAKE_FAST','bit':str(bit.relative_to(R)),'sha256':sha(bit),'device':'PH1P35MDG324','timing_ns':slack,'resources':resources,'suites':bench_results,'uart_frames':counts,'host_tests':10,'mirror_drivers':drivers,'panels':panel,'paired_host_sha256':{str(p.relative_to(R)):sha(p) for p in (R/'host').glob('*') if p.is_file() and (p.suffix in ('.ps1','.cmd','.py') or p.name=='asym_diag_fixture.txt')},'physical_brake_fast':'PENDING','control_revision':'brake_fast_20261026','capture_radius_pixels':90,'exit_radius_pixels':100,'capture_max_velocity_pixels_s':12,'velocity_frames':2,'desired_ball_speed_cap_pixels_s':200,'control_lookahead_ms':125,'velocity_servo_count_per_pixels_s':0.125,'fine_velocity_noise_deadband_pixels_s':8,'small_tilt_fine_rate_hz':20,'small_tilt_fine_slew_counts_s':12,'highspeed_threshold_pixels_s':160,'highspeed_rate_hz':200,'highspeed_slew_counts_s':200,'region_requested_slew_counts_s':256,'hold_exit_speed_pixels_s':24,'hold_outward_trend_pixels_s':12,'checkpoint_finish':'after60ms unresolved quiet checkpoint; frozen existing target only; remaining original64pulse/5s; original core real100ms arrival; no rebase/guard relaxation','checkpoint_recovery_test_maxspent':56,'checkpoint_bad_feedback_faults':[1,2],'D2_reserved_bit14':'quiescing/checkpoint processing, wire size148 unchanged','target_cap_counts':None,'native_uses_fixed_work_bounds_only':True,'runtime_zone_profiles':[80,100],'working_motor_degrees':[-182*360/4096,364*360/4096],'feedback_motor_degrees':[-204*360/4096,398*360/4096],'PWM_Z_active':False,'wide_schema_sha256':{n:sha(R/n) for n in ['wide_frame_layout.json','wide_diagnostic_schema.json']},'unchanged':'core/F1-F8/timer/budget/MC/P bounds/detector/HDMI/clocks/pins/wireformats','model_criterion':'8 assumed plants,including initial500/1000/1500px_s;tail abs(error)<=100px and abs(speed)<=25px_s;not physical acceptance','model_time_scaling_crosscheck':'weak B-5 and initial1500px_s B-20 rerun at50clocks_ms;other8cases at10;all real ms proportions preserved','model_time_scaling_crosscheck':'weak B-5 and initial1500px_s B-20 at50clocks_ms;8cases at10;real ms proportions preserved','auto_programmed':False}
(R/'brake_fast_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
