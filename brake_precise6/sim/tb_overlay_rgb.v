`timescale 1ns/1ps
module tb_overlay_rgb;
 localparam W=160,H=64;
 reg clk=0;always #5 clk=~clk;reg rst=0,v=0,sof=0,last=0;reg [127:0] data=0;
 wire [5:0] mask,mask2,mask_old;wire [4:0] meta_old;wire [127:0] old_video;wire ov,ou,oe;wire [4:0] meta,meta2;wire done,ball,bad,box_valid;
 wire [10:0] cx,cy,xmin,xmax,ymin,ymax,bl,br,bt,bb,dl,dr,dt,db;wire dv,leading;
 wire [127:0] base_video,lead_video;wire bv,bu,be,pv,pu,pe;
 steel_ball_detect_before_overlay_fix #(.IMG_WIDTH(W),.IMG_HEIGHT(H),.COLOR_MODE(1),.COLOR_MIN(45),.OVERLAY_EN(1),.OVERLAY_BOX(1),.EXTERNAL_BOX(1),.BOX_COLOR(24'h00FF00),.BOX_THICKNESS(2)) before_fix(
 .I_clk(clk),.I_rst_n(rst),.S_AXIS_tdata(data),.S_AXIS_tvalid(v),.S_AXIS_tuser(sof),.S_AXIS_tlast(last),
 .I_track_valid(1'b0),.I_track_x(11'd0),.I_track_y(11'd0),.I_roi_left(11'd0),.I_roi_right(11'd159),.I_roi_top(11'd0),.I_roi_bottom(11'd63),
 .I_box_valid(box_valid),.I_box_left(bl),.I_box_right(br),.I_box_top(bt),.I_box_bottom(bb),.I_box_confirmed(ball),
 .O_color_mask(mask_old),.O_color_meta(meta_old),.M_AXIS_tdata(old_video),.M_AXIS_tvalid(ov),.M_AXIS_tuser(ou),.M_AXIS_tlast(oe));
 steel_ball_detect #(.IMG_WIDTH(W),.IMG_HEIGHT(H),.COLOR_MODE(1),.COLOR_MIN(45),.OVERLAY_EN(1),.OVERLAY_BOX(1),.EXTERNAL_BOX(1),.BOX_COLOR(24'h00FF00),.BOX_THICKNESS(2)) base(
 .I_clk(clk),.I_rst_n(rst),.S_AXIS_tdata(data),.S_AXIS_tvalid(v),.S_AXIS_tuser(sof),.S_AXIS_tlast(last),
 .I_track_valid(1'b0),.I_track_x(11'd0),.I_track_y(11'd0),.I_roi_left(11'd0),.I_roi_right(11'd159),.I_roi_top(11'd0),.I_roi_bottom(11'd63),
 .I_box_valid(box_valid),.I_box_left(bl),.I_box_right(br),.I_box_top(bt),.I_box_bottom(bb),.I_box_confirmed(ball),
 .O_color_mask(mask),.O_color_meta(meta),.M_AXIS_tdata(base_video),.M_AXIS_tvalid(bv),.M_AXIS_tuser(bu),.M_AXIS_tlast(be));
 steel_ball_detect #(.IMG_WIDTH(W),.IMG_HEIGHT(H),.COLOR_MODE(1),.COLOR_MIN(45),.OVERLAY_EN(1),.OVERLAY_BOX(1),.EXTERNAL_BOX(1),.BOX_COLOR(24'h00FF00),.BOX_THICKNESS(2)) pred(
 .I_clk(clk),.I_rst_n(rst),.S_AXIS_tdata(data),.S_AXIS_tvalid(v),.S_AXIS_tuser(sof),.S_AXIS_tlast(last),
 .I_track_valid(1'b0),.I_track_x(11'd0),.I_track_y(11'd0),.I_roi_left(11'd0),.I_roi_right(11'd159),.I_roi_top(11'd0),.I_roi_bottom(11'd63),
 .I_box_valid(dv),.I_box_left(dl),.I_box_right(dr),.I_box_top(dt),.I_box_bottom(db),.I_box_confirmed(ball),
 .O_color_mask(mask2),.O_color_meta(meta2),.M_AXIS_tdata(lead_video),.M_AXIS_tvalid(pv),.M_AXIS_tuser(pu),.M_AXIS_tlast(pe));
 steel_ball_stream_bbox #(.IMG_WIDTH(W),.IMG_HEIGHT(H),.MIN_AREA(8),.MAX_AREA(1000),.BRIGHT_MIN(8),.CONFIRM_FRAMES(2),.FILL_MIN_PERCENT(15),.FILL_MAX_PERCENT(100),.DOMINANCE_PERCENT(40),.ASPECT_PERCENT(35),.CLUSTER_RADIUS(8),.MAX_JUMP(147),.EDGE_MARGIN(2),.MAX_DIM(60),.MARK_HALF(12),.MARK_AUTO(0),.ROI_EN(1)) detect(
 .I_clk(clk),.I_rst_n(rst),.I_mask(mask),.I_meta(meta),.I_roi_left(11'd0),.I_roi_right(11'd159),.I_roi_top(11'd0),.I_roi_bottom(11'd63),
 .O_frame_done(done),.O_ball_detected(ball),.O_bad_frame(bad),.O_box_valid(box_valid),.O_box_left(bl),.O_box_right(br),.O_box_top(bt),.O_box_bottom(bb),.O_xmin(xmin),.O_xmax(xmax),.O_ymin(ymin),.O_ymax(ymax),.O_ball_x(cx),.O_ball_y(cy));
 vision_overlay_lead #(.IMG_WIDTH(W),.IMG_HEIGHT(H)) lead(.clk(clk),.rst_n(rst),.sof(meta[4]),.frame(done),.valid(box_valid),.confirmed(ball),.bad(bad),.x(cx),.y(cy),.object_left(xmin),.object_right(xmax),.object_top(ymin),.object_bottom(ymax),.box_left(bl),.box_right(br),.box_top(bt),.box_bottom(bb),.roi_left(11'd0),.roi_right(11'd159),.roi_top(11'd0),.roi_bottom(11'd63),.display_valid(dv),.lead_active(leading),.display_left(dl),.display_right(dr),.display_top(dt),.display_bottom(db));
 integer frame_index=0,word_phase=0,px=0,py=0,k,green_lo=999,green_hi=-1,raw_lo=999,raw_hi=-1,old_lo=999,old_hi=-1,checks=0,words=0;
 reg [383:0] packed_raw,packed_pred,packed_old;reg [23:0] rgb_raw,rgb_pred,rgb_old;
 always @(negedge clk)if(rst)begin
  if(mask!==mask_old || meta!==meta_old || bv!==ov || bu!==ou || be!==oe || mask!==mask2 || meta!==meta2 || bv!==pv || bu!==pu || be!==pe)$fatal(1,"display lead changed classifier mask or video metadata");
  if(bu)begin frame_index=frame_index+1;word_phase=0;px=0;py=0;green_lo=999;green_hi=-1;raw_lo=999;raw_hi=-1;old_lo=999;old_hi=-1;end
  if(bv)begin
   words=words+1;packed_raw[383-word_phase*128 -:128]=base_video;packed_pred[383-word_phase*128 -:128]=lead_video;packed_old[383-word_phase*128 -:128]=old_video;
   if(word_phase==2)begin
    for(k=0;k<16;k=k+1)begin
     rgb_raw=packed_raw[383-k*24 -:24];rgb_pred=packed_pred[383-k*24 -:24];rgb_old=packed_old[383-k*24 -:24];
     if(py==32)begin
      if(rgb_pred==24'h00FF00)begin if(px+k<green_lo)green_lo=px+k;if(px+k>green_hi)green_hi=px+k;end
      if(rgb_old==24'h00FF00)begin if(px+k<old_lo)old_lo=px+k;if(px+k>old_hi)old_hi=px+k;end
      if(rgb_raw==24'h00FF00)begin if(px+k<raw_lo)raw_lo=px+k;if(px+k>raw_hi)raw_hi=px+k;end
     end
    end
    px=px+16;word_phase=0;
    if(px==W)begin
     if(py==32 && frame_index>=4 && frame_index<=6)begin
      if((old_lo+old_hi)/2 != (raw_lo+raw_hi)/2-6 || (green_lo+green_hi)/2 != 40+(frame_index-1)*4 || (raw_lo+raw_hi)/2!=40+(frame_index-2)*4)$fatal(1,"actual RGB overlay frame=%0d lead=%0d raw=%0d detector=%d leadbox=%d/%d",frame_index,(green_lo+green_hi)/2,(raw_lo+raw_hi)/2,cx,dl,dr);
      checks=checks+1;$display("OVERLAY_RGB_FRAME_PASS frame=%0d predictedcenter=%0d measuredprevious=%0d oldcounter=%0d",frame_index,(green_lo+green_hi)/2,(raw_lo+raw_hi)/2,(old_lo+old_hi)/2);
     end
     if(py==32 && frame_index==8)begin if((green_lo+green_hi)/2!=60)$fatal(1,"stationary overlay drifts");checks=checks+1;end
     if(py==32 && frame_index==11)begin
      if(green_hi!=159 || raw_hi!=159 || old_hi!=153)$fatal(1,"lastsixpixels not corrected new=%0d/%0d old=%0d",green_hi,raw_hi,old_hi);
      checks=checks+1;$display("OVERLAY_RGB_ROW_END_PASS correctedlastpixel159 archivedlastpixel153");
     end
     px=0;py=py+1;
    end
   end else word_phase=word_phase+1;
  end
 end
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 integer f,row,g,ph,p,xx,center;reg [383:0] group_rgb;
 initial begin
  tick(4);rst=1;tick(4);
  for(f=0;f<11;f=f+1)begin
   center=f<6 ? 40+f*4 : (f<8 ? 60 : 148);v=0;last=0;sof=1;if(f%2==0)begin tick(1);sof=0;end
   for(row=0;row<H;row=row+1)for(g=0;g<W/16;g=g+1)begin
    for(p=0;p<16;p=p+1)begin xx=g*16+p;group_rgb[383-p*24 -:24]=((xx-center)*(xx-center)+(row-32)*(row-32)<=64) ? 24'h640505 : 24'h0A0A0A;end
    for(ph=0;ph<3;ph=ph+1)begin v=1;data=group_rgb[383-ph*128 -:128];last=(g==W/16-1 && ph==1);tick(1);sof=0;end
    if(g==5 && f%2==0)begin v=0;tick(2);end
   end
   v=0;last=0;tick(100);
  end
  tick(100);if(checks!=5 || words!=11*H*W/16*3)$fatal(1,"RGB counts checks=%0d words=%0d",checks,words);
  $display("OVERLAY_RGB_PASS realpackedRGB,5/5/6,classifierandbbox,old6pixelbugreproduced,correctedoneframealignment,SOFpayload,bubbles,static,no-mask-or-metadatachange");$finish;
 end
 initial begin #10000000;$fatal(1,"RGB lead timeout");end
endmodule
