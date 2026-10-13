# 2026-10-13 · A102 升级安装器修正

反馈为 v0.48.1→v1.0.1 TWRP 升级失败。用户确认此 TWRP 无法解密内部存储；反馈日志中 v0.48.1 的完整 SYSTEM 文件树校验已通过，随后 `Pending or unsafe system module state` 停止，未进入模块备份和分区写入。

## 已复现的根因

**发布 ZIP 内的 `mainline-guard` 与安装器调用接口不匹配。** 实际打包二进制 2,239,088 字节、SHA256 `f0b671505a818808adc788d2524974b8fe3fd6c7365602d6b4a8443394335c66` 支持 `--identical-system-reinstall`，不支持 `--upgrade-preflight` / `--upgrade-hold`。原版 TWRP ARM64 工具环境中，安装器使用的命令实际返回：

```text
t860-mainline-preflight: invalid factory table: --upgrade-preflight
```

这是在空目录、可读 DATA 模拟目录上也可复现的参数错误。不能把 Recovery 中普通加密目录的 Permission denied 当作本次模块失败的已证实原因。旧校验结果只覆盖当前 UI8.5 的 identical-reinstall 分支；它不证明发布包能走 UI8 升级分支。删除版本校验不会改变此错误。

项目既有 A99 v3 工具 2,242,016 字节、SHA256 `4f3f04af10250a0522b4bf2805fe0567fef975da1aea9e24024d86eba8ca8176` 已实现两个升级参数；原件、源码、A99 构建输入均保持。

## 修正范围

- A102 只替换升级 ZIP 的模块检查工具、安装库与其摘要/元数据，加入只读目录访问探针。
- 模块目录不可读时，提前显示路径与 errno，停止写入；会话检查和备份拒绝的真实原因直接显示于 Recovery。
- SYSTEM/PRODUCT 所有压缩载荷和原始镜像摘要不变；VENDOR 三文件事务不变。
- 保留原来源、硬件、签名、会话、checkpoint 规则；不格式化 DATA，不删除密钥、账户或应用数据，不修改内核或 SELinux。
- 同时提供约 2.8 MB 的只读诊断 ZIP，可以从 SD 卡安装；它没有 ROM 载荷、模块改名、解密和自动重启操作。

## 验证与限制

新版模块工具在原版 Recovery ARM64 工具环境中全部 67 项检查通过，包括升级预检、原 inode 备份、备份碰撞、待激活/回滚会话、异常目录和重装。新增探针 9 项通过，覆盖 ENOENT、EACCES、符号链接、普通文件冒充目录、待激活会话拒绝和预检不修改模块；两份 shell 脚本在原版 shell 中语法通过。

此结论修正发布包已复现的参数错误，尚不等于反馈者的整机升级与 DATA 解锁完成。真实待激活更新或实际不可访问的模块目录仍需由检查包报告，不能跳过这些状态。

构建入口：`scripts/repack_upgrade_a102.py`。原 v1.0.1 A100 包和 Odin 包保留，A99 不改。诊断入口：`scripts/build_upgrade_check_a102.py`。旧 A102 诊断 v1 是根因发现前的历史输出，使用 v2。

## 实机只读对照

同一台 T860、同一个 TWRP 中，普通 `/data/system` 返回 EACCES，但 `/data/apex/active` 可读、4项且 encrypted=no。原包工具返回 `invalid factory table: --upgrade-preflight` / exit1；换入工具对同一状态返回 exit0 / 4个旧模块可保 inode 备份。只运行 preflight，没有执行改名。Recovery 本身为 Permissive，诊断工具未改变该状态；Android 既有 Enforcing 策略不改。公开结果见 `audit/upgrade-guard-live-a102.json`。

完整 A102 ZIP 已在当前 T860 执行原始 update-binary 的 `--preflight-only`，native exit0、A102_UPGRADE_PREFLIGHT_PASS。SYSTEM/PRODUCT/VENDOR/BOOT/DTBO/VBMeta 六分区完整 SHA 前后相同，无 DATA 格式化；临时 ZIP 只存 Recovery TMPFS，取回证据后移除、恢复临时挂载容量并返回 Android。此项是当前 UI8.5 来源的只读预检，不替代反馈者 v0.48.1 的整机升级结果。见 `audit/upgrade-full-live-a102.json`。
