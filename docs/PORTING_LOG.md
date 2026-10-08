# 公开阶段记录

私人原始日志保留在本地工程；此文件仅记录可公开复核的结论。

## A99 · 2026-10-08 · 阶段发布

- 症状/目的：需要将已运行的最新修复组合导出为独立 TWRP 包，并发布分卷。
- 根因/选择：保存的 A82 构建布局与 A98 实机已有差异，直接打包 A82 会遗漏后续修改。选择只读导出当前 SYSTEM / PRODUCT，以整分区 SHA-256 固定输入。
- 最终修改：新的阶段安装器沿用 A74 严格硬件检查和两份 VENDOR 文本事务；检查 DATA 持久 metadata、新旧会话与 checkpoint。相同 SYSTEM 重装保留既有四个 active 模块及备份原件，未声称在加密 Recovery 中验证其内容；原 UI8 保数据升级以原 inode 改名备份旧模块更新，保留原件；未知/待激活会话拒绝。
- 长期归属：metadata 的 DATA backing 是 S6 device patch；精确 raw 匹配、四模块状态集合和本阶段分区摘要是版本相关发布条件，下个版本必须重审。
- 验证：Mainline guard 67 项隔离检查通过，原厂全新安装与UI8升级统一流程50项通过；整包 CRC、所有数据块及 TWRP 原版工具结果见 release 验证清单。用户确认升级已真机测试无问题；本次新整包仅只读预检，全新安装实机测试按用户要求禁止。

## 最近已部署修复

| 问题 | 根因及修改 | 证据边界 | 归属 |
|---|---|---|---|
| 相册 JPEG OCR 原生崩溃 | donor 的 smart_scan.samsung.v2 调用 S6 缺失模型；仅移除该 capability token，保留新 Gallery 与 OCR fallback | 实机文本高亮/选取通过；文档矫正降级 | DEVICE_REQUIRED + DONOR_SPECIFIC |
| 照片 AI 挂起 | SNAP normal Acquire 同步等待 S6 缺失的新 AIDL backend；修改新 donor 的两个指令，保留 secure 路径 | 涂鸦生图和旋转补图云端实际结果通过；其他模式未全测 | DEVICE_REQUIRED + VERSION_SPECIFIC |
| 照片编辑器缺失 | 容量裁剪误删新 donor 原版编辑器及依赖；恢复原 S9 APK 与 68 个 native 文件 | 基础编辑及上述两项 AI 通过；完整人像依赖仍未验证 | 修正裁剪 |
| Google 模块更新引发启动失败 | 新网络模块与 S6 旧内核接口不兼容；采用选择性 installer whitelist 限制 | 不等于修好所有未来模块；不阻止 root/shell 特权路径 | WORKAROUND |
| CACHE 中 metadata 易被清除 | 持久 backing 移到非 FBE 的 DATA unencrypted 目录，init 顺序与 SELinux 配套 | DATA 格式化会清除，安装器检查 checkpoint | DEVICE_REQUIRED |

## v1.0.0 最终验证

完整 ZIP：4242041251 B，SHA256 `8128e7e9d42ae8b5d1071d04721d1bce52ffaf2b502f25598bd792a86ddde91a`。ZIP32 / CRC / 六分区138块原版TWRP工具检查通过；真实Recovery完整只读入口通过，前后六分区摘要相同。公开源码复现整包字节一致；三个7z分卷完整解压后摘要一致。现有系统正常重启、boot_completed=1、SELinux Enforcing。未执行全新实机刷入或DATA格式化；用户已确认先前升级测试通过。详细证明见 [release-audit](../release/release-audit.json) 和 [audit](audit)。
