# Galaxy Tab S6 · One UI 8.5

适用于 **Galaxy Tab S6 SM-T860（Wi-Fi版）**，以 Galaxy Tab S9 SM-X710 官方 `X710XXS6EZH3` 为 donor，Android 16 / One UI 8.5。保留 Tab S6 的 kernel、firmware、HAL 和硬件基础，设备适配逻辑独立维护。

## 下载和安装 / Download and installation

当前固件版本 **v1.0.1 (A100)**：[GitHub Release](https://github.com/starlight4you/t860_ui8dot5/releases/tag/v1.0.1)。

- 全新安装 / Clean install：下载 `Clean-Odin-v1.0.1-A100.7z.001`–`.004`，解压得到 Odin AP `.tar.md5`。刷入后在 TWRP 手动 Format Data，清空内部存储；首次设置后执行安装文档中的 QCC 隔离步骤。
- 保留数据升级 / Keep-data upgrade：下载 `Upgrade-TWRP-v1.0.1-A100.7z.001`–`.003`，解压得到完整 TWRP `.zip`。支持已核对的项目 UI8 v0.48.1、v1.0.0/A99 和当前 A100 来源。不要 Format Data 或预先清空 SYSTEM/PRODUCT。

每组所有分卷放在同一目录，使用 7-Zip / Keka 打开 `.001` 解压，核对 SHA-256。分卷与 GitHub Source code 压缩包不能直接刷入。 / Download every volume of your selected group, extract `.001` in 7-Zip / Keka and verify SHA-256. Individual volumes and GitHub Source code archives are not flashable.

完整说明 / Full guides：[中文](INSTALL.zh.md) · [English](INSTALL.en.md)。更新日志 / Changelog：[中文](CHANGELOG.zh.md) · [English](CHANGELOG.en.md)。[发布审计 / Release audits](docs/releases/v1.0.1)。

实机逐项修复与完整只读预检通过；本次未在测试机执行 Odin 全新刷入或完整 TWRP 升级。 / Individual fixes and the complete read-only preflight passed on the tablet; a new Odin clean flash or full TWRP upgrade has not been performed.

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
