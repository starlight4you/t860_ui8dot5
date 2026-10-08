## 2026-10-05 A95：普通SNAP缺接口等待补丁已部署实验设备

最近任务研究保持停止。新donor两指令补丁已通过原/新库获取与能力查询对照、实际单文件Recovery写入、全6562文件/7809 all-attributes独立读回和绑定当前raw的撤回只读预检。新boot45.56秒完成，核心/Enforcing稳定，基本应用打开通过。真实FaceService已启动但本轮周期job未走到native媒体推理，完整相册分析与实体生物识别、Knox secure功能仍需分别实测；不能将零wait日志当作这些功能已通过。

执行入口：`patch_snap_normal_a95.py`、`build_snap_transaction_a95.py`；设备profile为lab部署/完整QA待验证，不纳入冻结A84镜像。详见SNAP_NONBLOCKING_A95.md与audit/snap-native-live-ui85-a95.json。后续先等待/触发正常媒体分析并核对错误处理与重试，再决定source集成。微信唤醒锁会释放又重取，保留通知策略；Heatmap仍低优先级，先依赖证据，不为低负载无依据加参数。

## 2026-10-05 A94：当前全局优化顺序，最近任务专项停止

用户明确停止最近任务卡顿研究。后文A89–A93保留历史结果，其待调查前台任务不再作为当前执行项。

1. A94只读全局观察完成：60秒proc/top/PSI/log窗口，八核CPU约1.992%、可用RAM约3.45GiB，0持续swap-out/kswapd/OOM、温控0，核心/boot与原屏幕设置保持；当前Dozing/USB供电，不当作脱离充电器的待机功耗基准。QCC隔离继续有效。
2. 优先核对SNAP：`com.samsung.faceservice`19619/22932有61次约1秒等待，servicemanager183次lazy-start失败，AIDL SNAP未注册而S6保留HIDL manifest/service。新SYSTEM `lib64/libsnap_aidl.snap.samsung.so` SHA8d4d95da…：normal check0x1d110/空分支0x1d114，secure失败跳0x1d0e4，共同wait0x1d258、空检查0x1d27c。先补真实映射/调用者和现有空失败契约，随后才做保留secure及已注册成功路径的精确新源patch/撤回。当前不全局改wait重定位、不搬旧库、不伪装AIDL服务。
3. 微信push `VFS:Maintenance`同一PARTIAL_WAKE_LOCK后续已持有17分6秒；作为应用层待机候选。先确认维护任务/版本/锁释放，再选择保留通知的处理方式；不全局改Freecess/AppOps/消息联网或强停清数据，当前没有实测耗电收益。
4. Heatmap PID1288/init仍running，正确新init所需`/sys/class/power_supply/sec_auth/{batt_heatmap,ect_output}`不存在；EFS仅权限拒绝，不能判不存在。先新binary/Health/Battery/charger类依赖审计，随后做可撤销单service采集入口对照；保留S6 Health/Thermal及充电保护。不机械删除旧v0.39对应文件，新donor当前只见两次uevent且没有证明高CPU/I/O。
5. `cnss_diag`约1.2%单核、约0.15%八核容量，低优先级；缺实际I/O来源，不停Wi-Fi诊断。网络Alarm警告与Mainline/GMS无本轮崩溃/任务风暴证据，不扩大冻结或关闭网络能力。不盲改CPU/ZRAM/动画参数。

新报告：[GLOBAL_PERFORMANCE_A94.md](GLOBAL_PERFORMANCE_A94.md)，工具`collect_global_performance_a94.py`与`analyze_global_performance_a94.py`，审计`audit/global-performance-ui85-a94.json`。本轮0分区/包/属性修改、0新ZIP、无新增正式性能patch；当前阶段是发现与核对全局优化点。

## 2026-10-05 应用优化 A90–A93：历史调查结果与执行顺序

1. A88 QCC用户隔离保持，A90–A92流程均无其ANR/重启；未集成进冻结A84镜像。现有启动、硬件与Mainline门槛继续有效。
2. A90 HoneySpace日志ABBA只有小幅jank差异、P95无改善且部分标签随实例变化；A92 WindowManager同标签限制ABBA控制14.680%、处理15.412%，无稳定收益。两者全部原属性/显示设置已独立读回，均不纳入正式ROM。WindowManager属性也作用于SystemUI同名标签，原执行收据全进程计数和独立server计数分开记录。
3. A91四轮168采样确认Recents焦点下Launcher进入top-app、允许CPU0–7；不强制改CPU组/亲和性/S6 HAL。实际新APK通过MultiStateCallback.runOnceAtState协调启动；尚无删除startActivity的依据。
4. A93完成新snapshot load/store/density契约核对：新proto字段22、默认0→稳定密度回退、writer保存密度，当前三个Task缓存360dpi/2560×1600；七个services快照类与本地S9参考相同。密度警告的八次Binder caller为Launcher后台DefaultDispatch；准确原始task/proto尚未取得，不清数据或为警告改框架。
5. Trace全体最大45.398ms截图位于第一轮OPEN之后；完整1–7轮最大18.486ms，所有捕获都在OPEN之后。旧0.7高分辨率RRO仍未部署WORKAROUND候选，不把截图成本视作初始77.94ms长帧已证实根因。已核实新Task比例1.0/Activity0.6及真实buffer；低分辨率初始化/写入/读取尺寸继续单独追踪。
6. 下一条前台调查仍定位当前RecentsAnimationManager→HoneySystemController→Activity.startActivity→ATMS接收端35.775ms工作。按TaskbarWindow等待和ART线程列表锁具体调用点核对可选诊断/列表计算是否处于同步路径，保留任务复用、状态回调、leash和生命周期；禁止以减少日志、改变动画或转线程替代实际修复。现有A89 trace/实际代码先用于定位，只有具体改动需要验证时才增加新测量。
7. 如继续截图比例实验，先新donor单资源RRO/精确idmap/注册检查与固定来源撤回事务，再正常启动、读取实际比例及新buffer、同流程前后比较清晰度/长帧/多窗口；未达到这些门槛不加入device正式适配。当前不复制旧APK/JAR或改截图锁范围。

报告：[LAUNCHER_PERFORMANCE_FOLLOWUP_A90_A91.md](LAUNCHER_PERFORMANCE_FOLLOWUP_A90_A91.md)、[RECENTS_PERFORMANCE_A92_A93.md](RECENTS_PERFORMANCE_A92_A93.md)。以下A88/A89顺序保留为历史阶段，残余前台卡顿与完整ROM发布仍未完成。

## 2026-10-05 应用优化 A88 / A89：历史优先顺序

1. 已从当前user0保留数据地移除不兼容QCC客户端，原APK/硬件层保持；新boot installed=false、QCC缺席、42active APEX身份一致。60秒日志0 QCC ANR/重启/HIDL超时。
2. A89已正常解锁，设置/时钟/笔记九次启动、最近任务手势八轮通过，原临时屏幕设置恢复0/60000。有/无Perfetto桌面jank14.98%/14.59%、P95均57ms，残余卡顿未修；不能当作QCC优化前后收益。
3. 运行层profile `device/s6/app-optimization-ui85-a88.json`、执行/撤回脚本 `scripts/quarantine_qcc_a88.py`、独立采集 `scripts/collect_qcc_optimization_a88.py`。当前 lab serial/UID固定，正式安装器不能继承这一UID假设。
4. A84完整SYSTEM/PRODUCT已独立SHA和7777/351项全回读通过；本轮没有修改其冻结内容，也未加入QCC运行策略。下一版source/installer应独立重放策略或完成永久客户端裁剪依赖审计，然后新建清单/镜像/ZIP，继续原UI8 DATA直升门槛。
5. 下一项具体审计：当前Launcher的RecentsAnimationManager.startRecentsActivityInternal→HoneySystemController实现b2/j.startActivity→Activity.startActivity同步路径，实机ATMS事务0x3d等待46–53ms；检查动画结束/任务复用/页面生命周期及接收端锁，不能直接跳过启动或异步移动Activity调用。并行候选范围为TaskbarWindow.postAndWait及HoneySpace可选INFO诊断，均先量化；不关闭任务栏、全局日志或后台安全服务。
6. 当前EarlyWake两权限已授予且没有旧拒绝，不重放旧native权限替换；快照初始化/实际尺寸重新定位，资源lookup值不替代最终尺寸证据。新donor混淆类名/资源ID均不可用于UI9固定偏移补丁。
7. 当前实况/失败实验/风险见 [APP_OPTIMIZATION_A88.md](APP_OPTIMIZATION_A88.md) 和 [APP_PERFORMANCE_A89.md](APP_PERFORMANCE_A89.md)。下文为各阶段历史；原A88冻结profile/audit的UI待解锁字段不是当前状态。

## 2026-10-05 当前执行顺序：A82 / A83

1. A82已完成：只读完整旧metadata归档和非CE检查→跨文件系统复制及目录安全属性补齐→全239项/215文件独立回读→四SYSTEM文本事务→全6562文件/7809 metadata/275 links回读与源绑定撤回预检→首次实际DATA挂载/flags exit0/42模块身份→旧CACHE原路径缺失时第二次启动和42模块保持。
2. 当前设备Android已解锁；A83用户确认EDIFIER MR3BT铃声双端有声、音乐/视频蓝牙有声，追加只读采样active MEDIA仅A2DP sink/io21，与听音一致。无需新A83补丁。凭据/生物识别以及蓝牙断连/重连、重启后连接、其他codec和长时播放仍单列验证；原S6 HAL/配置保持。
3. A82独立构建源`/var/tmp/ui85-a82-metadata-stage-v1/stage`完整8129项/4bbbef4b…，四文本patch和独立generator已保存；原A81不变。完整新镜像入口/容量/installer还需接入DATA metadata来源与当前Mainline模块合同；旧冻结安装器不得直接接收新状态。
4. 运行后撤回：先在Recovery保存最新DATA metadata和全部attrs，检查APEX/checkpoint，再协调目标和生成当前来源固定的事务；旧激活前恢复脚本应拒绝更新后的tuple。不要把旧CACHE原件恢复成活动metadata而丢失新状态。
5. 后续首次干净DATA、原v0.48.1 DATA升级、完整安装/恢复及全功能门槛继续单独验证。未来UI9重新审计DATA fstab是否引入metadata encryption/checkpoint及init消费者时序，再重放逻辑。

## 2026-10-05 当前顺序：A81 选择性暂停已部署

1. 用户授权的单PRODUCT XML补丁已写入，完整回读、原SYSTEM/BOOT/VENDOR保持、独立恢复只读预检通过；原DATA保留。
2. 普通UID的实际系统权限正反测试四项通过；Play真实Calculator下载安装/打开通过并清理。第二次启动核心/42模块身份及四更新模块62秒观察通过，屏幕超时60000恢复。真实Google后台仍处于检查，没有后台拒绝日志；普通应用升级、Play自身升级和长时间后台行为待验证。
3. 已整合独立A81 COW源：8129项、fe2db1a7…，只改既有XML，完整父A80与其他内容/metadata/links不变。源脚本 `scripts/prepare_mainline_freeze_stage_a81.py`、profile `device/s6/mainline-freeze-stage-ui85-a81.json`、patch `patches/s6/a81-mainline-installer-freeze.patch`。这是用户选择的WORKAROUND，不是S6硬件必需项或A79更新兼容通过。
4. 新镜像入口 `scripts/build_rom_candidate_a81.py` / `device/s6/rom-candidate-a81.json` 保留原A80父源/policy和全部发布门槛，只接受该精确差异；先运行完整源check-only、测空间，再生成SYSTEM/PRODUCT并做全回读/容量/e2fsck。不改旧冻结构建器/profile，不放宽旧A74安装器。
5. 后续升级/恢复安装合同必须明确当前SYSTEM A79与PRODUCT A81来源、四个已更新模块；新完整镜像/ZIP、初始v0.48.1 DATA直升和完整硬件/Samsung功能仍待验证。当前暂停范围不保证独立非staged模块APK和下载停止；模块安全修复随维护ROM或已验证人工更新交付，未来UI9重新审计。

部署/测试/局限见 [MAINLINE_FREEZE_RESEARCH_A81.md](MAINLINE_FREEZE_RESEARCH_A81.md)，实机审计 `audit/mainline-freeze-live-ui85-a81.json`。以下保留历史阶段记录。

