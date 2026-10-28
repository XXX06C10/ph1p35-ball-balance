from pathlib import Path
import json,hashlib,difflib
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads(read(R/'brake_precise5_verification.json'));assert v['status']=='SOFTWARE_ROUTING_PASS_AWAITING_PHYSICAL_BRAKE_PRECISE5'
v.update(accepted_baseline_commit='d9b9dc415ac109f39bb50d708ca5157c1607d021',parent_commit='c6aca5857e336a77aeb4ca74521a9a32be887528',physical_brake_precise5='PENDING',quiet_anchor_rearm='after29 preceding valid frames if mean drift exceeds2px, restart coordinate window and stall dwell',extra_escape_counts={'near':40,'far':48,'step':8,'arrival_error':2,'arrival_fresh_frames':30,'total_near':64,'total_far':96},model_limitation='Assumed plants retain100px/25px_s criteria,not measured physical success rate',physical_scale=json.loads(read(R/'host/physical_scale_precise4.json')))
(R/'brake_precise5_verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
p=R/'精准回中5_测试说明.md';p.write_text(read(p)+f"\n## 最终构建结果\n\n23项RTL回归（含8个假设动态模型、2个时钟比例复核）、上位机与新旧面板检查通过。PH1P35MDG324，原引脚与双口镜像通过。时序{v['timing_ns']}；资源{v['resources']}。\n\nbit SHA256：{v['sha256']}\n\n软件检查通过，实机成功率待测，未自动烧录。\n",encoding='utf8')
header=f'''# 当前迭代precise5：2026-10-27

用户授权根据155804日志修复静止窗口失效及脱困24计数到位后球仍不动。认可基准仍为precise3 Git d9b9dc415ac109f39bb50d708ca5157c1607d021；直接父precise4 Git c6aca5857e336a77aeb4ca74521a9a32be887528已归档，不覆盖旧bit或标签。

precise5仅改vision_region100：静止窗口30帧后均值漂移超过2px则重新累计；保留初始8/16/24近区、最高48远区，初始阶段完成且电机距目标≤2计数、球仍静止时，连续30新视觉帧后增加8计数，近区最高64/远区96。运动退出或失效/断流/停机/K3清除新增状态。正常移动P/D/预判/速度/±35保持±70退出、内环及F1-F8/限位/预算/引脚时钟均冻结。相同毫米标定与K3语义。不得把电机到位当作球回中；上限仍不能克服静摩擦的情况仍可能存在，不无限加力。

23项RTL回归、模型与面板/布局布线通过。时序{v['timing_ns']}，bit SHA256 {v['sha256']}。仅软件通过，实机待测，不自动烧录。使用output/brake_precise5.bit和host/start_brake_precise5.cmd，verify_brake_precise5.py/publish_brake_precise5.py为本轮工具。以下历史。

'''
for n in ['AGENTS.md','README.md']:
 p=R/n;p.write_text(header+read(p),encoding='utf8')
old=Path(json.loads(read(R/'brake_precise5_lineage.json'))['archive'])/'snapshot';changes=[];diff=[]
for p in sorted(R.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(R)
 if rel.parts[0] not in ('rtl','host','sim') and len(rel.parts)!=1:continue
 if any(x in ('logs','results','__pycache__') for x in rel.parts) or p.suffix not in ('.v','.py','.ps1','.cmd','.md','.json'):continue
 if p.name=='brake_precise5_changed_files.json':continue
 q=old/rel
 if q.exists() and sha(p)==sha(q):continue
 changes.append({'file':rel.as_posix(),'before':sha(q) if q.exists() else None,'after':sha(p)})
 if p.name!='vision_monitor_all.v' and p.stat().st_size<2000000:diff.extend(difflib.unified_diff(read(q).splitlines(True) if q.exists() else [],read(p).splitlines(True),fromfile='precise4/'+rel.as_posix(),tofile='precise5/'+rel.as_posix()))
(R/'brake_precise5_changed_files.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf8');(R/'brake_precise5_changes.diff').write_text(''.join(diff),encoding='utf8')
print('PRECISE5_DOCUMENTED',v['sha256'])
