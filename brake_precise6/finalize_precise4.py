from pathlib import Path
import json,hashlib,difflib
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=json.loads(read(R/'brake_precise4_verification.json'))
assert v['status']=='SOFTWARE_ROUTING_PASS_AWAITING_PHYSICAL_BRAKE_PRECISE4'
v.update(accepted_baseline_commit='d9b9dc415ac109f39bb50d708ca5157c1607d021',accepted_baseline_tag='baseline/brake-precise3-accepted-20261027',accepted_baseline_bit_sha256='4878031b5703a9e0d1f17f36258dfc2e48ecc45594f6fc5443229d185f30fbdb',physical_brake_precise4='PENDING',stiction_escape='30 true frames:rawX range<=8px,position EWMA(alpha1/4,Q4) drift<=2px from frame8 anchor;parked control velocity0;otherwise precise3 unchanged',model_limitation='All original100px/25px_s criteria retained;not all cases within35px;no physical success-rate claim',user_reported_baseline_success_rate='about40percent,qualitative user estimate,not measured from this partial trace',core_and_moving_law='exact accepted precise3 hashes;F1-F8 unchanged')
v['physical_scale']=json.loads(read(R/'host/physical_scale_precise4.json'))
v['physical_scale']['pixels_per_mm']=1431/125
v['physical_scale']['changes_control_center']=False
(R/'brake_precise4_verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
guide=R/'精准回中4_测试说明.md';s=read(guide)
s+=f"\n## 最终构建结果\n\n22项RTL回归、8组动态模型和2组时钟比例交叉复核、上位机及新旧面板检查通过。SWNS {v['timing_ns']['SWNS']:+.3f}ns，HWNS {v['timing_ns']['HWNS']:+.3f}ns，STNS/HTNS为0。器件PH1P35MDG324，原引脚、电气配置与STEP/DIR/EN双口镜像通过。\n\nbit SHA256：{v['sha256']}\n\n资源：{v['resources']}\n"
guide.write_text(s,encoding='utf8')
header=f'''# 当前迭代与固定认可基准：2026-10-27

用户明确认可precise3成功时的停准效果，估计40%成功/60%卡在其他位置，要求以此为基准迭代。固定Git提交d9b9dc415ac109f39bb50d708ca5157c1607d021，标签/分支baseline/brake-precise3-accepted-20261027，bit4878031b5703a9e0d1f17f36258dfc2e48ecc45594f6fc5443229d185f30fbdb；见认可基准_20261027.md。不得覆盖该bit/标签，不要将用户反馈写成全面验收。原仓库无提交，基准通过独立索引创建，保留用户暂存区。

当前候选brake_precise4，仅改变静止资格/速度降噪：原始X30帧范围8px，Q4位置均值(alpha1/4)相对第8帧基准漂移≤2px才确认静止；静止时控制速度为0，真实移动退出。其余执行内核、移动P/D/预判/制动、各级脱困幅度和速度、F1-F8/64步5秒/限位/原始坐标/协议/时钟/引脚与认可基准一致。102218日志中−45px、−210px处坐标仅抖动数像素但估计速度几十px/s，旧脱困反复被撤。日志末尾656.42s有F2，P从0到−19而MC只+2；本版不绕过F2，不能从日志断言外力或硬件原因。22回归和模型/面板/布局布线通过，时序{v['timing_ns']}，bit SHA256 {v['sha256']}；实机成功率改善待新日志，不自动烧录。

用户2026-10-27提供两端球心(262,489)/(1693,513)，跨度约125mm。precise4配套面板已加入X线性毫米读数和端点/几何中点977.5标记；摄像头或缩放改变需重标。K3中心和控制增益不自动替换。

使用output/brake_precise4.bit、host/start_brake_precise4.cmd；核验verify_brake_precise4.py，发布publish_brake_precise4.py。回退precise3。以下为历史记录。

'''
for n in ('AGENTS.md','README.md'):
 p=R/n;p.write_text(header+read(p),encoding='utf8')
old=Path(json.loads(read(R/'brake_precise4_lineage.json'))['archive'])/'snapshot';changes=[];diff=[]
for p in sorted(R.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(R)
 if rel.parts[0] not in ('rtl','host','sim') and len(rel.parts)!=1:continue
 if any(x in ('logs','results','__pycache__') for x in rel.parts) or p.suffix not in ('.v','.py','.ps1','.cmd','.md','.json'):continue
 if p.name=='brake_precise4_changed_files.json':continue
 q=old/rel
 if q.exists() and sha(p)==sha(q):continue
 changes.append({'file':rel.as_posix(),'before':sha(q) if q.exists() else None,'after':sha(p)})
 if p.name!='vision_monitor_all.v' and p.stat().st_size<2000000:diff.extend(difflib.unified_diff(read(q).splitlines(True) if q.exists() else [],read(p).splitlines(True),fromfile='accepted_precise3/'+rel.as_posix(),tofile='precise4/'+rel.as_posix()))
(R/'brake_precise4_changed_files.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf8');(R/'brake_precise4_changes.diff').write_text(''.join(diff),encoding='utf8')
print('PRECISE4_DOCUMENTED',v['sha256'])
