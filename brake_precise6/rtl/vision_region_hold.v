// Built-in regional return. Custom C profiles keep their original controller.
// Region entry is position AND velocity; hysteresis prevents pixel hunting.
module vision_region_hold #(parameter WIDE_RANGE=0,NEUTRAL_BITS=8,LIVE_ZONE=0,RECOVER_ASYM=0)(
 input wire clk,rst_n,run,updated,valid,stale,clear,neutral_capture,polarity,
 input wire [10:0] x,input wire [15:0] center,input wire [7:0] limit,
 input wire signed [31:0] velocity_q4,work_min,work_max,input wire signed [NEUTRAL_BITS-1:0] neutral,
 output reg signed [31:0] target_q8=0,output reg changed=0,
 output reg holding=0,output reg [1:0] phase=2,
 output wire [15:0] max_hz,slew_rate,output wire signed [31:0] filtered_velocity_q4,
 input wire [15:0] hold_radius_setting
);
 reg signed [17:0] vh1=0,vh2=0,vh3=0;
 wire signed [19:0] pair_a=$signed(velocity_q4[17:0])+$signed(vh1);
 wire signed [19:0] pair_b=$signed(vh2)+$signed(vh3);
 // Reduce damping delay only in the wide-range controller.
 assign filtered_velocity_q4=WIDE_RANGE && !RECOVER_ASYM ? $signed(pair_a)>>>1 : ($signed(pair_a)+$signed(pair_b))>>>2;
 wire signed [31:0] control_velocity=filtered_velocity_q4;
 wire signed [12:0] error=$signed({1'b0,x})-$signed({1'b0,center});
 wire [12:0] distance=error<0 ? -error : error;
 wire [31:0] speed=control_velocity<0 ? -control_velocity : control_velocity;
 reg [3:0] pipe=0;
 reg signed [31:0] pd_stage=0,raw_stage=0,relative_stage=0,absolute_stage=0;
 reg signed [12:0] trim_stage=0;reg signed [NEUTRAL_BITS-1:0] neutral_stage=0;reg signed [17:0] cap_stage=0;reg hold_stage=0;
 reg [2:0] entry_frames=0;reg [1:0] exit_frames=0;
 reg signed [12:0] trim_q8=0;reg [12:0] range_distance=0;
 // Live P.DZ selects the capture radius; old DZ3 defaults to30pixels.
 wire [15:0] hold_radius=LIVE_ZONE ? (hold_radius_setting<15 ? 16'd30 : (hold_radius_setting>50 ? 16'd50 : hold_radius_setting)) : 16'd15;
 wire [15:0] hold_exit=LIVE_ZONE ? hold_radius+(hold_radius<20 ? 16'd10 : (hold_radius>>1)) : 16'd25;
 wire [15:0] trend_radius=LIVE_ZONE ? hold_radius+5 : 16'd20;
 wire [15:0] escape_radius=LIVE_ZONE ? (hold_radius<<1)+15 : 16'd45;
 wire enter_now=distance<=hold_radius && speed<=(LIVE_ZONE ? 64 : (WIDE_RANGE ? 128 : 240));
 wire outward=(error>0 && control_velocity>0) || (error<0 && control_velocity<0);
 wire exit_now=distance>hold_exit || speed>960 || (WIDE_RANGE && distance>=trend_radius && outward && speed>=128);
 wire leaving=holding && (distance>escape_radius || (exit_now && exit_frames>=1));
 wire entering=!holding && enter_now && entry_frames>=2;
 // Pixel position gains:1/4 far,1/8 mid,1/16 near. Velocity damping is
 //3/8,1/4,3/16 count/(pixel/s). No identified physical model is claimed.
 wire signed [23:0] proportional=distance>96 ? $signed(error)*24'sd64 : (distance>32 ? $signed(error)*24'sd32 : $signed(error)*24'sd16);
 wire signed [31:0] derivative=distance>96 ? $signed(control_velocity)*32'sd6 : (distance>32 ? $signed(control_velocity)*32'sd4 : $signed(control_velocity)*32'sd3);
 // Blend existing gains around32/96pixels; one pixel must not double gain.
 wire [6:0] p_gain=distance<=24 ? 7'd16 : (distance<40 ? distance-8 : (distance<=80 ? 7'd32 : (distance<112 ? distance-48 : 7'd64)));
 wire [6:0] d_gain_q4=distance<=24 ? 7'd48 : (distance<40 ? distance+24 : (distance<=80 ? 7'd64 : (distance<112 ? distance-16 : 7'd96)));
 // Smooth8pixel/s deadband for fine adjustment, retaining real coordinates
 // and the original15/25pixel holding hysteresis.
 wire [7:0] fine_deadband=distance<=24 ? 8'd128 : (distance<40 ? (40-distance)*8 : 0);
 wire signed [17:0] fine_velocity=control_velocity>$signed({1'b0,fine_deadband}) ? control_velocity-$signed({1'b0,fine_deadband}) : (control_velocity< -$signed({1'b0,fine_deadband}) ? control_velocity+$signed({1'b0,fine_deadband}) : 0);
 wire signed [20:0] smooth_p=$signed(error)*$signed({1'b0,p_gain});
 wire signed [25:0] smooth_d_product=$signed(fine_velocity)*$signed({1'b0,d_gain_q4});
 wire signed [31:0] smooth_d=$signed(smooth_d_product)>>>(LIVE_ZONE ? 5 : 4);
 wire signed [31:0] pd_sum=WIDE_RANGE && !RECOVER_ASYM ? $signed(smooth_p)+smooth_d : proportional+derivative;
 wire signed [31:0] pd=polarity ? -pd_sum : pd_sum;
 wire signed [31:0] raw_relative=(holding && !leaving) || entering ? trim_q8 : pd+$signed(trim_q8);
 wire signed [17:0] cap=$signed({1'b0,limit,8'b0});
 wire signed [31:0] relative=raw_relative>cap ? cap : (raw_relative< -cap ? -cap : raw_relative);
 wire signed [31:0] absolute=$signed(neutral)*256+relative;
 wire signed [31:0] bounded=absolute>15360 ? 15360 : (absolute< -15360 ? -15360 : absolute);
 wire signed [12:0] trim_next=trim_q8+((error>0)^polarity ? 13'sd8 : -13'sd8);
 reg fast_motion=0;reg [1:0] slow_frames=0;
 // A fast ball needs full actuator authority even near the center. Lower the
 // cap only after two slow valid results, avoiding speed-cap chatter.
 assign max_hz=WIDE_RANGE && !RECOVER_ASYM && fast_motion && !holding ? 16'd200 : (holding || range_distance<=64 ? 16'd50 : (range_distance<=128 ? 16'd100 : 16'd200));
 assign slew_rate=WIDE_RANGE && !RECOVER_ASYM && fast_motion && !holding ? 16'd200 : (holding || range_distance<=64 ? 16'd80 : (range_distance<=128 ? 16'd100 : 16'd160));
 always @(posedge clk)begin
  if(!rst_n || !run || !valid || stale || clear || neutral_capture)begin fast_motion<=0;slow_frames<=0;end
  else if(updated && WIDE_RANGE)begin
   if(speed>=960)begin fast_motion<=1;slow_frames<=0;end
   else if(speed<=480)begin
    if(slow_frames<2)slow_frames<=slow_frames+1'b1;
    if(slow_frames>=1)fast_motion<=0;
   end else slow_frames<=0;
  end
 end
 always @(posedge clk)begin
  if(!rst_n)begin target_q8<=0;changed<=0;holding<=0;phase<=2;entry_frames<=0;exit_frames<=0;trim_q8<=0;vh1<=0;vh2<=0;vh3<=0;range_distance<=0;pipe<=0;pd_stage<=0;raw_stage<=0;relative_stage<=0;absolute_stage<=0;trim_stage<=0;neutral_stage<=0;cap_stage<=0;hold_stage<=0;end
  else begin
   changed<=0;pipe<={pipe[2:0],updated && run && valid && !stale};
   if(pipe[0])raw_stage<=hold_stage ? $signed(trim_stage) : pd_stage+$signed(trim_stage);
   if(pipe[1])relative_stage<=WIDE_RANGE ? raw_stage : (raw_stage>cap_stage ? cap_stage : (raw_stage< -cap_stage ? -cap_stage : raw_stage));
   if(pipe[2])absolute_stage<=$signed(neutral_stage)*256+relative_stage;
   if(pipe[3] && run && valid && !stale)begin target_q8<=absolute_stage>(WIDE_RANGE ? work_max*256 : 15360) ? (WIDE_RANGE ? work_max*256 : 15360) : (absolute_stage<(WIDE_RANGE ? work_min*256 : -15360) ? (WIDE_RANGE ? work_min*256 : -15360) : absolute_stage);changed<=1;end
   if(updated && run && valid && !stale && !clear && !neutral_capture)begin
    vh1<=velocity_q4[17:0];vh2<=vh1;vh3<=vh2;
    pd_stage<=pd;trim_stage<=trim_q8;neutral_stage<=neutral;cap_stage<=cap;hold_stage<=(holding && !leaving) || entering;range_distance<=distance;
    if(!holding)begin
     exit_frames<=0;
     if(enter_now)begin if(entry_frames<3)entry_frames<=entry_frames+1'b1;end else entry_frames<=0;
     if(entering)begin holding<=1;entry_frames<=0;phase<=3;end
     else if((error>0 && control_velocity<0) || (error<0 && control_velocity>0))phase<=1;
     else phase<=distance<=64 ? 2 : 0;
     // K3 is the trusted level. Without measured beam dynamics, position
     // error alone must not teach a tilted "neutral" that rolls the ball away.
     trim_q8<=0;
    end else begin
     entry_frames<=0;phase<=3;
     if(exit_now)begin if(exit_frames<2)exit_frames<=exit_frames+1'b1;end else exit_frames<=0;
     if(leaving)begin holding<=0;exit_frames<=0;phase<=2;end
    end
   end
   if(!valid || stale)begin vh1<=0;vh2<=0;vh3<=0;pipe<=0;entry_frames<=0;exit_frames<=0;end
   if(!run)begin vh1<=0;vh2<=0;vh3<=0;pipe<=0;holding<=0;phase<=2;entry_frames<=0;exit_frames<=0;end
   if(clear || neutral_capture)begin vh1<=0;vh2<=0;vh3<=0;pipe<=0;target_q8<=$signed(neutral)*256;holding<=0;phase<=2;entry_frames<=0;exit_frames<=0;trim_q8<=0;changed<=0;end
  end
 end
endmodule
