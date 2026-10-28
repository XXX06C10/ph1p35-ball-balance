"""Read-only analysis of the195545 physical trace; never sends serial commands."""
from pathlib import Path
import sys,json,hashlib,csv,statistics
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'host'))
from asym_protocol import parse_diag,parse_record
p=R/'host/logs/20261026_195545_401.txt';out=R/'analysis_195545';out.mkdir(exist_ok=True)
lines=p.read_text(errors='replace').splitlines()
d=[r for l in lines if (r:=parse_diag(l))];v=[r for l in lines if (r:=parse_record(l))];a=[r for r in d if r['flags']&4];va=[r for r in v if r['AR']]
s=a[0]['time_ms'];N=a[0]['neutral'];anchor=a[0]['limit_anchor'];frames=list({r['frame_ms']:r for r in a if r['flags']&8}.values());first_fault=next(r for r in d if r['fault'])
near=[r for r in frames if abs(r['x']-r['center'])<=100];speeds=sorted(abs(r['velocity_q4']/16) for r in near)
frozen=[]
for r in reversed(a):
 if (r['spent'],r['frequency_hz'],r['command_position'],r['position'],r['reference_q8'])!=(48,0,8,7,3104):break
 frozen.append(r)
examples=[]
for t in [3.56,15.98,28.211,31.698,40.58]:
 r=min(frames,key=lambda r:abs((r['time_ms']-s)/1000-t));angle=(r['position']-N)*360/4096
 examples.append({'run_seconds':(r['time_ms']-s)/1000,'error_pixels':r['x']-r['center'],'estimated_velocity_pixels_s':r['velocity_q4']/16,'actual_angle_degrees':angle,'reference_angle_degrees':(r['reference_q8']/256-N)*360/4096,'frequency_hz':r['frequency_hz'],'min_return_to_neutral_ms_at50Hz':abs(angle)/(50*1.8/16)*1000,'time_to_move100px_ms_at_reported_speed':100/max(abs(r['velocity_q4']/16),1)*1000})
models={}
for f in (R/'sim/results').glob('region100_plant_*.csv'):
 rows=list(csv.DictReader(f.open()));models[f.name]=max(abs(float(r['velocity_pixels_s'])) for r in rows)
