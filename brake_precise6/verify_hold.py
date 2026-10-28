from pathlib import Path
import hashlib,json,re,subprocess,sys,zipfile
from decode_serial import parse_record
from cascade_contract import response_servo,hold_servo,check_hold
check_hold()
sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parent
name=root.name;run=root/f'{name}_Runs/phy_1';out=root/'output'
def read(p):
    raw=p.read_bytes()
    text=raw.decode('utf-16') if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else raw.decode('utf-8-sig')
    return text.replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise RuntimeError(message)
def execute(*args):
    result=subprocess.run(args,cwd=root,check=True,capture_output=True,text=True,encoding='utf-8',errors='replace')
    return result.stdout.strip()
execute(sys.executable,'record_contract.py');execute(sys.executable,'source_manifest.py','--check')
bit=out/f'{name}_hold.bit'
require(b'# Package: PH1P35MDG324' in bit.read_bytes()[:500],'bit package mismatch')
require(sha(bit)==sha(run/f'{name}.bit'),'output bit is not current routed bit')
require('VISION_FOLLOW_20261022_BUILD_COMPLETE' in read(root/'build.log'),'TD completion marker missing')
require('ERROR:' not in read(root/'build.log'),'TD errors present')
require('HDL-7225 CRITICAL' not in read(root/'build.log'),'implicit re-declarations present')
baseline=root.parent/'d36a_autocal_latch_20261020'
large_lineage=json.loads(read(root/'large60_lineage.json'))
large_archive=Path(large_lineage['archive'])
for rel,digest in json.loads(read(large_archive/'manifest.json'))['files'].items():require(sha(large_archive/rel)==digest,'pre-large60 archive changed: '+rel)
with zipfile.ZipFile(large_lineage['archive_zip']) as z:require(z.testzip() is None,'pre-large60 ZIP CRC failed')
before=large_archive/'project'
expected_core=read(before/'rtl/vision_move_core.v').replace('TIMEOUT_CYCLES=100000000','TIMEOUT_CYCLES=250000000').replace('POSITION_LIMIT=16,FEEDBACK_LIMIT=22,MOVE_BUDGET=12,NO_RESPONSE_LIMIT=3,TARGET_LIMIT=5,DEADBAND=2','POSITION_LIMIT=64,FEEDBACK_LIMIT=64,MOVE_BUDGET=64,NO_RESPONSE_LIMIT=3,TARGET_LIMIT=60,DEADBAND=2')
require(read(root/'rtl/vision_move_core.v')==expected_core,'executor changed beyond authorized defaults')

loss_lineage=json.loads(read(root/'loss500_lineage.json'));loss_archive=Path(loss_lineage['archive'])
for rel,digest in json.loads(read(loss_archive/'manifest.json'))['files'].items():require(sha(loss_archive/rel)==digest,'pre-loss VIS5 archive changed: '+rel)
with zipfile.ZipFile(loss_lineage['archive_zip']) as z:require(z.testzip() is None,'pre-loss VIS5 ZIP CRC failed')
loss_before=loss_archive/'project'
for rel in ['rtl/vision_move_core.v','rtl/enable_latch.v','rtl/encoder_ab_counter.v','rtl/vision_shadow_target.v','rtl/vision_report_tx.v','generate_uart.py','frame_layout.json','td_project/vision_follow_20261022.al','td_project/vision_follow_20261022.sdc','user_source/constraints_source/pin.adc']:
    require((rel=='rtl/enable_latch.v' or sha(root/rel)==sha(loss_before/rel)),'unchanged motor/protocol/pin source changed: '+rel)
