from pathlib import Path
r=Path(__file__).resolve().parent;read=lambda p:p.read_text(encoding='utf-8-sig')
def edit(rel,old,new):
 p=r/rel;s=read(p);assert old in s,rel+' missing';p.write_text(s.replace(old,new),encoding='utf-8')
edit('rtl/vision_servo_core.v',' reg signed [31:0] checkpoint_p=0,checkpoint_m=0;', ''' reg signed [31:0] checkpoint_p=0,checkpoint_m=0;
 // Drain the validated20ms feedback latency before a DIR reversal. The quiet
 // clock runs across segment boundaries; no pending feedback is forgiven.
 reg [31:0] fast_quiet_age=FAST_MS_CYCLES*20;reg fast_step_previous=0;''')
edit('rtl/vision_servo_core.v','checkpoint_p<=0;checkpoint_m<=0;', 'checkpoint_p<=0;checkpoint_m<=0;fast_quiet_age<=FAST_MS_CYCLES*20;fast_step_previous<=0;')
anchor='''  end else begin
   if(!fast_active || !active || !enable_raw || !permit || fault!=0)begin'''
edit('rtl/vision_servo_core.v',anchor,'''  end else begin
   fast_step_previous<=motor_step;
   if(motor_step && !fast_step_previous)fast_quiet_age<=0;
   else if(fast_quiet_age<FAST_MS_CYCLES*20)fast_quiet_age<=fast_quiet_age+1'b1;
   if(!fast_active || !active || !enable_raw || !permit || fault!=0)begin''')
edit('rtl/vision_servo_core.v','fast_positive==dir_r || fast_count==0','fast_positive==dir_r || (fast_count==0 && fast_quiet_age>=FAST_MS_CYCLES*20)')
anchor=' reg signed [17:0] goal_velocity_q4=0;reg [1:0] phase_candidate=2;'
edit('rtl/vision_cascade_outer.v',anchor,anchor+'''
 // Recognize sub-pixel/centroid noise only inside the real center deadband.
 // Four actual frames must fit a4pixel window; fast crossings never qualify.
 reg [10:0] history_x2=0,history_x3=0,window_hi=0,window_lo=0;reg capture_quiet=0;
 wire [10:0] hi_a=x>previous_x ? x : previous_x;
 wire [10:0] hi_b=history_x2>history_x3 ? history_x2 : history_x3;
 wire [10:0] lo_a=x<previous_x ? x : previous_x;
 wire [10:0] lo_b=history_x2<history_x3 ? history_x2 : history_x3;
 wire [10:0] frame_hi=hi_a>hi_b ? hi_a : hi_b;
 wire [10:0] frame_lo=lo_a<lo_b ? lo_a : lo_b;
''')
edit('rtl/vision_cascade_outer.v','phase_candidate<=2;control_phase<=2;', 'phase_candidate<=2;control_phase<=2;history_x2<=0;history_x3<=0;window_hi<=0;window_lo<=0;capture_quiet<=0;')
edit('rtl/vision_cascade_outer.v','previous_x<=x;last_ms<=time_ms;', 'previous_x<=x;history_x2<=previous_x;history_x3<=history_x2;window_hi<=frame_hi;window_lo<=frame_lo;last_ms<=time_ms;')
edit('rtl/vision_cascade_outer.v','if(pipe[0])begin measured_velocity_product<=', "if(pipe[0])begin capture_quiet<=predictive && err<=$signed({1'b0,deadzone}) && err>=-$signed({1'b0,deadzone}) && window_hi-window_lo<=4;measured_velocity_product<=")
edit('rtl/vision_cascade_outer.v','velocity_q4<=innovation_reset ? 0 : (predictive ?', 'velocity_q4<=(innovation_reset || (predictive && capture_quiet)) ? 0 : (predictive ?')
edit('rtl/vision_cascade_outer.v','if(clear || neutral_capture)begin control_phase<=2;', 'if(clear || neutral_capture)begin capture_quiet<=0;history_x2<=x;history_x3<=x;window_hi<=x;window_lo<=x;control_phase<=2;')
p=r/'AGENTS.md';p.write_text('# easy3 final regression refinements\n\nA real replay failure at200Hz showed F4 SP48 with fast_count1,delta0,net ratio-0.9375count: old-direction feedback could cancel a new-direction window. Add only20ms since actual STEP rising edge before DIR reversal;retain all response checks/thresholds and manual/common guard bytes. Do not forgive/clear pending feedback. Center noise:four real frames within4pixels AND current error inside deadzone may zero velocity estimate,prevent derivative jitter;fast crossing does not qualify. Attempt1 evidence saved,not delivered. Rebuild final bit.\n\n'+read(p),encoding='utf-8')
print('BRAKING_FINAL_GUARDS_READY')
