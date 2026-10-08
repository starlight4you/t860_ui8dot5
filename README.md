# Galaxy Tab S6 · One UI 8.5

适用于 **Galaxy Tab S6 SM-T860（Wi-Fi版）**，以 Galaxy Tab S9 SM-X710 官方 `X710XXS6EZH3` 为 donor，Android 16 / One UI 8.5。保留 Tab S6 的 kernel、firmware、HAL 和硬件基础，设备适配逻辑独立维护。

## 下载和安装

[下载 Release](https://github.com/starlight4you/t860_ui8dot5/releases)。当前版本 `v1.0.0`。

1. 下载全部 `TabS6-S9-OneUI8.5-v1.0.0-TWRP.7z.00x`、`SHA256SUMS` 和 `INSTALL.zh.md`。
2. 分卷放在同一目录，用 7-Zip / Keka 打开 `.001` 解压，得到完整 `.zip`，核对 SHA-256。
3. 进入 TWRP，按下面对应方式安装完整 ZIP。分卷不能直接刷入。

### 从项目 One UI 8 升级

支持已核对的 **v0.48.1** 基线，保留应用、账号、锁屏凭据和个人文件。备份后直接安装 ZIP，**不要清 DATA 或格式化**。安装器自动检查硬件和升级状态，并保留旧系统模块更新的备份，使用新系统的原厂模块。成功后手动重启。

### 全新安装

先备份个人数据，准备 S6 原厂系统（DWH1 硬件基础）与 TWRP。由用户在 TWRP 准备清洁 DATA / CACHE；可从原厂系统直接开始，SYSTEM 也可以已清为 ext4。随后安装同一个 ZIP，成功后手动重启。安装器不替用户自动格式化。

仅支持 SM-T860；T865 / T867、其他未核对硬件基础不在此包入口内。实机核对使用 TWRP `3.7.0_9-15_mentalmuso`。同一个包包含 SYSTEM / PRODUCT / S6 BOOT / S6 VENDOR / DTBO / VBMeta。全新安装装入完整 S6 适配基础；从 UI8 升级仅更新 SYSTEM / PRODUCT 与两项 VENDOR 文本配置，保留 BOOT / DTBO / VBMeta。不会安装 S9 kernel / VENDOR 或替换 TWRP。

## 适配与源码

```text
patches/       S6 framework/native/resource 适配逻辑
scripts/       离线配置生成、检查、当前发布包复现
device/s6/    配置、init、SELinux、overlay、native 源码
release/       发布安装器、支持工具、固定打包清单
docs/          四方分析、rebase 顺序与移植记录
```

metadata 持久 backing 位于 `/data/unencrypted/t860-metadata`，普通 CACHE 清理不影响它。DATA 格式化会同时清除用户数据和这个 backing。

原始固件、个人 DATA、设备密钥和私人原始日志不提交仓库。历史分析路径使用占位符；Android SDK 工具由 `ANDROID_SDK_ROOT` 指定。

### 复现当前 ZIP

需要 Python 3、7-Zip 26.01 和约 8.5 GiB 镜像空间：

```bash
python3 scripts/extract_release_images.py TabS6-S9-OneUI8.5-v1.0.0-TWRP.zip --out images
python3 scripts/rebuild_release.py --system images/system.raw.img --product images/product.raw.img --boot images/boot.raw.img --vendor images/vendor.raw.img --dtbo images/dtbo.raw.img --vbmeta images/vbmeta.raw.img --out rebuilt.zip
```

脚本固定镜像和安装器输入，并验证最终 ZIP 摘要；可通过 `RELEASE_7ZZ` 指定 7-Zip 26.01 可执行文件。Python / zlib / 7-Zip 环境见 `release/packaging.json`。新 donor 需要按 [S9_REBASE_PLAN](docs/S9_REBASE_PLAN.md) 重新定位逻辑和验证接口，不能复制旧 framework 二进制或盲目批量应用历史 patch。改动分类见 [UI8_PORT_CHANGES](docs/UI8_PORT_CHANGES.md)，验证记录见 [PORTING_LOG](docs/PORTING_LOG.md)。