require(sha(loss_before/'output/vision_follow_20261022.bit')==loss_lineage['old_bit_sha256'],'pre-loss bit mismatch')
follow_lineage=json.loads(read(root/'follow_lineage.json'));follow_parent=Path(follow_lineage['parent_project'])
for rel,digest in follow_lineage['parent_files'].items():require(sha(follow_parent/rel)==digest,'large60 parent changed: '+rel)
follow_archive=Path(follow_lineage['archive'])
for rel,digest in json.loads(read(follow_archive/'manifest.json'))['files'].items():require(sha(follow_archive/rel)==digest,'large60 archive changed: '+rel)
with zipfile.ZipFile(follow_lineage['archive_zip']) as z:require(z.testzip() is None,'large60 ZIP CRC failed')
require(sha(root/'rtl/vision_move_core.v')==sha(follow_parent/'rtl/vision_move_core.v'),'frozen finite executor changed')
# Reconstruct the exact, reviewable adaptation from the unchanged finite executor.
expected_servo=read(follow_parent/'rtl/vision_move_core.v')
expected_servo=expected_servo.replace('// New commands are K2 edges sampling a visual target, never a continuous setpoint.','// External requests share the finite guard sequence; follow retargets only at CHECK.')
expected_servo=expected_servo.replace('module vision_move_core','module vision_servo_core').replace('TARGET_LIMIT=60,DEADBAND=2','TARGET_LIMIT=60,DEADBAND=2,EXTERNAL_CONTROL=0,FOLLOW_DEADBAND=1')
expected_servo=expected_servo.replace('input wire clk,rst_n,enable_request,k4_n,k2_n,','input wire clk,rst_n,enable_request,k4_n,k2_n,\n input wire request,following,external_cancel,input wire [3:0] external_cancel_reason,')
expected_servo=expected_servo.replace('wire permit=visual_valid && !visual_stale && settings_ready && !config_changed;','wire extended_cancel=EXTERNAL_CONTROL && external_cancel;\n wire permit=visual_valid && !visual_stale && settings_ready && !config_changed && !extended_cancel;')
expected_servo=expected_servo.replace('reg previous_pressed=0,press_event=0;',"reg key_armed=0;\n reg previous_pressed=0,press_event=0;\n wire command_event=EXTERNAL_CONTROL ? request : press_event;\n wire command_armed=EXTERNAL_CONTROL ? 1'b1 : key_armed;")
expected_servo=expected_servo.replace('reg enabled=0,key_armed=0,active=0','reg enabled=0,active=0')
expected_servo=expected_servo.replace('wire in_band=wide_error<=DEADBAND && wide_error>=-DEADBAND;', 'wire [31:0] allowed_error=EXTERNAL_CONTROL && following ? FOLLOW_DEADBAND : DEADBAND;\n wire in_band=wide_error<=$signed(allowed_error) && wide_error>=-$signed(allowed_error);')
expected_servo=expected_servo.replace('if(press_event)begin','if(command_event)begin').replace('else if(!key_armed)reject_reason','else if(!command_armed)reject_reason').replace('if(press_event && key_armed &&','if(command_event && command_armed &&')
expected_servo=expected_servo.replace('cancel_reason<=config_changed || !settings_ready ? 5 : (visual_stale ? 4 : 3);','cancel_reason<=extended_cancel ? external_cancel_reason : (config_changed || !settings_ready ? 5 : (visual_stale ? 4 : 3));')
expected_servo=expected_servo.replace('CHECK:begin\n      if(in_band)', """CHECK:begin
      if(EXTERNAL_CONTROL && following && (visual_target>TARGET_LIMIT || visual_target< -TARGET_LIMIT))begin
       fault<=8;step_r<=0;active<=0;done<=0;state<=FAULT;cancel_reason<=6;
      end else if(EXTERNAL_CONTROL && following && locked_target!={{24{visual_target[7]}},visual_target})begin
       // Retarget only after the previous pulse/feedback phase. Never reset budget/time.
       locked_target<={{24{visual_target[7]}},visual_target};
      end else if(in_band)""")
require(read(root/'rtl/vision_servo_core.v')==hold_servo(response_servo(expected_servo)),'servo changed beyond documented request/cancel/CHECK retarget/auto deadband adaptation')
for rel in ['rtl/vision_shadow_target.v','rtl/vision_center_key.v','user_source/constraints_source/pin.adc']:
    require(sha(root/rel)==sha(follow_parent/rel),'retained source/constraints changed: '+rel)
for ext in ['al','sdc']:
    require(read(root/'td_project'/f'{name}.{ext}')==read(follow_parent/'td_project'/f'{follow_parent.name}.{ext}').replace(follow_parent.name,name),'project changed beyond isolated project name: '+ext)

def ps_function(source,name):return re.search(r'function '+re.escape(name)+r'\([^\n]*\)\{[\s\S]*?\n\}',source)[0]
old_host=read(before/'host/vision_panel_cn.ps1');new_host=read(root/'host/vision_panel_cn.ps1')
require(ps_function(new_host,'New-ParameterPacket')==ps_function(old_host,'New-ParameterPacket').replace('($Gain -band 127) -lt 4','($Gain -band 127) -lt 0').replace('$Limit -gt 5','$Limit -gt 60'),'P packet changed beyond bounds')
require(ps_function(new_host,'New-CameraPacket')==ps_function(old_host,'New-CameraPacket'),'V packet changed')
for fn in ['New-ParameterPacket','New-CameraPacket','New-FollowPacket','Convert-Record']:
    require(ps_function(new_host,fn)==ps_function(read(loss_before/'host/vision_panel_cn.ps1'),fn),'VIS5/P/V/S host protocol function changed: '+fn)
for rel in ['enable_latch.v','encoder_ab_counter.v']:
    require((rel=='enable_latch.v' or sha(root/'rtl'/rel)==sha(baseline/'rtl'/rel)),'motor source changed: '+rel)