## 最终A74本轮实机汇总

## 2026-10-04 当前实机阶段：A78 / A79 Mainline网络适配

1. 已从A77精确来源以最小SYSTEM文件事务安装A78；BOOT/VENDOR/DATA保留，raw2c1b664d…独立回读，撤回脚本完整只读预检通过。factory启动核心/新服务注册已观察。
2. 真实Google父78887815已经因BootTimeout在614.8秒由apexd自动回退，factory核心恢复。完整bugreport明确guard两阶段成功，loader因S6无JIT sysctl退出24；A79在新loader自身aa8c→aac0迁移A52初始化逻辑，只改loader单指令和guard摘要，两文件事务全回读/独立撤回预检通过。当前先factory新启动，再重新测试真实更新；900秒Recovery出口未实测。
3. 成功后核对实际绑定SHA、APEX身份、DNS路由、BPF/网络流量、代理与核心进程，再第二次重启保留验证；无成功证据不改PASSED。
4. 已将A75–A79及A76 Fabric适配重放至独立A79 COW构建树（原A74树不变），完整8129项内容/metadata比对通过，清单SHA014d7cb7…。只改五既有文件、新增二十八文件/四目录，增量19766246字节；证据`audit/mainline-stage-integration-ui85-a79.json`，脚本`scripts/prepare_mainline_stage_a79.py`。当前宿主约8GB不足旧镜像构建器的载荷加5GB余量门槛，暂未生成新镜像/ZIP。真实更新成功后完善新构建profile、容量审计和新安装器来源门槛，生成升级/独立恢复ZIP；A74旧安装器不覆盖当前A79，禁止绕过。
5. 原初始v0.48.1 UI8 DATA直升、未闭合硬件/Samsung功能仍需各自证据；当前UI85数据不替代首次升级测试。以下段落保留各历史阶段记录。


已完成升级—独立恢复—重新安装三个实际原生RC0路径，最终A74新boot d33f3a76…实际VINTF主要项GOOD、原用户解锁、有限传感器/OMX视频/相机/音频/DRM探针通过；当前停留最终A74。详情见[A74本轮实机报告](A74_DEVICE_VALIDATION_20261003.md)。后文是历史阶段；完整发布仍NOT_PASSED，保留初始UI8 DATA、Mainline、Fabric及实物/其他功能门槛。

## A74 升级—恢复—重装原生路径实测（2026-10-03）

实际A71完整升级A74原生RC0并新启动/VINTF通过；独立恢复ZIP从A74恢复固定A70/SDK28原生RC0并新启动/用户解锁通过；再从该A70完整重装同一A74 ZIP，真实原生RC0和完整两分区/BOOT/S6 SDK30_ADAPTED校验通过。三个Recovery运行均crash_counter0、原屏幕超时60恢复，三个调用/PID/退出结果独立绑定。当前正在最终A74新启动和功能采集，不能复用前一启动当本次通过。

实际证据分别为audit/native-full-upgrade-ui85-a74-v1.json、native-independent-restore-ui85-a74-v1.json、independent-restore-android-boot-ui85-a74-v1.json、native-return-after-restore-ui85-a74-v1.json。初始UI8 DATA条件仍缺，不能把已迁移DATA的升级/恢复循环写成初始v0.48.1 DATA升级完成。其余未闭合发布门槛仍保留。

## A74 独立恢复实测后状态（2026-10-03）

新A74真实完整安装、用户解锁及实际VINTF主要兼容检查已通过。独立恢复ZIP也已从A74/SDK30实际原生安装并完整回读至固定A70/SDK28，原生RC0，随后A70新启动、原密码解锁、核心服务及42 factory/no READY通过。当前DATA保持，不能替代原UI8 DATA快照还原。证据audit/native-independent-restore-ui85-a74-v1.json与independent-restore-android-boot-ui85-a74-v1.json。

当前正按计划返回A74：新Recovery → 原ZIP只读预检 → 原生完整安装 → 新启动/VINTF/功能验证。后文历史阶段“尚未恢复实测”的描述以本段后续证据为准；Fkeymaster/Fabric、未来Mainline兼容、初始UI8 DATA升级及完整功能/发布门槛继续未闭合。

## A74 当前执行状态（2026-10-03 实机后续）

用户已确认撤销当前Mainline批次1763514831：原记录同CACHE完整保留，实际Android平台已清Ready/Applied并标Failed，42 factory/no READY、用户区解锁。两份冻结A74 ZIP均已保存至平板并核对完整SHA；真实update-binary第四参数只读预检RC0，四分区前后原块不变。

A74升级包已从实际A71来源完成一次完整原生TWRP安装：SYSTEM/PRODUCT完整写入和回读、BOOT pin、完整SDK30_ADAPTED vendor通过；真实updater2064、Recovery550/crash_counter0，准确终态及原生RC0已捕获。原屏幕超时60已恢复。当前正在第一次A74 Android启动采集，尚未写启动/硬件/初始UI8 DATA升级或恢复测试通过。

下一顺序：实际安装VINTF/两配置 → 新启动及解锁/核心/APEX → 功能验证与独立恢复实测 → Mainline未来更新、Fabric及其他发布门槛。下文原拒绝/待答复段落保留为历史阶段；以本段及audit/native-full-upgrade-ui85-a74-v1.json为当前安装状态，不把实验包标稳定。

## A74实际Recovery预检结果

真实新完整vendor guard返回SDK28_ADAPTED，SDK30正确拒绝旧矩阵；BOOT/VENDOR/SYSTEM来源及原版TWRP工具符合预期，PRODUCT全字节只差四个ext4记账字段10B。当前Mainline会话1763514831 STAGED使原guard拒绝升级。其记录19模块SHA与两个旧失败批次相同。一次性保留原会话、由Android失败处理接管的候选已准备且未执行，用户选择待答复，见MAINLINE_READY_SESSION_A74.md。当前保持Recovery、不刷写、不普通重启。

## A74最新门槛：待生效Mainline会话

两份完整新ZIP及各114块原TWRP载荷检查已完成。整升级入口42项、恢复入口37项与旧A71回归33项通过，范围和fixture差异见DEVICE_SDK_CONTRACT_A74.md。实机尚未装A74。最新只读Android状态发现父会话1763514831 READY，23子会话，当前factory APEX尚未替换；先直接进入Recovery保存完整模块状态、原块和日志，保持guard拒绝未验证更新。Mainline条件未解决前不执行新安装或普通Android重启。

## 2026-10-03 A74最新执行顺序：两配置升级/恢复入口

SDK30固定vendor契约候选已形成独立XML/profile/patch，实际原vintf子进程FCM4+该候选整体GOOD；当前实机分区仍未部署。完整154平台成员/79类型与当前BOOT核对，11项编译注解独立解释；CACert业务与注册仍NOT_PROVEN。vendor COW只含A61/A74两配置，其余源码/硬件层/metadata保持，见DEVICE_SDK_CONTRACT_A74.md。

1. 从原2768项hardware table构建下一版本完整vendor guard，明确支持SDK28/30精确矩阵两种table与A61政策两状态。保留所有hash/labels/caps/UID/mode/nlink/hardlink检查；不能跳过XML。原A64源码和冻结A71产物可保持，采用新builder/profile及两个表分派以避免改变旧guard行为。
2. 升级/恢复安装脚本共同实现两配置事务、幂等/中断及回读/精确回滚，先完整preflight后写；新restore必须识别SDK30目标并按计划恢复28矩阵。旧A71 guard只允许A61，当前不能先用它刷入A74。真实UI8原/已适配vendor及当前精确A71来源分开检查，UNKNOWN一律拒绝。
3. 新SYSTEM基线A73 COW8097项（FCM4），vendor视图A74 /var/tmp/ui85-a74-vendor-sdk30-stage-v1/stage两配置、checkpoint5759f6d7…；PRODUCT沿用审计来源。刷新policy/精确ext4/目录metadata及ZIP32和原TWRP工具所有块，再真实安装/installed VINTF/Build/核心/功能回归，不能把单进程GOOD冒充全发布。
4. 持续处理Fabric安全硬件门控和Kmx签名/错误语义、Mainline netd模块更新、CACHE metadata生命周期、真实UI8初始DATA直接升级与独立恢复实测。A71原生重试启动证据保留，不替代这些范围；本輪未重启/刷写，包仍实验候选。

## 2026-10-03 A73最新执行顺序：SDK实际契约

已完成SDK28/29/30历史签名、原S6 SDK32选中定义及当前BOOT只读观测。SDK28的12个WebView旧接口已退出官方29/30参考；原S6自己也已没有其中9个owned定义。蓝牙新semSetPriority/semGetPriority已经存在并委托ConnectionPolicy。不能再机械恢复整个旧stub；详见SDK_CONTRACT_INVESTIGATION_A73.md。

1. 先追踪保留vendor/etc/vintf/compatibility_matrix.xml的system-sdk28来源，与原S6 system/etc/vintf/manifest.xml及Soong/Make生成变量对照；A39全部3个Java代码包366方法/53字段/119类型集合、native反射/回调及真实新服务访问仍是设备契约依据。没有变更声明或删除vendor要求。
2. 若找到实际BluetoothHeadset.setPriority消费者，在该消费者中迁移到新setConnectionPolicy或现有semSetPriority，核对0/100、AttributionSource、权限和断连返回；无消费者不重签com.android.bt APEX加入闲置alias。TokenBinding/WebView旧接口如有动态调用，应迁移消费逻辑到现代明确不支持/nullable路径，不恢复旧安全实现。
3. 只在上述契约范围/运行依据明确后生成独立SDK适配profile/patch，限定XML或实际消费者差异并解释支持声明。不得仅加28数字、删除设备要求或改Build返回值来获得GOOD。FCM4独立COW候选8097项保持，后续镜像不能继续使用仅8096项旧基线。
4. 继续Fabric实际硬件门控及Kmx签名/错误传播、Mainline netd更新依赖、真实UI8初始DATA升级及独立恢复验证。当前A71包保持实验版；本轮无刷写/重启，核心运行身份不变。

## 2026-10-03 本轮结果

原生TWRP精确目标来源PRODUCT重试RC=0，随后新启动会话boot_completed=1、user0正常解锁、Enforcing、42 active factory与四角23px/Clock系统注册均确认。没有把这次重试当作UI8首次升级；完整升级前DATA条件另询用户。FabricCrypto重复abort及未来Mainline更新仍未解决，继续保持EXPERIMENTAL。见`audit/native-target-retry-ui85-a71-v2.json`与`audit/native-retry-android-boot-ui85-a71-v2.json`。下文各阶段是对应时间的记录。

## 2026-10-03 最新原生安装与启动证据

A71 v2精确目标来源的实际TWRP PRODUCT重试已通过：真实updater1959、Recovery549、当前日志调用与PID starttick全程绑定，原生最终RC=0及包内完整验证明确记录，158秒；Recovery保持同一PID/crash_counter0。原TWRP屏幕超时60暂改0，测试后恢复60。此次不是UI8初始DATA升级，也不能覆盖此前A70首次整包终态未捕获；不将一次无崩溃推定所有条件下Recovery可靠。

此前普通重启已12.6小时uptime、user0解锁、42 active factory模块和四角23px；指纹accept10、人脸本会话accept0/reject5。FabricCrypto缺Fkeymaster循环仍未解决，新的全部DEX字串及Kmx984类/205直接调用审计见FABRIC_SECURITY_REBASE_A72.md。最新安装后正常重启采集中，尚未标此新会话启动通过。审计：`audit/native-target-retry-ui85-a71-v2.json`、`audit/normal-reboot-runtime-ui85-a71.json`。以下各阶段记录保留历史范围。

## 2026-10-03 当前验证状态

A71 v2已从精确审计的A70实验来源调用真实TWRP安装，并在Android中观察到boot_completed=1、user0 RUNNING_UNLOCKED及Enforcing。随后Recovery完整回读证明SYSTEM与目标逐字节相同；PRODUCT仅四个ext4超级块挂载记录字段共10字节变化，其余全部字节与目标相同。BOOT和已适配S6 VENDOR完整原块不变，2768项vendor检查及42 factory/no active APEX预检通过。证据见`audit/complete-package-runtime-ui85-a71-v2.json`与`audit/complete-package-readback-ui85-a71-v2.json`。

