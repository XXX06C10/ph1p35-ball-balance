from pathlib import Path
import json,hashlib,difflib
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads(read(R/'brake_precise3_verification.json'))
assert v['status']=='SOFTWARE_ROUTING_PASS_AWAITING_PHYSICAL_BRAKE_PRECISE3'
v['physical_brake_precise3']='PENDING'
v.pop('physical_brake_precise32',None)
v['parked_history']='30 actual valid frames,range<=4px,current filtered speed<=24px/s;only apply tilt at<=8px/s;noise pauses assistance without discarding stable history'
v['restart_slew_counts_s']=40
v['post_restart_braking']='100Hz/160counts_s until precision HOLD, motor within4counts of neutral and ball speed<=12px_s;200Hz highspeed retained'
v['real_clock_recovery']='sim/results/reversal_clock50.log: real50MHz,50000cycles/ms,40msquiet,5msDIR,2.5mspulsehalf;F1/noresponse and responsive reversal'
v['stiction_escape']='after30 parked frames outside35px,8/16/24counts;far32/40/48;10frames perincrement;withdraw above8px_s or range>4px'
v['model_limitation']='All original +/-100px and25px_s model criteria retained. Not all models settle within35px; physical precision pending.'
v['analysis']=json.loads(read(R/'evidence/brake_precise3_measurement/summary.json'))
(R/'brake_precise3_verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
p=R/'精准回中3_测试说明.md';s=read(p)
s=s.replace('位移跨度超4px或速度超过24px/s即撤回脱困','增倾角仅在速度不超过8px/s时生效；较大速度读数暂停增倾角，仍保留稳定位置历史。位移跨度超4px或速度超过24px/s清除脱困计时')
s+='\n## 最终构建\n\n21项当前源码RTL回归、8组动态模型与2组时钟比例交叉复核、实际50MHz恢复时序测试、上位机编解码及新旧面板测试通过。官方PH1P35MDG324器件、76个IO与双口STEP/DIR/EN镜像核对通过。\n\n'
s+=f"SWNS {v['timing_ns']['SWNS']:+.3f}ns，HWNS {v['timing_ns']['HWNS']:+.3f}ns，STNS/HTNS为0。资源{v['resources']}。\n\nbit SHA256：{v['sha256']}\n\n"
s+='未修改模型验收门槛；部分模型最后仍在35px外，模型通过不等于35px停准。实机效果待本次日志确认；未自动烧录。\n'
p.write_text(s,encoding='utf8')
header=f'''# 当前交付：brake_precise3 换向反馈恢复与渐进脱困

用户授权依据215118实测数据修改并交付新bit。原precise2存在CHECK SP1死锁的RTL复现：反向要求pending0，原向1～2步无反馈不足F1。新REGION_FAST专用REVERSAL_RECOVERY在40ms真实静默后补有限原方向脉冲，用真实反馈解除等待或累计3步F1；不重置pending/MC/origin/fault/64步5秒。保持所有公共/手动保护、硬工作范围、引脚时钟和旧协议。D2保留bit15用于恢复等待/MS10诊断。停滞30帧位置跨度≤4px，增倾角仅速度≤8px/s；8/16/24近区，远区逐级48，40counts/s建立，运动后100Hz/160counts/s撤倾。±35入口/±70退出，高速200Hz，全−16/+32不变。21项回归、8模型、2时钟比例及实际50MHz恢复通过；模型门槛±100px/25px_s，不保证实际35px。PH1P35MDG324与时序通过{v['timing_ns']}。bit SHA256 {v['sha256']}。

当前output/brake_precise3.bit、host/start_brake_precise3.cmd、精准回中3_测试说明.md；只使用verify_brake_precise3.py/finalize_precise3.py/publish_brake_precise3.py。父precise2及归档不可变。未自动烧录，实机待验。以下为历史记录。

'''
for name in ('AGENTS.md','README.md'):
 p=R/name;p.write_text(header+read(p),encoding='utf8')
old=Path(json.loads(read(R/'brake_precise3_lineage.json'))['archive'])/'snapshot'
entries=[];diff=[]
for p in sorted(R.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(R)
 if rel.parts[0] not in ('rtl','host','sim') and len(rel.parts)!=1:continue
 if any(x in ('logs','results','__pycache__') for x in rel.parts) or p.suffix not in ('.v','.py','.ps1','.cmd','.md','.json'):continue
 if p.name in ('brake_precise3_changed_files.json',):continue
 q=old/rel
 if q.exists() and sha(p)==sha(q):continue
 entries.append({'file':rel.as_posix(),'before':sha(q) if q.exists() else None,'after':sha(p)})
 if p.name!='vision_monitor_all.v' and p.stat().st_size<2000000:
  diff.extend(difflib.unified_diff(read(q).splitlines(True) if q.exists() else [],read(p).splitlines(True),fromfile='precise2/'+rel.as_posix(),tofile='precise3/'+rel.as_posix()))
(R/'brake_precise3_changed_files.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf8')
(R/'brake_precise3_changes.diff').write_text(''.join(diff),encoding='utf8')
print('PRECISE3_DOCUMENTED',v['sha256'])