center_lineage=json.loads(read(root/'center_lineage.json'))
center_parent=Path(center_lineage['parent_project'])
for rel,digest in center_lineage['parent_files'].items():require(sha(center_parent/rel)==digest,'K2 parent changed: '+rel)
for rel in ['enable_latch.v','encoder_ab_counter.v','vision_shadow_target.v','vision_camera_control.v']:
    require((rel=='enable_latch.v' or sha(root/'rtl'/rel)==sha(center_parent/'rtl'/rel)),'retained source changed: '+rel)
center_archive=Path(center_lineage['archive'])
for rel,digest in json.loads(read(center_archive/'manifest.json'))['files'].items():require(sha(center_archive/rel)==digest,'K2 archive changed: '+rel)
with zipfile.ZipFile(center_lineage['archive_zip']) as z:require(z.testzip() is None,'K2 archive ZIP CRC failed')
motion_lineage=json.loads(read(root/'motion_lineage.json'))
parent=Path(motion_lineage['parent_project'])
for rel,digest in motion_lineage['parent_files'].items():require(sha(parent/rel)==digest,'preserved visual parent changed: '+rel)
require(sha(parent/'output/vision_control_20261021_camera_roi.bit')==motion_lineage['parent_bit_sha256'],'saved visual bit changed')
require(sha(root/'rtl/reference_position_core.v')==motion_lineage['original_position_core_sha256']==sha(root.parent/'d36a_position5_20261020/rtl/position_core.v'),'passed executor reference changed')
visual_archive=Path(motion_lineage['archive'])
for rel,digest in json.loads(read(visual_archive/'manifest.json'))['files'].items():require(sha(visual_archive/rel)==digest,'visual archive changed: '+rel)
with zipfile.ZipFile(motion_lineage['archive_zip']) as z:require(z.testzip() is None,'visual archive ZIP CRC failed')
archive=Path('D:/AAAProject/FPGA/AAA_LookHere/成功版本归档/20261020_K1点按保持_实板通过')
archive_manifest=json.loads(read(archive/'manifest.json'))
for rel,digest in archive_manifest['files'].items():require(sha(archive/rel)==digest,'archive changed: '+rel)
with zipfile.ZipFile(archive.with_suffix('.zip')) as z:require(z.testzip() is None,'golden ZIP CRC failed')
lineage=json.loads(read(root/'camera_lineage.json'));reference=Path(lineage['reference'])
for rel,digest in lineage['unchanged_sources'].items():
    require(sha(reference/rel)==digest,'camera reference source changed: '+rel)
    if rel not in ('user_source/hdl_source/design_top_wrapper.v','user_source/hdl_source/steel_ball_detect.v','user_source/hdl_source/steel_ball_stream_bbox.v'):
        require(sha(root/rel)==digest,'camera/IP source outside loss500 allowlist changed: '+rel)
parts=['enable_latch.v','encoder_ab_counter.v','vision_move_core.v','vision_servo_core.v','vision_result_guard.v','vision_follow_control.v','vision_cdc_bridge.v','vision_config_rx.v','vision_center_key.v',
       'vision_shadow_target.v','vision_report_tx.v','vision_monitor.v','vision_value_cdc.v','vision_camera_control.v']
composed='\n'.join('// Source: '+p+'\n'+read(root/'rtl'/p) for p in parts)
require(read(root/'rtl/vision_monitor_all.v')==composed,'composition stale')
for bench,marker in [('tb_full','ALL_TESTS_PASS'),('tb_detector','DETECTOR_INTEGRATION_PASS'),('tb_camera','CAMERA_CONTROL_PASS'),('tb_motion','MOTION_GUARDS_PASS'),('tb_center','CENTER_CAPTURE_PASS'),('tb_large','LARGE_TARGET_PASS'),('tb_follow','FOLLOW_ALL_PASS'),('tb_plant','PLANT_ALL_PASS'),('tb_loss','LOSS_CONTROL_PASS'),('tb_rgb','RGB_INTEGRATION_PASS'),('tb_response','RESPONSE_ALL_PASS'),('tb_neutral','NEUTRAL_ALL_PASS'),('tb_hold','HOLD_ALL_PASS')]:
    log=read(root/f'sim/results/{bench}.log')
    require(marker in log and 'FATAL' not in log and 'FAIL:' not in log,'simulation failed: '+bench)
    require(composed in read(root/f'sim/results/{bench}.combined.v'),'simulation source stale: '+bench)
