## 2026-10-05 A95 新donor等价逻辑实现：普通SNAP缺接口退出等待

旧F15/v0.39全局wait PLT重定位不能迁移：新S9 secure/normal共享wait。已在当前新System lib64/libsnap_aidl.snap.samsung.so normal空分支0x1d210/214仅改两指令，保留已注册服务、安全等待、ABI/重定位及原null错误处理。分类VERSION_SPECIFIC/WORKAROUND，高风险；长期device原则是缺硬件能力不无限等，不是固定偏移或旧binary。

当前实验设备启动与null获取/能力查询契约通过，完整媒体QA待完成，未纳入A84成品。新实现/风险/实测/未决详见SNAP_NONBLOCKING_A95.md，replay与profile明确拒绝不同新donor。UI9需重新审计方法/调用者，不能机械套地址。

## 2026-10-05 A94：全局性能候选，最近任务专项停止

本轮只读发现，以下均不是新部署的补丁；A89–A93前台研究按用户要求停止，历史来源保留。

| 项目 | 分类 | 具体分区/文件/调用者 | 目的及新donor迁移方式 | 风险/当前结果 |
| --- | --- | --- | --- | --- |
| F15 SNAP缺后端阻塞 | WORKAROUND / VERSION_SPECIFIC；长期S6能力判断候选 | SYSTEM lib64/libsnap_aidl.snap.samsung.so（8d4d95da…），实际等待caller com.samsung.faceservice19619/22932；S6 VENDOR保留HIDL SNAP | 61次每秒等待/183次服务启动失败。新库normal与Knox secure共用wait，先证明实际映射/空失败契约，再仅对普通缺服务分支做新源有界查询；保留安全/成功路径 | 高；具体新调用/分支已解码，未构建/部署native patch。旧全局PLT重定位不能机械迁移，不能伪造AIDL或换HAL |
| F15 Heatmap可选采集 | WORKAROUND / DEVICE_REQUIRED候选 | SYSTEM bin/heatmap、etc/init/init.sec-heatmap.rc；新sec_auth sysfs节点 | 缺batt_heatmap/ect_output后端；重新审计新Health/Battery/charger消费者再对单采集入口做撤销对照；保留S6 Thermal/Health | 中至高；当前running但本轮仅两次uevent、未证高CPU/I/O。EFS权限拒绝不是缺失/可删除依据 |
| 微信VFS维护锁 | 应用状态，非已证明ROM device patch | DATA中的第三方应用运行状态；UID10276/push10161，系统PowerManager只读 | 同一partial锁后续17分6秒，评估保留消息通知的应用层处理，不固定UID到安装器 | 待机候选，未测电池收益；0强停/清数据/AppOps/联网限制 |
| cnss_diag诊断 | UNKNOWN/低优先级，未新增适配 | S6硬件诊断进程1469及其vendor配置 | 先量化写盘/驱动依赖再决定可选诊断门槛 | 约1.2%单核=0.15%八核容量，无高负载证明；不直接停Wi-Fi相关服务 |

全局CPU约1.992%、可用RAM约3.45GiB、低IO/memory PSI、0持续回收/换出/OOM、温控0，缺乏调整频率/ZRAM的依据。数据是USB供电Dozing一分钟，不称全面性能/功耗认证。详见[GLOBAL_PERFORMANCE_A94.md](GLOBAL_PERFORMANCE_A94.md)。

## 2026-10-05 当前增量：A82 metadata 持久化 / A83 蓝牙音频

| 修改 | 分类 | 分区/文件 | 目的与迁移方式 | 状态/风险 |
| --- | --- | --- | --- | --- |
| metadata 从 CACHE 迁至私有非 CE DATA | DEVICE_REQUIRED / VERSION_SPECIFIC | SYSTEM init/hw/init.rc、aconfigd.rc、gsid.rc、plat_file_contexts；DATA /unencrypted/t860-metadata | DATA挂载后绑定canonical /metadata，并在APEX前顺序运行flags；完整保留旧状态和20同类型alias。四文本patch、固定来源Recovery事务和独立A82 COW | 两次实际启动、42模块身份及旧CACHE backing缺失时启动通过；高风险，原凭据/生物识别、运行后协调撤回、首次新安装和完整安装器未认证 |
| 蓝牙音频路由核对 | 无新增适配；此前UNKNOWN故障假设未重现 | 只读Bluetooth/AudioService/AudioPolicy/AudioFlinger；无分区修改 | 铃声RING双端、音乐/视频MEDIA单蓝牙输出分别对照，保留现有S6 HAL | 用户确认双端铃声及蓝牙媒体有声，active媒体sink仅A2DP；当前播放通过，无A83补丁，重连/重启/长时回归未测 |

详情：[METADATA_PERSISTENCE_A82.md](METADATA_PERSISTENCE_A82.md)、[BLUETOOTH_AUDIO_ROUTING_A83.md](BLUETOOTH_AUDIO_ROUTING_A83.md)。原候选profile不改，实机状态另记audit；完整新ROM/ZIP/发布仍未通过。

## 2026-10-05 当前增量：A81 选择性暂停 Google 系统模块安装

用户已授权并完成单XML实机部署、完整PRODUCT回读和独立恢复只读预检。实际普通UID四项权限正反测试通过，Play普通应用真实下载安装并打开通过；第二次启动核心/全部42模块身份及四更新模块62秒保留观察通过。真实Google后台拒绝日志仍未取得，不能将更新UI的检查状态当作端到端拦截认证。

| 修改 | 分类 | 分区/文件 | 目的与迁移方式 | 状态/风险 |
| --- | --- | --- | --- | --- |
| 撤销 Play staged/module installer 资格 | WORKAROUND / VERSION_SPECIFIC | PRODUCT `/etc/sysconfig/google-staged-installer-whitelist.xml` | 只删除Play一个声明元素，保留Galaxy Store；普通非staged APK保持。独立A81源树/生成器/原文patch，不改framework二进制。未来donor重新审计XML与安装检查 | 实机部署及系统权限门槛通过、实际Play安装和二次启动通过；完整源8129项核验。中风险：模块安全更新需维护ROM交付，单独普通APK模块和下载/重试不保证冻结，实际Google后台拒绝与应用升级未测。 |

具体证据、恢复路径和限制见 [MAINLINE_FREEZE_RESEARCH_A81.md](MAINLINE_FREEZE_RESEARCH_A81.md)。源整合证据 `audit/mainline-freeze-stage-ui85-a81.json`；原A80与冻结候选保持。新完整镜像/ZIP和初始UI8 DATA升级仍未完成，A79新版网络模块兼容性不能因此标为通过。

## 2026-10-03 当前增量：A74实际SDK契约候选

| 修改 | 分类 | 分区/文件 | 目的与迁移方式 | 状态/风险 |
|---|---|---|---|---|
| S6 device Java契约28→30 | DEVICE_REQUIRED / VERSION_SPECIFIC | VENDOR /etc/vintf/compatibility_matrix.xml | 固定S6三个API30代码APK的154平台成员/68 SDK类型全部有官方30接口，11编译注解由新ART提供；当前154成员/79类型定义一致。只变两字符，保留12 HAL、VNDK30及全部其他要求；独立profile/patch，不虚报framework28、不复活旧安全API。 | 实机单进程FCM4+SDK30整体GOOD、独立vendor COW通过；未安装。高风险，动态/JNI/业务/完整VINTF及新安装guard/回滚未过。未来UI9复核实际provider与消费者再重放。 |

原S6 stock与working matrix完整SHA相同da6aa90c…；本轮根据当前保留消费者重定契约，不称已知原Samsung构建变量历史。原旧Build true绕过仍不移植。具体证据、原/新文件SHA、sdk30位置/方法、失败记录和未决项见[DEVICE_SDK_CONTRACT_A74.md](DEVICE_SDK_CONTRACT_A74.md)。当前升级包A71仅容许A61 vendor政策变化，新SDK配置须先集成新的升级/恢复协议；本轮设备和冻结包未改。

## 2026-10-02 当前增量：A65/A66/A67

| 修改 | 分类 | 分区/文件 | 目的及新实现 | 状态/风险/迁移方式 |
|---|---|---|---|---|
| A66自遮罩硬件能力 | DEVICE_REQUIRED候选 | SYSTEM /system/etc/floating_feature.xml | S6 stock/旧working版本0，新donor继承1使原BiometricSetting跳过软件光源；只改该字段一字节，原APK/HAL/模板不变 | 工程和Recovery全树回读通过；Mainline回退后开机/HW_LS=false通过，实体照明/认证待用户，暂不纳入整包，高风险；未来按真实S6能力定位重放 |
| A67已激活网络模块隔离 | WORKAROUND / VERSION_SPECIFIC | DATA /data/apex/active/com.android.tethering@372038420.apex | 最新last_kmsg确认19模块更新已激活，固定版本native guard拒绝新tethering manifest；仅保留该文件原inode改非APEX后缀，让apexd选择factory | 不清DATA/不动其余模块/不放行未知Java与native混配；恢复进行中，高风险；不是长期device patch，Mainline可更新能力独立未决 |
| A64完整vendor校验 | DEVICE_REQUIRED安装门槛 | Recovery-only helper/installer | 原S6完整2768项只允许一条A61 policy原/已适配状态，校验所有内容/metadata/xattrs/硬链接 | Linux16项与真实TWRP只读通过；安装集成未验证，Android镜像不包含此工具 |

症状、日志、根因及修改前记录见BIOMETRIC_RUNTIME_UI85_A65.md、MAINLINE_BOOT_REGRESSION_A67.md；原A62正常重启证据保持历史记录，本次新的启动失败独立记录，不能以历史PASS代替当前验证。

## 2026-10-02 当前增量：A60/A61/A62

