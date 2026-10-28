from pathlib import Path
import shutil,json,hashlib
r=Path(__file__).resolve().parent;e=r/'evidence/easy3_attempt1_before_final_guards'
assert not e.exists();e.mkdir(parents=True)
for rel in ['build.log','build_sources.json','rtl/vision_cascade_outer.v','rtl/vision_servo_core.v','rtl/vision_monitor.v','output/vision_follow_20261022_easy3.bit','vision_follow_20261022_Runs/phy_1/vision_follow_20261022_phy.ts','vision_follow_20261022_Runs/phy_1/vision_follow_20261022_phy.area']:
 p=r/rel
 if p.exists():q=e/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
(e/'说明.md').write_text('初版预判控制：基础与高速模型通过，综合布线完成；未交付。最终回归发现200Hz换向反馈混合可使检查点等待至F4；另需中心4帧范围噪声抑制，避免快速速度估计放大细小识别抖动。修复后重新构建，不能把此目录的bit当最终交付。',encoding='utf-8')
(e/'manifest.json').write_text(json.dumps({p.relative_to(e).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in e.rglob('*') if p.is_file()},ensure_ascii=False,indent=2),encoding='utf-8')
print('EASY3_ATTEMPT1_SAVED')