for code in range(1,9):require(f'HOLD_FAULT_PASS code={code} ' in read(root/'sim/results/tb_hold.log'),'fault-hold case missing')
motion_log=read(root/'sim/results/tb_motion.log')
require('PASS finite motion:' in motion_log,'finite motion test missing')
for code in range(1,9):require(f'PASS fault {code}:' in motion_log,'fault fixture missing: '+str(code))
large_log=read(root/'sim/results/tb_large.log')
require('LARGE_NORMAL_PASS' in large_log and 'LARGE_BUDGET_PASS' in large_log,'large-target timing/budget regression absent')
large_moves=[dict(zip(['target','position','error','pulses','scaled_cycles'],map(int,m))) for m in re.findall(r'LARGE_REACHED target=(-?\d+) P=(-?\d+) error=(-?\d+) pulses=(\d+) elapsed_scaled=(\d+)',large_log)]
require([row['target'] for row in large_moves[:4]]==[60,0,-60,0],'large-target sequence absent')
require(all(abs(row['error'])<=2 and row['pulses']<=64 and 200000<row['scaled_cycles']<500000 for row in large_moves),'large-target arrival or5s timing failed')
pixel_fixture=json.loads(read(root/'sim/detector_fixture_lineage.json'))
require(sha(Path(pixel_fixture['reference']))==pixel_fixture['sha256'],'reference pixel fixture changed')
simlog=read(root/'sim/results/tb_full.log')
wire_lines=[line.split(' ',1)[1] for line in simlog.splitlines() if line.startswith(('UART ','UART_FIXTURE '))]
rows=[parse_record(line) for line in wire_lines]
require(len(rows)>=4 and all(rows) and sum(line.startswith('UART_FIXTURE ') for line in simlog.splitlines())==2,'wire UART decode failed')
require(all(len(line)+2==429 for line in wire_lines),'wire UART frame length mismatch')
monitor_rows=[parse_record(line.split(' ',1)[1]) for line in simlog.splitlines() if line.startswith('UART ')]
require(monitor_rows[-1]['SEQ']==4 and monitor_rows[-1]['C']==960 and monitor_rows[-1]['G']==7,'real TX config acknowledgement failed')
require(rows[0]['E1']==-4 and rows[0]['T']==-5 and rows[0]['P']==4,'signed wire data incorrect')
require(rows[0]['MT']==-5 and rows[0]['ME']==-9 and rows[0]['MC']==-4,'signed motion UART fields incorrect')
require(rows[0]['CC']==0xabcd and rows[0]['KC']==1,'center fields missing from coherent serializer snapshot')
require(monitor_rows[-1]['DC']>=8 and monitor_rows[-1]['AC']>=monitor_rows[-1]['DC'] and monitor_rows[-1]['MB']==0 and monitor_rows[-1]['EN']==0 and monitor_rows[-1]['CR']==2,'real feedback movement/stop evidence missing')
require('LARGE_INTEGRATION_PASS' in simlog and any(row['T']==60 and row['MT']==60 and row['G']==0 and row['L']==60 for row in monitor_rows) and any(row['T']==-60 and row['MT']==-60 for row in monitor_rows),'real UART large target evidence missing')
require(all(row['F']==0 for row in monitor_rows),'unexpected fault in integrated normal/cancellation flow')
require(all(r['T']==0 for r in rows if not r['V']),'invalid target not zero')
response_log=read(root/'sim/results/tb_response.log')
require('RESPONSE_ARITHMETIC_PASS' in response_log,'fine/rate arithmetic absent')
for code in range(1,9):require(f'PASS fast fault {code}:' in response_log,'fast AUTO guard absent: '+str(code))
response_cases=[dict(zip(['fast','feedback_delay_ms','forward_ms','reverse_ms','pulses','manual_return_pulses'],map(int,m))) for m in re.findall(r'RESPONSE_MOTION_PASS FAST=(\d+) delay_ms=(\d+) forward_ms=(\d+) reverse_ms=(\d+) pulses=(\d+) manual_pulses=(\d+)',response_log)]
old_cases=[c for c in response_cases if not c['fast']];new_cases=[c for c in response_cases if c['fast']]
require(len(old_cases)==1 and len(new_cases)==2,'response timing cases incomplete')
require(all(c['forward_ms']*2<old_cases[0]['forward_ms'] and c['reverse_ms']*2<old_cases[0]['reverse_ms'] and c['manual_return_pulses']>=8 for c in new_cases),'response benchmark/manual path failed')
require(any(c['feedback_delay_ms']==12 for c in new_cases),'delayed trueAB evidence absent')
response_lines=[line.split(' ',1)[1] for line in response_log.splitlines() if line.startswith('UART_RESPONSE ')]
response_rows=[parse_record(line) for line in response_lines]
require(len(response_rows)==2 and all(response_rows) and all(len(line)+2==429 for line in response_lines),'response UART missing/format changed')
for row in response_rows:
 for key,value in {'G':3,'DZ':5,'L':32,'SL':8,'RU':60,'AR':1,'F':0,'X1':0}.items():require(row[key]==value,'response defaults/wire mismatch: '+key)
