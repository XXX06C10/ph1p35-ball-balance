"""One-time authorized preset revision, preserving the published cascade package."""
from pathlib import Path
import json,hashlib,shutil,zipfile
r=Path(__file__).resolve().parent
read=lambda p:p.read_text(encoding='utf-8-sig')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive=Path('D:/AAAProject/FPGA/AAA_LookHere/成功版本归档/20261024_一键回中前_cascade')
assert not archive.exists(), 'Already prepared; do not rerun'
archive.mkdir()
bundle=Path('D:/AAAProject/FPGA/AAA_LookHere/VIS5_串级标定_cascade_20261024.zip')
shutil.copy2(bundle,archive/bundle.name)
with zipfile.ZipFile(bundle) as z:
    assert z.testzip() is None
    z.extractall(archive/'published')
for p in (r/'host/logs').glob('20261024_205920_426.*'):
    (archive/'physical').mkdir(exist_ok=True)
    shutil.copy2(p,archive/'physical'/p.name)
manifest={p.relative_to(archive).as_posix():sha(p) for p in archive.rglob('*') if p.is_file()}
(archive/'manifest.json').write_text(json.dumps({'files':manifest},indent=2),encoding='utf-8')
lineage={'archive':str(archive),'parent_bit_sha256':sha(r/'output/vision_follow_20261022_cascade.bit'),
 'user_request':'K3 sets center;K2 continuously returns/holds ball;no manual calibration workflow;keep K1 enable and all fault/motion guards',
 'preset':{'kp':819,'kv':82,'ki':131,'inner_kp':8192,'feedforward':200,'max_hz':100,'slew_rate':102,'delay_ms':20,'polarity':0,'deadzone':3,'relative_limit':32,'runtime':0},
 'physical_gain_identified':False,'basis':'bounded preset previously verified for assumed B=-5 model;physical calibration incomplete;not a guaranteed actual plant model'}
(r/'easy_lineage.json').write_text(json.dumps(lineage,ensure_ascii=False,indent=2),encoding='utf-8')
def edit(rel,old,new):
 p=r/rel;s=read(p);assert old in s,rel+':missing edit';p.write_text(s.replace(old,new),encoding='utf-8-sig' if rel.endswith('.ps1') else 'utf-8')
edit('rtl/vision_cascade_config.v','DEFAULT_SELECTION=0)(','DEFAULT_SELECTION=0,DEFAULT_PRESET=0)(')
edit('rtl/vision_cascade_config.v','output reg diagnostics=0,polarity=0,','output reg diagnostics=DEFAULT_PRESET,polarity=0,')
edit('rtl/vision_cascade_config.v','kp=(DEFAULT_SELECTION==0 ? 512 : 0),kv=(DEFAULT_SELECTION==0 ? 128 : 0),ki=0,inner_kp=8192,feedforward=200,max_hz=50,slew_rate=80,','kp=(DEFAULT_PRESET ? 819 : (DEFAULT_SELECTION==0 ? 512 : 0)),kv=(DEFAULT_PRESET ? 82 : (DEFAULT_SELECTION==0 ? 128 : 0)),ki=(DEFAULT_PRESET ? 131 : 0),inner_kp=8192,feedforward=200,max_hz=(DEFAULT_PRESET ? 100 : 50),slew_rate=(DEFAULT_PRESET ? 102 : 80),')
edit('rtl/vision_cascade_config.v','delay_ms=0,amplitude=4','delay_ms=(DEFAULT_PRESET ? 20 : 0),amplitude=4')
edit('rtl/vision_cascade_config.v','diagnostics<=0;polarity<=0;','diagnostics<=DEFAULT_PRESET;polarity<=0;')
edit('rtl/vision_cascade_config.v','kp<=DEFAULT_SELECTION==0 ? 512 : 0;kv<=DEFAULT_SELECTION==0 ? 128 : 0;ki<=0;bias<=0;inner_kp<=8192;feedforward<=200;max_hz<=50;slew_rate<=80;delay_ms<=0;amplitude<=4;',
 'kp<=DEFAULT_PRESET ? 819 : (DEFAULT_SELECTION==0 ? 512 : 0);kv<=DEFAULT_PRESET ? 82 : (DEFAULT_SELECTION==0 ? 128 : 0);ki<=DEFAULT_PRESET ? 131 : 0;bias<=0;inner_kp<=8192;feedforward<=200;max_hz<=DEFAULT_PRESET ? 100 : 50;slew_rate<=DEFAULT_PRESET ? 102 : 80;delay_ms<=DEFAULT_PRESET ? 20 : 0;amplitude<=4;')