实际TWRP日志还记录Recovery界面进程在drmModePageFlip错误后SIGSEGV并重新启动；原安装最终RC=0未捕获。完整目标内容的证明不能代替可靠原生安装终态。最新从Recovery正常返回Android后ADB仍未授权，此次正常重启/解锁复测待正常授权。

已做新包Clock系统注册/当前用户版本打开、传感器/视频硬解/Camera2/存储及手动亮度有限回归。圆角用户仍感到切割、不流畅；原厂曲线及设备离屏抗锯齿已确认，实际面板质量未确认。直接v0.48.1初始DATA升级、恢复包实际执行、未来Mainline更新兼容、完整VINTF/CACHE生命周期和剩余功能继续未通过，包保持EXPERIMENTAL / NOT_PASSED。以下阶段记录保留历史范围。

## 下一执行顺序

1. 正常恢复USB调试授权后，在不刷写/清DATA情况下验证本次正常重启、用户区解锁、核心进程和现有功能；保留本次证据，不能复用前一启动会话作为重启通过。
2. 单独定位原TWRP界面DRM崩溃与安装终态缺失，使用已实现的当前调用/PID绑定观察器采集实际终态；不因日志缺失重刷已经回读完整的分区。
3. 继续定位更新APEX的netd实际崩溃依赖，保持更新拒绝规则；不能放宽guard或永久隔离更新来代替兼容性修复。
4. 在真实UI8初始DATA条件下完成直接升级验证；不降级现有已升级DATA伪造此条件。另完成独立恢复入口实机验证与功能矩阵，未达门槛不标稳定发布。

## 2026-10-02 当前执行顺序：指纹失败及Mainline回归

1. 已先保存A66返回Recovery的last_kmsg/pstore/recovery日志；明确失败是t860-tethering-check拒绝更新APEX manifest，尚未到system_server，不回退未知framework。
2. scripts/quarantine_live_tethering_update_a67.sh限定已激活tethering372038420改名保留原inode；核对BOOT/VENDOR/SYSTEM与所有其他active成员metadata、session不变。随后重启确认factory361153320被选择、guard两阶段通过、真实bpfloader成功及网络；Recovery未手动改其他18模块；Android随后因netd crash自动回退整批，当前factory active，Mainline更新兼容独立未过。
3. A66 XML候选保持隔离：启动后确认HW_LS=false及原LightSourceView分支，再由用户试原模板的照明/认证。人脸零模板必须独立进入设置抓录入/失败日志，不能由指纹修复推定人脸恢复。
4. 当前E2 SHA8d6bd400…含A66，旧A64源SHA34d8aaeb…不再适用于该树。只有A66实机验证通过后，生成新policy验证及候选profile/全ext4/ZIP；原A64镜像保持历史，不重命名冒充新包。
5. 完成format2安装器vendor-helper集成、正/负/中断与单配置恢复用例；新包升级前新增active/staged APEX门槛。已更新DATA保留升级必须明确处理未知模块，不能默许native目录混配，不能删用户数据或假称发布通过。

## 2026-10-02 当前状态与下一执行门槛

当前已完成原新升级引导进入桌面及普通重启复测，首轮自动化结果见VALIDATION_RESULTS_UI85_A62.md。仍不是稳定版。E2 SYSTEM/PRODUCT为A60的8084项，inventory SHA34d8aaebafebde5686bc19cf371a33ed37e543150d3bb411279cd3f90c8de93f；A61仅在实机vendor原有Codec2 policy做单文件变换，profile为device/s6/media-c2-seccomp-ui85.json。当前实机VENDOR SHA86cae6db076dea2e5c07506c2ca4f51c04ff4583aff1c1a46c71f5873a07ee36，BOOT仍原523664a8…；A45整包仍原失败实验基线，不含修复。

接续具体步骤：
1. 保留A60新增init、A59新services逻辑及A55 metadata桥接；不再沿用8085原A45源证据。重建前刷新完整inventory/policy证据/精确容量；CIL本轮未更改。
2. 将A61 patcher/profile和原S6政策来源引入独立vendor配置安装清单：不加入S9 vendor/HAL，不整盘刷vendor。明确原v0.48.1入口和已应用A61入口，不能宽泛放行旧完整VENDOR pin；以真实审核状态和单文件幂等/回滚设计处理。
3. 当前可启动基线继续实体触控/S Pen/指纹/音频、自动亮度、键盘及DeX/多窗口；对QCC新SKU gate与FabricCrypto Fkeymaster消费者追踪，记录不支持能力和真正兼容分支，不盲删服务。
4. 自动化已验证AVC硬解48帧/3路JPEG/4传感器/存储回读/联网、显示档位和手动方向链路；不据此把声音/画质/DRM影片/深睡和全部Samsung功能标PASS。
5. 新整包重建必须包含A50-A61所有独立device变换，排除诊断个人公钥。完成整包dirty upgrade/回滚、VINTF SDK28及CACHE metadata生命周期之后才考虑发布。

## 当前执行状态 A58/A59（2026-10-01）

已获用户“确认开始刷入验证”授权并实际完成A49及A50–A58修复；下文A45–A47等待授权描述均为历史。A58恢复原S9 Routines并撤销误裁剪，实际共享身份已获得Launcher READ_SETTINGS，330秒启动稳定窗口及密码真实验证/用户区解锁完成，桌面仍被独立3010错误锁屏阻挡。下一步先定位/验证限定KGTA缺失兼容逻辑，再进行界面解锁、硬件功能自动化测试，最后生成包含全部修复的新完整ZIP（原A45不含这些修复）。当前只读硬件证据不当作功能通过，完整VINTF与CACHE metadata生命周期未过。

# X710 One UI 8.5 → T860 rebase 执行计划

最新 A47：精确A46原样SYSTEM/PRODUCT的独立TWRP回滚ZIP已生成，原工具14项恢复协议测试及实际114块预检通过。升级输入仍是A45；失败恢复输入见 `out/rollback/A46-live-ui8/TabS6-A46-RESTORE-CURRENT-UI8-SYSTEM-PRODUCT-TWRP.zip` 和 [TWRP_ROLLBACK_PREPARATION.md](TWRP_ROLLBACK_PREPARATION.md)。不依赖半写SYSTEM挂载，不恢复DATA状态。设备未推送/刷写/重启，继续等待已提出的重要数据备份和实验刷入/首启确认；这两项收到前不能进入执行阶段。

最新 A46：实际TWRP只读预检、物理硬件pin和当前系统身份通过，精确SYSTEM/PRODUCT回滚副本已保存/验证；实机相对NO_DEBUG_ADB发布包的两个诊断文件已单独归为WORKAROUND，未迁入新donor。下一步：①确认重要数据独立备份及明确刷入/首启授权；②通过TWRP执行A45，仅写SYSTEM/PRODUCT，写前/后按安装器检查BOOT/VENDOR、全部块及整分区SHA；③用户手动首启，采集启动链/SELinux/system_server/SystemUI日志，先最小启动再基础硬件/Samsung/加密数据回归。新donorADB保留认证，能否连接取证未测；失败按日志定位，需回到recovery时由用户进入，使用原样副本恢复而不混刷旧framework/清DATA。恢复SYSTEM/PRODUCT不能恢复首启后的DATA状态。详见[TWRP_READONLY_PREFLIGHT.md](TWRP_READONLY_PREFLIGHT.md)。当前没有执行任何刷入/重启，新运行及完整VINTF仍未通过。

最新 A45：完整诊断候选已实际生成：主工程 `out/rom-candidates/A45/` 包含SYSTEM/PRODUCT raw、manifest、ZIP/SHA/README，全部内容/metadata回读、固定尺寸/e2fsck、原TWRP114块载荷预检通过。先由用户手动进入TWRP，只读核对物理BOOT/VENDOR和回滚条件；获明确刷入授权后才进行新boot→基础硬件→Samsung功能→PIN/CE/DATA升级验证。SDK28/完整VINTF未解决，继续保留原检查与真实未决表；候选不等于稳定升级目标已完成。剩余静态接口/SDK28与设备桥接工作继续按调用证据推进，不拿旧核心文件覆盖。

最新 A44：F04 的新 SF HIDL 后端和根窗口分流已加入隔离 E2；只改一个文件，metadata 保留，其余 8,084 项不变，删除清单不变。原因、可读汇编、patch/profile 和全树证据见 [FINGERPRINT_HIDL_REBASE_AUDIT.md](FINGERPRINT_HIDL_REBASE_AUDIT.md) / `audit/fingerprint-stage-evidence-ui85.json`。当前精确 SYSTEM/PRODUCT 空闲336,986,112/106,770,432 B，e2fsck0。新窗口标题已从原 BiometricSetting 确认；HWC/指纹/实际 namespace/回溯/升级未测，完整 VINTF 未过，无 ZIP。下面旧 A43 的“未调度/未安装”只描述当时状态。

### A44 之后的具体顺序

推进原则：先完成下列启动所需接口/VINTF/policy gate并生成**最小启动诊断候选**。人脸、相机附加模式、RGB/sysinput等尚未完成的功能须进入候选已知问题表；只有确实影响启动/核心服务的缺口才阻断首次诊断包。随后依据实机日志推进基础硬件与Samsung功能，不把全功能实测作为生成首个测试包的前提。

1. 对保留 VENDOR 的 `vendor.display.config@2.0` 与 SYSTEM_EXT 新 `libdisplayconfig.system.qti.so` / `vendor.display.config@2.0.so` 完成调用编号、Parcel 参数和 linker namespace 核对；F04 后端仅使用原新 HIDL Create/mask，真实服务注册/失败重试/lifecycle 保留动态验证项。新 `libgui.so`、`libui.so`、framework 指纹类和 BiometricSetting 继续用已核对原新实现。
2. 核对新 `services.jar` face provider 与保留 T860 的 AIDL face service/init/manifest/CDSP 依赖，先确定旧桥接是否已随固定 vendor 存在；原 donor face HAL 不替换硬件层。针对缺口做脚本化桥接，限定注册/调用/权限，不以吞异常伪造可用状态。
3. 在新 `priv-app/SamsungCamera`、`libSceneDetector_v1.camera.samsung.so` 中重定位旧 SceneDetector/FastAEC/portrait release 修复。`cameradata/camera-feature.xml` 已安装 T860 尺寸/0、1、2 ID，先验证消费和旧 HAL 接口再修改新方法或 native。
4. 新 Settings/framework RGB 路径对应 T860 `whiteRGB`、`T860ColorTemperature` 桥接，核对 sysinput 新消费者与固定 `vendor.samsung.hardware.sysinput@1.2-service`；音频检查新 policy 对保留 T860 mixer/旧 HAL 的 route。只补缺失的设备桥接/精确 contexts 和 policy。
5. 固定完成后的全树，处理 split policy 缓存输入与完整 VINTF/SDK28/FCM4 证据；任何未解决兼容条件明确记录，不能伪造声明通过。
6. 生成完整候选 SYSTEM/PRODUCT 镜像与 `rom_candidate` manifest，再由 `build_twrp_upgrade.py` 构建保留 BOOT/VENDOR/DATA 的诊断升级 ZIP并回读校验。真实启动/硬件/PIN/CE 测试需要候选先存在；不得用“新运行尚未测”循环阻止诊断候选打包。未经用户授权不刷入平板。

最新A43：保留light HAL raw修复/新Java编码已核对，当前USB旧系统选择Light回退路径；新运行仍待测。新S9 HIDL-only Null后端候选已生成，修复旧D23目的而避开新post-init再返回16B Null的变化；42B差、两重放和12静态路径通过，未加入E2。具体脚本/profile和理由见[FINGERPRINT_HIDL_REBASE_AUDIT.md](FINGERPRINT_HIDL_REBASE_AUDIT.md)。接下来完成FP根窗口到两处新output mask的分流，保持ScreenDecor原分支及新libgui/libui/framework原实现；复核CFI/namespace、HIDL2.0 wire、失败/lifecycle后整合F04，再处理其他硬件桥接、完整VINTF/policy cache与最终TWRP候选。A43回读8,085项全树与A42相同、删除清单不变，原容量仍适用。USB网络/加密基线未变，物理BOOT/VENDOR未读；dirty upgrade与新ROM运行NOT_TESTED，无ZIP。