summary={'status':'READ_ONLY_ANALYSIS_NO_NEW_BIT','file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'decoded_D2':len(d),'decoded_VIS6':len(v),'active_duration_seconds':(a[-1]['time_ms']-s)/1000,'center_x':a[0]['center'],'neutral':N,'anchor':anchor,'deadzone_readback_values':sorted(set(r['DZ'] for r in va)),'actual_motor_degrees_relative_K3':[ (min(r['position'] for r in a)-N)*360/4096,(max(r['position'] for r in a)-N)*360/4096],'work_degrees_relative_anchor':[(a[0][k]-anchor)*360/4096 for k in ['work_min','work_max']],'fault_code':first_fault['fault'],'fault_run_seconds':(first_fault['time_ms']-s)/1000,'frozen_run_seconds':(frozen[-1]['time_ms']-s)/1000,'frozen_duration_before_last_active_record_seconds':(frozen[0]['time_ms']-frozen[-1]['time_ms'])/1000,'frozen_state':{'spent':48,'command_position':8,'position':7,'reference_counts':3104/256,'frequency_hz':0},'final_fault_ball_error':first_fault['x']-first_fault['center'],'near100_unique_results':len(near),'near100_estimated_abs_velocity_median_p90_peak':[statistics.median(speeds),speeds[int((len(speeds)-1)*.9)],max(speeds)],'examples':examples,'assumed_model_peak_velocities_pixels_s':models,'checkpoint_residual_candidate':{'sampled_start_position':-40,'sampled_start_command':-32,'end_position':7,'end_command':8,'nominal_counts_per_pulse_used_by_guard':328/256,'estimated_residual_counts':47-40*328/256,'normal_consistency_limit_counts':4,'status':'SUSPECT_ONLY:20ms diagnostics do not expose exact checkpoint anchor/pending/wrong status'},'limits_of_inference':['VIS6/D2 do not uniquely identify bit;DZ100 matches current profile','Manual ball/beam intervention cannot be separated from plant motion','Q4 ball velocity is an estimate, not independently measured','Positive motor angle does not itself name the physical ball-right direction','No physical asymmetric gain fitted; exact checkpoint rejection condition remains to reproduce']}
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
with (out/'trajectory.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.writer(f);w.writerow(['run_s','frame_ms','ball_error_px','estimated_velocity_px_s','actual_angle_deg','reference_angle_deg','command_hz','spent','command_position','fault','flags'])
 for r in d:
  if r['time_ms']<s or r['time_ms']>first_fault['time_ms']+250:continue
  w.writerow([(r['time_ms']-s)/1000,r['frame_ms'],r['x']-r['center'],r['velocity_q4']/16,(r['position']-N)*360/4096,(r['reference_q8']/256-N)*360/4096,r['frequency_hz'],r['spent'],r['command_position'],r['fault'],r['flags']])
report='''# 195545实机日志分析：高速制动受限与检查点停顿

本轮只做日志分析，没有修改RTL、面板或bit。日志、提取轨迹和结论哈希保存在本目录。串口报文不能唯一证明bit身份，DZ=100与当前region100配置相符。

## 结论

这次有明显过冲，但不能仅据此认定“右向角度增益偏大”。有两项独立问题：高速接近中心时执行参考/电机尚未回平，而近区50Hz上限限制回平速度；末段48脉冲检查点没有完成，使电机先停止约4.4秒，之后才触发F4。降低静态微调已经不能解决这两个问题。

## 实测事实

运行47.36秒；中心X784，中立P−1。实际电机相对中立−8.61°～+13.18°，未到−16°/+32°工作边界。报文显示持续有效识别，最终不是角度保护或丢球停机，而是F4活动段超时。开头有串口乱码，两条D2未解析；其余8554条D2和743条VIS6可解析。

中心±100px内232个有效结果的速度估计：绝对值中位507.4px/s、90分位1152.8px/s、峰值1538px/s。这里是控制器估计，不是独立测速；是否有手动扰动无法从该日志判断。

运行15.98秒：球已向右过中心27px，连续帧偏差从−214、−181逐步上升到+110，估计球速1086.3px/s。电机实际角度仍为−2.20°，执行参考为−1.70°，正以50Hz尝试回转。按1.8°/16细分，每脉冲0.1125°，即使连续发步且无其它等待，回到中立也至少约0.39秒；球以该速度移动100px只需约0.092秒。更不包括让球真正减速所需时间。这说明高速制动必须提前，不能等进120px后再受慢速微调约束。

运行31.698秒也出现类似情况：向右过中心71px，估计1477.8px/s，而电机仍为−2.55°、50Hz。不能将这个50Hz与低速稳区的20Hz混为一谈：代码虽在高速时提高到了50Hz，仍不足以迅速撤掉已有倾角。运行40.58秒又出现向右过中心18px、估计1378.9px/s、电机−2.64°的同类轨迹。

## 最后一次停止

运行42.951秒开始，SP=48、MC=8、P=7、执行参考AT=12.125计数、频率=0持续冻结。候选T仍变化、球坐标继续向右；约43秒时球偏差已达数百像素。到47.38秒，F=4、SR=6，故障锁存；此时球偏差+909px。此前连续冻结至少4.409秒。

这与控制器在48脉冲后进入反馈检查点、等待核心结束后再开启下一段的源码逻辑一致。这里不是一直在施加巨大右向角度：最后4.4秒实际角度约+0.70°，但电机没有继续执行新的制动目标。

按检查点前可见样本估算：P从−40到7、MC从−32到8，实测47计数对应净40脉冲，按守卫328/256比率预期51.25，残差−4.25计数，略超普通±4计数一致性门槛。这是检查点被拒绝的具体线索。但20ms采样不能确定精确内部锚点，D2也未输出待确认脉冲/方向错误状态，不能据此宣称已确认唯一根因。需要在仿真中重放段内往返、反馈延迟和残差，检查所有准入条件，不能直接清零累计量或放宽保护。

## 为什么之前模型通过仍不够

当前五组假设模型记录的最高速度分别约18、22、64、247、249px/s；本次中心附近的日志估计速度频繁达到500～1500px/s。已有模型覆盖没有代表这次高速工况。后续必须加入实测量级的高速穿越、方向往返、检查点停顿/反馈偏差，模型通过不能替代这套机构的实测整定。

## 后续修改顺序

1. 先重放并定位48脉冲检查点等待未结束的条件；保留5秒超时、真实反馈核对和故障锁存，不靠延长超时掩盖停顿。
2. 分离低速微调与高速制动：低速100px区域继续柔和保持；高速时在进入中心区域之前按方向、速度和当前杆角提前撤倾角、制动，不能继续统一受50Hz近区上限控制。
3. 再判断左右动力学是否确有差异。记录上位机正负角和球运动方向，不把“球在右边”直接当作“电机正角推右”。只有控制链路连续工作、机械方向明确后，才评估方向增益补偿。
4. 保留用户规定的−16°～+32°工作范围；不重新收小幅度，也不让100px区域成为高速时忽略制动的死区。

具体数值与证据见summary.json及trajectory.csv。此处没有生成新bit，也未声称已经修好实机。
'''
(out/'日志分析.md').write_text(report,encoding='utf-8')
print(json.dumps({k:summary[k] for k in ['status','actual_motor_degrees_relative_K3','fault_run_seconds','frozen_run_seconds','frozen_duration_before_last_active_record_seconds','near100_estimated_abs_velocity_median_p90_peak']},indent=2))
