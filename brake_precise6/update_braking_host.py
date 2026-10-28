from pathlib import Path
import json
r=Path(__file__).resolve().parent
p=r/'diagnostic_schema.json';q=json.loads(p.read_text(encoding='utf-8-sig'))
q['reserved_flags_extension']={'11':'predictive builtin control active','10:9':'valid only when bit11=1:0drive,1predictive braking,2fine capture','wire_layout_changed':False}
p.write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf-8')
p=r/'host/vision_panel_cn.ps1';s=p.read_text(encoding='utf-8-sig')
anchor='if($SmokeTest){\n';assert anchor in s
extra='''if($SmokeTest){
 if($leftTabs.SelectedTab -ne $simpleTab){throw '日常操作应为默认页'}
 for($testPhase=0;$testPhase -lt 3;$testPhase++){
  Show-CascadeDiagnostic @{selection=1;flags=(2048 -bor ($testPhase -shl 9) -bor 398);x=960;center=960;position=0;fault=0;sequence=0;neutral=0;reference_q8=0;velocity_q4=0;frequency_hz=0;cal_status=0;cal_phase=0;spent=0}
  if(!$simpleState.Text.Contains(@('加速送回','预判制动','中心微调')[$testPhase])){throw '制动阶段解析错误'}
 }
'''
s=s.replace(anchor,extra)
anchor=' Show-Record (Convert-Record $responseSample) $responseSample'
s=s.replace(anchor," $responseSample=$responseSample.Replace(' DZ=0005 ',' DZ=0003 ').Replace(' L=20 ',' L=3C ').Replace(' RU=003C ',' RU=0000 ')\n"+anchor)
p.write_text(s,encoding='utf-8-sig')
print('BRAKING_HOST_PHASE_TEST_READY')
