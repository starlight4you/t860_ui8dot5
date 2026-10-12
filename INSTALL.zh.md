# Galaxy Tab S6 SM-T860 · One UI 8.5 · v1.0.1 A100

本目录提供两种安装包，基于同一套已在测试机运行的 A100 修复镜像。仅适用于 SM-T860 Wi-Fi，不适用于 T865/T867。

| 文件 | 用途 | 数据处理 |
|---|---|---|
| AP_TabS6_OneUI8.5_v1.0.1_A100_Clean_Odin.tar.md5 | Odin 全新安装，加载到 AP | 刷入后在 TWRP 手动 Format Data，会清空内部存储 |
| TabS6-OneUI8.5-v1.0.1-A100-Upgrade-TWRP.zip | 从已审计的项目 UI8 v0.48.1、v1.0.0/A99 或当前 A100 升级 | 保留应用、账号、凭据与文件；不执行 Format Data |

## 下载与分卷解压

按用途只下载一组分卷：

- 全新安装：`Clean-Odin-v1.0.1-A100.7z.001` 到 `.004`，共 4 卷。
- 保留数据升级：`Upgrade-TWRP-v1.0.1-A100.7z.001` 到 `.003`，共 3 卷。

同组所有分卷放在同一个文件夹，用 7-Zip / Keka 打开 `.7z.001` 解压。不要改名。Odin 组得到一个 `.tar.md5`；TWRP 组得到一个完整 `.zip`。**不能将分卷直接交给 Odin 或 TWRP，也不要使用 GitHub 自动生成的 Source code ZIP 作为刷机包。**

下载 `SHA256SUMS`，逐卷核对并核对解压后的原始包。Linux 可运行 `sha256sum -c SHA256SUMS --ignore-missing`，macOS 可运行 `shasum -a 256 <文件名>`，Windows PowerShell 可运行 `Get-FileHash <文件名> -Algorithm SHA256`。未下载的另一组可跳过；选定组必须齐全，解压后的文件必须匹配以下摘要：

```text
Odin: 15fc234753a7825df0b604ad3741fe662adfdea7cc9a23dff30bef1c4e25c436
TWRP: 601fc2b993bddad88344cced5c73335ed7be7e44da2cbdc6cf043a3a4e6a9bbf
```

先核对 SHA256SUMS，并备份重要数据。使用已解锁 Bootloader 的 T860，硬件基础为项目已验证的三星 Android 12/DWH1 层。包不替换 Bootloader，不包含 PIT、EFS、persist、modem 或用户数据镜像。

## Odin 全新安装

1. 在 Windows 上准备 Odin 与三星 USB 驱动。平板关机，按住音量上、音量下并连接电脑 USB，按下载模式提示进入。此步骤须先完成设备 Bootloader 解锁。
2. Odin 的 **AP** 选择 `.tar.md5` 文件。等待 MD5 检查完成。BL、CP、CSC 留空；取消 **Auto Reboot**，不要勾选 **Re-Partition、Nand Erase、Flash Lock**，不要加载 PIT。
3. 点击 Start，等待 PASS。此 AP 包包含 SYSTEM、PRODUCT、VENDOR、BOOT、DTBO、VBMeta 及已核对的 TWRP Recovery。
4. 保持 USB 连接，按住电源＋音量下直到屏幕熄灭，立即改为电源＋音量上进入 TWRP。选择 **Wipe → Format Data → 输入 yes**。这会清空内部存储；不要格式化外置 SD 卡。
5. 选择 **Reboot → System**，完成首次设置。Odin 包已经包含系统，无需再刷升级 ZIP。
6. **全新安装需重新落实下面的 QCC 用户级隔离。** 当前测试机的隔离状态属于 DATA，Format Data 后不能从系统镜像继承。升级则保留原有隔离状态。

这里的“全新安装”包含手动清空 DATA 的步骤；AP 文件自身不带 userdata/cache 擦除载荷。设备按键若仍处于下载模式，重新执行第 4 步进入 Recovery。

