from pathlib import Path
import json
r=Path(__file__).resolve().parent
read=lambda p:p.read_text(encoding='utf-8-sig')
p=r/'host/cascade_controls.ps1';s=read(p)
s=s.replace("TabPage('标定 / 新串级')","TabPage('标定工具')")
anchor='$script:lastCascade=$null;$script:cascadeSequence=0;'
prefix='''# Everyday operation has no tuning controls or automatic serial commands.
$cameraTab.Text='画面';$controlTab.Text='高级'
$simpleTab=New-Object Windows.Forms.TabPage('日常操作');$leftTabs.TabPages.Insert(0,$simpleTab);$leftTabs.SelectedIndex=0
$simpleHelp=New-Object Windows.Forms.Label;$simpleHelp.Font=New-Object Drawing.Font('Microsoft YaHei UI',13)
$simpleHelp.Text="① K1：使能电机`r`n`r`n② 调平、放球到中心`r`n    按 K3 记录中心`r`n`r`n③ 按 K2：持续送回中心`r`n    到中心后继续保持`r`n`r`n再按 K2：停止、保持锁定"
$simpleHelp.SetBounds(15,20,285,340);$simpleTab.Controls.Add($simpleHelp)
$simpleState=New-Object Windows.Forms.Label;$simpleState.SetBounds(15,380,285,120);$simpleState.Text='未连接。参数已内置easy.bit，无需操作标定工具。';$simpleTab.Controls.Add($simpleState)
$simpleNote=New-Object Windows.Forms.Label;$simpleNote.SetBounds(15,530,285,170)
$simpleNote.Text="运行中不用扶球；左右轻推后松手观察回中。`r`n`r`n持续丢球、限位或故障仍会停步。K4会释放使能。`r`n`r`n曝光和蓝框调节在“画面”页。"
$simpleTab.Controls.Add($simpleNote)
'''
assert anchor in s;s=s.replace(anchor,prefix+anchor)
anchor=' $script:lastCascade=$D\n'
new=''' $script:lastCascade=$D
 $live=if($D.flags -band 4){'正在持续回中 / 保持'}elseif($D.fault -ne 0){'故障停步（不能反复重试）'}elseif(!($D.flags -band 2)){'先按K1使能'}elseif(!($D.flags -band 128)){'放球到中心，按K3'}elseif(!($D.flags -band 8)){'等待真实有效识别'}else{'已准备，按K2开始回中'}
 $simpleState.Text=$live+"`r`n"+('球偏差：{0} 像素' -f ([int]$D.x-[int]$D.center))+"`r`n"+('电机位置：{0}；故障：{1}' -f $D.position,$D.fault)
'''
assert anchor in s;s=s.replace(anchor,new);p.write_text(s,encoding='utf-8-sig')
p=r/'host/vision_panel_cn.ps1';s=read(p).replace('默认G3/DZ5/幅度32/SL8，60秒。K3同时记录控制中立位；不重置编码器原点。','日常无需操作此页。easy版死区3、幅度32、会话不限时；控制增益已内置。')
s=s.replace('填入新版默认：G3 / 死区5 / 限幅32','高级：填入死区3 / 限幅32')
s=s.replace('$gain.Value=3;$deadzone.Value=5;$limit.Value=32','$gain.Value=3;$deadzone.Value=3;$limit.Value=32')
s=s.replace('$script:lastCascade=$null;$script:cascadePending=$null;',"if($simpleState){$simpleState.Text='未连接。参数已内置easy.bit，无需操作标定工具。'};$script:lastCascade=$null;$script:cascadePending=$null;")
p.write_text(s,encoding='utf-8-sig')
p=r/'verify.py';s=read(p).replace("bit=out/f'{name}_cascade.bit'","bit=out/f'{name}_easy.bit'")
s=s.replace("'tb_cascade_plant':'CASCADE_PLANT_ALL_PASS'}","'tb_cascade_plant':'CASCADE_PLANT_ALL_PASS','tb_easy':'EASY_ALL_PASS','tb_easy_plant':'EASY_PLANT_ALL_PASS'}")
s=s.replace("'SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_CASCADE_CALIBRATION'","'SOFTWARE_BUILD_PASS_AWAITING_PHYSICAL_EASY_TEST'")
s=s.replace("'PENDING_HUMAN_K2_CALIBRATION_AND_REAL_LOGS'","'PENDING_K3_K2_REAL_RETURN_AND_LOGS'")
s=s.replace('RU0,CASCADE_DEFAULT1 unqualified;physicalK2 cannot start continuous before checked C model','RU0,CASCADE_DEFAULT1/CASCADE_PRESET1;K1 enable,K3 center,K2 continuous return;no host calibration prerequisite')
s=s.replace("execute(sys.executable,'record_contract.py');", "from easy_contract import check_easy\ncheck_easy()\nexecute(sys.executable,'record_contract.py');",1)
s=s.replace("report={'status':", "require('EASY_HOLD_PASS 61s' in read(root/'sim/results/tb_easy.log'),'61s hold absent')\nfor i in [3,4,5]:require(f'CASCADE_PLANT_PASS id={i} ' in read(root/'sim/results/tb_easy_plant.log'),'preset plant absent')\nreport={'status':")
s=s.replace("'startup':'RU0", "'preset':json.loads(read(root/'easy_lineage.json'))['preset'],\n 'startup':'RU0")
p.write_text(s,encoding='utf-8')
print('EASY_HOST_VERIFY_PREPARED')
