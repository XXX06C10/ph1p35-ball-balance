from pathlib import Path
import json
r=Path(__file__).resolve().parent
read=lambda p:p.read_text(encoding='utf-8-sig')
p=r/'rtl/vision_cascade_config.v';s=read(p).replace('DEFAULT_PRESET ? 82','DEFAULT_PRESET ? 40');p.write_text(s,encoding='utf-8')
p=r/'easy_lineage.json';v=json.loads(read(p));v['preset']['kv']=40;v['basis']='bounded initial preset; software scan of B=-5/-10/-20 assumed models; no identified physical model';p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
p=r/'run_sim.ps1';s=read(p).replace("'tb_cascade_plant')","'tb_cascade_plant','tb_easy','tb_easy_plant')");s=s.replace("if($Testbench -in @('tb_detector','tb_rgb'))", "if($Testbench -eq 'tb_easy_plant'){$inputs+='sim/tb_cascade_plant.v'}\n    if($Testbench -in @('tb_detector','tb_rgb'))");p.write_text(s,encoding='utf-8-sig')
s=read(r/'sim/tb_cascade.v').split(' initial begin\n  tick(5);')[0]
s=s.replace('module tb_cascade;','module tb_easy;').replace('.CASCADE_DEFAULT(1))','.CASCADE_DEFAULT(1),.CASCADE_PRESET(1),.DEFAULT_DEADZONE(3))')
s+=''' initial begin
  tick(5);rst=1;tick(2500);
  check(dut.c_kp==819 && dut.c_kv==40 && dut.c_ki==131 && dut.c_max_hz==100 && dut.c_slew==102 && dut.c_delay==20 && dut.deadzone==3 && dut.runtime_seconds==0,"built-in preset defaults");
  check(!en && !dut.auto_run && pulses==0,"no boot motion");
  click(2);check(dut.center_confirmed && dut.c_profile_ready && pulses==0,"K3 records center without erasing built-in profile");
  click(1);check(!dut.auto_run && dut.supervisor_reject==1,"K1 enable still required");
  click(0);wait(dut.ready);click(1);check(dut.auto_run && dut.c_sequence==0,"K3 then K2 starts without any C configuration");
  tick(3050100);check(dut.auto_run && dut.fault==0 && pulses==0 && dut.n_stable,"continuous hold exceeds61s without timeout/arrived stop");
  $display("EASY_HOLD_PASS 61s center hold,zero pulses,no UART configuration");
  bx=1060;wait(dut.position>=8);check(dut.auto_run && dut.fault==0,"right disturbance drives positive correction");
  click(1);check(!dut.auto_run && en,"K2 stop retains enable");
  tick(4000);bx=980;tick(2500);click(2);tick(2500);check(dut.center==980 && dut.c_profile_ready,"second K3 directly rearms preset");
  saved=pulses;click(1);tick(1000);check(dut.auto_run && pulses==saved,"new center starts without initial reference jump");
  confirmed=0;tick(5000);check(dut.auto_run,"short loss keeps session");tick(21000);check(!dut.auto_run && dut.stop_reason==3 && en,"500ms invalid stops/holds");
  confirmed=1;tick(2500);check(!dut.auto_run,"no automatic restart after loss");
  click(1);check(dut.auto_run,"physical K2 resumes on real valid frame");
  keys[3]=0;#1;check(!step && !en,"K4 immediate release");tick(100);keys[3]=1;tick(1000);check(!dut.auto_run && !en,"no K4 replay");
  send_config(40,1,100,4,0);check(!dut.c_builtin && dut.c_profile_ready,"explicit C replaces builtin");
  click(2);tick(2500);check(!dut.c_profile_ready,"custom model still invalidates on K3");
  click(0);wait(dut.ready);click(1);check(!dut.auto_run && dut.supervisor_reject==12,"custom qualification semantics retained");
  check(dut.errors1==0 && dlines>2 && vlines>0,"actual AB and packet UART");
  $display("EASY_ALL_PASS: built-in preset,K3/K2,no C setup,61s center hold,disturbance,K2/K4,500ms loss,explicit C qualification");$finish;
 end
 initial begin #150000000;$fatal(1,"easy timeout F=%d run=%b",dut.fault,dut.auto_run);end
endmodule
'''
(r/'sim/tb_easy.v').write_text(s,encoding='utf-8')
p=r/'sim/tb_cascade_plant.v';s=read(p).replace('POL=0,SLEW=102)','POL=0,SLEW=102,USE_PRESET=0)')
s=s.replace('.CASCADE_DEFAULT(1))','.CASCADE_DEFAULT(1),.CASCADE_PRESET(USE_PRESET),.DEFAULT_DEADZONE(USE_PRESET ? 3 : 5))')
s=s.replace('fault");','fault,spent,completed_count");')
s=s.replace('  payload={8\'d1','  if(!USE_PRESET)begin\n  payload={8\'d1')
s=s.replace('sendbyte(10);tick(2500);click(1);wait(dut.auto_run);','sendbyte(10);tick(2500);\n  end\n  click(1);wait(dut.auto_run);')
p.write_text(s,encoding='utf-8')
(r/'sim/tb_easy_plant.v').write_text('''`timescale 1ns/1ps
module tb_easy_plant;
 wire [2:0] done;
 cascade_plant_case #(.ID(3),.B(-5.0),.USE_PRESET(1)) p0(done[0]);
 cascade_plant_case #(.ID(4),.B(-10.0),.USE_PRESET(1)) p1(done[1]);
 cascade_plant_case #(.ID(5),.B(-20.0),.USE_PRESET(1)) p2(done[2]);
 initial begin wait(&done);$display("EASY_PLANT_ALL_PASS:3assumed plants,same built-in gains,no serial configuration,K3/K2,5s recovery10s hold;physical pending");$finish;end
 initial begin #100000000;$fatal(1,"easy plant timeout %b",done);end
endmodule
''',encoding='utf-8')
print('EASY_TESTS_PREPARED')