edit('rtl/vision_monitor.v','DEFAULT_RUNTIME=60,CASCADE_DEFAULT=0,','DEFAULT_RUNTIME=60,CASCADE_DEFAULT=0,CASCADE_PRESET=0,')
edit('rtl/vision_monitor.v','reg c_fresh=0,c_profile_ready=0;','reg c_fresh=0,c_profile_ready=CASCADE_PRESET,c_builtin=CASCADE_PRESET;')
edit('rtl/vision_monitor.v','if(!rst_n || applied || center_request || settings_busy)c_profile_ready<=0;\n      else if(c_applied)c_profile_ready<=c_selection==1 && (c_kp!=0 || c_kv!=0);',
 'if(!rst_n)begin c_profile_ready<=CASCADE_PRESET;c_builtin<=CASCADE_PRESET;end\n      else begin\n        if(c_applied)begin c_builtin<=0;c_profile_ready<=c_selection==1 && (c_kp!=0 || c_kv!=0);end\n        else if(applied || center_request || settings_busy)c_profile_ready<=c_builtin;\n      end')
edit('rtl/vision_monitor.v','.DEFAULT_SELECTION(CASCADE_DEFAULT)) cascade_config(','.DEFAULT_SELECTION(CASCADE_DEFAULT),.DEFAULT_PRESET(CASCADE_PRESET)) cascade_config(')
edit('user_source/hdl_source/design_top_wrapper.v','.DEFAULT_RUNTIME(0),.CASCADE_DEFAULT(1))','.DEFAULT_RUNTIME(0),.DEFAULT_DEADZONE(3),.CASCADE_DEFAULT(1),.CASCADE_PRESET(1))')
edit('build.ps1',"ValidateSet('hold','cascade')","ValidateSet('hold','cascade','easy')")
edit('build.ps1',"$Release='hold'","$Release='easy'")
edit('cascade_contract.py',"top=read(before/'user_source/hdl_source/design_top_wrapper.v').replace('vision_monitor u_vision_monitor(', 'vision_monitor #(.DEFAULT_RUNTIME(0),.CASCADE_DEFAULT(1)) u_vision_monitor(')",
 "top=read(before/'user_source/hdl_source/design_top_wrapper.v').replace('vision_monitor u_vision_monitor(', 'vision_monitor #(.DEFAULT_RUNTIME(0),.DEFAULT_DEADZONE(3),.CASCADE_DEFAULT(1),.CASCADE_PRESET(1)) u_vision_monitor(')")
edit('host/vision_panel_cn.ps1',"PH1P35 标定串级控制｜故障停步并保持锁定","PH1P35 一键回中｜K3定中心 · K2持续纠偏")
edit('host/vision_panel_cn.ps1','配套cascade新bit。先调平/放球/K3/K1，再选择标定、回读后K2。保护保持锁定；K4释放。','配套easy新bit：K1先使能，调平放球按K3定中心，按K2持续回中；再按K2停止。无需填写控制参数。')
edit('host/vision_panel_cn.ps1',"618 0 200 5","618 0 200 3")
edit('host/cascade_controls.ps1',"$leftTabs.SelectedIndex=2","$leftTabs.SelectedIndex=0")
edit('host/cascade_controls.ps1',"先支撑机构、加载新bit，再调平/放球/K3/K1。每次选择下列测试后，确认回读，再按板上K2。设置本身不运动。", "日常只用板上按键：K1使能、K3定中心、K2持续回中。下列工具仅供进阶标定，不需要逐项操作。")
edit('host/cascade_controls.ps1','尚未选择标定；配套cascade.bit。故障会停步并保持锁定，K1/K4可释放。','easy.bit已内置回中参数，无需标定即可K3后K2。自定义参数仍可用；故障停步保持。')
edit('host/cascade_controls.ps1',"$names=@('旧控制','已整定串级'","$names=@('旧控制','回中串级（预置/自定义）'")
edit('host/cascade_controls.ps1','等待D1诊断。仅电机到位不代表球已稳定。标定完成后先测试左右小扰动。','等待D1诊断。到中心后仍持续纠偏；球暂时不到中心不会结束会话。限位、丢球与故障仍停步。')
agents=r/'AGENTS.md';agents.write_text('# Easy return preset authorization (2026-10-24)\n\nUser explicitly requests K3 center / K2 persistent return without multi-parameter calibration. Enable bounded built-in cascade preset, retain K1 established enable, all F1-F8 and limits; no fault auto retry. K3 and camera configuration do not invalidate this built-in preset, but fresh-result gating/cancel still applies; explicit C replaces preset and retains prior requalification semantics. Runtime0. No physical success claim. Parent cascade bit/package archived in easy_lineage.json. Only publish_easy.py may publish this revision; do not overwrite prior cascade bit.\n\n'+read(agents),encoding='utf-8')
print(json.dumps(lineage,ensure_ascii=False,indent=2))
