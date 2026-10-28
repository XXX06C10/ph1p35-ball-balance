# PH1P35 一维滚球平衡：队友交接

2026 全国大学生嵌入式芯片与系统设计竞赛 FPGA 赛道，安路科技赛题二。目标器件 PH1P35MDG324。

## 两套独立基线

- `brake_precise6/`：从原项目提交 `d0c6a743d3d11753348910a58a526e9730aacd14` 原样导出，避免把当前工作区后续实验混入 precise6。入口 `td_project/vision_follow_20261022.al`，配套 `host/start_brake_precise6.cmd`。
- `merged_vision_motor_logo/`：2026-10-28 从本地同名目录复制的 Logo/多算法工程。入口 `td_project/vision_follow_20261022.al`；构建脚本 `build_logo.tcl`；配套 bit 在 `logo_Runs/phy_1/merged_vision_motor_logo.bit`。

两者不可互换，也不能假定 Logo 工程已经包含 precise6 控制策略。未更改任何 RTL、约束、原工程或板卡。导出前读取的 precise6 归档目录实际仍包含 precise5，所以没有采用该同名旧快照。

## 任务与证据

请先阅读 [光照自适应可行性与实施任务](docs/lighting_adaptation.md)。当前任务阶段是分析、建立可复现实验与资源基线，先不要直接修改 RTL。真正的动态阈值和自动曝光须分别验证。

`docs/upload_sha256.json` 为初始导入文件哈希清单（不含后来新增的交接文档）。precise6 bit SHA256：`f86441586081166212696fe3914a27fc522889ec9d2a684833e76c5ad2998934`。原验证报告标注软件/布局布线通过、实机待验证，不能据此声明实机全部通过。

## 构建注意

TD 工程文件保留原始路径和字节；换电脑后用 TD 6.2 对应版本打开并检查项目路径。相对引用的 `.al` 源文件已检查全部存在。IP、DDR、ROM、引脚/时序约束保留；没有上传工具安装包和布局数据库。部分构建/核验脚本带原电脑绝对路径，运行前检查，禁止让历史发布脚本覆盖已有交付。

Logo 的 `rtl/vision_monitor_all.v` 是实际项目引用的聚合源。不要未经比对就运行 `compose.py`，它可能用旁边历史拆分模块重新覆盖聚合源。原始作者版权声明保留；本仓库未附加新的开源授权。

仓库用于团队协作，默认私有。队友需由仓库所有者在 GitHub Settings → Collaborators 中添加。
