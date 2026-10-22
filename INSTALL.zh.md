# Galaxy Tab S6 SM-T860 · One UI 8.5 · v1.0.3 A111

仅适用 SM-T860 Wi-Fi。请先备份重要数据，并核对 SHA256SUMS。解锁引导程序是前提。

## 下载与解压

Odin 与 TWRP 分别提供一组 7z 分卷。下载所选组的全部分卷，放在同一目录，用 7-Zip 或 Keka 打开 `.7z.001` 解压，得到完整刷机文件；不要直接刷入分卷。解压后再次核对完整文件的 SHA256。

## Odin 全新安装

1. 使用项目要求的 T860 Android 12 / DWH1 硬件底包，进入下载模式。
2. Windows Odin 的 AP 栏选择 `AP_TabS6_OneUI8.5_v1.0.3_A111_Clean_Odin.tar.md5`。BL、CP、CSC 留空，关闭 Auto Reboot。不要加载 PIT，不要开启 Re-Partition、Nand Erase 或 Flash Lock。
3. 出现 PASS 后直接进入内置 TWRP，执行 Wipe → Format Data → 输入 yes。此步骤清除内部存储；不要格式化外置 SD 卡。
4. Reboot → System，完成初始化。不需要再刷升级 ZIP，也不需要 Magisk 或手动处理 QCC。

AP 包含 SYSTEM、PRODUCT、VENDOR、BOOT、DTBO、VBMeta、Recovery，不包含 userdata、CACHE、PIT、引导程序、基带、EFS、persist。

## TWRP 保留数据升级

**仅支持从已有 One UI 8.5 升级。不能从 One UI 8（包括 v0.48.1）、One UI 4.1、原厂系统或其他 ROM 直接使用此升级包。其他系统请使用 Odin 全新安装。**

1. 将完整的 `TabS6-OneUI8.5-v1.0.3-A111-Upgrade-TWRP.zip` 放到外置 SD 卡/USB OTG，或通过 ADB sideload 安装。
2. 进入项目 TWRP 3.7.0_9-15_mentalmuso，直接安装 ZIP。不要先擦除 SYSTEM/PRODUCT/VENDOR，不要 Format Data。此版 TWRP 不能解密内部存储是已知限制，升级不需要为此格式化。
3. 安装器不检查原版本号、原 SYSTEM/VENDOR 文件白名单，也不要求指定的小版本。请自行确认当前是 One UI 8.5。机型、分区布局、项目内核/DTBO/VBMeta 硬件基线、载荷完整性、DATA 访问和系统模块安全状态检查仍保留。
4. 等待 `A111 upgrade verified` 后手动重启。

升级完整替换 SYSTEM、PRODUCT、VENDOR，保留 BOOT、DTBO、VBMeta、Recovery 以及用户数据。系统分区内自行添加的修改会被覆盖。不会清除应用、账号、锁屏凭据或个人文件，不调整用户的振动开关。断电或写入中断后留在 Recovery，重新刷入同一完整升级包；不要格式化 DATA。预检报错时保留 recovery.log 及提示的日志目录。

## 本版说明

- 累计保留此前 SD 卡、翻译语言目录、Quick Share、蓝牙配对/音频/AAC、账号管理闪退、振动及 QCC 隔离修复，并合入 A110 S Pen 旧 HAL 指令兼容。
- 发布镜像不包含本机 ADB root 调试配置：`ro.debuggable=0`，保留 USB 调试授权，SELinux 使用生产版策略，无 permissive 调试域。
- S Pen 修复已验证充电启动/停止命令到达原 Wacom 驱动；实际蓝牙笔配对、充电状态和遥控功能需有笔的反馈者复测。
- QCC 在系统完成启动后自动对主用户执行保留数据的隔离。已有隔离状态会跳过，不删除系统 APK。
- 未调整内核、快充参数、触控阈值或振动偏好。双击亮屏与首笔偶发延迟不作为本版已修复项。