最新A42：F07原厂355亮度曲线已用S9新资源表重编，两RRO在原新idmap2隔离执行中映射八资源成功，加入E2后全树8,085项只允许两新增；删除清单不变。精确SYSTEM/PRODUCT free337,219,584/106,770,432B、e2fsck0。F04原新Java已optical/position2/HIDLtype3，旧两Java操作为OBSOLETE_CANDIDATE；Layer真实FP getter虚槽+0x20已定位，native mask输出仍UNKNOWN。见[BRIGHTNESS_REBASE_AUDIT.md](BRIGHTNESS_REBASE_AUDIT.md)、[DISPLAY_REBASE_AUDIT.md](DISPLAY_REBASE_AUDIT.md)及`audit/brightness-stage-evidence-ui85.json`。接着核对FP虚调用/output state、保留vendor light/raw与新framework资源消费、其余namespace/策略缓存/完整VINTF，再完整候选打包。运行和dirty upgrade未测，无最终镜像/ZIP；以下A41等为历史状态。

最新A41：F03已从原S9 framework重实现并加入独立E2，保留原新签名SDHMS和S9策略；8,083条全树回读只改1JAR/移除163条对应编译缓存，应用删除清单不变。实际DEX模型3996用例通过；不是ART/HAL运行。精确SYSTEM/PRODUCT空闲337,256,448/106,770,432B，e2fsck均0。见[DVFS_REBASE_AUDIT.md](DVFS_REBASE_AUDIT.md)及`audit/dvfs-stage-evidence-ui85.json`。接下来F04新framework/SurfaceFlinger输出调度、F07资源RRO和native namespace桥接，随后完整VINTF/策略缓存/候选镜像。SDK28未宣告、完整VINTF/新运行/保留DATA未过，无ZIP。A40及以下全树/容量说明为历史状态。

状态：**分析、独立补丁和安装器已建立；尚无可启动镜像/刷机 ZIP**。执行基线及逐项分类见 [UI8_PORT_CHANGES.md](UI8_PORT_CHANGES.md)。此计划的“通过”只能由静态审计和 T860 实机日志共同确认；生成 Odin 包不等于适配完成。

最新A39：实际保留vendor的3个Java代码包引用已对原新framework/ART定义完整核对，无静态缺口；SDK28契约及native动态访问仍待证明，未新增28声明。FCM4原厂kernel requirements已与官方核对，适用231项匹配；独立诊断矩阵被原新libvintf解析/合并，SDK28错误仍真实可见。43类/154平台成员独立解码、全树8,246项回读一致；E2未改，无新裁剪/ZIP。接着查`libjnihelper`/HwBinder/时间socket和SDK28契约，再正式metadata/kernel/SEPolicy/APEX范围检查、其余bridge/policy cache与完整候选。见[SYSTEM_SDK_REBASE_AUDIT.md](SYSTEM_SDK_REBASE_AUDIT.md)及[VINTF_REBASE_AUDIT.md](VINTF_REBASE_AUDIT.md)；下列A38及更早段落为对应阶段的历史状态。

最新 A38：三split型号/名称六字段已安装，原软件版本/fingerprint/qssi及硬件init保留，全树仅三文件内容变、净增3 B。原S9 vintf/libvintf在隔离Linux实际运行，发现VNDK30与system SDK28声明不匹配；以真实B04 APEX为依据新增176 B独立VNDK30 fragment，其他8,245条目相同。新实现能够合成level4 matrix，但弃用检查仍缺实际level4文件，不能沿用“缺4必然无法合并”的静态推断。先处理SDK28实际consumer/API证据、level4/deprecation/kernel输入，再完整checkvintf/cache/桥接；此dump不是完整gate，未生成ZIP。见 [IDENTITY_INIT_REBASE.md](IDENTITY_INIT_REBASE.md) 与 [VINTF_REBASE_AUDIT.md](VINTF_REBASE_AUDIT.md)。

最新 A37（2026-10-01）：B05配对、F02→F01-ICCC→WIRE、floating/camera硬件值已安装到A36的同一E2树。全树只发生五替换/一新增/四services关联cache与profile移除，其他内容/链接/metadata全部相同。SYSTEM/PRODUCT精确空闲 **288,399,360 / 106,770,432 B**，两个e2fsck0；应用删除列表不变。身份/init只读追踪确认保留vendor已固定导入gts6lwifi，新三分区型号仍X710；下一步完成split身份配置、具体硬件桥接、policy cache和真实VINTF，再构建完整候选。见 [DEVICE_STAGE_INTEGRATION.md](DEVICE_STAGE_INTEGRATION.md)。A36旧系统APEX预检另有14个父session目录创建失败，ready/applied均0；不假设DATA更新集合为空、不自动清理，recovery原始DATA核对另列升级前条件。

最近构建进度 A35/E2（2026-10-01）：保留 E1 四应用，独立树仅清理九个已核对 APK 自身 oat 缓存，原 APK 和全树其他内容/metadata 不变；加入实际 B06 25 个 native 文件、CPU 配对和新权限 CIL 后，SYSTEM 空闲 **283,426,816 B**、PRODUCT **106,770,432 B**，两个 e2fsck 为 0。当前 payload 的容量子门槛通过，余量分别 **14,991,360 / 1,912,832 B**；不是完整 G1/G2/G3 或 ROM。执行脚本 `apply_app_preopt_capacity_ui85.py` → `apply_prepared_capacity_cost_ui85.py` → `build_capacity_probe.py --system-inodes 32768`，设备数据和应用删除列表不变。详细证据和修改前决定见 [CAPACITY_DECISIONS.md](CAPACITY_DECISIONS.md) A35/E2。

接下来的具体整合顺序：

A36 已在独立 E2 树接入 B06 启动组件：唯一 load-bpf-programs 点的 check→两目录 bind→bound 回读→原 bpfloader，19,928 B 新 helper、精确 property/file contexts 和两条只读 CIL。73 host 项、六输出重放、同 vendor 原参数策略编译/strict 不增冲突、29 label lookup 均通过；六文件安装 metadata 回读通过。原 APEX/真实 loader/设备未改，Android init/namespace/绑定/网络仍未测。具体实现和日志在 [TETHERING_BOOT_INTEGRATION.md](TETHERING_BOOT_INTEGRATION.md)。下面第1项的本地接入已实现，剩动态验证；继续第2项设备身份和 B05/F01/F02/设备值的同树整合。

1. 从原 X710 签名 CAPEX 再重放 B06-GATES/JNI/CLAT，并核对活动模块 `361153320` 与全部 native 输入身份；为 `/system/etc/t860-tethering-native/{bin,lib64}` 设计先验证身份再目录绑定的 init 逻辑。保持新签名 APEX/32 位目录不变，不能只放补丁文件而未让活动模块使用它们。核对 APEX 激活先后与 mount namespace/SELinux。
2. 对新 SYSTEM 的实际 `build.prop`/init 导入实现 T860 身份，保留 X710 软件版本；重放 B05 配对、F02→F01-ICCC→wire、floating/camera feature 值与必须的硬件桥接。新 services 改动后仅处理对应预编译产物，不能搬旧 runtime。
3. 在同一树维护修改后 split CIL/cache ID，核对保留 vendor、FCM level4 与真实 checkvintf；GPU/FUSE/OEM loader 中的具体未决项按调用者证据处理。运行门槛需要可审计候选生成后实机验证，不把未测写成通过。
4. 重测完整 SYSTEM/PRODUCT ext4、owner/mode/label/APEX/native ABI 和容量，生成真实 `rom_candidate` manifest 后交给已有 TWRP builder。E2 的临时容量树/镜像不能直接作为这个 manifest。

SELinux 编译检查更正（A33）：原 S9 init 使用 `-N -c 30`，同 vendor 的旧/新策略按该参数都静态编译成功且无 permissive 域。严格 neverallow 是独立权限审查，不作为原 init 编译失败证明；最终仍要验证策略加载、Enforcing、AVC、缓存身份及完整 VINTF。执行和证据见 [SELINUX_REBASE_AUDIT.md](SELINUX_REBASE_AUDIT.md)，其他容量/运行/升级门槛不变。

A34 已实现 NetworkStack generic bpffs 窄权限候选：`device/s6/network-stack-bpf-ui85.json`、`device/s6/sepolicy/network-stack-bpf.cil` 与 `patches/patch_network_stack_bpf_policy_ui85.py`。正式独立构建树应先重放B04，再从原新plat_sepolicy.cil生成此候选（root:root/0644/sepolicy_file），只增加network_stack例外和file read/write/getattr；再按原init参数生成策略/维护ID、与四native目录和CPU对象/库配对重放、重测ext4。新Java消费者22完整方法已核对；最终Linuxv2验证只有一条三权限allow差异，严格冲突与基线相同，其余规则/组件不变。仍需新ROM实际pin labels/Enforcing/AVC、Wi-Fi/DNS/IPv6/CLAT/Tethering与保留DATA；不把probe或隔离policy binary当ROM输入。GPU/FUSE/OEM BPF和VINTF依赖继续检查，见SELinux报告A34及BPF报告第17节。

## 目标产物与目录契约

以 X710 官方 `X710XXS6EZH3` 的 SYSTEM、SYSTEM_EXT、PRODUCT 为唯一新用户态 donor；以 T860 `T860XXS5DWH1` 的原厂 BOOT/DTBO/VENDOR 和旧工程已溯源的 T860 内核/设备补丁为硬件底层。新工程放 `device/s6/`（设备值和补丁 manifest）、`patches/`（可审计的文本/DEX/ELF/RRO 定向补丁）、`scripts/`（只读审计、构建和验证）、`docs/`（决策与日志）。`t860-ui8/` 仅作参考与已验证补丁来源，不作为新 ROM 的 parent image。

脚本须接受 `DONOR_BUILD`、官方 ZIP/提取 super 路径、T860 stock 输入路径与独立输出目录；校验 SHA-256 和版本，禁止覆写原 ZIP/原分区、旧成品和已有输出。每个 patch 记录：ID、分类、原因/日志、输入相对路径与哈希、定位锚点、预期输出哈希、owner/mode/SELinux context、撤回方法。对 method/resource patch 使用语义锚点和唯一命中断言；新 donor 未命中时停止而不是强行应用旧偏移。

## 0. 冻结输入与布局（已读审计，待脚本固化）

1. 记录 T860/X700/X710 官方 ZIP、X710 `super.img.lz4`、T860 BOOT/DTBO/VENDOR、旧 v0.48 镜像和 TWRP 的 SHA-256。解析 AP/BL/CSC tar 成员，保存 liblp 分区表、镜像文件系统类型与 `build.prop`/fingerprint/One UI 值。已知 X710 是 SDK36/One UI80500/EROFS、T860 stock 是 SDK32/One UI40101/ext4。
2. 用只读挂载生成文件哈希清单、VINTF 列表、init service 图、SELinux type/context 列表、permissions/features/overlay 清单和 APK/JAR/APEX 哈希。现有 `docs/audit/*.rsync` 作为路径级快照；补充 owner/mode/xattr 和 APK resource/DEX 差异，而非把 rsync 行数视作 patch。
3. 对照 X710 framework compatibility matrix 与 T860 VENDOR manifest，逐个核对 HIDL/AIDL 版本与实例。特别核实 composer 2.4、旧 sensors/health/DRM、Wi-Fi、audio、camera、ET713、ICCC；X710 VENDOR 的新 service 仅作参照。**首轮静态覆盖检查已完成并复核**（PORTING_LOG A08/A09）：`scripts/check_vintf_compat.py` 输出 `docs/audit/vintf-compat-x710-vs-t860.tsv`，X710 device matrix 的 247 条中 26 条被 T860 stock vendor 完整覆盖、221 条未完整覆盖；后者有 210 条与旧 UI8 需求签名相同、7 条版本/实例声明变化、4 条新增。Android 16 libvintf 将这些 HAL 条目视为 optional，但“0 mandatory 缺口”**不能**替代 `checkvintf`：T860 `target-level=4`，X710 与旧成品均缺 level-4 matrix，脚本也没有做 FCM 合并、kernel/SEPolicy 检查。下一步对 7 条变化和 4 条新增逐项追踪消费者，再在可构建的组合上运行真正的 `checkvintf` 与实机 `lshal`。

**门槛 G0：** 所有输入哈希、版本、分区列表、文件类型和旧成品来源可复核；相同路径的旧核心框架二进制不进入构建输入清单。