Odin 使用 AP TAR 的操作方式可参考开发者的[三星刷入说明](https://topjohnwu.github.io/Magisk/install.html#samsung-devices)，本包不要求安装 Magisk。

## TWRP 保留数据升级

1. 将 **完整 ZIP** 放到平板可被 TWRP 读取的位置，例如外置 SD 卡。
2. 进入项目使用的 TWRP 3.7.0_9-15_mentalmuso，确认 DATA 可以挂载。**不要 Format Data，也不要先清空 SYSTEM/PRODUCT。**
3. 选择 Install，刷入升级 ZIP。安装器会先校验全部载荷、现有系统、硬件文件与模块状态。
4. 等待显示 **A100 upgrade verified**，再手动 Reboot → System。

升级 ZIP 完整写入 SYSTEM 和 PRODUCT，并对 VENDOR 的两个既有兼容配置及显示诊断库执行受校验的三文件事务。它不刷写 BOOT、DTBO、VBMeta 或 Recovery。UI8 的旧系统模块按已审计流程原 inode 保留备份；兼容 UI8.5 来源保持现有模块状态。

若出现“来源未审计”“待激活模块”“无法挂载 DATA”或分区不能打开等错误，应保留完整安装日志，回到当前系统处理原因；不要跳过校验。它会在写分区前拒绝这些来源/状态问题。

## 全新安装后的 QCC 隔离

S9 的可选 QCC 遥测客户端会等待 T860 没有的 HAL。已验证的处理方式是保留数据的 user0 卸载；普通 disable-user 对该常驻程序无效。APK 与其他底层服务保留在 ROM 中。

首次设置完成后开启 USB 调试，在电脑的 Android platform-tools 中执行以下核对：

```text
adb shell getprop ro.product.model
adb shell sha256sum /system_ext/app/QCC/QCC.apk
```

型号必须是 `SM-T860`，APK SHA256 必须是 `44315310e814f2294789cca3b7b9b6e5d484d88b186c35b7e32101784a94f00e`。确认后执行：

```text
adb shell pm uninstall -k --user 0 --versionCode 6 com.qti.qcc
adb shell sync
adb reboot
```

等待 uninstall 返回 Success 再继续；这一步只处理该用户的指定版本 QCC，保留其数据。已经隔离的升级用户不重复执行。

## 包含的修复与已知范围

包含 SD 挂载参数、Quick Share 原签名预装入口、SIS 双目录缓存/翻译语言目录、蓝牙配对保存与 A2DP primary 路由、AFC 启动权限、用户配置 fs-verity 权限、BSOH 能力声明以及单条正常 GPU 回退日志修正。撤回的蓝牙 v1/v2 和 SBC encodedFormats 候选未打包。

- 阿拉伯语 S Pen 翻译与 EDIFIER MR3 SBC 音箱播放已实测；其他语言、完全断网翻译、耳机和其他 codec、Quick Share 传输仍未完整验证。
- 慢充、偶发双击/首笔卡顿仍缺受控复现。文档边缘/透视扫描降级，部分人像库及所有 AI 模式尚未完整认证。
- Google Play 系统模块更新继续采用已有暂停方案。
- Galaxy Store 的应用目录兼容配置属于应用 DATA，不从测试机复制进固件。全新安装或清理商店存储后需匹配已验证的商店版本重新配置；此包不宣称修复所有商店目录限制。
- SYSTEM/PRODUCT 余量满足原阶段 64 MiB 门槛，仍未达到稳定版 256 MiB/100 MiB 目标。

两个包的文件格式、镜像回读、完整载荷与升级事务均有审计记录；测试机执行完整升级包的只读预检。没有在测试机全新刷入 Odin、格式化 DATA 或实际执行这次完整升级。当前已验证修复在测试机的逐文件内容和权限，与打包镜像一致。
