# A111 / v1.0.3 累计发布

本次请求：累计修改生成 Odin 全新安装包与 TWRP 保留数据升级包；发布镜像去除 ADB root；升级安装器不校验原版本，在说明中明确仅支持从 One UI 8.5 升级。

## 镜像闭合

以已发布的 A109 生产镜像作为来源，逐块重建 SYSTEM，并只替换 `system/framework/secinputdev-service.jar` 为 A110 v3 已验证载荷。7885 个其他文件/目录条目的内容和元数据保持不变；原生产 build.prop、plat_sepolicy.cil 及策略摘要逐项固定，`ro.debuggable=0`、`ro.secure=1`、`ro.adb.secure=1`，不包含 permissive 调试域及私人 adb_keys。

VENDOR 完整复用 A109，保留 A107 V2 振动服务及全部已有有效硬件修复。PRODUCT、BOOT、DTBO、VBMeta、Recovery 与 A109 完全一致，不引入内核改动。A109 的所有有效修复及 A110 S Pen 桥接均保留，排除 A105 临时 AAC 限制、A107 V1、A110 本机 ADB root。

## 升级语义

安装器仅允许 SM-T860 的项目分区布局及硬件基线，不读取原系统版本号或文件树，也不将原 SYSTEM/VENDOR 与历史小版本白名单匹配。完整写入 VENDOR、SYSTEM、PRODUCT，替代原先受 VENDOR 来源树限制的文件事务。安装前校验全部载荷；每个分区写入后校验整分区 SHA256。

保留 DATA/metadata 访问、fscrypt、系统模块 active/session 状态检查，仅执行只读预检，不迁移模块、不清理用户数据。此安装器不支持从 One UI 8/0.48.1 迁移；中英安装说明明确要求原系统为 One UI 8.5。

中断后通过再次写入完整 ZIP 恢复三分区，不依赖完整的旧 SYSTEM 版本识别。保留原 BOOT、DTBO、VBMeta、Recovery。不处理当前测试机的本地 root 状态；本轮是打包发布，不进行设备刷写或格式化。

## 验证与发布记录

镜像逐文件闭合、e2fsck、root 排除、完整 ZIP CRC/逐块及整分区摘要、Odin sparse/LZ4 往返、TAR 成员/MD5 回读、原版 TWRP 用户态离线解包，以及安装器失败前阻止写入的流程检查，分别保存审计文件。安装器流程测试使用模拟写入调用，原版 TWRP 解包测试使用无设备块节点的隔离环境，均不等同于本轮实机刷入。

首次两次原版 TWRP 离线测试在虚拟机共享文件目录中出现不同位置的 ZIP 打开 I/O 错误，保留失败记录，并使用虚拟机本地磁盘重测来隔离文件共享层。最终结果以 `cumulative-twrp-native-payload-a111.json` 为准。

蓝牙 S Pen 真实配对/遥控仍需有笔的反馈者复测；本次使用的 A110 JAR 已有原 Wacom 驱动 EB/ED 命令验证。双击亮屏、首笔延迟和快充不作新增修复声明。