## 1. 先解决物理容量与文件系统

1. 以 X710 原树统计 SYSTEM、SYSTEM_EXT、PRODUCT 的 apparent 字节、inode、每个应用及模型目录的容量；保留 X710 签名的核心 app/APEX/framework/Knox/Samsung Settings/Account、SystemUI、桌面、相机与输入服务。旧 trim list 仅作候选。给每项候选写出依赖引用、移除后损失和可测替代路径。
2. 按 T860 PIT：`/system` 6,534,725,632 B，`/product` 1,048,576,000 B，`/vendor` 1,379,926,016 B。X710 SYSTEM_EXT 必须作为 `/system_ext` 合入 T860 SYSTEM；`system_ext` 的独立 EROFS 镜像不能原样刷入。T860 4.14 对 EROFS 的挂载能力尚未被证明，暂以旧已验证的 ext4 构建格式为基线。
3. 旧 X700 trim 在 X710 中命中的 SYSTEM 为 2,670,016,061 B、PRODUCT 为 1,397,956,764 B；root 权限重算后 SYSTEM+SYSTEM_EXT apparent 仍有 7,027,305,663 B，比 T860 物理 SYSTEM 多 492,580,031 B，尚未算 ext4 元数据与余量。用户选择保留核心功能、裁可选 AI/预装。`device/s6/capacity-policy-ui85.json` 是逐项理由的候选清单；保留 AirCommand/DynamicLockscreen，将 X710 Smart Suggestions 移到 PRODUCT，再审查可选语言、Bixby/编辑预装、无引用双摄特效库与 Wi-Fi 机型通话界面。静态投影见 `docs/audit/capacity-policy-evaluation.json`，SYSTEM 剩 489,362,291 B、PRODUCT 剩 197,735,327 B，均未扣 ext4 开销。**不得**为合容量直接删除核心 APK、权限 XML、服务库或 Framework。
4. 建立可重放的 trim manifest，文本中注明 `CAPACITY_ONLY` 与功能损失。每次构建前计算实际 ext4 镜像使用块/inode、最小剩余空间，构建后执行 e2fsck 与整镜像回读哈希。

B04 加入后首次精确探针的 SYSTEM 余量只有 235,843,584 B，低于 256 MiB 门槛。`device/s6/capacity-delta-ui85.json` + `scripts/apply_ui85_capacity_delta.py` 在隔离 staging 中保留 X710 原版 Weather 并搬至 PRODUCT，移除两个已无 Assistant 主包的 Google 热词注册预装；第二次精确探针记录于 `docs/audit/capacity-probe-b04-weather-results.json`：SYSTEM 297,013,248 B、PRODUCT 106,680,320 B 可用，`e2fsck` 均为 0。PRODUCT 只超 100 MiB 门槛 1,822,720 B；任何 PRODUCT 新增文件都要重测，不得用此数值批准功能依赖。

**门槛 G1：** 已有逐项解释的容量决策，SYSTEM/PRODUCT 在目标物理尺寸内且有明确余量；静态依赖扫描无被删除的必需 provider、shared library、privapp permission 或 init binary。候选的逐组功能损失和必需检查见 [CAPACITY_DECISIONS.md](CAPACITY_DECISIONS.md)。保留 OCR 后精确 ext4 探针的 SYSTEM 空闲 127,815,680 B，低于 256 MiB 门槛 140,619,776 B；两分区 `e2fsck` 均为 0，PRODUCT 高于 100 MiB 门槛 1,912,832 B。包依赖和 Weather 搬迁的运行时行为也未验证，G1 **未通过**，因此不制作可刷 ROM。

用户指定的应用清单已复核：`device/s6/capacity-policy-ui85.json` 新增 X710 实有的 `system/preload/GoodNotes`、`product/app/DuoStub`、`system/etc/spotify.conf`，并显式记录 X710 缺席的 `NoteShelf`；删除旧 donor 独有的 `Notes40` 假命中。Google 视频/邮件/地图/Chrome 与 Microsoft OneDrive/Your Phone、Clip Studio 已在原候选中，本轮确认 staging 中确实缺席。Netflix、Spotify 的 APK 均不在 X710，`netflixchid.conf` 保留以待 DRM 核对。Camera/Gallery/SmartCapture 等保留 APK 引用 `OCRDataProvider`，故已把它改为 **keep**，从 X710 原件恢复到 staging；不要把它当第三方笔记预装。恢复后当前策略静态投影 SYSTEM 6,214,550,578 B、PRODUCT 850,771,409 B；精确 ext4 探针见 `docs/audit/capacity-probe-ocr-retained-results.json`，SYSTEM 空闲只有 127,815,680 B，容量门槛未通过。此前 `capacity-probe-user-app-trim-results.json` 的 SYSTEM 298,528,768 B 是**未保留 OCR**的历史中间状态，不能批准当前 G1。细节见 [CAPACITY_DECISIONS.md](CAPACITY_DECISIONS.md)。

容量补救实验 E1 已在**独立副本**验证 `mkfs.ext4 -N 32768` 与四项可选 app 裁剪的组合：`LiveTranscribe`、`VoiceAccess`、`ARCore`、`LumaFusion` 共 58,009,672 B apparent；精确 ext4 的 SYSTEM 空闲 279,642,112 B（超 256 MiB 门槛 11,206,656 B），PRODUCT 空闲 106,770,432 B，两个 `e2fsck` 为 0。正式策略仍**保留**这四项。继续 G1 时先审计 X710 Settings/SystemUI/SetupWizard/Accessibility 对缺包的条件分支，特别验证 Live Transcribe、Voice Access 的 Play 商店回退、Camera/Gallery 的 AR 入口和 S Pen/视频编辑；确认后才将 E1 项加入 `capacity-policy-ui85.json`。构建脚本已新增 `--system-inodes` 供精确探针复现，并默认在记录 SHA/e2fsck 后清理大型 raw 镜像，避免再次占满 VM。见 [CAPACITY_DECISIONS.md](CAPACITY_DECISIONS.md) E1 与 `docs/audit/capacity-probe-alt-accessibility-results.json`。E1 只有容量子门槛通过，**G1 仍未通过**。

## 2. T860 硬件底座（最小可启动）

继续 G1 的最近依赖审计见 [removed-apk-reference-review.md](audit/removed-apk-reference-review.md) 和 PORTING_LOG A17。services 原 JAR 两段的所有 17,379 个类已覆盖，发现 SCS 的真实 IntelliVoice 绑定和缺包状态返回；仍须追踪上游任务是否正确失败。全归档扫描修复了 25 条漏报，优先查新增 SearchSelector/SetupWizard、语音输入/HoneyBoard 路径，再验证 Gallery/MDX/Routines/Knox。Microsoft 两主包依照用户要求保持裁剪候选；三星 MDX 是独立配套服务，目前保留。所审计 donor 分区也未发现 Samsung Notes/Samsung Internet 主包，后续核查 CSC/首次设置安装来源，禁止用旧 UI8 二进制直接补齐。G1 状态和容量数字不变。

1. 从 T860 stock BOOT 与旧 `t860-ui8/kernel/patches/` 重建内核：核对 v0.42 fs-verity、v0.43 FastRPC PM request 5 的源码、配置和模块签名；DTBO 使用 T860 stock 哈希 `864ca763…`。审查 X710 ART/odsign 与这两项补丁的需求。禁止使用 X710 `boot`/`init_boot`/`vendor_boot`/DTBO。
2. 从 T860 stock VENDOR 原树出发，重放明确的设备修复：`/vendor/build.prop` APEX 兼容值，T860 `mixer_paths_tavil.xml` 四扬声器路由、audio HAL/effects，sysinput/light，face/蓝牙桥接的可溯源部分。每项补丁保留 stock 文件哈希对照；HWC、vndservicemanager、gralloc 必须与原厂哈希相同，除非出现经过审计的具体接口原因。
3. 对 `/vendor/etc/vintf/manifest*.xml` 和 `manifest/` 仅添加真正运行的 T860 桥接服务；检查 `/vendor/etc/init/*.rc` 的 executable、class、onrestart 和依赖。X710 VENDOR/ODM/DLKM/firmware 不进入目标镜像。
4. 基于 X710 SYSTEM/SYSTEM_EXT/PRODUCT 重建 T860 的 ext4 分区，先只加入启动不可缺的 VNDK30 APEX、针对新 `mapping/30.0.cil` 计算的缺失属性，以及经静态 VINTF 检查必需的 init/context。B04 已具体化为 `device/s6/vndk30-ui85.json` + `patches/apply_vndk30.py`：只向有 staging 标记的 Linux 副本安装固定 SHA 的 APEX，按 X710 mapping 原始 SHA 和预期 264 个符号缺口生成补丁，并核对输出 SHA、owner/mode/SELinux 标签；隔离试跑见 `docs/audit/vndk30-ui85-probe.json`。正式诊断镜像构建仍需重放 B04 后重新测 SYSTEM 空间及 SELinux/VINTF。X710 的 SystemUI、`framework-res.apk`、`framework.jar`、`services.jar` 原样保留在第一轮诊断候选中。
5. 身份字段按设备身份、donor 软件版本分别设置：T860 型号/名称/CSC 使用真实值；One UI `80500`、SDK36、安全补丁和 donor 软件构建信息保持真实且内部自洽。旧工程 v0.35 为 X700 Launcher Edge 几何表把 vendor device 改为 `gts8wifi`，同时固定导入 `init.gts6lwifi.rc`；新构建先用真实 `gts6lwifi`，如 X710 Launcher 仍缺设备几何，优先用新 overlay/资源修复，若必须选 `gts9wifi` profile 则保持 T860 init 固定并独立审计所有属性消费者。

**门槛 G2：** VINTF 静态检查通过；BOOT/SYSTEM/PRODUCT/VENDOR 镜像尺寸、SHA、稀疏展开、e2fsck、SELinux labels、APEX 与签名族通过；没有 donor 硬件镜像或旧核心框架二进制混入。首次刷写采用可回退方案并保留完整 recovery/boot/pstore/logcat。

B06消费者审计与JNI候选（A24）：八个完整native函数2,851条指令、38个literal pin均对上新metadata；保留新libnetd的4.14/5.10条件分支，CLAT仍必须验证`fs_bpf_net_shared`标签。新`bpf-jni-ui85.json` / `patch_bpf_jni_next_key_ui85.py`仅在GET_NEXT_KEY错误分支接收2/524；新JNI四指令14bytes，完整函数/独立汇编/4,096错误条件模型/七项拒绝已验证。旧“所有失败→false”不迁移，LPM无法枚举的缓存语义仍须实测。先用`collect_ui8_upgrade_baseline.py`读取当前v0.48.1实际APEX路径/版本、有效native hash、cgroup/BPF labels及保留硬件hash；核对DATA更新模块是否影响激活，不自动删除更新模块。所有probe仍不可刷，G1/G2/G3未通过。

## 3. 首次启动故障处理顺序

1. 只刷 G2 审计后的最小候选。收集 `last_kmsg`/pstore、`dmesg`、`logcat -b all`、init service 状态、`lshal`/`service list`、VINTF、AVC、tombstone 与每个关键进程的启动次数。
2. 按 **kernel/init/挂载 → VINTF/linker/APEX → zygote/ART → system_server → SurfaceFlinger/HWC → SystemUI** 排障。每轮只改一个已定位原因，在 `PORTING_LOG.md` 填症状、日志、根因、旧 UI8 是否同故障、最终 patch 与 device patch 判断。
3. 若出现旧的 KnoxGuard/ICCC 3010 或 CE unlock 故障，先对照 X710 `services.jar` 的新方法、T860 HAL、异常堆栈。KnoxGuard 两个类仍在 DEX 041 第二逻辑 DEX，ICCC 在第一段；解析器必须覆盖两段。CE unlock 的新调用点是 `StorageManagerService$StorageManagerInternalImpl.unlockCeStorage`，不能沿用旧 `IStorageManager` 定位。按方法语义编制新补丁，并做 locked/unlocked、PIN、重启回归；不直接运行旧 `patch-services-jar-v0.15`/`v0.20`。
4. B06先使用`BPF_REBASE_AUDIT.md`的真实BOOT/SDK、对象metadata和native退出链。保留新netd、签名CAPEX/NetworkStack、全局libbpf/libmeminfo，重做新版本4.14/解释器兼容；逐个核对modern loader、新JNI与必需pins，再审platform GPU与隔离闭包。旧GSI族只作参考，不直接覆盖新网络栈。验证Wi-Fi `VALIDATED`、IPv6/CLAT、热点、UID/local-network权限及SELinux。
5. 若显示失败，验证 T860 原 HWC 的 composer 2.4 发现、gralloc usage、API28 分支与 X710 SurfaceFlinger；只针对新 ELF 的精确路径修复。

