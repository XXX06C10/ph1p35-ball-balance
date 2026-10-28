"""Immutable response snapshot before correcting the AUTO neutral reference."""
from pathlib import Path
import hashlib,json,shutil,zipfile,sys
sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parent;look=Path('D:/AAAProject/FPGA/AAA_LookHere')
archive=look/'成功版本归档/20261023_VIS5_中立位修正前'
assert not archive.exists(),'Never overwrite an archive'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
delivery=json.loads((root/'delivery_manifest.json').read_text(encoding='utf-8-sig'))
for rel,digest in delivery['files'].items():assert sha(root/rel)==digest,rel
archive.mkdir(parents=True)
for rel in list(delivery['files'])+['delivery_manifest.json']:
 dest=archive/'project'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/rel,dest)
log=root/'host/logs/20261023_213642_531.txt'
(archive/'physical').mkdir()
shutil.copy2(log,archive/'physical'/log.name)
shutil.copy2(log.with_suffix('.analysis.json'),archive/'physical'/log.with_suffix('.analysis.json').name)
(archive/'physical/human_feedback.json').write_text(json.dumps({'date':'2026-10-23','before_K2':'Mechanism leveled/neutral before placing ball and K3 capture; trace P=31 while C=1021 ball centered','during_AUTO':'User manually moved/held the ball; do not infer autonomous closed-loop oscillation from this trace','diagnosis':'AUTO absolute PD assumes neutral0 and initially drives P31 toward0; last valid ball error651px, target32 saturated, P31, no faults/AB errors'},ensure_ascii=False,indent=2),encoding='utf-8')
(archive/'恢复说明.md').write_text('旧response bit及源码在project/；SHA256 '+delivery['bit_sha256']+'。恢复开发先将project内容复制到独立、名为vision_follow_20261022的工作目录；勿修改本归档。旧版仍用原K3仅视觉中心、AUTO围绕P0的行为，不能把模型PASS视作实板回中。原故障保护有效；用户新日志显示机械中立P31而非0。',encoding='utf-8')
files={p.relative_to(archive).as_posix():sha(p) for p in archive.rglob('*') if p.is_file()}
(archive/'manifest.json').write_text(json.dumps({'files':files},ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(archive.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
 for p in archive.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(archive))
with zipfile.ZipFile(archive.with_suffix('.zip')) as z:assert z.testzip() is None
(root/'neutral_lineage.json').write_text(json.dumps({'archive':str(archive),'archive_zip':str(archive.with_suffix('.zip')),'old_bit_sha256':delivery['bit_sha256'],'date':'2026-10-23','source_log_sha256':sha(log),'human_confirmed_level_before_K3':True,'human_manual_intervention_during_capture':True,'change':'K3 records AUTO control neutral from current P, without resetting encoder origin/MC/guards. T/AT remain absolute targets; AUTO L becomes deviation limit around neutral, hard target±60 and feedback/MC±64 retained. No movement on K3 or auto restart.'},ensure_ascii=False,indent=2),encoding='utf-8')
agent=root/'AGENTS.md'
agent.write_text('# Authorized neutral-reference correction (2026-10-23)\n\nUser reports failed return to ball center and confirms leveling before K3, manual ball intervention during run. Trace shows levelP31 but AUTO center target0. Fix K3 idle capture to also record a separate AUTO neutral offset; do not reset encoder origin,MC,limits or faults. No motion from K3. Preserve normal direction,response timings,all safeguards,raw vision,VIS5 429byte and P/V/S formats. AUTO target is neutral+bounded relative PD, clamped absolute±60; manual/initial-reference return unchanged. K3 outside±60 cannot arm AUTO (new reject11), limits stay absolute±64. Archive neutral_lineage immutable. New paired bit/host/docs/tests required; only new neutral publisher current, no automatic download/Flash. Earlier K3-only-vision restrictions below describe older behavior; new control neutral must be documented distinctly from encoder origin.\n\n'+agent.read_text(encoding='utf-8-sig'),encoding='utf-8')
print('NEUTRAL_BASELINE_ARCHIVED',len(files))
