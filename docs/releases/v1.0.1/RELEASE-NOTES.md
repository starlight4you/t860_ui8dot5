# Galaxy Tab S6 SM-T860 · One UI 8.5 · v1.0.1 (A100)

**SM-T860 Wi-Fi only / 仅限 SM-T860 Wi-Fi。** Android 16 / One UI 8.5 port with the S6 hardware base. Unlocked bootloader and the verified Android 12/DWH1 baseline required. / 基于 S6 硬件基础的移植版本，需要已解锁 Bootloader 与已核对的 Android 12/DWH1 基础。

## Download / 下载

Choose **one** group and download every volume in that group. / 按安装方式选择一组，下载该组全部分卷。

| Purpose / 用途 | Assets / 附件 | Extracted file / 解压结果 |
|---|---|---|
| Clean installation / 全新安装 | `Clean-Odin-v1.0.1-A100.7z.001`–`.004` (4 volumes / 4 卷) | `AP_TabS6_OneUI8.5_v1.0.1_A100_Clean_Odin.tar.md5` |
| Keep-data upgrade / 保留数据升级 | `Upgrade-TWRP-v1.0.1-A100.7z.001`–`.003` (3 volumes / 3 卷) | `TabS6-OneUI8.5-v1.0.1-A100-Upgrade-TWRP.zip` |

Keep all volumes in the same folder, open `.7z.001` with 7-Zip / Keka and extract. Verify `SHA256SUMS`, including the extracted package. **Never flash individual volumes or GitHub's Source code archives.** / 同组分卷放在同一目录，用 7-Zip / Keka 打开 `.7z.001` 解压，核对 `SHA256SUMS` 与解压后的原始包。**分卷和 GitHub 自动生成的 Source code 压缩包不能直接刷入。**