B05-SELECTOR 已在新 donor 主选择函数定位单 CMP（`0x568d70`），候选由 `surfaceflinger-ui85.json` / `patch_surfaceflinger_display_ui85.py` 配对独立 init 生成。完整69条指令、7项拒绝及32组静态分支模型通过，输出仅1字节改变；邻近34阈值、FP mask与EarlyWake保持原样。完整构建将按 uid0/gid2000/0755/`surfaceflinger_exec` 安装SF，按root/0644/`system_file`安装init，再核对启动时属性最终值、实际Null选择与HWC/present fence。不能把候选当成首屏已通过；参见 [DISPLAY_REBASE_AUDIT.md](DISPLAY_REBASE_AUDIT.md)、PORTING_LOG A21。

F04 native子链已追加只读审计（A22）：X710 `libgui::BLASTBufferQueue::initialize()`原生匹配`[FP Maskview]`并设bit34；libui Gralloc4 invalid masks已与旧patched值相同。这两项旧替换操作仅标OBSOLETE_CANDIDATE，完整构建暂用原X710 libgui/libui，继续核对初始化/update/重建时的消费者usage和硬件allocator。SF的新FP constructor标记尚未证明等价于旧exact-root output dispatch；接着追踪DisplayConfig state/标记消费者/新framework窗口再决定定向补丁，禁止搬旧代码洞。F04整体DEVICE_REQUIRED与实机mask亮度/注册/解锁门槛不变。

B06（A23）从v0.48/v0.48.1固定BOOT抽出4.14.190及JIT=n；新SDK36.1 loader在APEX override下先因4.19门槛返回5，另有5.4/5.10要求与解释器拒绝。`bpf-gates-ui85.json` / `patch_bpf_kernel_gates_ui85.py`已在两个原X710 APEX native中准备六条分支候选，2,469条指令独立解码只见六处变化，12项拒绝通过。它只移植较高内核检查与解释器允许逻辑，原SDK/最低4.14/错误传播不变；不是完整网络适配。执行顺序为：新BpfHandler/JNI必需pin与struct/条件 → `.android_maps/.android_progs`与现代loader的4.14路径 → 新platform GPU闭包 → 独立APEX native bind元数据/namespace/SELinux → 完整构建容量/checkvintf → 实机loader/verifier/pins/VALIDATED/IPv6/热点/权限。新L4S metadata最低3700，当前3610不满足，不能说当前必需或擅删；新map容量与旧不同需按消费者验证。原netd/CAPEX/全局libs不变；旧始终成功wrapper不迁移。见[BPF_REBASE_AUDIT.md](BPF_REBASE_AUDIT.md)，G2尚未通过。

**门槛 G3：** 冷启动/重启两轮，`system_server` 与 SystemUI 无循环崩溃，触摸/显示/锁屏/基础存储可用，SELinux Enforcing。未满足时不进入三星功能层。

## 4. 基础硬件，再到 Samsung 功能

| 顺序 | 具体目标位置与动作 | 必须留下的实机证据 |
|---|---|---|
| H1 显示与输入 | X710 `floating_feature.xml`、PRODUCT framework RRO、T860 light/sysinput 服务；重编亮度/自动亮度/UDFPS RRO，确认双击唤醒。 | 触摸、旋转、255/305/355、自动亮度、HBM、睡眠/唤醒、充电 AOD、输入设备事件。 |
| H2 连接与音频 | X710 NetworkStack/Tethering、T860 Wi-Fi/BT/audio HAL、`mixer_paths_tavil.xml`、蓝牙音频 manifest。 | Wi-Fi VALIDATED、热点/CLAT、BT 开关扫描与 A2DP 实听、USB/MTP、四功放播放/录音。 |
| H3 存储与传感器 | X710 `vold` 与 T860 `sdfat`，VINTF sensors、T860 FastRPC 内核。 | 内外存读写、SD 重挂载、传感器枚举/旋转、睡眠唤醒、温度/电池/充电。 |
| H4 生物识别 | T860 ET713/face bridge，X710 `framework.jar`、`services.jar`、`floating_feature.xml`。 | 指纹/人脸真实注册与锁屏解锁、模板持久、HAL death/拒绝为零。 |
| H5 媒体与相机 | X710 `camera-feature.xml`、SamsungCamera/媒体库，T860 camera HAL；按真机公开逻辑 ID 0/1/2（广角底层物理 ID 50）配置，替换 X710 错把前摄 ID 设为 2 的路径；更新前摄 3264×2448 及 crop/快照分辨率。 | 三 ID 预览、照片/JPEG、模式切换、视频硬解、DRM L1/实际级别记录，不以 APK 启动代替功能验证。 |
| H6 三星体验 | X710 AirCommand/HoneyBoard/Settings/Account/Knox/DeX，T860 S Pen/HWRDB/CSC/mDNIe。 | 笔悬浮与离线手写、键盘、DeX/多窗口、Samsung Settings/Account、Knox 基础服务无循环、RGB 实际 sysfs 写入。 |

旧项目的最近任务快照优化、DailyBoard/provider、QCC/Heatmap/SNAP 和 Smart Suggestions 问题放在对应基础功能正常后独立验证。每项修复要有前后日志；若 X710 没有相同症状，标记 `OBSOLETE_CANDIDATE` 或 `DONOR_SPECIFIC`，不应用旧补丁。

## 5. 发布与 One UI 9 重放门槛

### 当前 v0.48.1 TWRP 保留数据升级路径

用户已确认当前版本为 **v0.48.1**，复用 v0.48 七个镜像。新 `device/s6/twrp-upgrade-ui85.json` 固定 T860 物理布局、BOOT/VENDOR 原有哈希、source SDK/One UI 和不写 DATA 的契约。`installer/update-binary`/`libupgrade.sh` 与 `scripts/build_twrp_upgrade.py` 已建立；打包器只接受经过 ext4/容量/目标身份/B04 核对的 raw SYSTEM/PRODUCT，不能把容量树当成成品。固定 recovery 的 14 项模拟及 6 项大偏移/API 检查通过；发现并修正 mksh 32 位算术、awk substr、原生 dd 选项与 ZIP64 限制，见 [TWRP_UPGRADE.md](TWRP_UPGRADE.md)。这些是 recovery 用户态工具验证，未完成真实安装。

F02 已准备新 donor 的一条 CE 分支补丁，独立探针在 `out/patch-probes/F02/`，基础 staging 未动。执行顺序：继续 G1 → 将已审计设备配置/补丁与新 donor 组成完整构建 → 记录 F02 新 JAR 元数据并使其 donor 编译缓存重新生成 → G2 文件系统/VINTF/SELinux → ZIP32 分块打包/反向检查 → TWRP 真实分区核对及保留 DATA 安装 → 旧 PIN/错误 PIN/Keystore/CE/DE/账户/资料与 G3/H1–H6 回归。F2FS/ICE 和 v1/v2/v3 blob 静态路径已检查，SDP/Enterprise 的新路径仍未理解，见 [CE_UPGRADE_AUDIT.md](CE_UPGRADE_AUDIT.md)。

F01 ICCC 已细化为 `device/s6/iccc-ui85.json` 和 `iccc-transactions-ui85.json`：新权限检查保留，三项不兼容查询生成空数组；新 donor system 接口库只把 measurement/terminate 的编号8/9映射回旧6/7。**两者必须配对**，仅 JAR 会留下 `iccc_unload` 的不兼容调用。准备顺序为原 X710 JAR → F02 → F01-ICCC；接口库从原 X710 独立生成，不能取旧 UI8 库。`build_services_compat_probe_ui85.py` 已重放得到 `out/patch-probes/F01-F02-bundle/`，两个产物及 manifest 两次相同；TWRP builder 实际拒绝其 probe kind。未来完整构建须在独立树应用成对文件的 owner/mode/SELinux metadata，清理仅属于原 donor services 的编译缓存并重新生成，不清用户 DATA/密钥，再测容量/真实 VINTF/SELinux。当前32位接口和 native/APEX 动态调用范围、共享内存、TEE/企业降级、KG状态仍未过；具体证据/运行项目见 [ICCC_REBASE_AUDIT.md](ICCC_REBASE_AUDIT.md)。

发布候选需完成用户列出的全部项目：boot、system_server、SystemUI、触摸、显示、亮度/自动亮度、旋转、Wi-Fi、Bluetooth、音频、USB、存储、睡眠/唤醒、充电/电池、传感器、指纹、相机、视频硬解、DRM、S Pen、键盘/输入、DeX/多窗口、Samsung Settings/Account、Knox 基础组件。每项记录版本、测法、结果、日志位置；未测项目明确写 `NOT_TESTED`。再做两次冷启动、保留 DATA 的升级/回滚测试、分区回读哈希、SELinux Enforcing/AVC 审计和 Odin/TWRP 包反向解包审计。

未来切换到 X710 One UI 9 时只更新 donor 输入与预期版本、重新跑差异/容量/VINTF/定位断言。设备值、T860 内核/vendor 补丁可以按 ID 重放，但所有 `VERSION_SPECIFIC`/`WORKAROUND` 先重新验证；不得以本次成品镜像作为 One UI 9 的输入。

A25：当前v0.48.1已通过ADB只读核对，真实kernel/JIT/Enforcing/cgroup2及有效旧JNI相符，BOOT/VENDOR全SHA因无su保持UNKNOWN。新APEX目录31文件已审计，lib64+新netbpfload复制至少13,141,624B，超过E1门槛外余量1,934,968B（未计ext4）；完整适配后必须重测容量。具体模块/新JNI/32位/6755元数据和证据见`docs/UI8_DEVICE_BASELINE.md`，未刷写或新增裁剪。


A26：`audit_netbpfload_selection_ui85.py`已确认SDK3610走自有loader0xa378，4.14跳过kernel BTF；选中36map/25program（19必需6可选），无需为对象含BTF而替换旧libbpf。`audit_preserved_kernel_bpf_interfaces_ui85.py`从固定BOOT中的完整Image/RELA确认所需类型与必需helper存在，四optional缺helper125且原loader有失败继续。不是verifier通过；One UI9重审alternate SDK>3611。后续先合并policy/pin标签与APEX bind同源闭包，再platform GPU、独立树重放/容量/VINTF与实机。旧单文件bind EACCES缺明确AVC，禁止凭此添加allow；见BPF审计第10节。


A27：`audit_split_sepolicy_ui85.py`已合并新三个分区+B04 mapping+固定VENDOR，A27严格264冲突和19查询保留为历史证据；A33原init使用-N/-c30，同vendor旧/新策略均静态编译成功且0permissive domains，严格结果继续审查，见SELINUX_REBASE_AUDIT.md。目录mounton有allow，两个native文件类型没有；保留目录bind候选。`audit_preserved_kernel_bpffs_labels_ui85.py`从实际BOOT Image核对4函数1,082指令/17锚点，path-label白名单不含bpf；新CIL专用标签不证明4.14运行标签。下一步先新loader pin/create链→新CLAT等价检查/窄权限→同源native目录/元数据及容量→同vendor旧策略baseline冲突对比与完整验证。


A28/A29：新CLAT只改唯一rodata context为固定4.14 generic label，363代码指令不变、八精确比较/11拒绝通过；B06-GATES+JNI+CLAT从原X710 tree组合25bin/lib64文件（仅四文件改动），两次重放一致。Linuxscratch全回读owner/mode/label，clatd6755和for-system0750保留；未安装init/bind。下一步platform GPU新loader、同vendor策略baseline、generic窄权限/consumer及活动APEX版本/身份guard，再完整目录bind与容量/VINTF/实机。15.7MB复制成本尚不满足容量门槛，probe被真实TWRP builder拒绝；删除列表未改。

