from pathlib import Path
import json,sys
r=Path(__file__).resolve().parent;read=lambda p:p.read_text(encoding='utf-8-sig')
sys.path.insert(0,str(r/'host'));from cascade_protocol import parse_diag
p=r/'rtl/vision_servo_core.v';s=read(p).replace('if(CHECKPOINT_CAPABLE && checkpoint && following && fast_rate_hz==0 && fast_count==0 && checkpoint_consistent)', 'if(CHECKPOINT_CAPABLE && checkpoint && following && visual_target<=TARGET_LIMIT && visual_target>=-TARGET_LIMIT && fast_rate_hz==0 && fast_count==0 && checkpoint_consistent)');p.write_text(s,encoding='utf-8')
# Preserve real timestamps; duplicates of one camera frame are not new measurements.
rows=[q for line in (r/'host/logs/20261024_213354_678.txt').read_text(encoding='utf-8-sig').splitlines() if(q:=parse_diag(line)) and q['flags']&4]
frames=[];seen=set();t0=rows[0]['time_ms']
for q in rows:
 if q['frame_ms'] in seen:continue
 seen.add(q['frame_ms']);frames.append((max(0,q['frame_ms']-t0),q['x']))
(r/'sim/easy2_recorded_frames.mem').write_text(''.join(f'{t:08x}{x:04x}\n' for t,x in frames),encoding='ascii')
(r/'sim/easy2_recorded_frames.json').write_text(json.dumps({'source':'20261024_213354_678.txt','frames':len(frames),'duration_ms':frames[-1][0],'physical_feedback':'simulated1.28count/pulse AB,12ms latency; only camera trajectory is recorded','physical_ball_stability_claim':False},indent=2),encoding='utf-8')
p=r/'sim/tb_easy.v';s=read(p).replace('.DEFAULT_DEADZONE(3))','.DEFAULT_DEADZONE(3),.DEFAULT_LIMIT(48))');p.write_text(s,encoding='utf-8')
p=r/'sim/tb_cascade_plant.v';s=read(p).replace('.DEFAULT_DEADZONE(USE_PRESET ? 3 : 5))','.DEFAULT_DEADZONE(USE_PRESET ? 3 : 5),.DEFAULT_LIMIT(USE_PRESET ? 48 : 32))');p.write_text(s,encoding='utf-8')
# Extra observer test: normal rapid motion no longer repeatedly zeroes the estimate.
p=r/'sim/tb_outer.v';s=read(p);anchor='  $display("OUTER_ALL_PASS:'
insert='''  clear=1;tick(1);clear=0;run=1;x=500;center=960;kp=512;kv=40;result(33);
  for(i=0;i<8;i=i+1)begin x=x+45;result(33);end
  check(vel>8000,"45pixel/frame motion retains velocity estimate instead of repeated reset");
  $display("OUTER_FAST_VELOCITY_PASS Vq4=%0d",vel);
'''
assert anchor in s;s=s.replace(anchor,insert+anchor);p.write_text(s,encoding='utf-8')
# Same recorder/AB fixture runs both the old source and current source.
prefix=read(r/'sim/tb_easy.v').split(' integer dlines=0')[0]
prefix=prefix.replace('module tb_easy;','module replay_case #(parameter OLD=0)(output reg done=0);')
prefix=prefix.replace('.DEFAULT_LIMIT(48)', '.DEFAULT_LIMIT(OLD ? 32 : 48)')
prefix=prefix.replace('if(auto_frames)begin if(fc==1649)begin fc=0;frame<=1;end else fc=fc+1;end','if(auto_frames)begin if(fc==1649)begin fc=0;frame<=1;end else fc=fc+1;end')
prefix=prefix.replace('integer cyc=0,','integer cyc=0,')
body=f'''
 reg [47:0] trajectory[0:{len(frames)-1}];integer idx=0,elapsed=0,j=0,boundaries=0,max_spent=0,old_dc=0;reg replaying=0,prev_busy=0;
 always @(negedge clk)begin
  if(dut.spent>max_spent)max_spent=dut.spent;
  if(replaying)begin
   if(dut.fault!=0 && !OLD)$fatal(1,"REPLAY unexpected F=%0d elapsed=%0d SP=%0d P=%0d",dut.fault,elapsed,dut.spent,dut.position);
   if(dut.n_checkpoint && dut.ready)boundaries=boundaries+1;
  end
 end
 initial begin
  $readmemh("sim/easy2_recorded_frames.mem",trajectory);
  bx=1041;tick(5);rst=1;tick(2500);click(0);wait(dut.ready);click(2);tick(2500);click(1);wait(dut.auto_run);replaying=1;
  for(j=0;j<3;j=j+1)begin
   idx=0;elapsed=0;
   while(elapsed<{frames[-1][0]+40} && dut.fault==0)begin
    while(idx<{len(frames)} && trajectory[idx][47:16]<=elapsed)begin bx=trajectory[idx][15:0];idx=idx+1;end
    tick(50);elapsed=elapsed+1;
   end
  end
  if(OLD)begin check(dut.fault==5 && dut.spent==64,"old version reproduces SP64 F5");$display("REPLAY_OLD_F5_PASS pulses=%0d P=%0d",pulses,dut.position);end
  else begin
   check(dut.auto_run && dut.fault==0 && en && pulses>200 && boundaries>=3 && max_spent<64,"new continuous trajectory crosses200 pulses with verified boundaries");
   $display("REPLAY_NEW_PASS pulses=%0d checkpoints=%0d max_segment=%0d",pulses,boundaries,max_spent);
   wait(dut.cascade_control.quiescing);keys[3]=0;#1;check(!step && !en,"K4 during checkpoint immediate stop");tick(100);keys[3]=1;tick(1000);check(!dut.auto_run && !en,"K4 checkpoint no restart");
  end
  done=1;
 end
endmodule
'''
(r/'sim/tb_replay.v').write_text(prefix+body+'''module tb_replay;
 wire done;replay_case #(.OLD(0)) c(done);
 initial begin wait(done);$display("REPLAY_ALL_PASS");$finish;end
 initial begin #120000000;$fatal(1,"replay timeout");end
endmodule
''',encoding='utf-8')
arch=Path(json.loads(read(r/'easy2_lineage.json'))['archive'])/'published'
shutil_src=next(arch.rglob('rtl/vision_monitor_all.v'))
(r/'sim/replay_old_all.v').write_bytes(shutil_src.read_bytes())
(r/'sim/tb_replay_old.v').write_text('''module tb_replay_old;
 wire done;replay_case #(.OLD(1)) c(done);
 initial begin wait(done);$display("REPLAY_OLD_ALL_PASS");$finish;end
 initial begin #120000000;$fatal(1,"old replay timeout");end
endmodule
''',encoding='utf-8')
p=r/'run_sim.ps1';s=read(p).replace("'tb_easy_plant')","'tb_easy_plant','tb_checkpoint','tb_replay','tb_replay_old')")
anchor="    if($Testbench -eq 'tb_easy_plant')"
s=s.replace(anchor,"    if($Testbench -eq 'tb_replay_old'){$inputs=@('sim/replay_old_all.v','sim/tb_replay.v','sim/tb_replay_old.v')}\n"+anchor)
p.write_text(s,encoding='utf-8-sig')
print('EASY2_TEST_FIXTURES_READY',len(frames))
