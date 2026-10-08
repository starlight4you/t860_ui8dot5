# Tab S6 One UI 8.5 安装

适用机型：**SM-T860（Wi-Fi）**。版本：**v1.0.0**。

## 下载和解压

下载全部 `TabS6-S9-OneUI8.5-v1.0.0-TWRP.7z.00x`，放在同一目录，用 7-Zip / Keka 从 `.001` 解压，得到 `TabS6-S9-OneUI8.5-v1.0.0-TWRP.zip`。按 `SHA256SUMS` 检查分卷及解压后的完整 ZIP。不要将分卷直接交给 TWRP。

## 从项目 One UI 8 保留数据升级

1. 当前为项目 **v0.48.1**，先备份个人数据及系统恢复材料。
2. 进入 TWRP，保持 DATA 已挂载；直接安装完整 ZIP。
3. **不清 DATA、不格式化**，保留应用、账号、密码和个人文件。
4. 等待安装器完成全部回读检查，成功后手动重启。

升级安装保留 BOOT / DTBO / VBMeta 和 S6 硬件内容，仅更新 SYSTEM / PRODUCT 与两项 VENDOR 配置。旧系统模块更新自动保留为 `.A99-held` 备份，目标使用自己原厂模块；不删除原件。待激活更新或不符合基线的硬件状态会让安装停止，停止后保持 Recovery 并保存安装日志。

## 从原厂系统全新安装

1. 以 **S6 T860XXS5DWH1 原厂硬件基础＋TWRP** 开始；Bootloader 已允许安装自定义系统，Recovery 验证版本为 `3.7.0_9-15_mentalmuso`。
2. 先备份个人数据、BOOT / VENDOR / DTBO / VBMeta 和恢复材料。
3. 在 TWRP 手动准备清洁 DATA / CACHE；需要时使用 Format Data，这会清除内部个人文件，请在备份完成后操作。安装器不会自动格式化。
4. 挂载 DATA，安装同一个完整 ZIP。无需先安装 UI8；不要另外刷 S9 BOOT / VENDOR。
5. 成功后手动重启，完成系统首次设置。

全新入口写入本包的 S6 BOOT / VENDOR / DTBO / VBMeta 及 S9-based SYSTEM / PRODUCT。不改 PIT / Bootloader，不替换 TWRP；照片、账号等不包含在包内。

## 恢复

安装器报告错误时不自动重启。保存 TWRP 安装日志并留在 Recovery；需要恢复时使用刷前自己的成套备份，恢复匹配的 SYSTEM / PRODUCT / BOOT / VENDOR / DTBO / VBMeta。不要为处理错误而清锁屏数据、密钥或使用 S9 的硬件镜像。

metadata backing 为 `/data/unencrypted/t860-metadata`：清普通 CACHE 不会清它，格式化 DATA 会清它。
