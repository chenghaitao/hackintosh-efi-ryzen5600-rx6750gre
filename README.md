# macOS 26 Tahoe Hackintosh EFI · Ryzen 5 5600 + RX 6750 GRE

一份**已在真机跑通**的 OpenCore EFI 备份。重点在于两件通常要自己动手的事：

1. **AMD RX 6750 GRE（Navi 22, `1002:73DF`）没有原生驱动** —— 这份 EFI 带的是**自行编译**的 [NootRX](https://github.com/ChefKissInc/NootRX)，并修掉了上游手工编译时必然踩的 `kmod_info` 缺失问题；
2. **Intel AX210 在 macOS 26 上官方 AirportItlwm 已不适用** —— 换成了 Tahoe 专用的社区构建，恢复原生 Wi-Fi 菜单，不再需要 HeliPort。

> ⚠️ 仓库里的 `config.plist` **三码已脱敏**（`SystemSerialNumber` / `MLB` / `SystemUUID` / `ROM` 全是占位符）。直接拿去用之前必须自己生成一套，见 [使用前必做](#使用前必做改三码)。

---

## 硬件配置

| 组件 | 型号 | 识别 / 说明 |
|---|---|---|
| CPU | AMD Ryzen 5 5600 | 6 核 12 线程，Zen 3，需 `SSDT-PLUG` + `revpatch=cpuname` |
| 主板 | AMD B450 平台 | 400 系列芯片组（PCI `1022:43C7`） |
| 内存 | 32 GB = 16 GB × 2 | DDR4-3600，`JHD3600U1816JG` |
| 显卡 | **AMD Radeon RX 6750 GRE 12 GB** | **Navi 22**，`1002:73DF`，靠 NootRX 驱动 |
| 有线网卡 | Realtek RTL8111 | → `en0`，`RealtekRTL8111.kext` |
| 无线网卡 | **Intel Wi-Fi 6E AX210** | `8086:2725` → `en1`，`AirportItlwm.kext` |
| 蓝牙 | AX210 内置（USB 总线） | `IntelBluetoothFirmware` + `IntelBTPatcher` + `BlueToolFixup` |
| 存储 | 500 GB macOS APFS 卷 / 500 GB NTFS / 2 TB 数据盘 | NVMe + SATA 混装，`NVMeFix` 已启用 |
| 显示器 | ASUS VG279 | 1920×1080，DP 输出 |
| 音频 | **仅 DP/HDMI 音频** | 未装 AppleALC → 板载声卡不工作 |
| SMBIOS | **MacPro7,1** | `board-id = Mac-27AD2F918AE68F61` |

## 软件环境

| 项 | 值 |
|---|---|
| macOS | 26.7.2（Build `25G332`，Darwin 25） |
| 引导 | OpenCore（本 EFI 内未标注版本号，建议用 OpenCore Configurator 校对后再升级） |
| 引导驱动 | `apfs_aligned.efi`、`HfsPlus.efi`、`OpenRuntime.efi`、`ResetNvramEntry.efi` |
| ACPI | `SSDT-EC`、`SSDT-PLUG`、`SSDT-USB-Reset`、`SSDT-USBX` |
| boot-args | `keepsyms=1 -ibtcompatbeta revpatch=sbvmm` |
| csr-active-config | `0x03`（SIP 部分关闭：允许非签名 kext + 文件系统无限制；**NVRAM 保护仍开启**） |
| SecureBootModel | `Disabled`（必须，否则非签名 kext 无法注入） |

### Kext 清单

| Kext | 版本 | 作用 | 状态 |
|---|---|---|---|
| `Lilu` | 1.7.3 | 补丁框架，其余 kext 的前置 | ✅ |
| `VirtualSMC` | 1.3.9 | SMC 模拟 | ✅ |
| `NootRX` | 1.0.0 | **Navi 22 图形加速（自行编译）** | ✅ |
| `AirportItlwm` | 2.4.0 | **Intel 无线原生 Wi-Fi（Tahoe 构建）** | ✅ |
| `itlwm` | 2.3.0 | Intel 无线（以太网模式，需 HeliPort） | ⛔ 已禁用 |
| `IntelBluetoothFirmware` | 2.5.0 | Intel 蓝牙固件 | ✅ |
| `IntelBTPatcher` | 2.5.0 | Intel 蓝牙补丁 | ✅ |
| `BlueToolFixup` | 2.7.3 | macOS 12+ 蓝牙修复 | ✅ |
| `RealtekRTL8111` | 2.4.2 | 有线网卡 | ✅ |
| `NVMeFix` | 1.1.4 | NVMe 电源管理 | ✅ |
| `RestrictEvents` | 1.1.7 | 屏蔽 CPU 型号警告 / 内存提示 | ✅ |
| `AppleMCEReporterDisabler` | 1.2 | 关掉 AMD 平台上无用的 MCE 上报 | ✅ |
| `USBToolBox` + `UTBDefault` | 1.2.0 / 1.0 | USB 端口映射 | ✅ |

> `itlwm` 与 `AirportItlwm` **绝不可同时加载**，这里保留前者只是为了回退方便，`Kernel > Add` 中已设为 `Enabled=false`。

---

## 三个最关键的技术点

### 1. NootRX 是自己编译的，并补了 `kmod_info`

Apple 从未出货 Navi 22 机型，macOS 里只有 Navi 10/21/23 的支持。不装 NootRX 时显卡会挂在 `AMDSupport` 的通用帧缓冲上，表现为 **显存 7 MB、没有 Metal、能亮屏但卡顿**。

NootRX 仓库没有任何 release / tag，所以这份 kext 是从 `master` 手工构建的，并踩到并修复了一个坑：

> 手工用 `clang -Wl,-kext` 链接时，**链接器不会自动生成 `kmod_info` 结构**（Xcode 的 Kernel Extension target 才会）。缺了它，OpenCore 注入是成功的，但内核**不会注册这个 kext**，`kextstat` 里根本看不到它 —— 现象和"没装"一模一样。只有 `_kmod_start` 别名是不够的。

修复办法：显式定义 `kmod_info_t`（`name` / `version` 是 `uint8_t[]`，必须逐字符初始化，不能塞字符串字面量；`start` / `stop` 在 64 位头里是函数指针，不能 cast 成 `uint64_t`）。

验证结果：

```
kmutil showloaded | grep NootRX
  → org.ChefKiss.NootRX (1.0.0)   ✓

system_profiler SPDisplaysDataType
  → AMD Radeon RX 6750 GRE / VRAM 12 GB / Device ID 0x73df / Metal 3   ✓
```

### 2. NootRX 与 WhateverGreen 互斥

两者都 hook 图形驱动栈，**同时加载会黑屏或失去加速**。本 EFI **没有** WhateverGreen，`boot-args` 里也**没有** `agdpmod=pikera`（那是 WEG 的参数，没有 WEG 时无意义）。

### 3. AirportItlwm 用的是 Tahoe 专用社区构建

| 候选 | 结论 |
|---|---|
| 官方 OpenIntelWireless 的 AirportItlwm | 只到 Sonoma 14.4，Tahoe 不可用 |
| `kgp-macPro/AirportItlwm-Tahoe` | 需配合 OCLP 的 legacy 无线环境 + root patch，侵入性大 |
| **`laobamac/itlwm` v2.4.0-alpha 的 Tahoe 构建** ← 本仓库 | 只依赖 `IO80211Family` + `IOSkywalkFamily`（系统自带），无需 root patch |

配套改动：`Kernel > Quirks > DisableIoMapper = true`（AMD 平台没有 AppleVTD，走常规 DMA 路径）。

副作用说明：这个 alpha 驱动对 CoreWLAN 的状态桥接不完整，`system_profiler` 可能显示 `Status: Network Service Inactive`、`networksetup -getairportnetwork` 报 `not associated`，**但链路是通的**。判断有没有连上要看实测：

```bash
ping -c3 -b en1 192.168.1.1          # 网关
curl -s -o /dev/null -w '%{http_code}\n' --interface <en1 的 IP> https://www.apple.com
```

> 顺便一个坑：`curl --interface en1`（绑设备名）会瞬间返回 000，必须绑**源 IP** 才正常。

---

## 已知限制（诚实版）

| 限制 | 说明 | 能不能修 |
|---|---|---|
| **无硬件视频编解码** | `ioreg` 里没有 `AppleGVA`/`VDA` 节点，`kmutil` 里没有 `X6000VCN`。NootRX 只打通图形/计算通路，媒体引擎不参与 | 换 Navi 21/23 原生机型 |
| **无板载声卡** | 未装 AppleALC，当前只有 DP/HDMI 音频 | 加 `AppleALC` + 对应 `layout-id` 可解 |
| 睡眠唤醒未验证 | NootRX 常见雷区：唤醒后花屏/掉加速 | 试 `hibernatemode=0`（当前值），出问题用 `-NRXDebug` 抓日志 |
| 多屏热插拔未验证 | — | — |
| Alpha 驱动 | AirportItlwm 是社区 alpha 构建，作者本人标注"硬件验证前别日常用" | 出问题回退 `itlwm` + HeliPort |
| `sudo nvram` 写不进 | `csr-active-config=0x03` 缺 `0x08`，SIP 的 NVRAM 保护是开的 | 要改 boot-args 只能改 `config.plist` 或临时把 csr 调到 `0x0B` |

---

## 使用前必做：改三码

仓库里的三码是占位符：

```xml
<key>SystemSerialNumber</key><string>XXXXXXXXXXXX</string>
<key>MLB</key>               <string>XXXXXXXXXXXXXXXXX</string>
<key>SystemUUID</key>        <string>00000000-0000-0000-0000-000000000000</string>
<key>ROM</key>               <data>AAAAAAAA</data>   <!-- 6 个零字节，需替换 -->
```

步骤：

1. 用 [GenSMBIOS](https://github.com/corpnewt/GenSMBIOS) 生成 **MacPro7,1** 的 `Serial` / `MLB` / `SystemUUID`；
2. 打开 `OC/config.plist` → `PlatformInfo > Generic`，把三项填进去；
3. `ROM` 填**你自己的有线网卡 MAC**（`en0` 的 `xx:xx:xx:xx:xx:xx` 转成 6 字节 data）——这关系到 iMessage / App Store 是否正常；
4. 想恢复默认就反着来：把三码换回占位符（仓库带了个小工具）：

```bash
python3 tools/sanitize_smbios.py OC/config.plist
```

## 安装到 EFI 分区

```bash
# 1. 挂载 ESP（需要管理员权限）
sudo diskutil mount disk1s1

# 2. 备份原有 EFI
sudo cp -R /Volumes/EFI/EFI /Volumes/EFI/EFI.backup-$(date +%Y%m%d)

# 3. 覆盖，但保留 EFI/APPLE（固件更新用，删了会影响系统更新）
sudo ditto BOOT /Volumes/EFI/EFI/BOOT
sudo ditto OC   /Volumes/EFI/EFI/OC
```

> `bless --setBoot` 对 OpenCore 无效（返回 `0xe00002e2`），这是预期行为。这份 EFI 已设 `Misc > Boot > LauncherOption = Full`：从目标盘引导一次后，OpenCore 会把自己写成固件启动项。

## 目录结构

```
EFI/
├── BOOT/
│   └── BOOTx64.efi                 # 兜底引导，删了就起不来
└── OC/
    ├── ACPI/                       # SSDT-EC / PLUG / USB-Reset / USBX
    ├── Drivers/                    # apfs_aligned / HfsPlus / OpenRuntime / ResetNvramEntry
    ├── Kexts/                      # 见上表
    ├── Resources/                  # 引导界面资源（3.6 MB）
    ├── OpenCore.efi
    └── config.plist                # 三码已脱敏
```

`EFI/APPLE`（固件更新文件）**未包含**在本仓库 —— 那是 Apple 的二进制，且与本配置无关，安装时请保留目标分区里原有的那一份。

---

## 出处与致谢

| 项目 | 作者 | 用途 |
|---|---|---|
| [OpenCore](https://github.com/acidanthera/OpenCorePkg)、[Lilu](https://github.com/acidanthera/Lilu)、[VirtualSMC](https://github.com/acidanthera/VirtualSMC)、[RestrictEvents](https://github.com/acidanthera/RestrictEvents)、[NVMeFix](https://github.com/acidanthera/NVMeFix)、[BlueToolFixup](https://github.com/acidanthera/BrcmPatchRAM) | Acidanthera | 引导与基础 kext |
| [NootRX](https://github.com/ChefKissInc/NootRX) | ChefKissInc | Navi 22 图形加速（本仓库为自行构建版） |
| [itlwm](https://github.com/OpenIntelWireless/itlwm) / [laobamac 的 Tahoe 分支](https://github.com/laobamac/itlwm) | OpenIntelWireless、laobamac | Intel 无线 |
| [RealtekRTL8111](https://github.com/Mieze/RTL8111_driver_for_OS_X) | Mieze | 有线网卡 |
| [USBToolBox](https://github.com/USBToolBox/kext) | dhinakg 等 | USB 端口映射 |

## 免责声明

- 只在上述**唯一一套硬件**上验证过，其他平台请当作参考而不是保证；
- 黑苹果不适合承载不可丢失的数据或生产业务，装之前请准备好可引导的救援盘；
- 仓库里的 kext 二进制各自遵循其原始许可证，`config.plist`、文档与脚本部分采用 MIT。
