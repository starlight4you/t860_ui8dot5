# Galaxy Tab S6 · One UI 8.5

适用于 **Galaxy Tab S6 SM-T860（Wi-Fi版）**，以 Galaxy Tab S9 SM-X710 官方 `X710XXS6EZH3` 为 donor，Android 16 / One UI 8.5。保留 Tab S6 的 kernel、firmware、HAL 和硬件基础，设备适配逻辑独立维护。

## 下载和安装 / Download and installation

当前版本 **v1.0.3 (A111 累计修复 / cumulative fixes)**：[GitHub Release](https://github.com/starlight4you/t860_ui8dot5/releases/tag/v1.0.3)。

- **Odin 全新安装 / Clean install：**下载 `Clean-Odin-v1.0.3-A111.7z.001`–`.004` 共 4 卷，解压得到 AP `.tar.md5`。刷入后直接进入 TWRP 执行 Format Data，会清空内部存储。
- **TWRP 保留数据升级 / Keep-data upgrade：**下载 `Upgrade-TWRP-v1.0.3-A111.7z.001`–`.003` 共 3 卷，解压完整 ZIP。不要 Format Data，也不要预先擦除系统分区。

**升级包仅支持从已有 One UI 8.5 升级，不支持 One UI 8/v0.48.1、原厂或其他 ROM。 / The upgrade ZIP supports existing One UI 8.5 installations only; One UI 8/v0.48.1, stock and other ROMs require a clean Odin installation.**

取消原版本号及 SYSTEM/VENDOR 来源文件白名单，保留机型、分区、项目硬件基线、载荷及系统模块检查。完整替换 SYSTEM/PRODUCT/VENDOR，保留用户数据及 BOOT/DTBO/VBMeta/Recovery。 / No installed-version or source-tree whitelist; model, partition, project hardware baseline, payload and module checks remain. SYSTEM/PRODUCT/VENDOR are replaced; user data and BOOT/DTBO/VBMeta/Recovery are retained.

每组选定分卷必须全部下载到同一目录，用 7-Zip/Keka 打开 `.001`，核对 SHA256SUMS 后刷入解压结果。分卷与 GitHub Source code 压缩包不能直接刷入。 / Download all volumes of one set, extract `.001` and verify SHA256SUMS. Individual volumes and GitHub Source code archives are not flashable.

完整说明 / Full guides：[中文](INSTALL.zh.md) · [English](INSTALL.en.md)。更新日志 / Changelog：[中文](CHANGELOG.zh.md) · [English](CHANGELOG.en.md)。[发布审计 / Release audits](docs/releases/v1.0.3)。

包含 A109 全部有效修复和 A110 S Pen 旧 HAL 兼容，不含本机 ADB root。原版 TWRP 离线校验覆盖全部 135 个镜像块；Odin 完成 sparse/LZ4 往返及成员回读。蓝牙笔实物配对/遥控需有笔反馈者复测。 / Includes all effective A109 fixes and A110 S Pen legacy compatibility, excludes local ADB root. Original-TWRP offline validation covers all 135 image chunks; Odin sparse/LZ4 round trips and member readback pass. Physical pen pairing/remote actions require reporter testing.

历史版本保留。 / Historical releases are retained.

## 适配与源码

```text
patches/       S6 framework/native/resource 适配逻辑
scripts/       离线配置生成、检查、v1.0.0 发布包复现
device/s6/    配置、init、SELinux、overlay、native 源码
release/       发布安装器、支持工具、固定打包清单
docs/          四方分析、rebase 顺序与移植记录
```

metadata 持久 backing 位于 `/data/unencrypted/t860-metadata`，普通 CACHE 清理不影响它。DATA 格式化会同时清除用户数据和这个 backing。

原始固件、个人 DATA、设备密钥和私人原始日志不提交仓库。历史分析路径使用占位符；Android SDK 工具由 `ANDROID_SDK_ROOT` 指定。

### 复现历史 v1.0.0 ZIP

以下复现工具与 `release/` 固定输入保持 v1.0.0/A99，不适用于新 A100 包。v1.0.1 的安装说明与审计位于 `docs/releases/v1.0.1/`。

需要 Python 3、7-Zip 26.01 和约 8.5 GiB 镜像空间：

```bash
python3 scripts/extract_release_images.py TabS6-S9-OneUI8.5-v1.0.0-TWRP.zip --out images
python3 scripts/rebuild_release.py --system images/system.raw.img --product images/product.raw.img --boot images/boot.raw.img --vendor images/vendor.raw.img --dtbo images/dtbo.raw.img --vbmeta images/vbmeta.raw.img --out rebuilt.zip
```

脚本固定镜像和安装器输入，并验证最终 ZIP 摘要；可通过 `RELEASE_7ZZ` 指定 7-Zip 26.01 可执行文件。Python / zlib / 7-Zip 环境见 `release/packaging.json`。新 donor 需要按 [S9_REBASE_PLAN](docs/S9_REBASE_PLAN.md) 重新定位逻辑和验证接口，不能复制旧 framework 二进制或盲目批量应用历史 patch。改动分类见 [UI8_PORT_CHANGES](docs/UI8_PORT_CHANGES.md)，验证记录见 [PORTING_LOG](docs/PORTING_LOG.md)。

### 复现 A102 安装器修正 / Reproduce the A102 installer hotfix

A102 不改变 A100 SYSTEM/PRODUCT 载荷或历史 A99 输入。以摘要固定的原 A100 升级 ZIP 为输入，使用 `release/a102-tools/` 的工具，可通过 `scripts/repack_upgrade_a102.py` 生成修正版 ZIP；只读检查包通过 `scripts/build_upgrade_check_a102.py --source ORIGINAL_A100.zip --guard release/a102-tools/mainline-guard --ndk NDK_R27D --out NEW_OUTPUT` 构建。输出必须为新目录。原因、工具接口复现及实机只读验证见 [A102 审计](docs/UPGRADE_INSTALLER_HOTFIX_A102_20261013.md)。
