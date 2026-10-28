// Display-only one-frame lead. Raw detector coordinates/history/validity never
// pass through this module into motion control or the local weak classifier.
module vision_overlay_lead #(parameter IMG_WIDTH=1280,IMG_HEIGHT=720,MAX_LEAD=24,MAX_DELTA=48)(
 input wire clk,rst_n,sof,frame,valid,confirmed,bad,
 input wire [10:0] x,y,object_left,object_right,object_top,object_bottom,
 input wire [10:0] box_left,box_right,box_top,box_bottom,roi_left,roi_right,roi_top,roi_bottom,
 output reg display_valid=0,lead_active=0,
 output reg [10:0] display_left=0,display_right=0,display_top=0,display_bottom=0
);
 reg previous_valid=0;reg [10:0] previous_x=0,previous_y=0;
 reg signed [11:0] previous_dx=0,previous_dy=0;reg [1:0] starts=3;
 wire signed [11:0] dx=$signed({1'b0,x})-$signed({1'b0,previous_x});
 wire signed [11:0] dy=$signed({1'b0,y})-$signed({1'b0,previous_y});
 wire [11:0] ax=dx<0 ? -dx : dx,ay=dy<0 ? -dy : dy;
 wire [11:0] object_w=object_right>=object_left ? {1'b0,object_right}-{1'b0,object_left}+1'b1 : 12'd0;
 wire [11:0] object_h=object_bottom>=object_top ? {1'b0,object_bottom}-{1'b0,object_top}+1'b1 : 12'd0;
 wire [10:0] cap_x=(object_w>>1)>MAX_LEAD ? MAX_LEAD : (object_w>>1);
 wire [10:0] cap_y=(object_h>>1)>MAX_LEAD ? MAX_LEAD : (object_h>>1);
 wire reversed_x=(dx>2 && previous_dx< -2) || (dx< -2 && previous_dx>2);
 wire reversed_y=(dy>2 && previous_dy< -2) || (dy< -2 && previous_dy>2);
 wire adjacent=starts==1 || (starts==0 && sof);
 wire qualified=valid && confirmed && !bad;
 wire roi_ok=roi_left<=roi_right && roi_top<=roi_bottom && roi_left<IMG_WIDTH && roi_top<IMG_HEIGHT;
 wire predict=qualified && previous_valid && adjacent && roi_ok && ax<=MAX_DELTA && ay<=MAX_DELTA;
 wire signed [11:0] lead_x=predict && ax>2 && !reversed_x ? (dx>$signed({1'b0,cap_x}) ? $signed({1'b0,cap_x}) : (dx< -$signed({1'b0,cap_x}) ? -$signed({1'b0,cap_x}) : dx)) : 12'sd0;
 wire signed [11:0] lead_y=predict && ay>2 && !reversed_y ? (dy>$signed({1'b0,cap_y}) ? $signed({1'b0,cap_y}) : (dy< -$signed({1'b0,cap_y}) ? -$signed({1'b0,cap_y}) : dy)) : 12'sd0;
 wire [10:0] max_x=roi_right>=IMG_WIDTH ? IMG_WIDTH-1 : roi_right;
 wire [10:0] max_y=roi_bottom>=IMG_HEIGHT ? IMG_HEIGHT-1 : roi_bottom;
 // Frame results are sparse; pipeline display math for the112.5MHz
 // pixel clock without delaying video data or adding a frame buffer.
 reg pending_a=0,pending_b=0,valid_a=0,valid_b=0,predict_a=0,predict_b=0;
 reg signed [11:0] lead_x_a=0,lead_y_a=0;
 reg [10:0] left_a=0,right_a=0,top_a=0,bottom_a=0;
 reg [10:0] roi_l_a=0,roi_r_a=0,roi_t_a=0,roi_b_a=0,roi_l_b=0,roi_r_b=0,roi_t_b=0,roi_b_b=0;
 reg signed [12:0] left_b=0,right_b=0,top_b=0,bottom_b=0;
 function [10:0] clip_x;input signed [12:0] v;begin clip_x=v<$signed({1'b0,roi_l_b}) ? roi_l_b : (v>$signed({1'b0,roi_r_b}) ? roi_r_b : v[10:0]);end endfunction
 function [10:0] clip_y;input signed [12:0] v;begin clip_y=v<$signed({1'b0,roi_t_b}) ? roi_t_b : (v>$signed({1'b0,roi_b_b}) ? roi_b_b : v[10:0]);end endfunction
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin previous_valid<=0;previous_x<=0;previous_y<=0;previous_dx<=0;previous_dy<=0;starts<=3;
   display_valid<=0;lead_active<=0;display_left<=0;display_right<=0;display_top<=0;display_bottom<=0;
   pending_a<=0;pending_b<=0;valid_a<=0;valid_b<=0;predict_a<=0;predict_b<=0;lead_x_a<=0;lead_y_a<=0;
   left_a<=0;right_a<=0;top_a<=0;bottom_a<=0;roi_l_a<=0;roi_r_a<=0;roi_t_a<=0;roi_b_a<=0;roi_l_b<=0;roi_r_b<=0;roi_t_b<=0;roi_b_b<=0;
   left_b<=0;right_b<=0;top_b<=0;bottom_b<=0;end
  else begin
   pending_a<=frame;pending_b<=pending_a;
   if(pending_a)begin
    left_b<=$signed({1'b0,left_a})+$signed(lead_x_a);right_b<=$signed({1'b0,right_a})+$signed(lead_x_a);
    top_b<=$signed({1'b0,top_a})+$signed(lead_y_a);bottom_b<=$signed({1'b0,bottom_a})+$signed(lead_y_a);
    valid_b<=valid_a;predict_b<=predict_a;roi_l_b<=roi_l_a;roi_r_b<=roi_r_a;roi_t_b<=roi_t_a;roi_b_b<=roi_b_a;
   end
   if(pending_b)begin
    display_valid<=valid_b;lead_active<=predict_b;
    display_left<=predict_b ? clip_x(left_b) : left_b[10:0];display_right<=predict_b ? clip_x(right_b) : right_b[10:0];
    display_top<=predict_b ? clip_y(top_b) : top_b[10:0];display_bottom<=predict_b ? clip_y(bottom_b) : bottom_b[10:0];
   end
   if(sof && starts<3)starts<=starts+1'b1;
   if(frame)begin
    starts<=0;valid_a<=valid && !bad;predict_a<=predict && (lead_x!=0 || lead_y!=0);
    lead_x_a<=lead_x;lead_y_a<=lead_y;left_a<=box_left;right_a<=box_right;top_a<=box_top;bottom_a<=box_bottom;
    roi_l_a<=roi_left;roi_r_a<=max_x;roi_t_a<=roi_top;roi_b_a<=max_y;
    if(qualified)begin previous_valid<=1;previous_x<=x;previous_y<=y;previous_dx<=previous_valid && adjacent ? dx : 12'sd0;previous_dy<=previous_valid && adjacent ? dy : 12'sd0;end
    else begin previous_valid<=0;previous_dx<=0;previous_dy<=0;end
   end
  end
 end
endmodule
