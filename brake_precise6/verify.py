from pathlib import Path
import hashlib,json,re,subprocess,sys,zipfile
from decode_serial import parse_record
from cascade_contract import check_cascade
sys.path.insert(0,str(Path(__file__).resolve().parent/'host'))
from cascade_protocol import parse_diag
sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parent;name=root.name;run=root/f'{name}_Runs/phy_1';out=root/'output'
def read(p):
 raw=p.read_bytes();return (raw.decode('utf-16') if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else raw.decode('utf-8-sig')).replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
def execute(*args):return subprocess.run(args,cwd=root,check=True,capture_output=True,text=True,encoding='utf-8',errors='replace').stdout.strip()
from easy3_contract import check_easy3
check_easy3()
execute(sys.executable,'record_contract.py');execute(sys.executable,'source_manifest.py','--check');check_cascade()
bit=out/f'{name}_easy3.bit'
require(bit.is_file() and b'# Package: PH1P35MDG324' in bit.read_bytes()[:500],'current cascade bit/device absent')
require(sha(bit)==sha(run/f'{name}.bit'),'cascade alias differs from current routed bit')
log=read(root/'build.log');require('VISION_FOLLOW_20261022_BUILD_COMPLETE' in log and 'ERROR:' not in log,'TD incomplete/errors')
require('HDL-7225 CRITICAL' not in log,'implicit/redeclared integration signals')
baseline=root.parent/'d36a_autocal_latch_20261020';reference=Path(json.loads(read(root/'camera_lineage.json'))['reference'])
for filename in ['camera_lineage.json','center_lineage.json','motion_lineage.json','large60_lineage.json','follow_lineage.json','loss500_lineage.json','response_lineage.json','neutral_lineage.json']:
 lineage=json.loads(read(root/filename))
 if 'archive' in lineage:
  folder=Path(lineage['archive']);manifest=folder/'manifest.json'
  if manifest.exists():
   for rel,h in json.loads(read(manifest))['files'].items():require(sha(folder/rel)==h,'older archive changed: '+filename+' '+rel)
  zpath=Path(lineage.get('archive_zip',str(folder.with_suffix('.zip'))))
  if zpath.exists():
   with zipfile.ZipFile(zpath) as z:require(z.testzip() is None,'archive CRC '+filename)
execute(sys.executable,'compose.py');execute(sys.executable,'source_manifest.py','--check')
composed=read(root/'rtl/vision_monitor_all.v')
benches={'tb_full':'ALL_TESTS_PASS','tb_detector':'DETECTOR_INTEGRATION_PASS','tb_camera':'CAMERA_CONTROL_PASS','tb_motion':'MOTION_GUARDS_PASS',
 'tb_center':'CENTER_CAPTURE_PASS','tb_large':'LARGE_TARGET_PASS','tb_follow':'FOLLOW_ALL_PASS','tb_plant':'PLANT_ALL_PASS','tb_loss':'LOSS_CONTROL_PASS',
 'tb_response':'RESPONSE_ALL_PASS','tb_neutral':'NEUTRAL_ALL_PASS','tb_hold':'HOLD_ALL_PASS','tb_outer':'OUTER_ALL_PASS',
 'tb_fast':'FAST_ALL_PASS','tb_cascade':'CASCADE_ALL_PASS','tb_cascade_config':'CASCADE_CONFIG_PASS','tb_cascade_plant':'CASCADE_PLANT_ALL_PASS','tb_easy':'EASY_ALL_PASS','tb_easy_plant':'EASY_PLANT_ALL_PASS','tb_checkpoint':'CHECKPOINT_ALL_PASS','tb_replay':'REPLAY_ALL_PASS','tb_braking':'BRAKING_ALL_PASS','tb_braking_plant':'BRAKING_PLANT_ALL_PASS'}
