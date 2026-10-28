RTL：vision_follow_control.v新增K3控制中立、相对纠偏→绝对目标裁剪、无动作的启动目标同步及中立越界拒绝；vision_monitor.v只连接K3采样并反馈KC8/RD；vision_monitor_all.v重生成。执行器、编码器、解析器、相机、引脚、时钟均不改。

面板：解释两种参考和相对L/绝对T，增加越界映射，删除不可靠的|T|>=L饱和推断。协议函数和解析器不改。新增tb_neutral及精确合同/归档/发布脚本，原直接控制器测试显式连接neutral_capture=0；验证脚本保留全部核对并增加非零中立回归。完整清单neutral_changed_files.json，差异neutral_changes.diff。