(out/'simulated_uart_frames.txt').write_text('\n'.join(wire_lines)+'\n',encoding='ascii')
camera_lines=[line.split(' ',1)[1] for line in read(root/'sim/results/tb_camera.log').splitlines() if line.startswith('UART_CAMERA ')]
require(len(camera_lines)==1,'camera-flow UART fixture absent')
camera_row=parse_record(camera_lines[0]);require(camera_row is not None,'camera-flow UART decode failed')
require(len(camera_lines[0])+2==429,'camera-flow UART length wrong')
for key,value in {'CS':4,'CA':4,'RA':4,'CB':0,'AE':3600,'AG':143,'RL':20,'RT':30,'RR':1000,'RB':600,'EN':1,'F':0,'MB':0,'MC':0}.items():
    require(camera_row[key]==value,'camera-flow UART mismatch: '+key)
center_lines=[line.split(' ',1)[1] for line in read(root/'sim/results/tb_center.log').splitlines() if line.startswith('UART_CENTER ')]
require(len(center_lines)==1 and len(center_lines[0])+2==429,'center wire fixture absent/wrong length')
center_row=parse_record(center_lines[0]);require(center_row is not None,'center wire decode failed')
for key,value in {'C':500,'BX':500,'T':0,'CC':7,'KC':1,'F':0,'MB':0,'AC':2,'DC':2,'P':2}.items():
    require(center_row[key]==value,'center wire mismatch: '+key)
(out/'simulated_uart_frames.txt').write_text('\n'.join(wire_lines+camera_lines+center_lines)+'\n',encoding='ascii')

require(rows[0]['VE']==-4 and rows[0]['AT']==-5 and rows[0]['RU']==30 and rows[0]['RT']==200,'new signed/unique report fields failed')
follow_log=read(root/'sim/results/tb_follow.log')
require('FOLLOW_CONTROL_PASS' in follow_log and 'PD_ARITHMETIC_PASS' in follow_log and 'RETARGET_GUARD_PASS fault=4' in follow_log and 'RETARGET_GUARD_PASS fault=5' in follow_log,'follow safety/arithmetic paths not covered')
follow_lines=[line.split(' ',1)[1] for line in follow_log.splitlines() if line.startswith('UART_FOLLOW ')]
require(len(follow_lines)==1 and len(follow_lines[0])+2==429,'follow wire frame absent')
follow_row=parse_record(follow_lines[0]);require(follow_row is not None,'follow wire decode failed')
from analyze_follow import analyze
evaluation=analyze([follow_lines[0],follow_lines[0].replace(' BX=03C0 ',' BX=03D4 '),follow_lines[0].replace(' AR=1 ',' AR=0 ').replace(' SR=0 ',' SR=7 ')])
require(len(evaluation['automatic_sessions'])==1 and evaluation['automatic_sessions'][0]['stop_reason']==7 and evaluation['automatic_sessions'][0]['whole']['error_pixels']['rms']==14.142,'capture analysis/session metrics failed')
for key,value in {'MD':1,'AR':1,'RU':0,'DS':3,'CZ':1,'F':0,'AT':0,'RT':0,'SR':0}.items():
    require(follow_row[key]==value,'follow wire mismatch: '+key)