for bench,marker in benches.items():
 require((root/f'sim/results/{bench}.log').stat().st_mtime_ns >= (root/f'sim/results/{bench}.combined.v').stat().st_mtime_ns,'suite not completed since current compilation '+bench)
 s=read(root/f'sim/results/{bench}.log');require(marker in s and 'FATAL' not in s and 'FAIL:' not in s,'failed/stale suite '+bench)
 require(composed in read(root/f'sim/results/{bench}.combined.v'),'suite compiled old RTL '+bench)
 require(read(root/f'sim/{bench}.v') in read(root/f'sim/results/{bench}.combined.v'),'suite compiled old fixture '+bench)
for code in range(1,9):
 require(f'PASS fault {code}:' in read(root/'sim/results/tb_motion.log'),'legacy fault absent')
 require(f'PASS fast fault {code}:' in read(root/'sim/results/tb_response.log'),'legacy AUTO fault absent')
 require(f'HOLD_FAULT_PASS code={code} ' in read(root/'sim/results/tb_hold.log'),'hold fault absent')
 require(f'FAST_FAULT_PASS code={code} ' in read(root/'sim/results/tb_fast.log'),'new fast fault absent')
easy_parent=next((Path(json.loads(read(root/'easy_lineage.json'))['archive'])/'published').rglob('delivery_manifest.json')).parent
inherited_rgb=read(easy_parent/'sim/results/tb_rgb.log')
for i in range(18):require(f'RGB_FRAME_PASS frame={i}' in inherited_rgb,'inherited RGB coverage incomplete')
require('RGB_BOUNDARY_PASS:2560' in inherited_rgb,'inherited RGB edge guard missing')
wire=[];diagnostic=[]
for bench in benches:
 for line in read(root/f'sim/results/{bench}.log').splitlines():
  if line.startswith(('UART ','UART_FIXTURE ','UART_CAMERA ','UART_CENTER ','UART_FOLLOW ','UART_LOSS ','UART_RESPONSE ','UART_NEUTRAL ','UART_CASCADE ')):
   text=line.split(' ',1)[1];require(len(text)+2==429 and parse_record(text) is not None,'VIS5 wire incompatibility');wire.append(text)
  if line.startswith('UART_DIAG '):
   text=line.split(' ',1)[1];require(len(text)+2==94 and parse_diag(text) is not None,'D1 CRC/length/fields');diagnostic.append(text)
require(len(wire)>=15 and len(diagnostic)>=3,'actual UART coverage missing')
for hz in [50,100,200]:require(f'CASCADE_CAL_MOTOR_PASS hz={hz}' in read(root/'sim/results/tb_cascade.log'),'calibration rate untested')
for i in range(3):require(f'CASCADE_PLANT_PASS id={i}' in read(root/'sim/results/tb_cascade_plant.log'),'new controlled plant absent')
require('C_K3_COLLISION_PASS' in read(root/'sim/results/tb_cascade.log'),'new C/K3 collision absent')
for level in [-31,31]:require(f'CASCADE_NEUTRAL_PASS level={level} ' in read(root/'sim/results/tb_cascade.log'),'new calibrated nonzero reference absent')
parent=Path(json.loads(read(root/'cascade_lineage.json'))['archive'])/'project'
def ps_function(source,name):return re.search(r'function '+re.escape(name)+r'\([^\n]*\)\{[\s\S]*?\n\}',source)[0]
for fn in ['New-ParameterPacket','New-CameraPacket','New-FollowPacket','Convert-Record']:
 require(ps_function(read(root/'host/vision_panel_cn.ps1'),fn)==ps_function(read(parent/'host/vision_panel_cn.ps1'),fn),'legacy host function changed '+fn)