A30：新平台Rust loader七个描述项在user/4.14选18map/6program；GPU三个map/two program pins及0:1003权限已与原新work consumer literals核对。保留原新全局libbpf，继续其feature/BTF/flags审核。明确阻塞项：新`system/etc/bpf/cputimeinstate/timeInState.bpf`的`raw_tp/sched_process_free`在实际libbpf映射type17，固定S6内核只接受1–14；整对象失败会被非critical继续记录，不能据此通过。先抽取新`libtimeinstate.so`/BatteryStats的map与attach依赖、核对T860 sched_process_free tracepoint上下文，再从新donor源重建等价process-free逻辑和整个timeInState对象，保留PID清理/复用语义。不要禁用单program或复制旧对象/private15库。新Samsung legacy `.o`三个扫描目录/critical失败和ztd独立路径另审；详见BPF审计第13节。

A31：上述CPU ctx/attach配对已从原新两文件生成`B06-CPU-v2`候选，实机format固定pid offset24，原新退出清理主体不变；详见`bpf-cpu-ui85.json`及BPF报告第14节。两次重放、640完整cleanup模型、八错误输入拒绝、独立Linux ELF结构已通过，仍不可刷。执行顺序：固定原新global libbpf的feature探测/无kernel BTF分支与mapflags → 检查CPU/GPU/FUSE对象所需条件 → 完整构建树同时重放timeInState对象与libtimeinstate（root:root/0644及各原标签）→ 重测ext4容量、按原init参数重编策略并审查neverallow/VINTF → 实机verifier/perf附加、CPU统计/BatteryStats及PID复用。对象净增14,760B须计入镜像；不单装统计库、不因非critical继续把统计记为通过。独立v2 manifest/provenance固定于audit/bpf-cpu-ui85-*，UI9从新原件重新定位，不能复用当前offset/hash。

A32：原新global libbpf的局部BTF路径已核对：CPU候选/两GPU无CO-RE，普通对象在feature2不支持时跳过BTF上传，program BTF FD负数时不设置相关options；不新增笼统禁用BTF或旧库替换。CPU调度/调频九个ctx成员与实机相符，CPU候选另通过Linux bpftool用户态BTF解析。当前两个GPU事件与FUSE type节点缺失，原GpuWork attach false走普通return；这不证明其他map/init错误或Storage fallback安全。下一步具体入口：libbpf bpf_object__load的map creation/options/type/helper链 → libgpuwork/libmeminfo的map失败处理 → 新vold/MediaProvider对/sys/fs/fuse/bpf_prog_type_fuse、ro.fuse.bpf.*能力检测 → OEM .o/实际init策略编译及neverallow审查与全镜像 gates。BPF报告第15节及platform-btf-features/live-events证据固定这些条件，所有load/consumer运行门槛仍未过。

### A40 后的具体执行顺序

1. **继续保留真实SDK28诊断**：使用factory完整v3的54个JAR，不再用遗漏CAPEX的v2。13签名差异与vendor直接调用交集0已定位，独立验证完成；不声明全面支持28/删除vendor要求/复用旧Build true。真实VINTF仍未通过，warning日志留供诊断；便利dump/缺metadata的弃用检查不是正式门槛。
2. **完成剩余设备逻辑**：F03已按A41加入独立树：新`framework.jar`的SemDvfs接口配合原新`priv-app/SamsungDeviceHealthManagerService`，运行未测；接着F04 ET713/HBM相关新framework和SurfaceFlinger输出路径，F07 PRODUCT资源overlay的255/305/355及自动亮度。先固定原新文件、记录目的、唯一定位和拒绝不匹配输入，再生成patch/profile与独立scratch候选，不覆盖旧JAR/APK或扩大裁剪。
3. **补齐实际硬件接口闭包**：保留`vendor/lib{,64}/libjnihelper.so`、time/CACert/QMI库及`etc/init/init.time_daemon.rc`。用新`ld.config`/linkerconfig、VNDK30和新zygote加载路径核对两ABI DT_NEEDED；原JNI表签名存在只是静态前提。保留ABSTRACT time_genoff、vendor_time_daemon及qtidataservices域，以当前旧v0.48.1只读证据为对照，新候选记录JNI/HwBinder/AVC/时间日志。
4. **完整构建与可审查候选**：把每个已审计独立patch重放至新donor构建树，记录元数据/cache失效范围，测最终ext4 free、策略及VINTF真实输入，保留失败/未测状态。TWRP分块打包与反向核对可生成明确标注运行未测的诊断候选；不得标为稳定发布。平板只读授权不等于允许刷机/重启，真实安装应在具体包、摘要、操作范围就绪后取得对应授权。

A40全树与A39完全相同（8,246条），容量仍以A37最后精确镜像为历史值。本轮没有新image/ZIP，USB读到的是旧UI8，不能填入新ROM验证表。全证据见`audit/factory-sdk28-jni-evidence-ui85.json`。

## A50：增加实际首启前 property_contexts 合并门槛

在所有platform/system_ext/product设备patch加入后，与真实保留vendor/odm property_contexts一起解析精确/prefix所有权，重复项必须逐条解释；不能用单独CIL编译通过替代属性表序列化检查。新donor的wvkprov状态prefix冲突按 `property-contexts-stage-ui85.json` / `apply_property_contexts_stage_ui85.py` 定向去除，vendor类型保留。已重放E2新inventory84932b4b…，A45成品仍原样不改。下一完整候选须从这个新stage重新构建并走原文件系统/容量/内容与metadata回读门槛，不把小型诊断addon当完整ROM。r2实机进入Download，需要先取新last_kmsg判断失败层，暂不继续刷写。UI9重新定位是否仍有该冲突，不机械按行号删新文件。

## A52 实机反馈补充执行顺序

A50 属性重复修正 → A51 平台 contexts 原类型标签恢复 → A52 解释器启动适配。先用 `build_bpf_interpreter_probe_ui85.py` 从冻结 B06 loader/guard 输入构建，仅新 S9 loader 一条分支和 guard 表一项 SHA；再 `apply_bpf_interpreter_stage_ui85.py` 对 A51 全树 inventory 重放并证明两文件内容之外不变。实机以 `apply_live_bpf_interpreter_ui85.sh` 在 TWRP 限定硬件、旧文件、context 修正后写同两文件，持久回读后单次启动观察。

后续门槛：真实 loader 通过/map 与 pin 建立 → platform BPF 完成 → system_server/SystemUI → 基础硬件/网络；首次失败继续取日志，不提前移除后续失败检查。若是 BPF/helper/map 功能缺失，按真实代码及保留内核接口定位，不能仅改退出值。完整新 ROM 重建须使用 A52 后 inventory，并明确 A45 旧包不包含这些修正。

## A53 后续顺序

A52网络对象真实加载后，按实机121根因重放A53：`build_bpf_platform_map_abi_probe_ui85.py`绑定精确kernel Image/System.map与原S9库，生成单指令候选；`apply_bpf_platform_map_abi_stage_ui85.py`以A52 inventory逐文件验证，仅一库内容变，其他metadata/CIL/APEX不变。实机 `apply_live_bpf_platform_map_abi_ui85.sh` 验证A50/A51/A52已在位、硬件原样后定点写库并只读回读；再次观测全部Samsung critical对象及原最终加载成功链。

随后才定位新日志中的后续verifier/helper/pin/消费者问题；目前明确保留critical/失败检查，不删除对象。完整ROM从A53新inventory2c59e2b2…重建，A45原包仍是未含修正的失败基线。

## A54 增量执行顺序

1. 原S9/B06→A50属性冲突→A51标签→A52解释器→A53 map_name→A54 prog_name。
2. 运行 `scripts/build_bpf_platform_prog_abi_probe_ui85.py --out out/patch-probes/A54-platform-prog-abi-v1`（新目录）；输入A53新库，仅修正0x789c，真实syscall/错误传播保留。
3. Linux root运行 `scripts/apply_bpf_platform_prog_abi_stage_ui85.py`，绑定完整A53 inventory，目标E2中 `system/system/lib64/libbpf_android.so`；仅内容变化，保存stage-before/after及全树差异。
4. TWRP shell运行 `scripts/apply_live_bpf_platform_prog_abi_ui85.sh`，严格核对当前A50–53/BOOT/VENDOR，再写同一库/只读重挂回读。独立记录授权启动，取新日志验证是否实际加载程序和到达system_server/SystemUI。
5. 如出现验证器helper/类型/指令错误，分析新日志和对象调用关系；不能跳过critical或用旧库/对象覆盖。uprobestats单独追踪。全功能/保留DATA升级与VINTF仍待验证；原A45包不包含A50–54，待阻断排除后重建完整候选。

## A55 有序重放与新运行门槛

1. 保留S6原BOOT/VENDOR/ODM，完成A50–A54。A54全树pin89ecf423…。确认实际无metadata分区、CACHE sda27/419430400且新backing目录缺席、vendor/etc/aconfig缺席。
2. `build_aconfig_metadata_probe_ui85.py`从固定新init/rc/contexts/Rust原件生成四文件；原new coreAPK/JAR无变化。`probe_aconfig_storage_ui85.py`独立ARM64原native正常/失败传播验证，输出真正三容器maps/boot/flags并读取RANGING=1。
3. Linux root执行 `apply_aconfig_metadata_stage_ui85.py`，以完整A54 inventory核对输入、仅4内容变化；新stage inventory6bc4228733ea410e6b3be8536211ffece59555a8f404f234cc09373a94656c8a。原CIL/APEX及硬件不变，二十alias与canonical实际regex标签核对通过。
4. `apply_live_aconfig_metadata_ui85.sh`在TWRP固定硬件/空间/前置SHA/labels验证后定点写四文件；失败恢复原内容，不清DATA/CACHE、不改硬件、不自动重启。回读完成后观察一次授权首启，采集aconfig/init/权限注册/system_server/SystemUI/boot_completed证据。
5. 如新失败先取真实logcat/last_kmsg与调用链，继续最小硬件→Samsung功能回归。新metadata在CACHE，wipe cache将破坏其生命周期；发布前须验证并给恢复/更新协议，不能把实验桥声明为稳定方案。
6. 完整候选必须从通过记录的新stage重新构建，含A50–A55；原A45不可覆盖或宣称已修复。全VINTF/SDK28与dirty-upgrade/PIN/账号/所有硬件门槛继续保持未过，UI9重定位逻辑而非复用字节偏移。

## A68 当前工程与应用回归纳入顺序

1. 保留A66单字节软件光源能力与A61单条S6 vendor Codec2策略修复；其他硬件层不换。
2. `patches/build_wifi_telephony_rro_ui85.py` → 原S9 idmap2核验 → `scripts/apply_wifi_telephony_stage_ui85.py`。只有voice bool资源修改；未来UI9需重查vendor能力回退，不照搬services/framework二进制。
3. `scripts/prepare_official_clock_ui85.py` 从 `device/s6/prebuilts/clock/SamsungClock-12.5.00.46.apk` 验签/核验五库 → `scripts/apply_official_clock_stage_ui85.py` 全树只新增6文件/3目录。新的8094项inventory SHA5a5157766b0552d0d1c202c9be1fbeb9db49861f788169fdca02aaed3d53db91；旧A64 profile不能直接拿来构建此树。
4. `scripts/probe_official_clock_capacity_ui85.py` 按正式mke2fs -d配方复测精确SYSTEM/PRODUCT尺寸、完整metadata/hardlinks和原空闲门限。传统rsync容量失败记录保留；诊断image不作为刷机input。
5. 新完整candidate profile/policy report/installer须明确纳入A66/A68与唯一S6 vendor配置差异，并完成真实SYSTEM预装Clock/native/闹钟验证。禁止把旧A45 ZIP或A64旧镜像作为新修复成品。
6. Weather dirty upgrade若实际重现Not supported cp，先确认原签名/当前CP/profile，再执行明确授权的 `scripts/reset_weather_data_ui85.py` 仅包级数据重置，文字城市获取/冷启动复测。此用户已授权并通过；此脚本不能变成无条件安装器清数据。新安装使用原Weather实现，不增加永久地图全局禁用。
7. 当前实际生图仅水彩流程PASS；继续验证其他AI/Samsung功能，保留未知native警告记录，不把全部AI写成PASS。Mainline更新、完整VINTF、CACHE metadata、安全daemon及完整重刷/回滚尚未完成。

## A69：地区身份与摘要验证纳入顺序