plant_log=read(root/'sim/results/tb_plant.log')
plant_cases=[{'id':int(i),'coupling':float(c),'peak_pixels':float(p),'final_error_pixels':float(e),'final_velocity_pixels_per_frame':float(v),'rms_tail_pixels':float(r),'P':int(pos)} for i,c,p,e,v,r,pos in re.findall(r'PLANT_MODEL_PASS id=(\d+) coupling=([\d.]+) peak=([\d.]+) final_error=([-\d.]+) final_velocity=([-\d.]+) rms_tail=([\d.]+) P=(-?\d+)',plant_log)]
require(len(plant_cases)==3 and all(abs(c['final_error_pixels'])<=80 and abs(c['final_velocity_pixels_per_frame'])<=1 for c in plant_cases),'assumed plant acceptance failed')
(out/'simulated_uart_frames.txt').write_text('\n'.join(wire_lines+camera_lines+center_lines+follow_lines)+'\n',encoding='ascii')
loss_log=read(root/'sim/results/tb_loss.log')
require('LOSS500_BOUNDARY_PASS elapsed=50000' in loss_log,'exact500ms boundary absent')
loss_lines=[line.split(' ',1)[1] for line in loss_log.splitlines() if line.startswith('UART_LOSS ')]
loss_rows=[parse_record(line) for line in loss_lines]
require(loss_rows and all(loss_rows) and all(len(line)+2==429 for line in loss_lines),'loss real UART wire invalid')
require(any(r['AR']==1 and r['V']==0 and r['T']!=0 and r['AT']!=0 and r['EN']==1 and r['F']==0 for r in loss_rows),'no raw-invalid/held-target wire proof')
require(all(r['F']==0 and r['X1']==0 for r in loss_rows),'loss flow spurious motor faults')
require('RGB_BOUNDARY_PASS:2560' in read(root/'sim/results/tb_rgb.log'),'per-pixel ROI/radius/floor/ratio boundary suite absent')
require(all('RGB_FRAME_PASS frame='+str(i) in read(root/'sim/results/tb_rgb.log') for i in range(18)),'RGB frame coverage incomplete')
neutral_log=read(root/'sim/results/tb_neutral.log')
old_repro=json.loads(read(root/'before_neutral_reproduction.json'))
require(old_repro['status']=='EXPECTED_OLD_REFERENCE_FAILURE_REPRODUCED','old reference reproduction missing')
require(re.search(r'LEVEL=31 T=\s*0 AT=\s*0 P=\s*31',read(root/'sim/results/before_neutral.log')),'old failure is not the same reference mismatch')
require(read(Path(json.loads(read(root/'neutral_lineage.json'))['archive'])/'project/rtl/vision_monitor_all.v') in read(root/'sim/results/before_neutral.combined.v'),'old reproduction used different source')
for level in [-31,31]:
 require(f'NEUTRAL_START_PASS LEVEL={level} centered_no_motion_ms=300' in neutral_log,'offset startup proof absent')
 require(f'NEUTRAL_MOTION_PASS LEVEL={level}:' in neutral_log,'offset closed-loop actuator cases absent')
for level in [-63,63]:require(f'NEUTRAL_INVALID_PASS LEVEL={level} KC8/RD0/AJ11' in neutral_log,'invalid neutral guard absent')
require('NEUTRAL_ARITHMETIC_PASS' in neutral_log,'neutral arithmetic/bounds/invert absent')
neutral_lines=[line.split(' ',1)[1] for line in neutral_log.splitlines() if line.startswith('UART_NEUTRAL ')]
neutral_rows=[parse_record(line) for line in neutral_lines]
require(len(neutral_rows)==2 and all(neutral_rows) and all(len(line)+2==429 for line in neutral_lines),'neutral VIS5 wire compatibility failed')
require({row['P'] for row in neutral_rows}=={-31,31},'signed neutral wire cases missing')
for row in neutral_rows:
 require(row['P']==row['T']==row['AT']==row['MT'] and row['ME']==0,'centered neutral actual target mismatch')
 for key,value in {'MC':0,'TS':0,'AR':1,'F':0,'X1':0,'OK':1}.items():require(row[key]==value,'neutral wire safety/history mismatch: '+key)
