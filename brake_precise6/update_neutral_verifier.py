from pathlib import Path
import json
root=Path(__file__).resolve().parent
before=Path(json.loads((root/'neutral_lineage.json').read_text(encoding='utf-8'))['archive'])/'project'
s=(before/'verify.py').read_text(encoding='utf-8-sig')
s=s.replace('from response_contract import response_servo','from response_contract import response_servo\nimport neutral_contract')
s=s.replace("bit=out/f'{name}_response.bit'","bit=out/f'{name}_neutral.bit'")
s=s.replace("('tb_response','RESPONSE_ALL_PASS')", "('tb_response','RESPONSE_ALL_PASS'),('tb_neutral','NEUTRAL_ALL_PASS')")
s=s.replace('SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_RESPONSE_TEST','SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_NEUTRAL_TEST')
idx=s.index("(out/'simulated_uart_frames.txt').write_text('\\n'.join(wire_lines+camera_lines+center_lines+follow_lines+loss_lines+response_lines)")
checks='''neutral_log=read(root/'sim/results/tb_neutral.log')
old_repro=json.loads(read(root/'before_neutral_reproduction.json'))
require(old_repro['status']=='EXPECTED_OLD_REFERENCE_FAILURE_REPRODUCED','old reference reproduction missing')
require(re.search(r'LEVEL=31 T=\\s*0 AT=\\s*0 P=\\s*31',read(root/'sim/results/before_neutral.log')),'old failure is not the same reference mismatch')
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
'''
s=s[:idx]+checks+s[idx:]
s=s.replace('wire_lines+camera_lines+center_lines+follow_lines+loss_lines+response_lines','wire_lines+camera_lines+center_lines+follow_lines+loss_lines+response_lines+neutral_lines')
idx=s.index("(root/'verification.json').write_text")
extra='''report['neutral']={'capture':'accepted idle K3 center_applied samples current absolute P; no motion','default':0,'relative_PD_limit_field':'L applies around control neutral only in AUTO','T_AT_MT_P':'absolute encoder-origin coordinates,hard target +/-60; neutral not a separate wire field','invalid_capture':'outside +/-60 leaves original target origin/history untouched,KC8/RD0/AJ11 prevents AUTO start','encoder_origin_MC_faults_rebased':False,'manual_and_initial_zero_return_unchanged':True,'start_target_sync':'K2 first accepts an in-band request at current P,zero STEP; MT/ME synchronize without rebasing','prior_response_bit_sha256':json.loads(read(root/'neutral_lineage.json'))['old_bit_sha256'],'archive':json.loads(read(root/'neutral_lineage.json'))['archive'],'human_confirmed_mechanical_level_P31_before_K3':True,'human_manual_ball_intervention':True,'physical_new_neutral_pending':True}
report['neutral']['old_response_failure_reproduced']=True
report['neutral']['timing_pipeline']='one50MHz target stage separates PD+neutral from slew; valid cleared on loss/config/K3, no clock relaxation'
report['K3_center']['records_separate_AUTO_control_neutral']=True
report['simulations'] += ['neutral +/-31 fixture via trueAB movement while disabled,re-enable preserves origin,accepted K3 records level,centered K2 emits zeroSTEP,relative +/-16/+/-32,absolute60 clamps,originalMC/origin retained,K3busy rejection,K2/K4,no resume,signed429byte actualUART; invalid +/-63 KC8/RD0/AJ11']
report['pending_physical']=['new neutral reference behavior and ball-center recovery','unassisted plant tuning/stability; prior trace manually disturbed','mechanical platform level/calibration','contest performance','power-cycle/Flash persistence']
'''
s=s[:idx]+extra+s[idx:]
(root/'verify.py').write_text(s,encoding='utf-8')
print('Neutral verifier includes all inherited checks and nonzero-level regressions')
