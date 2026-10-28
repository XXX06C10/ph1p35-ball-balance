from pathlib import Path
import json
root=Path(__file__).resolve().parent
snapshot=Path(json.loads((root/'response_lineage.json').read_text(encoding='utf-8'))['archive'])/'project'
s=(snapshot/'verify.py').read_text(encoding='utf-8-sig')
s=s.replace('from decode_serial import parse_record','from decode_serial import parse_record\nfrom response_contract import response_servo')
s=s.replace("bit=out/f'{name}_loss500.bit'","bit=out/f'{name}_response.bit'")
s=s.replace("['rtl/vision_servo_core.v','rtl/vision_move_core.v'", "['rtl/vision_move_core.v'",1).replace("'rtl/vision_config_rx.v',",'',1)
s=s.replace("==expected_servo,'servo changed", "==response_servo(expected_servo),'servo changed")
s=s.replace("('tb_rgb','RGB_INTEGRATION_PASS')", "('tb_rgb','RGB_INTEGRATION_PASS'),('tb_response','RESPONSE_ALL_PASS')")
anchor="(out/'simulated_uart_frames.txt').write_text"
idx=s.index(anchor)
checks='''response_log=read(root/'sim/results/tb_response.log')
require('RESPONSE_ARITHMETIC_PASS' in response_log,'fine/rate arithmetic absent')
for code in range(1,9):require(f'PASS fast fault {code}:' in response_log,'fast AUTO guard absent: '+str(code))
response_cases=[dict(zip(['fast','feedback_delay_ms','forward_ms','reverse_ms','pulses','manual_return_pulses'],map(int,m))) for m in re.findall(r'RESPONSE_MOTION_PASS FAST=(\\d+) delay_ms=(\\d+) forward_ms=(\\d+) reverse_ms=(\\d+) pulses=(\\d+) manual_pulses=(\\d+)',response_log)]
old_cases=[c for c in response_cases if not c['fast']];new_cases=[c for c in response_cases if c['fast']]
require(len(old_cases)==1 and len(new_cases)==2,'response timing cases incomplete')
require(all(c['forward_ms']*2<old_cases[0]['forward_ms'] and c['reverse_ms']*2<old_cases[0]['reverse_ms'] and c['manual_return_pulses']>=8 for c in new_cases),'response benchmark/manual path failed')
require(any(c['feedback_delay_ms']==12 for c in new_cases),'delayed trueAB evidence absent')
response_lines=[line.split(' ',1)[1] for line in response_log.splitlines() if line.startswith('UART_RESPONSE ')]
response_rows=[parse_record(line) for line in response_lines]
require(len(response_rows)==2 and all(response_rows) and all(len(line)+2==429 for line in response_lines),'response UART missing/format changed')
for row in response_rows:
 for key,value in {'G':3,'DZ':5,'L':32,'SL':8,'RU':60,'AR':1,'F':0,'X1':0}.items():require(row[key]==value,'response defaults/wire mismatch: '+key)
'''
s=s[:idx]+checks+s[idx:]
s=s.replace('wire_lines+camera_lines+center_lines+follow_lines+loss_lines','wire_lines+camera_lines+center_lines+follow_lines+loss_lines+response_lines')
s=s.replace('SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_LOSS500_TEST','SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_RESPONSE_TEST')
s=s.replace("'date':'2026-10-22'","'date':'2026-10-23'")
s=s.replace("'human_confirmed':'motor down -> ball right'","'human_confirmed':'2026-10-23: current correction direction confirmed correct; normal bit7=0 in latest capture'")
s=s.replace("'default':'normal, positive P reference tilt assumed to move ball left, from log trend; configurable P gain bit7'","'default':'normal, confirmed by user; preserved bit7=0, still configurable'")
s=s.replace("'gain':4,'limit':12,'damping':12,'slew':2,'runtime_seconds':30", "'gain':3,'deadzone':5,'limit':32,'damping':12,'slew':8,'runtime_seconds':60")
s=s.replace("'control_tick_ms':100", "'control_tick_ms':20,'slew_units':'encoder counts/100ms unchanged; fractional20ms rate accumulator'")
s=s.replace("'executor_source_byte_identical':True", "'executor_source_byte_identical':False,'response_change':'only AUTO setup/settle multiplexing; all guards and manual timings exact'")
s=s.replace("'correction direction check'", "'new response speed, braking and stability'")
s=s.replace("exact documented external interface/CHECK retarget/auto DB1 adaptation checked", "exact documented external interface/CHECK retarget/auto DB1 and AUTO-only timing mux checked")
idx=s.index("(root/'verification.json').write_text")
extra='''report['response']={'phase_ms':{'AUTO_setup':5,'STEP_high':2.5,'STEP_low':2.5,'AUTO_feedback_wait':10,'AUTO_cycle_nominal':20,'manual_return_setup':20,'manual_return_feedback_wait':50,'manual_return_cycle_nominal':75},'benchmark':response_cases,'fine_target':'ceil outside deadzone,minimum2 then clamp to limit; zero inside DZ','slew_units_unchanged':True,'direction_user_confirmed':True,'prior_loss500_bit_sha256':json.loads(read(root/'response_lineage.json'))['old_bit_sha256'],'archive':json.loads(read(root/'response_lineage.json'))['archive'],'new_physical_tuning_pending':True}
report['simulations'] += ['response real1.28AB with6/12ms latency,>=2x same16count step/reversal improvement,manual return75ms unchanged,all8faults under fast AUTO,fine/deadzone/invert/limit quantization andSL1/SL8 rate compatibility']
'''
s=s[:idx]+extra+s[idx:]
(root/'verify.py').write_text(s,encoding='utf-8')
print('Response verifier ready with all inherited checks and exact response contract')