(out/'simulated_uart_frames.txt').write_text('\n'.join(wire_lines+camera_lines+center_lines+follow_lines+loss_lines+response_lines+neutral_lines)+'\n',encoding='ascii')
top=read(root/'user_source/hdl_source/design_top_wrapper.v')
expected_top=read(loss_before/'user_source/hdl_source/design_top_wrapper.v')
expected_top=expected_top.replace('wire [10:0] S_ball_x, S_ball_y;', 'wire [10:0] S_ball_x, S_ball_y;\n    wire S_track_valid;\n    wire [10:0] S_track_x,S_track_y;')
expected_top=expected_top.replace('.COLOR_MODE(1), .COLOR_MIN(45),', '.TRACK_EN(1), .TRACK_RADIUS(48), .TRACK_COLOR_MIN(35),\n        .COLOR_MODE(1), .COLOR_MIN(45),')
expected_top=expected_top.replace('.I_box_valid(S_detect_box_valid),', '.I_track_valid(S_track_valid),.I_track_x(S_track_x),.I_track_y(S_track_y),\n        .I_box_valid(S_detect_box_valid),')
expected_top=expected_top.replace('.O_cluster_count(S_ball_clusters)', '.O_track_valid(S_track_valid),.O_track_x(S_track_x),.O_track_y(S_track_y),\n        .O_cluster_count(S_ball_clusters)')
require(top==expected_top,'camera top changed beyond local tracking connections')
pixel_source=read(root/'user_source/hdl_source/steel_ball_detect.v')
require(pixel_source.split('    // Synchronous BRAM FIFO')[1]==read(loss_before/'user_source/hdl_source/steel_ball_detect.v').split('    // Synchronous BRAM FIFO')[1],'unused legacy CCL source changed')
require(pixel_source.split('    // Synchronous BRAM FIFO')[0] in read(root/'sim/results/tb_rgb.combined.v'),'real RGB classifier/overlay simulation source stale')
require(read(root/'user_source/hdl_source/steel_ball_stream_bbox.v') in read(root/'sim/results/tb_rgb.combined.v'),'RGB bbox source stale')
require('ae_set u_ae_set' not in top and 'vision_camera_control u_camera_control' in top,'camera button/control conflict')
require(top.index('wire S_detect_rst_n')<top.index('vision_camera_control u_camera_control'),'reset declared after use')
require(top.index('wire [10:0] S_roi_left')<top.index('vision_camera_control u_camera_control'),'ROI declared after use')
require('.src_frame(S_detect_done)' in top,'CDC does not use completed detection results')
require('u_steel_ball_motor_manual' not in top and 'u_steel_ball_motion' not in top,'legacy motor/motion instantiated')
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
report={'status':'SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_HOLD_TEST','date':'2026-10-24',
 'device':'PH1P35MDG324','bit':str(bit),'delivery_bit':str(bit),'sha256':sha(bit),'physical_test':'PENDING_USER_BOARD_TEST',
 'automatic_motion':{'continuous_PD':True,'manual_K2_snapshot':True,'explicit_software_reference_return':True,'K2_required_to_start':True,'automatic_resume':False,'automatic_homing':False},
 'direction':{'human_confirmed':'2026-10-23: current correction direction confirmed correct; normal bit7=0 in latest capture','P_delta_human':'not recalled; user authorized log default','default':'normal, confirmed by user; preserved bit7=0, still configurable','physical_dynamic_calibration':False},
 'parent_large60_bit_sha256':follow_lineage['parent_bit_sha256'],'parent_large60_archive':str(follow_archive),
 'parent_observations':'large60 logs show finite moves, not measured ball-loop stability or complete mechanical calibration',
 'flash_cold_boot':'not tested; SRAM bit delivery; no hardware programming performed',
 'motion_bounds':{'target_counts':[-60,60],'manual_deadband_counts':2,'follow_deadband_counts':1,'active_burst_pulse_budget':64,'active_burst_timeout_seconds':5,'no_response_pulses':3,'wrong_direction_observations':2,'net_command_limit_pulses':64,'feedback_limit_counts':64,'stale_ms':200,'CHECK_retarget_does_not_reset_budget_or_timer':True},
 'control_parameters':{'gain_range':[0,12],'limit_range':[0,60],'damping_range':[0,16],'slew_range':[1,8],'runtime_seconds_range':[0,300],'defaults':{'mode':1,'gain':3,'deadzone':5,'limit':32,'damping':12,'slew':8,'runtime_seconds':60},'control_tick_ms':20,'slew_units':'encoder counts/100ms unchanged; fractional20ms rate accumulator','velocity_format':'signed Q4 pixels/frame; filtered (3*VE + delta*16)/4; delta clipped +/-256','P_V_format_checksum_unchanged':True,'S_config_only':True},
 'K3_center':{'requires_idle_session':True,'center_confirmed_required_for_auto':True,'K1_required':False,'motor_motion':False,'resets_encoder_reference':False,'same_cycle_UART_commit_priority':True,'nonvolatile':False},
 'software_reference':'origin captured once after first K1 enable settles; not a mechanical home or measured platform level',
 'simulations':['retained finite executor with eight latched fault guards','large +60/0/-60/0 at1.28 counts/pulse and production timing; direct cross-end budget fault','K3 capture/reject/collision and coherent wire echo','real camera RX and I2C completion/ROI CDC','full720p detection integration','full automatic session, safe CHECK retarget, K2 held/toggle/stop, manual/return, loss/stale/settings/K1/K4/fault, runtime and no resume','moving targets cannot reset timeout or64pulse budget','three explicitly assumed rolling-ball models with disturbance; no measured physical calibration'],
 'large_target_regression':large_moves,'assumed_plant_cases':plant_cases,
 'plant_limits':'final abs(error)<=80px and abs(velocity)<=1px/frame at28s, with residual oscillation/quantization; not a physical accuracy claim',
 'report_version':5,'wire_UART_bytes':429,'parameter_packet_bytes':20,'camera_packet_bytes':32,'follow_packet_bytes':18,
 'source_manifest':str(root/'build_sources.json'),'baseline_files_frozen':37,'camera_IP_files_byte_identical':len(lineage['unchanged_sources'])-3,
 'executor_lineage':'finite executor byte-identical to archived large60; exact documented external interface/CHECK retarget/auto DB1 and AUTO-only timing mux checked; reference '+motion_lineage['original_position_core_sha256'],
 'camera_defaults':{'exposure':3600,'sensor_gain':143},'ROI':'1920x1080 host ->1280x720 sensor, existing frame-boundary commit',
 'resources':resources,'timing_ns':times,'STA_coverage_percent':float(re.search(r'STA coverage\s*:\s*([\d.]+)%',timing)[1]),
 'timing_limitations':'original clocks/groups retained; held-data camera mailboxes bounded10ns; positive routed timing is not board validation',
 'routed_pins':routed,'routed_motor_drivers':drivers,'official_pin_reference':str(official),
 'host_tests':[host,smoke],'remaining_camera_IP_undriven_warnings':warnings,'reference_clock_routing_notices':clock_notices,
 'camera_confirmation':'configuration-flow completion, not electrical register/ACK readback',
 'pending_physical':['loss500 false-detection and recovery behavior','new response speed, braking and stability','actual plant tuning and stability','mechanical platform level/calibration','contest performance','power-cycle/Flash persistence']}