1. 将真实XAR/US单项countryiso纳入设备层；同样新donor未来先核对已有值/CSC初始化，不把Android/OneUI软件版本改成旧值。prepare_csc_country_ui85.py生成仅追加属性，apply_csc_country_stage_ui85.py依完整inventory写入；源码/已有值不同必须重新审计。
2. current stage为8094条SHA60781b040f0c9507800a5114dff3c5c788ac2b0cd8409fdd8f30571a85f4b15a，checkpoint /var/tmp/ui85-a69-csc-country-stage-v1；仅SYSTEM build.prop增加96字节。A64旧builder/profile不能直接打包该树，需刷新新的全树/policy/容量记录和安装清单。
3. 实机英文及原中文PDF摘要已通过，作为独立功能条目纳入新候选的升级后测试；Notes/SIS/SCS保持官方更新签名/版本。其他Galaxy AI继续分项而非整体标PASS。
4. 国家属性为真实设备身份，保留到OneUI9；sales_code缺失与init/CSC依赖另审计，未加该第二变量。保持BOOT和唯一A61 vendor策略差异，后续仍完成Mainline/VINTF/CACHE/Knox及长期硬件验证再发布。


## A70：S6面板圆角遮罩重放

在A69 country修复之后，以`/var/tmp/ui85-a69-csc-country-stage-v1/stage-after.json`为完整基线，构建`device/s6/rounded-corners-overlay`，在原新idmap2中验证SystemUI bool/config_enableRoundedCorner、drawable/rounded_corner两项映射。用`apply_rounded_corners_stage_ui85.py`限定新增`system/system_ext/overlay/T860RoundedCornersOverlay.apk`。新树checkpoint为`/var/tmp/ui85-a70-rounded-stage-v1/stage-after.json`，不能让后续打包脚本继续认A68/A69为当前完整树。实际设备安装须限定Recovery事务与完整文件差异检查；重启后检查23px上下半径与四角provider、横竖屏/锁屏/应用触控，记录真实屏幕确认。UI9重新定位新资源/实现并重新编译映射。本轮不意味着已经重建或验证最终刷机ZIP。


A70运行补充：针对SystemUI目标的RRO还需`device/s6/rounded-corners-allowed-preload.xml`→`apply_rounded_corners_registration_stage_ui85.py`，独立新增SYSTEM_EXT/etc/sysconfig/t860-rounded-corners.xml注册该单包。最终8096项checkpoint `/var/tmp/ui85-a70-registration-stage-v1/stage-after.json` / e21e7efaaa1e1d06154cda4dc63ae31c1e6d5f887f9b8929c0535304607f6df7；后续完整构建采用此基线。注册后的四方向23px/四角provider实测通过，实体外观待确认。A71以新基线重编译政策与完整ext4并逐项回读通过，下一步集成完整TWRP安装器单vendor适配、源入口与Mainline预检、ZIP32打包、故障/只读预检，然后完整升级与回滚实机验证。自动更新已两次造成早期循环，不能把这一风险在整包测试中跳过。
## 2026-10-03 A72 下一执行顺序

1. Fabric错误契约的独立ART试验12项已通过，尚不合入。对S9原签名KmxService.apk/classes2.dex的E2eeServiceInternal.containsKey及E2eeService调用方解决错误6被105覆盖的路径，并核对其他7个调用类；保留明确失败，不改实际账户密钥。详细文件/摘要/工具见FABRIC_SECURITY_REBASE_A72.md。
2. 结合原厂34 VINTF XML/实际缺Fkeymaster日志设计system/etc/init/fabric_crypto.rc与对应framework manifest的S6硬件能力门控；JAR缺服务检查独立试验不等于native循环修复，不导入S9 vendor HAL。
3. 在错误传播及权限/签名方案明确后才将JAR补丁、精确编译缓存清单和init/manifest变更加入新stage/profile，验证Samsung Account/安全设置/AI隐私；保留冻结A71升级/恢复ZIP作为基线，不覆盖历史产物。
4. 未解决Mainline更新APEX netd兼容、真实v0.48.1初始DATA直接升级和独立恢复包实测；继续跟踪原UI8 DATA条件与剩余功能矩阵。新实验结果不能替代这些门槛。
## 2026-10-03 A72 实机VINTF与错误保留结果后的优先项

1. 新系统实机原vintf诊断已确认SDK28声明/4.14 kernel entry/FCM4缺口，不再只依赖隔离VM判断。基于已有官方/原厂FCM4完整规则及S6真实config落实独立fragment；对System SDK28的1类/13成员及native动态消费者完成新实现兼容依据，再决定支持声明。保留硬件需求和新Build检查。见VINTF_REBASE_AUDIT.md。
2. Kmx containsKey最小错误保留试验16项ART通过，但原Samsung APK/权限身份保持，未合入重签包。继续其余7调用类错误传播及Fabric生命周期，寻找可维护且保持签名/权限的适配位置；真实device HAL matrix方向已GOOD，不猜测删除Fkeymaster矩阵条目。
3. 仅在上述声明/逻辑/生命周期变更具备明确依据后创建新stage/profile/候选镜像和TWRP包；冻结A71产物保留独立，结合原生入口与回滚流程实机验证。
4. Mainline更新兼容、真实v0.48.1初始DATA直接升级、独立恢复包执行及剩余功能仍未完成，当前已升级数据不能冒充首次UI8升级条件。
## 2026-10-03 A73：FCM4候选已验证，接续SDK28

1. FCM4已进入独立S6源码/profile及VM COW stage8097项，仅加49,951B matrix.4.xml，冻结原stage8096项保持。真实设备单进程原vintf已确认kernel/config方向GOOD；仍是未安装候选，完整metadata检查未完成。重建方式与证据见VINTF_REBASE_AUDIT.md。
2. 继续SDK28原定义缺口13成员/1类：核对BluetoothHeadset.setPriority的原0/100语义与新setConnectionPolicy权限/调用；核对TokenBindingService现代废弃实现及原28抽象API/嵌套类；核对WebViewFactory旧内存常量与新行为。不复制旧framework/APEX或仅加28数字。已下载固定AOSP Android9/Android16-QPR2源作为下一分析输入，见out/audit-probes/A73-sdk28-official-sources-v1/source-index.json；尚未编写SDK28实现补丁。
3. 在SDK28接口/metadata与服务生命周期变更具备证据后，在新候选上完成正式矩阵/镜像/策略/容量校验并生成新的升级/恢复包；旧A71冻结产物保持独立，原TWRP验证流程复用。
4. Mainline未来更新、Fabric/Fkeymaster重复abort、真实v0.48.1初始DATA升级条件、独立恢复与其余功能仍待闭合；保持EXPERIMENTAL，不由FCM4这一方向通过标全ROM稳定。
# A74 当前执行点：已生成 format3 升级与配套恢复包

- 新SYSTEM/PRODUCT完整镜像已构建并全树回读通过；新适配只增加FCM4 XML以及安装时S6两文本配置，BOOT/HAL/固件/DATA保持。
- 完整vendor双表42项、原TWRP工具与完整S6 ext4两配置事务24项已通过。新升级/恢复都固定9 support及独立状态协议；A71冻结包保留。
- `TabS6-A74-S9-UI85-EXPERIMENTAL-UPGRADE-TWRP-v1.zip`：3,823,094,600B，SHA80953c8c…534b；`TabS6-A74-RESTORE-A70-STABLE-SYSTEM-PRODUCT-TWRP-v1.zip`：3,803,471,944B，SHA63857d56…fa3f。恢复target为精确稳定A70完整分区与SDK28+A61，不是原UI8用户数据快照。
- 升级包114块及9 support已经原TWRP工具全载荷检查通过；恢复包同范围检查正在运行。两者真实入口、实机Recovery源/回滚条件、实际刷入/启动/installed VINTF尚未完成。
- 下一步依次：保存恢复载荷终态；执行format3整入口的来源、模块、数据、写入/中断/恢复失败测试；实机Recovery只读预检及完整回滚身份确认；实际候选安装及installed VINTF/原硬件/数据与Samsung功能回归。单进程VINTF GOOD和载荷CRC不能替代上述证据。
- SDK30候选的直接vendor消费者154成员/79类型已核对；平台wide SDK30 stub仍有未用BluetoothHeadset.setPriority别名缺项，见A73接口报告，未将其称全SDK认证。完整正式VINTF/HIDL metadata、Fabric/Fkeymaster、Mainline更新、CACHE生命周期、真实初始v0.48.1 DATA升级及未验证硬件项继续保留。

### 2026-10-03 Mainline后续执行顺序更新

A76实际单文件Fabric生命周期适配已部署，原签名广告两模块372038020两次启动各五分钟保持；不是网络组完成。正常Google串行列车先广告/时区/统计，再primary；checkpoint unsupported对应同批多列车限流，不改StorageManager返回值或盲开DATA checkpoint。A77固定init候选只在原Tethering采集旁保存DNS372038020，不放开guard或复制旧二进制；随后审计真实新网络组的native/BPF/Java完整闭包，重定位长期4.14补丁，再验证实际模块保留和网络功能。详见MAINLINE_PAYLOAD_CAPTURE_A77.md。

### 2026-10-05 A96：核心相册编辑器保留规则纠正

实机恢复新S9 PhotoEditor_AIFull及68私有库，普通编辑入口/旋转/另存测试通过，裁剪策略改keep。后续新独立stage按photo-editor-ui85-a96.json、prepare_photo_editor_a96.py、apply_photo_editor_stage_a96.py执行（后者尚未实跑）。两可选人像库撤销“无保留者”删除依据，实机待容量和人像专项验证。正式镜像先恢复/核算全部闭包，再调整用户指定可删预装、重做256MiB SYSTEM门槛；当前live约100MiB不能充当发布证据。最后分别验证JPEG/PNG基础编辑、绘画、AI和人像，UI9重新pin新donor；A84冻结镜像不覆盖。

### 2026-10-05 A97：商店目录与donor型号的应用内适配

1. 先保留A96 S9原签名PhotoEditor闭包，再核对Store安装版本/完整APK SHA及DeviceInfoLoader。系统仍S6真实硬件身份。
2. 对当前Store4.6.11.4仅用其自有OBB saconfig.ini key12=SM-X710；不设置API key15、不改全局Build。受保护profile及probe/apply/restore在device/s6和scripts，A/B/A/B加空配置对照已完成。
3. 下载链已用三星计算器12.5.10.28实证Store下载+安装+启动+1+2=3，测试包已清理。实机配置保留，A84构建未集成。
4. 正式构建门槛：审查目标Store APK（工厂4.6.06.8尚不适用此pin）、内置配置副作用/诊断日志增长/Wearable；首次启动只在目标不存在且版本匹配时部署，拒绝循环覆盖用户配置。APK升级/清理后显式复核。
5. UI9重查parser/field/端点、SDK保持真实版本，验证目录与真实安装、S6硬件能力；不复制旧Store二进制或无限放宽hash。详见GALAXY_STORE_CATALOG_A97.md。

### 2026-10-06 A98：相册OCR与AI实机验证

1. 新独立stage先完成A96闭包恢复，保留S9 Gallery/SmartScan原件和S6硬件层。定位SYSTEM etc/floating_feature.xml的CAMERA_CONFIG_VENDOR_LIB_INFO，只移除smart_scan.samsung.v2；禁止整份旧XML覆盖新donor。
2. 当前已审计输入35256B/SHAa51ddc…，由prepare_gallery_scan_a98.py输出35234B/SHA81d9ea…；源不匹配必须先比较全部feature并建立新审计profile，不能放宽摘要后强行套用。Recovery事务已实跑、整SYSTEM内容/元数据/硬件分区独立回读和撤回预检通过。正式stage集成尚未执行，A84冻结保持。
3. 部署后用JPEG而非只有PNG复测右下角OCR，核对识别高亮/可选和无新native崩溃；普通相机服务连接回归，文档边缘/透视扫描明确降级。当前实验设备已通过上述范围。
4. 照片助手涂鸦和旋转补全必须取得真正runGenAI、云端响应及实际结果页。两者本轮通过，不再根据VisualCore枚举标签或初始化告警直接改安全/模型。其他AI模式未验证；若再失败保留完整请求前后日志再定位。
5. UI9重查Features gate/DocumentScanner模型格式与SM8150后端，不复用UI8.5库/地址或盲拷S9 DSP/vendor。详见GALLERY_OCR_AI_A98.md和qa-result.json。
