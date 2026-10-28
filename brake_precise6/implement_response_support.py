"""Prepare response regression fixtures and paired host from immutable sources."""
from pathlib import Path
import json
root=Path(__file__).resolve().parent
archive=Path(json.loads((root/'response_lineage.json').read_text(encoding='utf-8'))['archive'])/'project'
read=lambda p:p.read_text(encoding='utf-8-sig')
write=lambda p,s:p.write_text(s,encoding='utf-8')
legacy='.DEFAULT_DEADZONE(20),.DEFAULT_SLEW(2),.DEFAULT_RUNTIME(30),'
for bench in ['tb_full','tb_center','tb_camera','tb_follow','tb_loss','tb_plant','tb_rgb']:
 s=read(archive/f'sim/{bench}.v')
 s=s.replace('vision_monitor #(', 'vision_monitor #('+legacy,1)
 if bench in ['tb_follow','tb_loss','tb_plant','tb_rgb']:
  s=s.replace('vision_monitor #(', 'vision_monitor #(.DEFAULT_GAIN(4),.DEFAULT_LIMIT(12),',1)
 if bench in ['tb_loss','tb_rgb']:s=s.replace('vision_monitor #(', 'vision_monitor #(.CONTROL_MS(100),',1)
 s=s.replace('.CONTROL_MS(1000)', '.CONTROL_MS(100)')
 write(root/f'sim/{bench}.v',s)
s=read(archive/'run_sim.ps1').replace("'tb_loss','tb_rgb'","'tb_loss','tb_rgb','tb_response'")
write(root/'run_sim.ps1',s)
s=read(archive/'build.ps1').replace('Copy-Item -LiteralPath $bitPath -Destination output/vision_follow_20261022_loss500.bit -Force','Copy-Item -LiteralPath $bitPath -Destination output/vision_follow_20261022_response.bit -Force')
write(root/'build.ps1',s)
# Keep the diagnostic host features and exact protocol functions.
host=Path('D:/AAAProject/FPGA/AAA_LookHere/20261023_纠偏诊断/vision_panel_cn.ps1')
s=read(host)
s=s.replace('PH1P35 纠偏诊断｜当前loss500固件通用｜区分电机到位与球回中','PH1P35 快速纠偏｜20ms外环·AUTO20ms/步｜G3/L32/SL8')
s=s.replace('当前bit继续使用。电机到位≠球已回中；先核对纠偏方向。试调按钮仅填值，应用后须重新按K2。K4停机。','配套response新bit；方向保持。K3定球中心→K1使能→K2开始；K4停机。丢球500ms/断流200ms停止。')
s=s.replace("'中心死区（像素）' 618 0 200 20", "'中心死区（像素）' 618 0 200 5")
s=s.replace("'控制衰减档（越大越弱）' 656 0 12 4", "'控制衰减档（越大越弱）' 656 0 12 3")
s=s.replace("'目标限幅（编码器计数）' 694 0 60 12", "'目标限幅（编码器计数）' 694 0 60 32")
s=s.replace("'目标缓变（计数/100ms）' 850 1 8 2", "'目标缓变（计数/100ms）' 850 1 8 8")
s=s.replace("'会话时限秒（0=不限）' 850 0 300 30", "'会话时限秒（0=不限）' 850 0 300 60")
s=s.replace('默认：连续PD，G4 / L12，阻尼12。配置不会启动电机。','默认：G3/DZ5/L32，阻尼12/SL8，60秒。20ms外环；仅连续动作提速。')
s=s.replace('填入试调：G3 / 死区5 / 限幅24','填入新版默认：G3 / 死区5 / 限幅32')
s=s.replace('$gain.Value=3;$deadzone.Value=5;$limit.Value=24','$gain.Value=3;$deadzone.Value=5;$limit.Value=32')
s=s.replace('$slew.Value=4;$runtime.Value=60','$slew.Value=8;$runtime.Value=60')
s=s.replace('先核对方向，再分别应用两组参数；读回后按K2。限幅24约2.11度。','方向已确认，分别应用两组参数；读回后按K2。限幅32约2.81度。')
s=s.replace('$runtime.Value -ne 30','$runtime.Value -ne 60')
s=s.replace('$limit.Value -ne 24','$limit.Value -ne 32')
s=s.replace('当前loss500固件通用','配套response固件')
# Current host includes an additional actual UART_RESPONSE preview fixture;
# do not rerun this one-time migration over the published release.
(root/'host/vision_panel_cn.ps1').write_text(s,encoding='utf-8-sig')
print('Response host/fixtures prepared, P/V/S functions unchanged')
