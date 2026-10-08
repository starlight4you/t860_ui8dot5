# v1.0.0 发布记录

用户授权创建 `t860_ui8dot5` 并上传 TWRP 包分卷；要求同一个 ZIP 支持全新安装与原 UI8 保数据升级，不在真机进行全新安装测试。

## 固定输入

- SYSTEM：6534725632 B，`c2c249d94e4028ba3c550bb4a51fe2c3397bf80f4f8b9f82ad8236f3ed2340a8`。
- PRODUCT：1048576000 B，`bd1e4f1598ccfc8b24890e97b3562e1941ebd27c17b284491c8965981db45aa7`。
- BOOT 基线：`523664a8caf6b403526efa6e3b77e8645cc6f84a7573ff7e39159fa9b36843e9`。
- 系统、产品为 A98 实机只读导出，不导出 DATA / metadata / 密钥，不加入个人 ADB 公钥。

## 安装流程

全新安装接受原厂 DWH1＋TWRP 与清洁 DATA，写入已验证的 S6 BOOT/VENDOR/DTBO/VBMeta 和新 SYSTEM/PRODUCT；不替换Recovery。原UI8升级保留 CE/DE、凭据、账号、应用和个人文件；不清锁设置、不修改加密模式。旧模块更新保留原 inode 并改备份后缀，目标系统使用自己原签名 factory APEX；不宣称在加密 Recovery 中验证更新内容。相同目标 SYSTEM 重装保留当前模块状态，不重复备份。全新安装检查已核对原厂或项目 S6 硬件；升级检查完整既有VENDOR与BOOT。全部入口先验证ZIP、来源、挂载、会话和checkpoint，之后才允许系统写入。

## 证据

- 用户确认升级安装已真机测试无问题，记录为用户提供的运行结果。
- 全新安装仅隔离环境检查，未在真机格式化或执行。
- 67 项 native guard 检查、50项原厂全新安装与UI8升级流程检查通过；后者 block / mount / VENDOR discovery 与 fscrypt ioctl 使用 fixture，真实 TWRP 工具、模块备份和分区文件读写执行。
- 实机三个 DATA backing 目录均无 fscrypt policy（ENODATA 61）。
- 全包数据块及分卷结果另见 Release 验证清单。

内部容量审计仍记录 SYSTEM 99.87 MiB，未把原256MiB稳定余量目标改为通过。历史全功能验证范围见四方分析与移植记录；不将两项照片 AI 测试外推为全部 AI 功能验证。

## 原厂全新安装的硬件来源

全新入口包含 S6 项目已部署 BOOT / VENDOR、原厂同一 DTBO、项目同一 VBMeta，不含 S9 硬件。DWH1 stock BOOT及VENDOR整分区摘要固定，DTBO两来源一致；VBMeta8320B前缀与旧UI8发布原件相同，保持其 AVB flags=3。升级入口不刷这些完整硬件镜像。全新执行仅用隔离文件fixture验证，按用户要求不在真机测试。

## ZIP32 与复现编码

六分区镜像全部保持原始 SHA-256；只改变 payload 的标准 DEFLATE 编码方式以满足原版 Recovery 的 unsigned ZIP32 上限。固定 7-Zip 26.01，Deflate/fb258/pass1/单线程，独立块最多四路编码、按原顺序写出；非 payload 元数据使用 zlib9。压缩格式仍为 ZIP method 8，禁止 ZIP64。原厂与项目 VBMeta 有效8320B前缀唯一差异是offset123的 AVB flags 0→3。

公开 `scripts/rebuild_release.py` 的完整包复现只依赖本仓库 `release/inputs`、打包清单以及用户本地六个镜像。历史离线实验构建器保留作逻辑参考，其中原版 Recovery root、旧固件和历史二进制证明链需维护者自行提供；不上传这些私有输入。

## v1.0.0 最终验证

完整 ZIP：4242041251 B，SHA256 `8128e7e9d42ae8b5d1071d04721d1bce52ffaf2b502f25598bd792a86ddde91a`。ZIP32 / CRC / 六分区138块原版TWRP工具检查通过；真实Recovery完整只读入口通过，前后六分区摘要相同。公开源码复现整包字节一致；三个7z分卷完整解压后摘要一致。现有系统正常重启、boot_completed=1、SELinux Enforcing。未执行全新实机刷入或DATA格式化；用户已确认先前升级测试通过。详细证明见 [release-audit](../release/release-audit.json) 和 [audit](audit)。