report['loss500']={'normal_red_floor':45,'normal_ratio':2,'local_red_floor':35,'local_ratio':1.5,'local_radius_sensor_pixels':48,'local_missing_frames_retained':2,'AUTO_last_good_deadline_ms':500,'any_result_watchdog_ms':200,'manual_start_K3_return_strict':True,'raw_validity_unchanged':True,'executor_source_byte_identical':False,'response_change':'only AUTO setup/settle multiplexing; all guards and manual timings exact','prior_VIS5_bit_sha256':loss_lineage['old_bit_sha256'],'archive':str(loss_archive),'RGB_sim_adapter':'Actual RGB mask+overlay prefix and actual stream_bbox/controller/CDC/AB; unused unconnected legacy CCL tail excluded, as TD trims it'}
report['simulations'] += ['real RGB1280x720 packed5/5/6, threshold floors/ratios, local1/2 recovery and3miss expiry, noise/background/ROI/bad-frame plus CDC/AUTO/AB','exact500ms valid-ball and200ms result watchdog, repeated drops, frozen AT/T, raw invalid429byte UART, strict start/K3/manual/return and stops']
report['response']={'phase_ms':{'AUTO_setup':5,'STEP_high':2.5,'STEP_low':2.5,'AUTO_feedback_wait':10,'AUTO_cycle_nominal':20,'manual_return_setup':20,'manual_return_feedback_wait':50,'manual_return_cycle_nominal':75},'benchmark':response_cases,'fine_target':'ceil outside deadzone,minimum2 then clamp to limit; zero inside DZ','slew_units_unchanged':True,'direction_user_confirmed':True,'prior_loss500_bit_sha256':json.loads(read(root/'response_lineage.json'))['old_bit_sha256'],'archive':json.loads(read(root/'response_lineage.json'))['archive'],'new_physical_tuning_pending':True}
report['simulations'] += ['response real1.28AB with6/12ms latency,>=2x same16count step/reversal improvement,manual return75ms unchanged,all8faults under fast AUTO,fine/deadzone/invert/limit quantization andSL1/SL8 rate compatibility']
report['neutral']={'capture':'accepted idle K3 center_applied samples current absolute P; no motion','default':0,'relative_PD_limit_field':'L applies around control neutral only in AUTO','T_AT_MT_P':'absolute encoder-origin coordinates,hard target +/-60; neutral not a separate wire field','invalid_capture':'outside +/-60 leaves original target origin/history untouched,KC8/RD0/AJ11 prevents AUTO start','encoder_origin_MC_faults_rebased':False,'manual_and_initial_zero_return_unchanged':True,'start_target_sync':'K2 first accepts an in-band request at current P,zero STEP; MT/ME synchronize without rebasing','prior_response_bit_sha256':json.loads(read(root/'neutral_lineage.json'))['old_bit_sha256'],'archive':json.loads(read(root/'neutral_lineage.json'))['archive'],'human_confirmed_mechanical_level_P31_before_K3':True,'human_manual_ball_intervention':True,'physical_new_neutral_pending':True}
report['neutral']['old_response_failure_reproduced']=True
report['neutral']['timing_pipeline']='one50MHz target stage separates PD+neutral from slew; valid cleared on loss/config/K3, no clock relaxation'
report['K3_center']['records_separate_AUTO_control_neutral']=True
report['simulations'] += ['neutral +/-31 fixture via trueAB movement while disabled,re-enable preserves origin,accepted K3 records level,centered K2 emits zeroSTEP,relative +/-16/+/-32,absolute60 clamps,originalMC/origin retained,K3busy rejection,K2/K4,no resume,signed429byte actualUART; invalid +/-63 KC8/RD0/AJ11']
report['pending_physical']=['new neutral reference behavior and ball-center recovery','unassisted plant tuning/stability; prior trace manually disturbed','mechanical platform level/calibration','contest performance','power-cycle/Flash persistence']
report['fault_hold']={'F1_F8':'STEP stopped/fault latched,established EN retained','K1':'fault permits release only','K4_reset':'release','new_physical_test':'PENDING','archive':str(__import__('cascade_contract').archive)}
(root/'verification_hold.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['status','sha256','resources','timing_ns','STA_coverage_percent']},indent=2))