Full instructions: [English INSTALL.en.md](https://github.com/starlight4you/t860_ui8dot5/releases/download/v1.0.1/INSTALL.en.md) · [中文 INSTALL.zh.md](https://github.com/starlight4you/t860_ui8dot5/releases/download/v1.0.1/INSTALL.zh.md). Read the relevant full guide before flashing. / 刷入前请完整阅读对应安装说明。

## English changelog

- Repair SD card mount parameters for the older S6 driver.
- Restore the original signed Quick Share package and permission allowlist.
- Restore the SIS translation language catalog and migrate both caches. Arabic download, persistence after reboots and physical S Pen translation were verified.
- Fix Bluetooth pairing persistence with native v3 and A2DP primary routing; retain the original S6 audio policy. EDIFIER MR3 SBC playback was heard and pairing survived reboots.
- Grant AFC control-node permissions before zygote starts; charging speed still needs a wall-charger test.
- Add the narrowly scoped fs-verity ioctl permission for user configuration files.
- Correct the unsupported BSOH capability declaration and remove one normal GPU fallback diagnostic call without changing composition logic.
- Provide a clean-install Odin AP package and a separate data-preserving TWRP upgrade ZIP. Existing A99 fixes, including rounded corners, are retained.

### English installation summary

**Clean Odin:** back up data; use Windows Odin; load the extracted TAR.MD5 in **AP**, leave BL/CP/CSC empty, uncheck Auto Reboot and leave Re-Partition/Nand Erase/Flash Lock unchecked. Do not load a PIT. After PASS, boot directly into the included TWRP, **Wipe → Format Data → yes** (erases internal storage; do not format SD), then Reboot System and finish setup. The upgrade ZIP is not needed afterward. **Apply the verified QCC user 0 isolation from INSTALL.en.md after initial setup**; this DATA state cannot be inherited after Format Data.

**TWRP upgrade:** supports the audited project UI8 v0.48.1, v1.0.0/A99 and current A100 source trees. Use TWRP **3.7.0_9-15_mentalmuso**, ensure DATA mounts, install the fully extracted ZIP, wait for **A100 upgrade verified**, then reboot manually. **Do not Format Data or wipe SYSTEM/PRODUCT first.** Unsupported/modified sources and unsafe module states are refused before partition writes. Upgrade preserves BOOT, DTBO, VBMeta, Recovery and user data.

### English verification and known limitations

Image/format readbacks passed, all 114 payload chunks and 20 support files passed in original TWRP userspace, and all 12 VENDOR transaction cases passed. The actual tablet passed a complete **read-only Recovery preflight**, with all six partition hashes unchanged. **No new Odin clean flash or full TWRP upgrade was performed on the test tablet.**

Actual slow charging and intermittent double-tap/first-stroke reports remain unconfirmed. Fully offline translation, other languages/codecs/headphones and Quick Share transfers are not fully tested. Document edge/perspective scanning remains unavailable; some portrait libraries and all AI modes are not fully certified. Google Play system-module updates remain paused. Galaxy Store catalog configuration is application DATA and is not bundled. SYSTEM/PRODUCT free space meets the 64 MiB stage threshold, not the stable targets of 256 MiB/100 MiB. See the full installation guide and public audit files for details.

## 中文更新日志

- 修复 SD 卡挂载参数与旧 S6 驱动的兼容问题。
- 恢复 Quick Share 原签名预装包及权限列表。
- 修复 SIS 翻译语言目录，并迁移两份缓存；阿拉伯语下载、重启保留及实体 S Pen 翻译已验证。
- 修复蓝牙 native v3 配对保存与 A2DP primary 路由，保留原 S6 音频策略；EDIFIER MR3 SBC 播放及重启后配对保留已验证。
- 将 AFC 控制节点授权提前到 zygote 启动前；实际充电速度仍需墙充测试。
- 补齐用户配置文件所需的单一 fs-verity ioctl 权限。
- 纠正不支持的 BSOH 能力声明，去除一条正常 GPU 回退诊断调用，保持图层合成逻辑。
- 提供 Odin 全新安装 AP 包与独立 TWRP 保留数据升级包；继承 A99 的圆角等已有修复。

### 中文安装摘要

**Odin 全新安装：**先备份数据，在 Windows Odin 的 **AP** 加载解压后的 TAR.MD5，BL/CP/CSC 留空，取消 Auto Reboot，不勾选 Re-Partition/Nand Erase/Flash Lock，不加载 PIT。PASS 后直接进入包内 TWRP，执行 **Wipe → Format Data → yes**（清空内部存储，不格式化 SD 卡），再 Reboot System 完成首次设置。无需再刷升级 ZIP。**首次设置后按 INSTALL.zh.md 落实指定版本 QCC 的 user0 隔离**；Format Data 后不能继承原隔离状态。

**TWRP 升级：**支持已审计的项目 UI8 v0.48.1、v1.0.0/A99 和当前 A100 来源。使用 TWRP **3.7.0_9-15_mentalmuso**，确认 DATA 可挂载，安装解压后的完整 ZIP，等待 **A100 upgrade verified** 后手动重启。**不要 Format Data，也不要预先清空 SYSTEM/PRODUCT。** 未核对或被修改的来源及异常模块状态会在写分区前被拒绝。升级保留 BOOT、DTBO、VBMeta、Recovery 与用户数据。

### 中文验证与已知限制

镜像及文件格式回读通过，原 TWRP 用户空间校验全部 114 个载荷块与 20 个支持文件，12 项 VENDOR 事务测试通过。实机执行完整升级包的 **Recovery 只读预检**，六个分区哈希前后不变。**没有在测试机执行新的 Odin 全新刷入或完整 TWRP 升级。**

慢充、偶发双击亮屏/首笔卡顿仍未确认；完全断网翻译、其他语言/耳机/codec、Quick Share 实际传输尚未完整验证。文档边缘/透视扫描仍不可用，部分人像库及所有 AI 模式未完整认证。Google Play 系统模块更新继续暂停。Galaxy Store 目录配置属于应用 DATA，不随固件打包。SYSTEM/PRODUCT 余量达到 64 MiB 阶段门槛，但未达到 256 MiB/100 MiB 稳定目标。详情见完整安装说明与公开审计文件。