result=subprocess.run([sys.executable,'sim/test_cascade_host.py'],cwd=root,capture_output=True,text=True,encoding='utf-8',errors='replace')
(root/'sim/results/host_cascade_tests.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
require(result.returncode==0 and 'Ran 7 tests' in result.stderr,'host fitter/protocol/rejection tests failed')
(out/'simulated_cascade_uart.txt').write_text('\n'.join(wire+diagnostic)+'\n',encoding='ascii')
top=read(root/'user_source/hdl_source/design_top_wrapper.v')

al=read(root/'td_project'/f'{name}.al')
for forbidden in ['steel_ball_motor_manual.v','steel_ball_motion.v','steel_ball_uart_diag.v','ae_set.v','steel_ball_roi_uart.v']:
    require(forbidden not in al,'legacy source remains in project: '+forbidden)
for path in re.findall(r'<File Path="([^"]+)"',al):require((root/'td_project'/path).exists(),'missing project source '+path)
def adc(path):
    result={}
    for line in read(path).splitlines():
        if line.lstrip().startswith('#'):continue
        m=re.search(r'set_pin_assignment\s*\{\s*(.*?)\s*\}\s*\{(.*?)\}',line)
        if m:result[m[1]]={k.strip():v.strip() for k,v in re.findall(r'(\w+)\s*=\s*([^;]+);',m[2])}
    return result
official=root.parents[1]/'2_Example/32_cs500_mipi_hdmi/pin/pin.adc'
official_pins=adc(official);constraints=adc(root/'user_source/constraints_source/pin.adc')
aliases={'I_sys_clk_25m':'I_sys_clk','O_clk_24m':'O_cam_24m'}
for port,fields in official_pins.items():
    dest=aliases.get(port,port)
    require(dest in constraints,'missing official camera port: '+dest)
    for key in ['LOCATION','IOSTANDARD']:require(constraints[dest][key]==fields[key],'official pin mismatch: '+dest)
def pins(path):
    result={}
    for line in read(path).splitlines():
        f=line.split()
        if len(f)>=8 and f[1] in ('INPUT','OUTPUT','INOUT'):
            result[f[0]]={'pin':f[2],'direction':f[1],'standard':f[3],'pull':f[6]}
    return result
area_path=run/f'{name}_phy.area';area=read(area_path);routed=pins(area_path)
reference_pins=pins(reference/'td_project/camera_to_dsi_display_Runs/phy_1/camera_to_dsi_display_phy.area')
for port,fields in reference_pins.items():
    require(port in routed,'reference IO lost: '+port)
    for key in ['pin','standard','direction']:require(routed[port][key]==fields[key],'reference IO changed: '+port)
for port,fields in constraints.items():
    require(port in routed and routed[port]['pin']==fields['LOCATION'] and routed[port]['standard']==fields['IOSTANDARD'],'routed constraint mismatch: '+port)
    require(routed[port]['pull']==fields['PULLTYPE'],'routed pull mismatch: '+port)
require(len({r['pin'] for r in routed.values()})==len(routed),'duplicate IO location')
golden_by_pin={fields['LOCATION']:fields for fields in adc(baseline/f'{baseline.name}.adc').values()}
for port in ['O_motor_step','O_motor_step_v2','O_motor_dir','O_motor_dir_v1','O_motor_en','O_motor_en_u2',
             'I_encoder_j1[1]','I_encoder_j1[0]','I_encoder_j2[1]','I_encoder_j2[0]']:
    old=golden_by_pin[routed[port]['pin']]
    require(routed[port]['pull']==old['PULLTYPE'] and routed[port]['standard']==old['IOSTANDARD'],'golden electrical settings changed: '+port)
netlist=read(root/'routed_netlist.v');drivers={}
for port in ['O_motor_step','O_motor_step_v2','O_motor_dir','O_motor_dir_v1','O_motor_en','O_motor_en_u2']:
    match=re.search(r'\b'+port+r'_syn_\d+\s*\(\s*\.doq\(\{([^}]+)\}\),\s*\.opad\('+port+r'\)\);',netlist)
    require(match is not None,'output pad driver not found: '+port)
    drivers[port]=match[1].split(',')[-1].strip()
for primary,mirror in [('O_motor_step','O_motor_step_v2'),('O_motor_dir','O_motor_dir_v1'),('O_motor_en','O_motor_en_u2')]:
    require(drivers[primary]==drivers[mirror] and drivers[primary] not in ("1'b0","1'b1"),'active motor mirror driver mismatch: '+primary)
timing=read(run/f'{name}_pr.timing')
times={key:float(re.search(r'\b'+key+r':\s*([-\d.]+)ns',timing)[1]) for key in ['SWNS','STNS','HWNS','HTNS']}
require(times['SWNS']>=0 and times['HWNS']>=0 and times['STNS']==times['HTNS']==0,'timing failed')
require('Confidence          : Routed' in timing and 'Device              : PH1P35MDG324' in timing,'timing/device wrong')
clock_notices=[]
for line in read(root/'build.log').splitlines():
    if 'CRITICAL-WARNING' not in line:continue
    known=re.match(r'^PHY-5060 CRITICAL-WARNING: Clock net candidate (u_uicfgcs500/uii2c_inst/scl_clk|O_cam_24m_syn_\d+) has mixed fanouts',line) or re.match(r'^PHY-5079 CRITICAL-WARNING: Marked \d+ clock net\(s\) utilize the local routing resources',line)
    require(known,'unreviewed critical diagnostic: '+line);clock_notices.append(line)
sdc=read(root/'td_project'/f'{name}.sdc');ref_sdc=read(reference/'td_project/camera_to_dsi_display.sdc')
clock_commands=lambda text:[line for line in text.splitlines() if line.startswith(('create_clock','rename_clock','derive_clocks'))]
require(clock_commands(sdc)==clock_commands(ref_sdc),'reference clocks/periods changed')
clock_groups=lambda text:re.findall(r'set_clock_groups[\s\S]*?(?=\n\s*\n)',text)
require(clock_groups(sdc)==clock_groups(ref_sdc),'reference asynchronous clock groups changed')
require('set_false_path -from [get_clocks' not in sdc,'legacy blanket clock false path retained')
require(sdc.count('set_max_delay -datapath_only')==2 and sdc.count('10.000')>=2,'bounded camera mailboxes not constrained')
require('CAMERA_CDC_BOUNDED_CLOCK_PAIRS 10.000ns' in read(root/'build.log'),'bounded camera CDC constraints absent')
for start,end in re.findall(r'Begin Point\s*:\s*(.*?)\nEnd Point\s*:\s*(.*?)\n',timing):
    if ('sys_clk_50m' in start and 'pll_clk_24m' in end) or ('pll_clk_24m' in start and 'sys_clk_50m' in end):
        require('u_camera_control/' in start and 'u_camera_control/' in end,'non-camera crossing entered bounded mailbox clock pair')
host=execute('cmd.exe','/c','host\\start_panel.cmd','-SelfTest')
require('HOST_SELF_TEST_PASS' in host,'host protocol self test failed')
smoke=execute('cmd.exe','/c','host\\start_panel.cmd','-SmokeTest')
require('HOST_UI_SMOKE_PASS' in smoke,'host UI did not render')
resources={key:int(re.search(r'^#'+label+r'\s+(\d+)',area,re.M)[1]) for key,label in [('slice','slice'),('register','reg'),('IO','IO'),('ERAM','eram'),('DSP','dsp')]}
require(resources['slice']>15000 and resources['ERAM']>=45 and resources['DSP']>=17,'camera/ISP logic unexpectedly trimmed')
for instance in ['u_isp_top','u_steel_ball_stream_bbox','u_steel_ball_detect','u_camera_control','motor_core']:
    require(instance in area,'required active hierarchy missing: '+instance)
warnings=[line for line in read(root/'build.log').splitlines() if 'WARNING:' in line and ('Undriven' in line or 'undriven' in line)]
require(not any('S_uart_' in line or 'u_vision_monitor' in line or 'u_camera_control' in line for line in warnings),'new integration undriven net')
require('EASY_HOLD_PASS 61s' in read(root/'sim/results/tb_easy.log'),'61s hold absent')
for i in [3,4,5]:require(f'CASCADE_PLANT_PASS id={i} ' in read(root/'sim/results/tb_easy_plant.log'),'preset plant absent')
require('REPLAY_OLD_F5_PASS' in read(root/'sim/results/tb_replay_old.log'),'archived source did not reproduce F5')
require('OUTER_FAST_VELOCITY_PASS' in read(root/'sim/results/tb_outer.log'),'rapid motion observer absent')
require('CHECKPOINT_PASS bad_ratio=1' in read(root/'sim/results/tb_checkpoint.log'),'bad ratio checkpoint guard absent')
require('BRAKING_NOISE_PASS' in read(root/'sim/results/tb_braking.log'),'center noise proof absent')
require('EASY_NOISE_HOLD_PASS' in read(root/'sim/results/tb_easy.log'),'real noisy frames/noSTEP proof absent')
for i in range(6,11):require(f'CASCADE_PLANT_PASS id={i} ' in read(root/'sim/results/tb_braking_plant.log'),'high speed plant coverage absent')
report={'status':'SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_EASY3_TEST','date':'2026-10-25','device':'PH1P35MDG324',
 'delivery_bit':str(bit),'bit':str(bit),'sha256':sha(bit),'timing_ns':times,'resources':resources,'STA_coverage_percent':float(re.search(r'STA coverage[^0-9]*(\d+(?:\.\d+)?)%',timing)[1]),
 'simulations':list(benches),'inherited_rgb':{'status':'PARENT_FULL_PASS_UNCHANGED_VIDEO_AND_LEGACY_PATH','source':str(easy_parent/'sim/results/tb_rgb.log'),'frames':18,'current_video_rerun_completed':False},'legacy_report_bytes':429,'diagnostic_bytes':94,'C_packet_bytes':54,
 'fault_policy':'F1-F8 latch/STEP inhibited;retain establishedEN;K1release-only,K4/reset release;no fault restart',
 'guards':{'segment_pulses':64,'segment_timeout_s':5,'MC_net_limit':64,'P_limit':64,'absolute_target':60,'manual_deadband':2,'follow_arrival':1},
 'physical_test':'PENDING_UNTOUCHED_K3_K2_PREDICTIVE_BRAKING_LOGS','physical_stability_claim':False,
 'preset':dict(json.loads(read(root/'easy_lineage.json'))['preset'],relative_limit=60,kv=64,max_hz=200,slew_rate=200),
 'checkpoint':{'start_pulses':48,'start_ms':3500,'quiet_ms':40,'net_ratio_counts_per_pulse':1.28125,'tolerance_counts':4,'faults_auto_cleared':False,'origin_MC_reset':False},
 'replay':'actual recorded camera coordinates,simulated trueAB12ms1.28;archived easy reproducesF5;new>200pulses with verified segment boundaries',
 'startup':'RU0,CASCADE_DEFAULT1/CASCADE_PRESET1;K1 enable,K3 center,K2 continuous return;no host calibration prerequisite',
 'control':'preset frame-time fast velocity,actuator reversal lookahead80ms+5ms/count,bounded piecewise speed envelope,13-stage outer;custom C keeps alpha-beta PD;5ms ramp/inner;20ms command prediction;200Hz preset',
 'phase_flags':{'predictive_active':11,'control_phase':'bits10:9,0drive/1brake/2capture'},
 'model':'continuous integrated position fitting,3cycle cross-validation R2>=.70;bounded offline gain search;no physical pass from simulation',
 'known_clock_routing_notices':clock_notices,'motor_mirror_drivers':drivers,'automatic_programming':False}
(root/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','sha256','resources','timing_ns','STA_coverage_percent']},indent=2))
