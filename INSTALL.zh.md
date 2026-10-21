# Galaxy Tab S6 SM-T860 · One UI 8.5 · v1.0.2 A109

这是累计有效修复版本，包含 A100、A102、A104/A106、A107 V2 和 QCC 自动隔离。仅适用于 SM-T860 Wi-Fi；原 QCC-only A108 成品已撤回。

先备份重要数据，核对 SHA256SUMS。若下载分卷，同组全部放在同一目录，用 7-Zip/Keka 打开 .7z.001 解压；不要将分卷直接交给 Odin 或 TWRP。解压后的完整文件也必须匹配摘要。

分卷下载：全新安装使用 `Clean-Odin-v1.0.2-A109.7z.001` 至 `.004`（4卷）；保数据升级使用 `Upgrade-TWRP-v1.0.2-A109.7z.001` 至 `.003`（3卷）。

## Odin 全新安装

1. 使用已解锁 Bootloader、项目 Android 12/DWH1 硬件基础的 T860，进入下载模式。
2. Windows Odin 的 AP 选择 `AP_TabS6_OneUI8.5_v1.0.2_A109_Clean_Odin.tar.md5`。BL/CP/CSC 留空，取消 Auto Reboot；不加载 PIT，不启用 Re-Partition、Nand Erase 或 Flash Lock。
3. 等待 PASS，按键直接进入所带 TWRP。选择 Wipe → Format Data → 输入 yes。这一步清空内部存储；请勿格式化外置 SD 卡。
4. Reboot → System，完成首次设置。无需再刷升级包，无需手动运行 QCC 命令，也不要求 Magisk。

AP 含 SYSTEM、PRODUCT、VENDOR、BOOT、DTBO、VBMeta 和 Recovery；不含 userdata、CACHE、PIT、Bootloader、modem、EFS 或 persist 载荷。

## TWRP 保留数据升级

1. 将完整 `TabS6-OneUI8.5-v1.0.2-A109-Upgrade-TWRP.zip` 放到 SD 卡，或使用 ADB sideload。
2. 使用项目 TWRP 3.7.0_9-15_mentalmuso 安装。不要先清空 SYSTEM/PRODUCT，不要 Format Data。此 TWRP 不能解密内部存储，不需要为此格式化。
3. 支持已审计的项目 UI8 v0.48.1、v1.0.0/A99、A100/A102，以及已打 A104、稳定 A105、A106/A107 和本次 A109 修复的完整来源。
4. 等待 `A109 upgrade verified` 后手动重启。若来源/模块/硬件检查拒绝，保存 recovery.log 和具体报错，处理原因，不要绕过检查。

升级保留应用、账号、锁屏凭据和个人文件；写 SYSTEM/PRODUCT，事务处理三份既有 VENDOR 文件及三份新增振动文件，不刷 BOOT/DTBO/VBMeta/Recovery。中断后保留在 Recovery，按日志处理；不要重复格式化数据。

## 首次启动与修复范围

- QCC 在开机完成后自动做保数据的主用户卸载，保留 APK/底层库，已隔离则跳过。开机完成前可能短暂出现原错误。可选状态检查：`adb shell logcat -d -s T860QccPolicy:I`。
- 触摸反馈、手势振动和其他用户开关不主动更改；恢复马达识别不等于强行开启所有振动场景。
- AAC、账号和振动组件沿用此前已通过实机验证的准确载荷。当前累计包完成离线载荷/格式/事务验证；本轮未执行累计整包刷入或清空 DATA。
- 偶发双击/首笔问题仍无根因补丁；电池容量已确认7040mAh，剩余时间属历史预测，不包含虚构容量/充电修正。普通应用更新仍保留，Play 系统模块更新沿用既有暂停策略。
