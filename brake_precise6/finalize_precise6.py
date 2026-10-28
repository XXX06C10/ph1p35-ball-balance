from pathlib import Path
import json,hashlib,difflib
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads(read(R/'brake_precise6_verification.json'));assert v['status']=='SOFTWARE_ROUTING_PASS_AWAITING_PHYSICAL_BRAKE_PRECISE6'
v.update(accepted_baseline_commit='d9b9dc415ac109f39bb50d708ca5157c1607d021',parent_commit='7351ea595865f90f68caaf37781fb5541ff0508c',physical_brake_precise6='PENDING',quiet_anchor_rearm='after29 preceding valid frames if mean drift exceeds2px, restart coordinate window and stall dwell',extra_escape_counts={'near':40,'far':48,'step':8,'arrival_error':2,'arrival_fresh_frames':30,'total_near':64,'total_far':96},model_limitation='Assumed plants retain100px/25px_s criteria,not measured physical success rate',physical_scale=json.loads(read(R/'host/physical_scale_precise4.json')))
v.update(acquired_escape_release={'requires_bidirectional_samples_each':2,'requires_window_raw_velocity_over_pixels_s':24,'raw_displacement_px':12,'mean_displacement_px':3,'same_direction_raw_px':6,'requalify_after_motion':True},coordinate_replay={'source_window_ms':[120000,126000],'new_assist_frames':133,'parent_assist_frames':62,'limitation':'recorded coordinates,derived30fps velocity,ideal motor arrival;not physical outcome'})
(R/'brake_precise6_verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
p=R/'精准回中6_测试说明.md';p.write_text(read(p)+f"\n## 最终构建结果\n\n24项RTL回归（含8个假设动态模型、2个时钟比例复核）、上位机与新旧面板检查通过。PH1P35MDG324，原引脚与双口镜像通过。时序{v['timing_ns']}；资源{v['resources']}。\n\nbit SHA256：{v['sha256']}\n\n软件检查通过，实机成功率待测，未自动烧录。\n",encoding='utf8')
header=f'''# 当前迭代precise6：2026-10-27

用户反馈precise5成功率提高，要求继续按211211日志优化。直接父7351ea595865f90f68caaf37781fb5541ff0508c；认可precise3基准d9b9dc415ac109f39bb50d708ca5157c1607d021不变。旧bit/标签/面板归档保留。

本次确认主要停滞在保持区外，抖动导致脱困反复撤回；不是HOLD宽度的主要证据。只在取得原静止资格且稳定坐标历史中正负各至少2次超过24px/s原速度估计后维持脱困：固定本次原始X/均值参考，raw位移>12px或mean位移>3px且同向raw>6px退出，真实运动优先且清除旧静止累计，丢球/断流/停止/K3/进入35px亦清除。保持连续均值滤波。其余precise5各级幅度/到位后30帧加级/64和96上限、正常移动/35-70HOLD/全部内核保护/限位/IO时钟协议不变。新日志开头已有F2，重启后169.660秒新F2；不绕过故障，也不以日志推断硬件原因。

24项RTL回归、模型与面板/器件引脚/布局布线通过，时序{v['timing_ns']}，bit SHA256 {v['sha256']}。坐标回放脱困有效帧133对62，只是策略测试，实机成功率待测。使用output/brake_precise6.bit、host/start_brake_precise6.cmd，verify_brake_precise6.py与publish_brake_precise6.py为当前工具。不自动烧录。以下历史。

'''
for n in ['AGENTS.md','README.md']:
 p=R/n;p.write_text(header+read(p),encoding='utf8')
old=Path(json.loads(read(R/'brake_precise6_lineage.json'))['archive'])/'snapshot';changes=[];diff=[]
for p in sorted(R.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(R)
 if rel.parts[0] not in ('rtl','host','sim') and len(rel.parts)!=1:continue
 if any(x in ('logs','results','__pycache__') for x in rel.parts) or p.suffix not in ('.v','.py','.ps1','.cmd','.md','.json'):continue
 if p.name=='brake_precise6_changed_files.json':continue
 q=old/rel
 if q.exists() and sha(p)==sha(q):continue
 changes.append({'file':rel.as_posix(),'before':sha(q) if q.exists() else None,'after':sha(p)})
 if p.name!='vision_monitor_all.v' and p.stat().st_size<2000000:diff.extend(difflib.unified_diff(read(q).splitlines(True) if q.exists() else [],read(p).splitlines(True),fromfile='precise5/'+rel.as_posix(),tofile='precise6/'+rel.as_posix()))
(R/'brake_precise6_changed_files.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf8');(R/'brake_precise6_changes.diff').write_text(''.join(diff),encoding='utf8')
print('PRECISE6_DOCUMENTED',v['sha256'])