| 修改 | 分类 | 分区/文件 | 目的/新实现 | 迁移/风险 |
|---|---|---|---|---|
| A60 CPU RT budget | DEVICE_REQUIRED | SYSTEM /system/etc/init/init.t860-bluetooth-rt.rc | 旧v0.23 init时序重实现，foreground950000，保留新Bluetooth APEX | 继续设备层，下一donor验证时机；实机ON/OFF/重启/线程policy1通过，配对未测，高风险 |
| A61 Codec2 mremap | VERSION_SPECIFIC / DEVICE_REQUIRED | VENDOR /etc/seccomp_policy/samsung.software.media.c2-base-policy | 原S6同文件只允许flags3，新运行时拒绝MAYMOVE1；只扩展为1或3，保留所有其他沙箱规则 | 独立patcher+Recovery单文件事务；VENDOR摘要实际改变，其他文件全比一致；服务注册/原升级引导/48帧硬解通过，高风险，未来版本重新定位 |
| A62自动化验证 | 无新增ROM内容 | device/s6/tests/ui85、scripts/*validation_probe*、run_ui85_display_storage_tests.py | 临时隔离APK执行后卸载，原显示偏好恢复、存储临时文件删除；凭据不保存在工程 | 完整范围/实际结果见VALIDATION_RESULTS_UI85_A62.md，发布仍NOT_PASSED |

B08中旧fabric_crypto删除仍仅是WORKAROUND参考。新系统实际缺Fkeymaster；QCC受新SKU启动限制，当前均保留并记录失败，不因可进桌面就删除或声明Knox通过。原A45 ZIP不含后续修复。

## 当前 A58

裁剪依赖更正：原S9 Routines共享android.uid.systemui并请求Launcher READ_SETTINGS，缺包导致SystemUI DeX回调权限崩溃；现恢复同donor未修改APK，实际PMS授权通过。以Telecom可再生成APK-local预编译缓存替代容量，不删除应用。新增文件/缓存删除及完整元数据回读见 ROUTINES_SYSTEMUI_REBASE_A58.md。启动稳定330秒、原凭据真实验证及用户RUNNING_UNLOCKED已确认；3010错误锁屏仍挡桌面，A59兼容分析中。以下旧阶段“最新”均为历史。

# Tab S6 One UI 8 设备适配层审计

最新A55：实机新aconfig early/platform均exit0，原RANGING崩溃消失，29.54秒boot_completed=1。用户确认进入系统后3010；SystemUI反复退出触发RescueParty并返回Recovery，尚非稳定通过。A56仅实机新增指定电脑诊断公钥，原ADB认证保留，E2/完整发布包排除个人key。需读取完整Java异常链再做KG/SystemUI等价适配；SDK28/VINTF、CACHE metadata生命周期、全硬件和保留DATA升级仍未过。以下较早“最新”段均为历史阶段。

最新 A46：实机TWRP只读核对BOOT/VENDOR pin完全相同，原样SYSTEM/PRODUCT回滚副本已保存；当前SYSTEM相对正式NO_DEBUG_ADB包的全树差异只有`/system/build.prop`四诊断属性和新增`/system/etc/init/t860-diag-adb.rc`。两项分类 **WORKAROUND**、目的为旧诊断传输、非硬件必需；不默认迁移到S9。当前A45新donor仍保持ADB认证/非debuggable，若首启取证需要另行诊断实现应按新init/USB依赖重定位。其他旧SYSTEM条目内容/uid/gid/mode/xattr/链接均与发布镜像相同，PRODUCT仅superblock不同。没有修改donor/stage/删除列表或设备；新运行/升级未测。详情见[TWRP_READONLY_PREFLIGHT.md](TWRP_READONLY_PREFLIGHT.md)。

最新 A45：当前完整树已由原新S9 secilc编译policy30/0 permissive，platform摘要按实际CIL/current mapping收尾；8085项仅该65B文件变化。已生成**真实完整SYSTEM/PRODUCT与TWRP实验ZIP**，全内容/metadata回读、e2fsck和原TWRP114块预检通过，删除清单/硬件层不变。SDK28/完整VINTF及新运行/升级仍未通过，不宣称稳定或目标完成。候选在 `out/rom-candidates/A45/`，当前操作是用户手动进入TWRP后只读核对硬件哈希；未刷入。见 [TWRP_UPGRADE.md](TWRP_UPGRADE.md) 和候选manifest。

最新 A44：F04 已在原 S9 SF 上完成 HIDL 后端与两处 FP 根窗口调度，候选两重放一致，并加入隔离 E2。两个入口分别进入新参数准备块，不移植旧二进制或旧代码洞。独立 ELF/父栈 CFI、44 个真实 ARM64 helper 执行案例、原新 linker 的 100 文件闭包列表通过；原 BiometricSetting 的 `UdfpsMaskWindow.getLayoutParams()` 仍设置 `FP Maskview`，APK 保留。全树 8,085 项仅 SF 一项变更，容量复测 SYSTEM/PRODUCT free336,986,112/106,770,432 B、e2fsck0；裁剪清单/硬件层不变。真实 HWC/ET713/namespace/回溯与保留数据升级仍未测，完整 VINTF 未过，无最终镜像/ZIP。见 [FINGERPRINT_HIDL_REBASE_AUDIT.md](FINGERPRINT_HIDL_REBASE_AUDIT.md)；A43及以下为历史阶段。

最新A43：USB旧v0.48.1基线重新采集，版本/加密/Enforcing/九项网络观察与上次相同；物理BOOT/VENDOR哈希仍UNKNOWN。保留vendor light的40B raw修复与新S9Java编码已核对，0–355静态模型通过。F04已解释Null遮罩后端丢失，并生成新S9 HIDL-only后端隔离候选（42B改变、两次相同、12条静态路径）；尚未处理FP窗口dispatch，也未加入E2。当前8,085项全树再次回读与A42完全相同，应用删除清单不变。见[FINGERPRINT_HIDL_REBASE_AUDIT.md](FINGERPRINT_HIDL_REBASE_AUDIT.md)与[BRIGHTNESS_REBASE_AUDIT.md](BRIGHTNESS_REBASE_AUDIT.md)。无最终镜像/ZIP，新运行/dirty upgrade未测；以下较早状态为历史。

最新A42：F03已定向重实现；F07以S6原厂vendor overlay曲线和S9新资源表生成两RRO，原新idmap2八资源映射/全树/精确容量通过，当前8,085项。F04新Java自带旧optical/type修复，具体旧操作标OBSOLETE_CANDIDATE，native mask仍UNKNOWN。完整VINTF、实际硬件/保留数据升级未测，无最终ROM/ZIP。当前原因/脚本与分类见[DVFS_REBASE_AUDIT.md](DVFS_REBASE_AUDIT.md)、[BRIGHTNESS_REBASE_AUDIT.md](BRIGHTNESS_REBASE_AUDIT.md)、[DISPLAY_REBASE_AUDIT.md](DISPLAY_REBASE_AUDIT.md)；下面A39/A40等为历史。

A39：固定S6 vendor/ODM完整Java归档盘点8包/3代码包，其366方法/53字段/119类型引用在实际原新framework/ART定义中全部解析；154条平台成员引用独立解码对应，仍不宣称完整SDK28/JNI/运行支持。保留vendor要求，SDK28为UNKNOWN继续追踪，未加数字或改硬件镜像。FCM4以官方冻结HAL+已核对的4.14 kernel要求生成诊断XML，新libvintf能解析/合并；真实BOOT适用231条config无缺口，正式metadata/kernel/运行gate仍未过。E2全8,246条目与A38结束一致，删除清单/所有APK未改。详见[SYSTEM_SDK_REBASE_AUDIT.md](SYSTEM_SDK_REBASE_AUDIT.md)、[VINTF_REBASE_AUDIT.md](VINTF_REBASE_AUDIT.md)。

A38：真实split型号/名称DEVICE_REQUIRED，在新三份build.prop只改六值，保留donor软件身份、通用qssi及T860硬件导入；旧vendor.device=gts8wifi仍为待验证DONOR_SPECIFIC，不改固定硬件镜像。真实B04 APEX另配独立VNDK30 framework fragment（DEVICE_REQUIRED/新位置VERSION_SPECIFIC），176 B新增，无其他原文件变化。原新libvintf实际诊断发现system SDK28不匹配与弃用检查缺4；未据此删除vendor要求或伪造SDK支持，UNKNOWN继续追踪。Linuxdump无真实property/APEX/kernel上下文，不作完整checkvintf或Android运行成功证据。具体文件/原因/风险/迁移与撤回见 [IDENTITY_INIT_REBASE.md](IDENTITY_INIT_REBASE.md)、[VINTF_REBASE_AUDIT.md](VINTF_REBASE_AUDIT.md)。

A37同树整合：已按原新输入SHA/配对要求安装B05、F02/F01-ICCC/WIRE和floating/camera硬件值。分类保持原表，新增处理仅为新services自身四个过期编译/profile文件（VERSION_SPECIFIC，不是长期硬件patch）。全树仅六安装/四cache移除，其余文件/链接/metadata相同，原APK/ART/APEX/BOOT/VENDOR/DATA保留。精确容量通过，动态显示/CE/TEE/硬件功能未测。新三分区身份和init导入位置已只读核对，身份仍待修改；迁移位置/方式/风险/撤回见 [DEVICE_STAGE_INTEGRATION.md](DEVICE_STAGE_INTEGRATION.md)。

A36 网络启动整合：DEVICE_REQUIRED 是让固定4.14硬件使用兼容的新网络实现；VERSION_SPECIFIC 为原X710 init加载点的check→bind→bound→真实loader顺序、19,928 B新helper和精确contexts、两条校验所需只读规则。六个文件由原新输入重建，已安装到独立E2副本并通过本地73项、两次输出重放、策略/29标签/容量检查；原APEX和loader退出码/真实加载状态保留。没有迁入旧wrapper/native/APEX/framework。Android实际namespace/绑定/AVC/网络/升级仍未验证，详细位置、理由、风险和撤回在 [TETHERING_BOOT_INTEGRATION.md](TETHERING_BOOT_INTEGRATION.md)。

构建增量 A35/E2（2026-10-01）：九个 X710 原 APK 的本地 preopt 为 `VERSION_SPECIFIC` 容量调整，非 S6 硬件能力修复。独立副本只移除 `app/{ARCore,HiyaService,HoneyBoard,LiveTranscribe}`、`priv-app/{SamsungCamera,SamsungCloudClient,SamsungContacts,SamsungGallery2018,SecMyFiles2020}` 下的 `oat/`，九 APK/28 DEX 保留。配合较少 inode，并计入真实新 B06 native/CPU/CIL 后，精确 SYSTEM/PRODUCT 容量子门槛通过；不需要新增 E1 的四项应用删除。文件/理由/风险/输出位置与证据在 [CAPACITY_DECISIONS.md](CAPACITY_DECISIONS.md) A35/E2，脚本/profile 已建立。未来 UI9 重核 APK DEX 是否完整再清理对应缓存，不能默认所有缓存可删。真实 APEX 绑定、其他适配/完整镜像/VINTF/保留 DATA 和九应用编译运行仍待完成，尚无新 ROM ZIP。

审计日期：2026-09-29。此文档是 **构建前的只读分析基线**，不是 S9 ROM 的完成声明。目录中没有题述的 `roms/`；实际输入是根目录的 T860、X700、X710 三个官方固件 ZIP，`t860-ui8/` 中的逐版脚本、v0.48 分区镜像、日志，以及 `t860-ui7/` 的历史资料。没有独立的 `s6_ui7_working` 分区镜像可做逐字节四方 diff；UI7 资料只用于交叉核对 T860 设备补丁。UI8 v0.47 是旧工程记录的真机验证基线；v0.48/v0.48.1 是其后发布处理，不能把发布包审计等同于重新完成所有真机测试。

## 1. 输入、分区与版本

| 角色 | 已核对来源 | 系统版本及布局 | 对本次 rebase 的含义 |
|---|---|---|---|
| T860 硬件基线 | `SAMFW.COM_SM-T860_XAR_T860XXS5DWH1_fac-2.zip`；旧工程 `inputs/t860-dwh1/` | Android 12、SDK 32、One UI `40101`；AP 有 `boot.img`、`dtbo.img`、`system.img.ext4`、`vendor.img.ext4` 等。原 PIT 大小：SYSTEM 6,534,725,632 B、PRODUCT 1,048,576,000 B、VENDOR 1,379,926,016 B。 | Kernel/DTBO/vendor/VNDK30/原生 HAL 是硬件契约。T860 官方 camera feature、floating feature 可作为硬件值来源。 |
| X700 原 donor | `SAMFW.COM_SM-X700_XAR_X700XXSBEZE1_fac.zip`；`t860-ui8/inputs/x700-eze1/super.img.lz4` | Android 16、SDK 36、One UI `80000`；super 中 SYSTEM 6,914,449,408 B、PRODUCT 1,525,723,136 B、SYSTEM_EXT 215,293,952 B，另有 VENDOR、ODM、VENDOR_DLKM；逻辑分区为 F2FS。 | 与旧成品进行文件级差异分析；不再作为新构建输入。 |
| T860 UI8 成品 | `t860-ui8/out/v0.48/`，逐版原因在 `t860-ui8/docs/PORTING-NOTES-v*.md` | SYSTEM/PRODUCT/VENDOR 重建为 T860 PIT 大小的 sparse ext4；X700 SYSTEM_EXT 合入 SYSTEM 的 `/system_ext`。 | 提供旧 patch 的目的和验证记录；旧核心二进制不是 S9 输入。 |
| X710 新 donor | `SAMFW.COM_SM-X710_XAR_X710XXS6EZH3_fac.zip`；本次提取的 `t860-ui8/inputs/x710-ezh3/super.img.lz4` | Android 16、SDK 36、One UI `80500`，安全补丁 2026-08-05；SYSTEM 7,567,130,624 B、PRODUCT 1,466,732,544 B、SYSTEM_EXT 179,093,504 B；另有 VENDOR、ODM、SYSTEM_DLKM、VENDOR_DLKM；逻辑分区为 EROFS。 | 必须重新解包、重定位并重建 T860 可挂载的分区，不能刷入 X710 super/vendor/kernel。 |

X700 与 X710 的系统同为 Android 16，但 One UI、构建基线和几乎所有核心 framework 构件不同。X710 vendor 为 `gts9wifi`、vendor SDK/VNDK 33；T860 原 vendor 为 VNDK 30。X710 AP 还带 `vendor_boot`、`init_boot`；这不代表 T860 的原启动布局可照搬。

只读挂载下的 apparent tree 大小：X700 SYSTEM 约 8.0 GiB、SYSTEM_EXT 266 MiB、PRODUCT 1.9 GiB；旧成品 SYSTEM 约 6.0 GiB、PRODUCT 726 MiB；X710 SYSTEM 9,417,572,460 B、SYSTEM_EXT 279,749,264 B、PRODUCT 2,072,816,197 B。此处容量脚本须以 root 权限读取只读挂载树；第一次普通用户扫描漏算约 75 MiB，已重算并修正审计文件。旧 `system-trim-list.txt` 对 X710 中仍存在的路径合计 2,670,016,061 B，`product-trim-list.txt` 合计 1,397,956,764 B。即使套用这些**尚未批准的容量删除**，X710 SYSTEM 与 SYSTEM_EXT 仍有 7,027,305,663 B，高于 T860 的 6,534,725,632 B SYSTEM 物理容量，至少差 492,580,031 B，且还未留 ext4 元数据与安全余量。旧 T860 内核配置明确 `CONFIG_EXT4_FS=y`、`CONFIG_F2FS_FS=y`、`CONFIG_F2FS_FS_COMPRESSION` 未启用；没有 EROFS 配置项。不能把 X710 EROFS 镜像当成现成的容量解法；容量是构建硬门槛，不能为了出包直接无审查地扩大删除范围。

`docs/audit/` 保存逐路径原始清单。X700→旧成品分别有 SYSTEM 1525、SYSTEM_EXT 18、PRODUCT 117 行；T860 stock→旧成品 VENDOR 有 189 行。目录移动、预编译 oat/vdex 与大批容量裁剪占多数；真正同路径内容变化在 SYSTEM 16 个文件、SYSTEM_EXT 4 个文件、PRODUCT 1 个文件。`framework-res.apk` 和 `SystemUI.apk` 在旧 X700 成品中与原 donor **逐字节相同**，而在 X710 中均已更新。

## 2. X700 UI8 → T860 UI8 的重要改动及分类

表中“迁移”表示迁移**适配目的**，不表示复制旧文件。风险为新 donor 上未验证时的初始等级。`条件`必须先完成相应日志、接口或代码检查。分区路径以设备挂载路径表示。

### 2.1 启动、分区、接口与网络

| ID | 旧成品相对原包的具体改动 | 分类 | 目的与旧证据 | X710 对应位置；迁移判断/方式 | 风险 |
|---|---|---|---|---|---|
| B01 | `/boot` 使用 T860 内核和 ramdisk，后续 v0.40–43 加 fs-verity、FastRPC PM；`/dtbo` 与 T860 stock 哈希完全相同 | DEVICE_REQUIRED | 官方硬件启动与 SensorDSP。stock BOOT SHA `714ae657…`，v0.48 BOOT `523664a8…`，DTBO 均 `864ca763…`；见 v0.42/43 记录和 `kernel/patches/`。 | 不采用 X710 BOOT/DTBO/init_boot/vendor_boot；从 T860 已审计内核补丁源重建 BOOT，核实 ramdisk/fstab 与新 system 的需要。 | 极高 |
| B02 | X700 `system`+`system_ext` 合并进 T860 SYSTEM，PRODUCT/VENDOR 重建为物理 PIT 尺寸 sparse ext4 | DEVICE_REQUIRED | T860 没有 X700 的动态 super 布局；`build-v0.1-in-linux.sh` 固化物理尺寸。 | X710 EROFS 三分区重新提取成树，保留 `/system_ext` 结构但合入 T860 SYSTEM；PRODUCT 独立 ext4。先过容量、inode、SELinux/xattr、e2fsck 门槛。 | 极高 |
| B03 | `/vendor` 以 T860 stock 为底重建；原 HWC、vndservicemanager、gralloc 和 `ro.vndk.version=30` 不变 | DEVICE_REQUIRED | 原 HWC SHA `6520df51…`、vndservicemanager `7a676899…` 在 stock 与 v0.48 一致。 | 继续以 T860 stock VENDOR 为底，按显式补丁重放；X710 VENDOR/ODM/DLKM/固件仅作接口参照。 | 极高 |
| B04 | `/system_ext/apex/com.android.vndk.v30.apex` 新增；`mapping/30.0.cil` 增加 263 个属性声明 | DEVICE_REQUIRED | 旧 vendor VNDK30 与 Android 16 system SELinux 兼容；首版脚本和差异均确认。 | 已验证：X710 SYSTEM_EXT 只有 `com.android.vndk.v33.apex`，无 VNDK30（T860 vendor `ro.vndk.version=30`）；沿用已实机验证的固定输入 `com.android.vndk.v30.arm64.apex`（SHA `d0db2522…`，`inputs/compat` 与 `compat-arm64-a16` 两份一致）。X710 `mapping/30.0.cil` 有 264 个 expand 但未声明的 typeattribute（旧 X700 为 263）；`device/s6/vndk30-ui85.json` 与 `patches/apply_vndk30.py` 已在隔离副本按输入/输出哈希重放，输出 owner/mode/label 正确，结果见 `docs/audit/vndk30-ui85-probe.json`。正式诊断 ROM 与实机 APEX 激活仍待验证。 | 极高 |
| B05 | `surfaceflinger` API28 分支补丁、`t860-display-compat.rc`、旧 HWC 共存；后续指纹 mask 与 EarlyWake 原生补丁 | VERSION_SPECIFIC | 旧 4.14/旧 HWC 首屏、UDFPS、最近任务；`patch-surfaceflinger-*.py` 与 v0.47 trace。 | 新 selector `0x568d70` 的单 CMP34→28与配对init已准备；69条指令独立核验、7项拒绝与32组静态分支模型通过。未应用或实机测试；FP mask/EarlyWake和邻近gates须另审计。见 `DISPLAY_REBASE_AUDIT.md`，禁止旧ELF覆盖。 | 极高 |
| B06 | X700 BPF 程序替为 A16 GSI 兼容集；`bpfloader`、`netd`、Tethering CAPEX、NetworkStack、私有 lib 与 init bind 经过多轮修复 | VERSION_SPECIFIC；解释器/权限需求DEVICE_REQUIRED；旧status wrapper等WORKAROUND | 适配 T860 4.14 BPF、CLAT、共享签名和 Wi-Fi `VALIDATED`；v0.4–18、v0.20。 | 已从保留BOOT确认4.14.190/JIT=n，审计新25/旧7 platform对象、新旧五个network对象及114/99个metadata声明。新SDK36.1 loader要求最高5.10，先因V+4.19失败；新libnetd在cgroup2查询成功后另abort。新两native的六条分支候选已独立解码/12项拒绝，未应用；已审八个native函数/38个pin literal，JNI仅接收errno2/524的新四指令候选已独立校验，尚未应用；已确认SDK3610自有loader、4.14跳过kernel BTF及36map/25program选择；实际BOOT Image中所需类型/必需helper存在，四optional缺125。已合并policy做19查询；A33已核对原S9 init使用-N/-c30；同vendor旧/新策略均按原参数静态编译成功且0permissive domains，严格248/264冲突保留审查，不当作启动失败。实际内核path-label白名单无bpf；CLAT候选已实现，A34新CIL仅加network_stack例外及三权限allow，按原init参数编译、严格冲突不增、其他规则/组件不变，仍待实机labels/AVC/网络。新CLAT data-only标签候选已独立验证，四native从原新APEX目录组合25文件并重放/metadata回读；未bind/应用ROM。verifier/maps/cache/namespace、platform GPU与容量仍待审。保留新netd/CAPEX/全局libs，禁止旧族直接覆盖；见`BPF_REBASE_AUDIT.md`。 | 极高 |
| B07 | `/system/etc/init/netd.rc` 启用 `persist.vendor.net.doxlat` 映射，保留 `stdio_to_kmsg`；另有 `t860-*net*.rc` | WORKAROUND | 前者解决旧 kernel/CLAT，后者是诊断残留；文件级 diff 已确认。 | 检查 X710 的 netd/Tethering 接口与 T860 属性后按需重写 init；默认不带诊断 `stdio_to_kmsg`。 | 高 |
| B08 | `/vendor/build.prop` 设 `ro.apex.updatable=true`；`boringssl_self_test.rc` 去重启行为；`fabric_crypto.rc` 移除，补挂载目录和少量 SELinux | WORKAROUND | 旧首启阻塞与 APEX 加载；v0.1 脚本和运行日志。 | 针对 X710 `/system/etc/init/fabric_crypto.rc`、T860 vendor init 的实际服务依赖逐条复核，保留可证实的必要项。 | 高 |
| B09 | T860 VBMETA flags 0→3，固定 TWRP，并删 vendor 的 `vendor_flash_recovery.rc`、`recovery-from-boot.p`、`install-recovery.sh` | WORKAROUND | 旧 Odin/TWRP 刷写策略和 AVB；stock→working vendor 清单证实删除。 | 先设计 X710 新构建的 AVB/启动链与测试刷写方法；不得直接继承“关闭校验”作为发布安全策略。 | 极高 |
| B10 | 旧 release 去掉 `ro.debuggable`、`ro.force.debuggable`、强制 adbd init，默认仅 MTP | DEVICE_REQUIRED | v0.48 审计有脚本与属性；首版诊断 ADB 不属于正式适配。 | X710 构建脚本应把诊断/发布 profile 隔离并断言 release ADB 认证开启。 | 中 |

### 2.2 Samsung framework、硬件功能与应用

| ID | 旧成品相对 X700 的改动及文件 | 分类 | 目的与旧证据 | X710 对应位置；迁移判断/方式 | 风险 |
|---|---|---|---|---|---|
| F01 | `/system/framework/services.jar` 中 KnoxGuard/ICCC 路径补丁 | WORKAROUND；新 ICCC 部分另属 DONOR_SPECIFIC | 旧 BAD_VALUE/未检查 HIDL Return 堆栈证明 ICCC transport mismatch；T860 HAL 确实存在，不能笼统说缺失。旧八方法 stub 会在新 donor 移除权限检查并伪造部分整数状态，不能照搬。 | 已准备三处新 native 调用降级，保留权限/锁/其他查询；还发现同名1.0接口的 measurement/terminate 编号6/7→8/9，须配对新 system 接口库的两条常量映射。F02+F01组合 JAR `d47261aa…`、原生库 `ffb6b7e9…`，重放/独立反编译与拒绝测试通过，仅探针，未应用。7 个 APK/JAR 消费者及32/64 native链已索引，企业缺失分支/TEE/32位/实机仍待核验。新 `kg30_setRemoteLockToLockscreen` 本来已是 unsupported；其余 KG 状态/锁 workaround 单独保留 UNKNOWN。见 `ICCC_REBASE_AUDIT.md`。 | 极高 |
| F02 | `services.jar` 的 `LockSettingsService.unlockCeStorage` 走无 HAT 分支 | VERSION_SPECIFIC | v0.20 真机 `RUNNING_UNLOCKED`；旧日志确有 vold 拒绝非空 HAT。重新核对发现旧成品 vold 来自 X700 Android16（v0.35 时区补丁），旧笔记称 Android12 vold 不准确。 | 已按 X710 新 `StorageManagerInternalImpl` 调用、field/寄存器与现有空 HAT 目的地重写：`patches/patch_services_ce_unlock_ui85.py` + `device/s6/ce-unlock-ui85.json`。只改一条等宽分支，独立反编译/双 DEX/ZIP/拒绝测试通过，输出 `29363c60…`；候选未应用。旧 DATA/PIN、Keystore/SDP/工作资料待实机验证，见 `CE_UPGRADE_AUDIT.md`。 | 极高 |
| F03 | `/system/framework/framework.jar` 的 `SemDvfsManager`/`SemDvfsHyPerManager` 对 T860 原生 DVFS 档位映射，配原签名 A16 SDHMS | DEVICE_REQUIRED逻辑；DONOR_SPECIFIC数组；VERSION_SPECIFIC定位/缓存 | X700加密SSRM策略使用SM8450档位，v0.21实机解决同类问题。 | A41已在原X710 `classes6.dex`改两个getter/setDvfsValue，用新策略八CPU/六GPU alias与动态HAL floor，保留新SDHMS/selector；失效准确boot graph/SDHMS编译缓存，模型3996用例与全树核对通过。OverLimit、HAL单位/温控、ART及dirty upgrade未测。见 `DVFS_REBASE_AUDIT.md`。 | 高 |
| F04 | `/system/framework/framework.jar` 与 `/system/lib64/libgui.so`、`libui.so`、SurfaceFlinger 调整 ET713 UDFPS 类型/usage/mask；`floating_feature.xml` 改 optical | DEVICE_REQUIRED整体；两旧native及两Java操作为OBSOLETE_CANDIDATE | v0.25/27 真机实体录入与锁屏验证；T860 stock 原值是 `optical_display_phone`。 | X710原生optical tablet，libgui初始化已有FP窗口bit34，libui原生invalid masks已含旧修复值，先保留新原件、不应用旧两项操作。新Java已optical/position2/HIDLtype3，保留原件。A44仅在新SF重写Null→新HIDL后端和两处FP根窗口→原mask参数准备分流，加入隔离E2；脚本/profile/汇编、27,700原EH条目及父CFI、44真实ARM64案例/容量通过。新BiometricSetting原根标题已确认，APK不改。HIDL wire/实际namespace/CFI调用/HWC/ET713/lifecycle仍待验证；见 `FINGERPRINT_HIDL_REBASE_AUDIT.md`。整个指纹适配不可标为废弃。 | 极高 |
| F05 | 新增 AIDL face service、manifest、CDSP 模型/依赖及 vendor SELinux；`debug.t860.face.enroll_backend=0` | DEVICE_REQUIRED | 旧 v0.25/28 实体人脸录入与认证，vendor stock 无该服务。 | 从 T860 stock vendor 和可溯源旧桥接代码重建，不引 X710 face HAL；X710 biometric framework/manifest 与 AIDL 版本先匹配，再做真实注册验证。 | 极高 |
| F06 | `/system/cameradata/camera-feature.xml` 改主摄 4128×3096、前摄 3264×2448、广角 2576×1932 与 ID；`floating_feature.xml` 去不兼容相机库；scene detector/FastAEC、portrait release 补丁 | DEVICE_REQUIRED | T860 stock XML 证实传感器尺寸；v0.26 真机验证广角逻辑 ID `2`/底层物理 ID `50`，以及前摄逻辑 ID `1`、后摄 `0`。当前 UI8 `dumpsys media.camera` 也公开 0/1/2。 | X710 `camera-feature.xml` 无广角分辨率和 ID，且把 `FRONT_NORMAL_CAMERA_ID`/`FRONT_CROP_FOV_CAMERA_ID` 设为 `2`（在 T860 是广角）。用 T860 UI7/UI8 已验证逻辑映射和 stock 硬件尺寸在 X710 原 XML 定向修改，并检查新 SamsungCamera、`libSceneDetector_v1.camera.samsung.so` 对新字段的消费；不复制旧库。 | 极高 |
| F07 | T860 355阶亮度/HBM/自动与指纹RRO，`floating_feature.xml` AMOLED；`/vendor/bin/hw/vendor.samsung.hardware.light-service` 的40B raw-level修复 | DEVICE_REQUIRED | v0.24/28真机255/305/355与HBM；A43确认working vendor中light SHA e3e1…，原厂348cb…仅40B不同。 | A42七曲线/355以新表重编两RRO并加入SYSTEM_EXT，原新idmap2八映射通过；A43原S9 BacklightAdapter/LightImpl与保留AIDL light接口匹配，0–355静态编码模型通过，无需重做vendor patch。新资源选择/实际路径/auto/HBM/UDFPS仍未测，见 `BRIGHTNESS_REBASE_AUDIT.md`。 | 高 |
| F08 | `floating_feature.xml` 的 mDNIe `57137`、安全桥接、`T860ColorTemperature.apk` 和 `whiteRGB` sysfs | DEVICE_REQUIRED | T860 stock 同为 `57137`；旧 v0.24 真机写入成功。 | X710 `floating_feature.xml` 是 `65303`；在新 Settings/框架中确认 RGB 入口与写入链，再使用可重编译设备 APK/小范围权限。 | 高 |
| F09 | T860 sysinput 双击唤醒、`vendor.samsung.hardware.sysinput@1.2-service` 修改与 SELinux | DEVICE_REQUIRED | v0.24 实机 Doze→Awake；T860 原生设备节点。 | X710 自身 sysinput AIDL/HAL 已不同；保留 T860 1.2 硬件服务，只对 X710 framework/Settings 接口做桥接和定向 policy。 | 高 |
| F10 | `/vendor/etc/mixer_paths_tavil.xml` 四功放 slot fanout、`/vendor/etc/audio_effects_sec.xml` 与 `/vendor/bin/hw/android.hardware.audio.service`，移除无效私有 AEC | DEVICE_REQUIRED | 旧 v0.24 四个 CS35L41 同时启动；v0.39 去无效 AEC。 | T860 stock vendor 重放最小 mixer/Audio HAL 补丁；检查 X710 音频 policy 对旧 HAL 的 profile/route，先验证有声再四扬声器；私有 AEC 单独判断。 | 高 |
| F11 | `/system/bin/vold` 改 `sdfat` 时区参数 | VERSION_SPECIFIC | 旧 v0.35 SD 卡挂载 `tz=UTC` 成功。 | X710 `vold` 已不同；实测 T860 SD 卡，若重现 `EINVAL` 才在新 vold 的 mount 参数处做等价修复。 | 高 |
| F12 | `/system/etc/floating_feature.xml` 增 S Pen 充电侧位置信息、alert；恢复 AirCommand、HWRDB 中英文库 | DEVICE_REQUIRED | T860 stock garage spec 同旧成品；v0.38 S Pen 离线手写通过。 | X710 新 AirCommand/Notes/HoneyBoard 优先保留；仅适配设备 spec 与必要本地库，检查新包/数据库格式。 | 中 |
| F13 | AOD 充电信息开关、Edge panel 几何、DailyBoard 所需 DynamicLockscreen provider；`ro.product.vendor.device=gts8wifi` 与固定 `init.gts6lwifi.rc` | DONOR_SPECIFIC | v0.35 查明 X700 Launcher 无 `gts6lwifi` 几何表，旧工程选 `gts8wifi` 平板 profile，同时固定真实 T860 硬件 init；实机属性与脚本吻合。另有旧容量裁剪误删 provider。 | X710 先检查 Launcher 对 `gts6lwifi`/`gts9wifi` 的表与新 overlay；优先做面板资源定向适配，若必须伪装 profile 则同时断言 T860 init 导入。AOD 与 provider 独立验证。 | 中 |
| F14 | CSC `T860OXM5DWH1`、XAR/US、设备营销名称、FCC/充电规格、Samsung Notes/Bixby/Smart Suggestions | DEVICE_REQUIRED（身份/Smart Suggestions）；Bixby 为容量候选 | T860 stock 特征与 v0.44 运行日志；旧 Smart Suggestions 曾被误裁掉，后恢复到 PRODUCT。 | X710 的 Samsung Notes、Settings/Account 和 Smart Suggestions 保持新版本与签名/权限族；只生成 T860 CSC/identity 和设备文案，绝不改写新 donor 版本号为旧 `T860XXS5DWH1`。用户选择裁可选 AI/预装，Bixby 候选详见容量决策；其移除需做入口与依赖检查。 | 高 |
| F15 | v0.39 移除 X700 QCC、Heatmap，对 SNAP AIDL 阻塞服务发现改非阻塞 | WORKAROUND | X700 特定服务风暴与不存在的 HAL；真机安静窗口通过。 | X710 新 vendor 自有 SNAP/thermal，但 T860 不会提供。检查 X710 调用者与超时日志，优先裁掉 donor 专属组件/可选 feature，必要时才改新 `.so` 的查询逻辑。 | 高 |
| F16 | v0.42 内核 fs-verity 与 `system_server` 对 `users_system_data_file` 的 ioctl xperm；v0.43 FastRPC PM request 5 | DEVICE_REQUIRED | 旧内核上 odsign、SensorDSP 测试通过；补丁有源码与实机前后日志。 | 重建 T860 BOOT 时保留并重新审计这两项内核补丁；X710 新 ART/APEX 与旧内核接口仍要验证。 | 极高 |
| F17 | v0.45–47 低/高分辨率任务快照比例和 SurfaceFlinger EarlyWake 权限 | WORKAROUND | 旧 UI8 特定卡顿；v0.47 trace 有定量改善。 | X710 `services.jar`、PRODUCT RRO、`surfaceflinger` 均变化；仅在复现卡顿和拒绝后定位新实现。 | 中 |
| F18 | `framework.jar` build consistency 弹窗门槛抑制 | WORKAROUND | v0.24 旧混合构建避免“Android 内部问题”弹窗。 | X710 首先保持真实且自洽的 build/vendor 身份；如仍出现弹窗，用属性/检查调用链定因，不默认绕过新框架检查。 | 高 |
| F19 | 大量 TTS 语言、预装/AI 应用及模型裁剪，旧误删的 Galaxy Store/ClockPack/DressRoom/DynamicLockscreen/Smart Suggestions 曾恢复 | OBSOLETE_CANDIDATE | 旧物理容量限制；`config/*trim-list.txt` 记录路径，但不全是兼容修复。 | 对 X710 重新做依赖、签名、许可和空间审计；仅裁可证明可选资源，保留 Samsung Settings/Account/Knox/输入/核心 provider。 | 高 |

旧成品 **没有**修改 `framework-res.apk`、`SystemUI.apk`、绝大多数 Samsung framework JAR/APK；这些文件仅用于版本对照。`/vendor/build.prop` 中 `ro.product.vendor.device=gts8wifi` 的原因已由 v0.35 笔记、脚本和当前实机属性互证，属于针对 X700 profile 表的 `DONOR_SPECIFIC` 绕法，不能照抄到 X710。旧 `/system/etc/init/netd.rc` 的 `stdio_to_kmsg` 是待清理的诊断痕迹，归 `OBSOLETE_CANDIDATE` 而非自动删除。

DEX 041 的第二逻辑 DEX 需要容器感知解析。X700 `services.jar` 两段为 9,864,688 / 15,347,188 B，X710 为 10,073,648 / 16,382,652 B。用旧工程的只读 `DexContainer` 解析器按 class/method/descriptor 核对后，X710 的 KnoxGuard `getTAStateSetError`、`Utils.getStateAndSetToKGSystemProperty`、两条 `Utils.setRemoteLockToLockscreen` 与 ICCC 八个旧目标都仍存在；相应指令 SHA-256 均不同。X710 的 ICCC `getSecureData(I)I` 从 10 个指令单元增至 16 个。仅用普通 baksmali 列第一个逻辑 DEX 会错误得出 KnoxGuard 类已删除。`KnoxGuard.apk` 中的 `getTAStateSetError` 是对 framework `KnoxGuardManager` 的调用点，不是旧服务实现所在。

## 3. X700 UI8 → X710 UI8.5 donor 自身变化

全路径差异见 `docs/audit/s8-to-s9-*.rsync`，SYSTEM 4370、SYSTEM_EXT 864、PRODUCT 155、VENDOR 3914 行。同名文件大面积内容改变是 donor 升版事实，不是 T860 补丁。

| 子系统 | 已核对的变化 | T860 风险与检查点 |
|---|---|---|
| Framework/SystemUI | `framework-res.apk`、`framework.jar`、`services.jar`、`system_ext/priv-app/SystemUI/SystemUI.apk` 哈希全变；系统 build ID 从 `BP2A.250605.031.A3` 到 `BP4A.251205.006`。 | 旧方法/资源/偏移不能直接复用；逐类、逐资源重定位。 |
| 产品 overlay/权限 | PRODUCT `framework-res__gts8wifixx__auto_generated_rro_product.apk` 被 `gts9wifixx` 版取代；权限 XML 整体同样为 290 个但内容有差异；新增 VirtualDeviceManager/开发者验证等。 | 设备 RRO 必须以新 framework resource 表编译；签名与 privapp allowlist 需重审。 |
| VINTF/HAL | X700 vendor VNDK32→X710 VNDK33；X710 指纹、Samsung camera provider、health、sysinput、sensors、DRM 等 manifest/service 名称从 HIDL 世代转向不同 AIDL 实现。通用 framework matrix 5–8 在两包哈希相同，但 `compatibility_matrix.device.xml` 有 display config 1–12→1–13、KeyMint extension 1–2、SKPM HIDL→AIDL、新 displayquality、Widevine key provisioning 等变化；display composer/mapper 仍是新 Qualcomm vendor 组合。 | T860 vendor 仍为 VNDK30，HWC 2.4 与旧硬件 HAL；用 T860 manifest 与 X710 framework matrix 做机器化兼容检查，逐项找 shim/可选声明，尤其检查安全/DRM 实例，不可凭文件名认为兼容。 |
| SELinux/init | 两者有 `mapping/30.0.cil`，X710 stock 相对 X700 加入少量类型/属性，但没有旧成品的 263 项补充；X710 实测缺口为 264 个未声明 typeattribute；`fabric_crypto.rc` 仍存在。 | 已对 X710 staging 副本重算 mapping 缺口（264 项，可重放 `patch-mapping30.sh`）；仍需核对 service/property/file contexts；拒绝直接替换新 plat policy。 |
| 显示/生物识别 | X710 floating feature 原生 AMOLED、`optical_display_tablet`、mDNIe `65303`；X700 为电源键指纹、mDNIe `0`。 | AMOLED 旧补丁可能多余；T860 原生 `optical_display_phone`/`57137` 和 ET713 mask 仍需验证。 |
| 相机/媒体 | X710 camera-feature 保留前摄 4000×3000，缺少旧 X700 广角配置；模型文件由 sm8450 转向 sm8550，media/codec 服务与库已换版。 | T860 的 0/1/2、物理广角 ID 50 和尺寸不能从 X710 推断；避免新 donor 模型/后处理库硬件误调用。 |
| BPF/网络 | 部分 X700 `.o` 改成 X710 `.bpf`，新增/删除多个 BPF 对象；Tethering、NetworkStack、netd 都换版。 | 旧 GSI 兼容族是否仍适配须以内核加载、map、Wi-Fi/CLAT 日志验证。 |
| 音频/BT/安全 | X710 vendor 提供不同蓝牙音频、AIDL DRM、更新 Knox/安全服务；X700 vendor 本身也不是旧成品的 vendor。 | 不移入 X710 HAL、固件或安全服务；分析 X710 用户态对 T860 原 vendor 的实际要求。 |

## 4. T860 stock → UI8 成品的硬件来源核实

T860 原厂 `/system/cameradata/camera-feature.xml` 的主摄 `4128x3096`、前摄 `3264x2448`、广角 `2576x1932`，原厂 floating feature 的 UDFPS `optical_display_phone`、mDNIe `57137`、AMOLED 标记和 S Pen 侧位置信息均与旧成品适配目标相符。这些是可从真实设备基线迁移的值，而非 X700/X710 的猜测。原厂 vendor 的 HWC、vndservicemanager、gralloc 在旧成品中哈希不变。VENDOR 同路径内容变化主要在 `build.prop`、audio/light/sysinput HAL、audio effects/mixer、init、SELinux 与少量 kernel modules；新增 face/CDSP 与蓝牙音频桥接，删除 stock recovery 恢复链。详细路径在 `stock-to-working-vendor.rsync`。

旧成品 BOOT 与 stock 不同是明确的 T860 内核补丁结果，不是 S8 BOOT；DTBO 与 stock 逐字节相同。VBMETA flags 改动与 TWRP 是旧刷写策略，并非硬件兼容性的天然要求。T860 stock vendor VINTF 包含 HWC 2.4、health 2.1、GNSS 2.1、旧 DRM、Wi-Fi、thermal、ICCC 等，旧成品增加 face 与蓝牙音频声明；X710 VENDOR 列表不作为替代来源。

## 5. 尚未理解、需实验决断的修改

1. **KnoxGuard/ICCC 默认/空响应**：ICCC 已有具体 wire 差异与新最小组合候选，旧八方法 stub 不迁移；未授权拒绝、TEE/共享内存、错误返回/32位范围和企业降级运行仍未测。KnoxGuard 状态与 RemoteLock 的旧 workaround 尚未证明，新增 KG30 方法已由 donor 自身返回 unsupported，不再额外 patch。
2. **旧 face/CDSP 与蓝牙 audio bridge 的具体 ABI**：原厂 T860 无对应 Android 16 AIDL 服务；需要对 X710 framework matrix、AIDL 版本、SELinux 和实际认证/耳机测试。
3. **X710 新相机/媒体后处理对旧 T860 HAL 的要求**：单看 camera feature 不足以判断库依赖。需记录 camera ID、stream combination、JPEG/视频编码、tombstone。
4. **旧早唤醒、快照比例、`netd.rc` 诊断输出及容量裁剪**：只有复现、依赖检查或 trace 才能决定保留。不能以“旧成品有”为依据。
5. **EROFS→ext4 的容量与文件元数据**：旧 trim 路径仍不足以保证 SYSTEM 装入；必须按每个候选应用/资源的依赖和用户功能损失审批技术方案，重建后核对 owner/mode/SELinux xattr 与余量。

下一步逐文件、逐阶段执行顺序见 [S9_REBASE_PLAN.md](S9_REBASE_PLAN.md)。任何首次刷机、启动日志与缺陷修复须写入 [PORTING_LOG.md](PORTING_LOG.md)。

### B06 平台子链补充（A30）

原新Rust loader在user/4.14选18map/6program，GPU三map/两program pins已列，新work消费者两个OBJ_GET路径匹配。旧private loader/15库仍VERSION_SPECIFIC，未批准直接迁移或废弃。新timeInState的raw_tp/sched_process_free对应global libbpf type17，保留kernel guard仅接受1–14，静态预测整对象load失败；其noncritical继续不证明统计正常。A31新增成对CPU候选：原新timeInState对象首56B改为读取实机tracepoint PID(offset24)，仅重建对应section/BTF/ext；原新libtimeinstate仅切换一条attach调用，保留新清理主体/maps/relocations。需求DEVICE_REQUIRED，实现VERSION_SPECIFIC，风险极高；不复制旧对象或禁用program。两次重放、640完整cleanup模型、1,002 BPF/640 native指令及八错误输入拒绝通过，Linux独立readelf结构正常。详情见BPF审计第13–14节；global libbpf/GPU/verifier/CPU运行验证未过，配对probe不可刷。

A32补充：原新libbpf已审的BTF条件可处理普通对象的旧kernel无BTF情况；CPU候选/两GPU无CO-RE，不为这些条件新增全局BTF禁用patch。新CPU另外两事件布局九成员匹配实机，候选BTF通过独立Linux bpftool文件解析。当前GPU两统计事件及FUSE type节点缺失；其新consumer能力回退仍UNKNOWN，不据此删除对象或判定渲染/存储故障。实际map创建、verifier/attach与完整回退仍未过，旧private族未批准删除。详见BPF审计第15节。

### A40 补充：旧 Build 绕过与真实 SDK28 差异

| 修改/分区文件 | 分类/目的 | S9对应位置/迁移建议 | 风险与未解项 |
|---|---|---|---|
| 旧SYSTEM `framework.jar` Build.isBuildConsistent返回true；旧services移除warning分支 | WORKAROUND，压制移植时版本/接口不一致提示 | 新Build仍调用VintfObject；新services AMS$$ExternalSyntheticLambda8.run classId2中投递UI警告。保留真实检查/日志与独立UID错误提示，不机械迁移旧return true。false本身不令这段caller停止启动。 | 高；真实VINTF未通过，不能把提示绕过视为兼容通过 |
| 固定VENDOR TimeService/CACert/JNI/time_daemon和init/seapp配置 | DEVICE_REQUIRED，时间与QTI硬件服务 | 新factory54 BOOT JAR检查：3份vendor代码包无13个SDK28差异直接引用；JNI32/64真实APS2+RELR表签名一致。保留原硬件层，按新zygote/VNDK30namespace定位绑定；ABSTRACT time_genoff不建文件socket。 | 高；JNI_OnLoad/native回调/权限、新ROM运行与dirty upgrade未验证 |
| SDK28完整声明/旧接口恢复 | UNKNOWN（声明是否能满足）；13处实现差异VERSION_SPECIFIC | 当前factory BOOT缺旧Bluetooth setPriority、TokenBinding11项及WebView旧VM字段。新BT提供setConnectionPolicy；有实际消费者时做语义迁移，无消费者不凭数字恢复旧安全接口。未新增28声明/删vendor需求。 | 高；签名存在不证明行为，反射/native/可选共享库未知 |

完整输入、13项签名、独立工具和CAPEX范围错误纠正见[SYSTEM_SDK_REBASE_AUDIT.md](SYSTEM_SDK_REBASE_AUDIT.md)。A40未修改删除列表或E2固件，没有导入旧framework/ART/核心APK。

## A50 实机新发现：属性上下文冲突

新S9 system_ext_property_contexts:1009声明`init.svc.vendor.wvkprov_server_hal → wvkprov_prop`，保留S6 vendor_property_contexts:132已有同一prefix→vendor_wvkprov_prop；旧精确UI8无重复。新init在5.115833秒序列化属性表fatal，导致PID1退出/panic，尚未到system_server。分类DONOR_SPECIFIC，中风险，推荐保留vendor归属并只移除新donor重复行，不能复制旧整表/替换init/清DATA或全局permissive。逻辑/profile/replay在 `patches/property-contexts-ui85.patch`、`device/s6/property-contexts-stage-ui85.json`、`scripts/apply_property_contexts_stage_ui85.py`，全树仅一文件变化。后续核对Knox bsd读取vendor状态的实际权限；没有日志证明前不扩allow。实际诊断包r2结果未确认，设备进入Download后等待回TWRP日志，不能报告已修复。

## A52 实机新增差异：S6 BPF 解释器

| 修改 | 分类 | 分区/位置 | 目的与 S9 实现 | 迁移方式 | 风险/状态 |
|---|---|---|---|---|---|
| JIT sysctl 初始化 | DEVICE_REQUIRED、VERSION_SPECIFIC | SYSTEM `/system/etc/t860-tethering-native/bin/netbpfload` | S6 固定内核无 JIT，新 S9 loader doLoad 在程序加载前强制启用 JIT，实机 exit24 | 当前 donor 精确函数 `0xc7a8` 的 `0xd20c` 跳至原 `0xd240`；profile/ELF patch 重放，不复用旧 loader | 中高；网络/BPF 实际执行待验证，One UI 9 重新定位 |
| 候选完整性表 | 配套部署逻辑 | SYSTEM `/system/bin/t860-tethering-guard` | 上述文件内容变化后 guard 必须校验新 SHA | 原 C 源码/原编译器重建，仅表中 netbpfload 的 after SHA 改变；其他 native/APEX 检查保持 | 中；实际启动校验待验证 |

旧 UI8 的零 jited_prog_len 兼容已迁入 B06；旧版初始 JIT sysctl 处理仍 UNKNOWN，不能以复制旧 wrapper、伪造 bpf.progs_loaded 替代分析。理由/证据/限制详见 `BPF_INTERPRETER_BOOT_A52.md`。

## A53：平台 legacy map_name ABI

| 改动 | 分类 | 位置 | 修改目的/S9对应实现 | 迁移方式 | 风险/状态 |
|---|---|---|---|---|---|
| MAP_CREATE名称参数 | DEVICE_REQUIRED + VERSION_SPECIFIC | SYSTEM `/system/lib64/libbpf_android.so` | 新库loadProg无条件写attr+28名称；精确保留S6 kernel检查该区域必须为零，Samsung critical对象MAP_CREATE -22后平台loader121重启 | 原新库0x65cc名称复制call→NOP，已有清零保留，无修改类型/大小/flags/pin/对象/错误传播；profile+脚本重放 | 中高；静态证明+Recovery瞬时对比通过，实际系统全链待验证，OneUI9重新定位 |

网络loader已实证加载/pin，并不等于网络消费者通过；uprobestats部分可选对象/FUSE缺接口另记，禁止把critical改optional掩盖。本项详细证据与重放见 `BPF_PLATFORM_MAP_ABI_A53.md`。

## A54：新Samsung库 BPF_PROG_LOAD 名称 ABI

| 分类 | 分区/文件 | 目的/迁移 | 新实现与推荐方式 | 风险/未理解项 |
|---|---|---|---|---|
| DEVICE_REQUIRED + VERSION_SPECIFIC | SYSTEM `/system/lib64/libbpf_android.so` | 48字节旧S6 BPF attr ABI不接受新prog_name；旧UI8具体实现尚需独立追踪，不能复制旧库 | 保留新loadProg，0x789c NOP名称复制；全输入/函数/指令及精确kernel锁定，profile/patch/stage脚本重放A53之后 | 中高；程序helper及消费者/流量/硬件未验证，uprobestats另属APEX。未来UI9重新定位，不能泛化为所有内核 |

详细证据和修改前理由见 `BPF_PLATFORM_PROG_ABI_A54.md` 与 `PORTING_LOG.md`。A53实际map创建成功，启动仍阻断于上述PROG_LOAD E2BIG。

## A55：新 aconfig 持久存储与 S6 分区布局

| 分类 | 分区/文件 | 目的/是否迁移 | 新 donor 等价实现与方式 | 风险/未知 |
|---|---|---|---|---|
| DEVICE_REQUIRED / VERSION_SPECIFIC | SYSTEM system/etc/init/hw/init.rc、system/etc/init/aconfigd.rc、system/etc/selinux/plat_file_contexts | 修复新 manifest featureFlag 读不到持久storage，导致 RANGING permission被过滤及system_server崩溃；旧UI8对应修改尚未解释，不能称为原旧patch | CACHE独立目录bind到metadata；原初始化在post-fs有序执行；20条新metadata类型镜像到alias，保留新storage/权限解析 | 高；CACHE清理、APEX/密码slots/早期clients与DATA升级待测 |
| DEVICE_REQUIRED / DONOR_SPECIFIC | SYSTEM system/lib64/libaconfigd_rust.dylib.so | 新storage初始化原本跳缺vendor，却再次无条件应用vendor overrides；S6硬件原vendor无容器，迁移等价存在性逻辑 | 固定原新函数，仅0x15234单指令跳过不存在vendor项；三真实容器和真实错误检查保留 | 高；硬件SHA及vendor无容器为强前提，UI9重新定位，不导入S9vendor flags |

详见ACONFIG_METADATA_REBASE_A55.md。V9原native隔离正常0、缺metadata/现有PRODUCT复制失败6；实际生成storage的RANGING=1。E2全树8,085条，仅上述4文件内容变化，metadata/link/CIL/APEX其余均同A54，inventory6bc42287…。实机新权限注册与启动待测，原A45包未包含本修改。

## A68 后续实际修复与新适配（2026-10-02）

| 修改 | 分类 | 路径/分区 | 原因及旧UI8证据 | S9迁移方式 | 风险/验证 |
|---|---|---|---|---|---|
| Wi-Fi voice能力 | DEVICE_REQUIRED + VERSION_SPECIFIC | SYSTEM_EXT overlay/T860WifiTelephonyOverlay.apk；device/s6/telephony-overlay | S6 stock false，旧working true；S9新框架对vendor API28回退导致PhoneType1，无IMEI而账号token失败。旧UI8相同AI症状未知 | 只将config_voice_capable设false，原新SamsungAccount/framework保持。原S9 idmap2映射、完整工程/Recovery差异核验；未来新donor重定位能力接口 | 中；实机PhoneType0与实际水彩生图成功，其他AI仍未测 |
| 官方时钟预装 | DONOR_SPECIFIC optional app packaging | SYSTEM app/ClockPackage；device/s6/prebuilts/clock | S9原donor/CSC无主钟，非已证实旧diff或误裁。用户官方Play版本通过 | 新官方签名原APK+其5个本地arm64库，单独可重放；不是复制旧成品core APK | 中；DATA安装用户PASS，SYSTEM预装/闹钟唤醒未测；必须精确容量门限 |
| 天气旧profile修复 | VERSION_SPECIFIC upgrade state | DATA user0 com.sec.android.daemonapp（授权包级重置）；PRODUCT原APK不变 | 中国区HUA没有BriefApi，旧persisted map开关与接口不匹配。旧UI8相同问题未知 | 新donor原实现重新生成profile；未来dirty upgrade作为可选、有明确授权的应用状态修复，不无条件清DATA | 中；文字搜索、真实预报、刷新、冷启动显示PASS；GPS/小组件重设未测 |

未解释的S Pen native注册与可选库告警仍UNKNOWN，当前实际生图通过，不据此替换全部旧/新原生库。详见APP_REPAIRS_UI85_A68.md。

## A69：F14 真实地区属性遗漏修复

| 改动 | 分类 | 分区/文件 | 目的与旧基线 | 新donor位置/迁移方法 | 风险/实测 |
|---|---|---|---|---|---|
| ro.csc.countryiso_code=US | DEVICE_REQUIRED（固定XAR设备地区） | SYSTEM /system/build.prop；device/s6/csc-country-ui85.json | 旧v0.24脚本及working均为XAR/US，bootloader XAR。新工程遗漏造成SIS country-code空 | 官方X710 optics/configs/carriers/single/XAR/conf/customer.xml确认US；SemSystemProperties和新SIS header读取同一属性。只追加真实字段，profile+guarded scripts，不复制旧文件/改新版本 | 中；恢复后英文及原中文PDF真实摘要PASS，weather冷启动显示PASS；server内部规则未知 |

ro.csc.sales_code仍未补入：其init trigger/当前CSC初始化独立待审计，不能因country修复而同时覆盖整套旧CSC。新版AWESOME_INTELLIGENCE=-1在成功请求中仍存在，不能为此次摘要问题凭感觉加旧flag或降级APK。


## A70：S6屏幕四角遮罩

| 改动 | 分类 | 分区/文件 | 目的和新实现 | 迁移方式 | 风险 |
|---|---|---|---|---|---|
| S6原厂2mm尺寸与3.0控制点vector曲线 | DEVICE_REQUIRED | 参考S6 vendor framework RRO及旧SystemUI；新增SYSTEM_EXT/overlay/T860RoundedCornersOverlay.apk | 当前旧vendor 2mm仍生效，但新SystemUI默认drawable为8dp且形状不同 | 新资源overlay直接以2mm intrinsic实现原曲线，不复制旧APK | 中：几何与旋转实测 |
| 新S9 SystemUI config_enableRoundedCorner false→true | VERSION_SPECIFIC | 同一RRO；目标RoundedCornerResDelegateImpl.reloadRes | 新delegate直接以boolean决定hasTop/Bottom，旧原厂以半径启用 | 仅覆盖该bool，使用新provider绘制四角 | 中：装饰窗口/隐私指示/新版本重定位 |

详细分析与结果见`ROUNDED_CORNERS_UI85_A70.md`。未修改其他浮动feature，也未替换SystemUI/framework/硬件层。此项是遮罩恢复；framework应用可见圆角几何仍单独记录，不能混同。


A70补充：新增SYSTEM_EXT/etc/sysconfig/t860-rounded-corners.xml，仅allowed-system-preload该RRO包，属于新版Samsung包注册差异/VERSION_SPECIFIC。原允许清单不改，无权限授予/通配符/跳过过滤。注册后真实资源lookup与4方向provider验证通过；原idmap成功本身不能替代PM注册及运行验证。
# 2026-10-03 A73 SDK适配范围补充

本轮不迁移旧UI8 Build一致性绕过，也未补回旧framework/APEX。官方SDK28差异中的11项TokenBinding和1项WebView常量已不在官方29/30参考；固定S6原厂SDK32仍声明28–32，却在选中类中已无其中9个owned成员。全部补回旧stub的方案归OBSOLETE_CANDIDATE（方案候选，未删除文件），实际版本接口变化归VERSION_SPECIFIC。

BluetoothHeadset.setPriority的旧逻辑需在实际消费者中等价迁移；S9 /apex/com.android.bt/javalib/framework-bluetooth.jar已有semSetPriority→setConnectionPolicy和semGetPriority→getConnectionPolicy，保留新权限/AttributionSource/异常语义。A39保留vendor代码无直接调用这13项，不能由此排除反射/native或全部用户应用。原SDK28 matrix约束仍保留，支持声明来源与范围UNKNOWN，高风险，尚未修改或通过正式VINTF。

涉及system/framework/framework.jar、system/etc/vintf/manifest.xml、vendor/etc/vintf/compatibility_matrix.xml及Bluetooth APEX；本轮只增加调查/观测脚本及证据。具体原厂/新实现位置、分类、是否迁移、方式、风险和未决项见[SDK_CONTRACT_INVESTIGATION_A73.md](SDK_CONTRACT_INVESTIGATION_A73.md)。后续OneUI9重查实际消费者及现有新接口，不继承旧成员清单为强制二进制补丁。

### 2026-10-03 实机Mainline适配增补

| 改动 | 分类 | 路径 | 目的与迁移 | 风险/验证 |
|---|---|---|---|---|
| A76缺Fkeymaster后端的Fabric生命周期 | DEVICE_REQUIRED / WORKAROUND | SYSTEM etc/init/fabric_crypto.rc | 本机仅停止缺后端服务自动启动；保留原daemon/client/其他安全服务。UI9重新核对硬件能力和消费者错误处理 | 高；真实广告模块更新及第二次重启各五分钟保持。Fabric/Kmx业务仍不支持 |
| A75固定manifest失败恢复 | WORKAROUND | SYSTEM init.rc, tethering guard rc/bin | check失败留官方600秒回退窗口、900秒Recovery出口；不是新网络兼容 | 高；factory启动通过，真实未知网络组回退窗口尚待实测 |
| A77确切DNS原件采集候选 | WORKAROUND | SYSTEM etc/init/hw/init.rc | 与Tethering保存同列车新包用于逻辑重定位；不改包、源、API能力、硬件层 | 中；候选重放一致，未部署 |

## 2026-10-04 实机证据补充：Mainline更新后的BPF解释器初始化

DEVICE_REQUIRED / VERSION_SPECIFIC：S6保留BOOT无CONFIG_BPF_JIT，不能因为新版Tethering要求JIT就换S9内核。factory S9已有A52初始化适配与后续零JIT长度适配；真实Google372038420在自己的新版main/FDE中重新定位为aa8c→aac0，仅跳过两个不存在的JIT sysctl初始化。新loader错误处理和真实BPF装载保持。A78更新试验已证实该缺口，A79主机候选已重放/严格校验，尚未实际部署或证明新版网络成功；完整报告见MAINLINE_NATIVE_REBASE_A78.md和PORTING_LOG.md。未来UI9/新Mainline版必须重新核对源码目的、函数、输入SHA与内核能力，不迁移旧整二进制。

## 2026-10-05 A88 可选遥测客户端隔离

| 修改 | 分类 | 分区/目标 | 目的 | S9迁移位置与方式 | 风险/当前结果 |
| --- | --- | --- | --- | --- | --- |
| QCC可选客户端用户级隔离 | DONOR_SPECIFIC | SYSTEM_EXT/app/QCC/QCC.apk保留，DATA中的user0 installed状态由PM管理；vendor/库/init/VINTF/权限XML不改 | 消除新QCC主线程等待本机不存在HIDL1.2而每16秒ANR的循环；旧UI8 v0.39有同类逻辑参考 | 在新QCC准确APK/版本/provider/权限依赖核对后用keep-data用户卸载，脚本和device profile独立保存；disabled-user实测不能隔离此persistent客户端 | 中。实机新boot与60秒0ANR/0HIDL超时通过；UI/长期/完整镜像集成待验证。不是永久删除APK/库的充分证据 |

未知项：全部静态provider/权限调用者未穷尽；未来donor常驻启动逻辑、正式升级用户UID/安装状态、源树裁剪路径须重审。当前A84镜像未包含运行策略，不删除未知依赖或替换framework。详见[APP_OPTIMIZATION_A88.md](APP_OPTIMIZATION_A88.md)。

### A89 最近任务旧逻辑重新审计

后续设置/时钟/笔记九次启动和八轮手势通过；有/无Perfetto仍有14.98%/14.59%桌面jank、P95均57ms，不是QCC前后收益。新桌面已有WAKEUP/ROTATE两权限、无旧EarlyWake拒绝，该旧权限替换对当前donor归OBSOLETE_CANDIDATE，不新增旧native patch。低分辨率资源0.5不能证明最终快照比例；旧构造函数已变化，仍VERSION_SPECIFIC。高分辨率新AbsAppSnapshotController读资源1.0，旧0.7 RRO为待成本验证WORKAROUND候选，不直接复制。

当前明确卡点为动画结束同步启动RecentsActivity（新HoneySystemController实现b2/j→Activity.startActivity→ATMS0x3d），等待46–53ms；是否应消除某段工作尚UNKNOWN/高风险，须先查生命周期/任务复用与接收端锁。TaskbarWindow等待和可选INFO日志另列候选，尚无前台性能patch；详见[APP_PERFORMANCE_A89.md](APP_PERFORMANCE_A89.md)。

### A90–A93 性能候选的最新迁移决定

下表为旧逻辑/新候选的审计结论，不是已部署的新ROM修改列表。

| 项目 | 分类 | 涉及分区/新位置 | 目的与迁移方式 | 当前判断/风险 |
| --- | --- | --- | --- | --- |
| HoneySpace普通日志减负 | DONOR_SPECIFIC候选 | SYSTEM Launcher APK，当前helper和实例tag | 在消息构造前定位稳定可选诊断入口；volatile tag实验仅量化传输成本 | A90 P95无改善、标签会变化，不加正式属性规则；中风险 |
| WindowManager普通日志减负 | DONOR_SPECIFIC实验，未采用 | SYSTEM services.jar及SystemUI同名WindowManager tag | 单tag WARN门槛ABBA，警告错误保留；不作跨版本全局过滤 | A92控制14.680%、处理15.412% jank，无稳定收益；已恢复，正式迁移不推荐 |
| 旧F17高分辨率0.7 RRO | WORKAROUND / VERSION_SPECIFIC候选 | PRODUCT资源overlay候选；新AbsAppSnapshotController.initSnapshotScale、SnapshotManagerService.takeTaskSnapshot | 只在实际尺寸/成本/清晰度对照成立后构建新单资源RRO，不复制旧APK | 当前Task比例1.0、实际2560×1600。完整七轮捕获最大18.486ms且均在OPEN后，初始启动根因未证明；保持未部署，中风险 |
| 截图密度兼容 | VERSION_SPECIFIC现成donor逻辑；原始异常来源UNKNOWN | services.jar AppSnapshotLoader/StoreWriteQueueItem；framework.jar TaskSnapshotProto字段22；受保护DATA snapshot proto | 新字段≤0回退DENSITY_DEVICE_STABLE，writer已保存；新donor重新审计schema而不硬编码字段偏移 | 当前缓存360dpi、七个services类与S9参考一致；准确出警告task/file未取得，无需凭警告清数据/新增框架补丁 |
| 强制Launcher CPU组假设 | UNKNOWN假设已缺乏支持，无新增适配 | 只读proc/cpuset/current task profiles，S6 vendor/kernel保持 | 先区分锁屏restricted与实际Recents top-app | A91四轮168样本，明确Recents焦点均top-app/CPU0–7；不部署亲和性/频率patch |

旧UI8是否有相同日志成本/密度记录仍未认证；S8参考缺density字段只支持旧数据假设。新启动入口由runOnceAtState协调，不能视为无条件重复调用。原A88冻结profile/audit、A89来源与所有失败记录保持；全部临时属性/屏幕设置已独立复核恢复，0新分区修改/ZIP。详见[最新报告](RECENTS_PERFORMANCE_A92_A93.md)及[A90/A91](LAUNCHER_PERFORMANCE_FOLLOWUP_A90_A91.md)。

### A96：旧PhotoEditor裁剪规则不再迁移

| 项目 | 分类 | 新位置与目的 | 推荐迁移方式 | 风险/未完成 |
| --- | --- | --- | --- | --- |
| 旧PhotoEditor_AIFull删除候选 | VERSION_SPECIFIC容量决定，已确认应纠正 | SYSTEM priv-app；Gallery SPEActivity核心普通编辑依赖 | 保留新S9原签名APK，重建68个私有native库及原allowlist；UI9重新审查版本/权限/ABI | 普通编辑旋转另存通过；正式容量不足，中风险 |
| 图片编辑器可选人像两库的旧删除依据 | UNKNOWN/OBSOLETE_CANDIDATE（删除规则） | SYSTEM lib64/libdualcam_portraitlighting_gallery_360.so、libdualcam_refocus_gallery_59.so | 恢复消费者后不再声称无引用；策略keep，正式构建恢复或专项验证后审查裁剪 | 合计168360464B，实机未回填、人像未认证 |

新S9 core editor在当前实机已恢复，未使用旧UI8二进制。旧UI8商店下载/相册入口是否同样缺失尚未认证；相册-92和商店9909都是本轮实机日志。详见PHOTO_EDITOR_RESTORE_A96.md。

## A97新增：Galaxy Store目录拒绝的应用级WORKAROUND

| 修改 | 分类 | 分区/文件 | 目的与证据 | 迁移方式 | 风险/未知 |
| --- | --- | --- | --- | --- | --- |
| Store自有saconfig.ini只覆盖目录型号SM-X710 | WORKAROUND；DONOR_SPECIFIC/VERSION_SPECIFIC约束 | 用户存储Android/obb/com.sec.android.app.samsungapps/saconfig.ini | S6型号+SDK36目录9909；型号配置A/B/A/B通过、空配置仍失败；真实Store下载安装计算器及1+2=3通过 | device/s6/galaxy-store-catalog-ui85-a97.json与受保护apply脚本；不改全局SDK/硬件身份或Store原签名 | 低开机风险；额外OBB诊断和Watch空名称fallback；清理可移除，版本升级重审。工厂Store/真实Wearable/长期日志增长未验证 |

旧UI8同类商店修改用途未认证，本轮依据新donor/实际Store调用链重实现。UI9需重新定位和验证，不能当跨版本常量；A84冻结构建未集成。详见GALAXY_STORE_CATALOG_A97.md。

## A98：Gallery 文档扫描能力声明纠正

| 修改 | 分类 | 分区/位置 | 目的与新实现 | 迁移/风险 |
|---|---|---|---|---|
| 删除 CAMERA_CONFIG_VENDOR_LIB_INFO 内 smart_scan.samsung.v2 单 token | DEVICE_REQUIRED + DONOR_SPECIFIC | SYSTEM etc/floating_feature.xml；Gallery Features$262/DocumentScanner | S6没有SS_segmenter模型，新donor gate却启用扫描，JNI抛std::out_of_range；采用新Gallery已有无扫描OCR路径 | 实机JPEG OCR通过；中风险，相机文档扫描入口可能降级，普通相机服务连接通过，UI9重查模型/后端及gate |

旧UI8同类修改没有已认证用途，不能声称原项目也如此修复。新S9 Gallery/APK/SmartScan均未改；S9 DSP模型未导入S6。scripts/prepare_gallery_scan_a98.py + build_gallery_transaction_a98.py + device/s6/gallery-scan-ui85-a98.json记录精确版本、原因和回滚。编辑器涂鸦/旋转云端链路实机通过，没有追加AI二进制补丁，其他模式未验证。正式冻结A84不覆盖。详见GALLERY_OCR_AI_A98.md。
