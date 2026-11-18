# Z7-Nano 主线 Linux 移植 — 权威素材库(DIGEST)

> 本文档由亲历者从完整工作 session 中萃取,是本仓库所有文档的**唯一事实来源**。
> 时间:2026-11-18,一天之内完成:开箱 → 制卡 → 开箱测试 → 工具链 → 内核/U-Boot/Debian 构建 → 制卡启动 → 深夜 JTAG 排雷 → 全自主启动成功。
> 硬件:微相科技(MicroPhase) Z7-Nano R20,Xilinx Zynq XC7Z020-2CLG400,DDR3 512MB。
> 工作机:Ubuntu 24.04.5,24 核,62GB 内存。

---

## 第 0 章 板卡与硬件档案

- SoC: Zynq XC7Z020(双核 Cortex-A9 @ ~766MHz-1GHz + Artix-7 级 FPGA 逻辑)
- DDR3: 512MB @ 0x0(内核可见 ~479MB)
- 串口: 板上唯一启用的串口是 **UART0 @ 0xE0000000,经 CH340E 接 type-C "UART" 口**,115200 8N1
  - 重要:ps7_init 里 **UART1 时钟未开启**(UART1_CPU_1XCLKACT=0),硬件上不存在第二个可用串口
- JTAG: 板载 FT232H(USB VID:PID 0403:6014)接 type-C "JTAG" 口,OpenOCD 可直接驱动
- 双 RJ45: **PS ETH**(Zynq GEM @ 0xE000B000 + Realtek RTL8211F PHY,RGMII-ID,PHY 挂 MDIO 地址 1,PHY 复位脚 MIO46)/ PL ETH(需 FPGA 逻辑,当前系统不可用)
- 启动: 跳线选 SD/QSPI/JTAG;BOOT_MODE 寄存器 @ 0xF800025C 读回 5 = SD
- 供电: UART 和 JTAG 两个 type-C 口的 VBUS 经 OR 二极管汇到主 5V,**任一口可独立供电**(实测单 UART 口供电可完整跑 Linux)
- 踩坑: 网线第一次插到 PL ETH 口,电脑侧有链路而板子 eth0 无载波——"单边有链路"是插错口的典型特征

## 第 1 章 出厂系统与开箱测试(PetaLinux 2018.3)

- 出厂 SD:FAT32 根目录 BOOT.BIN(10.6MB,三分区:FSBL+u-boot+image.ub)+ image.ub
- 串口登录 root/root;主机名 petalinux-boot-from-sd
- 测试流程: 配 IP `ifconfig eth0 192.168.1.10 netmask 255.255.255.0 up` → 电脑配同网段 → 双向 ping
- 电脑侧(Ubuntu): `nmcli con add type ethernet ifname enp129s0 con-name fpga-board ipv4.method manual ipv4.addresses 192.168.1.20/24`
- 老系统的 dropbear 只支持 ssh-rsa:Ubuntu 24.04 的 OpenSSH 需在 ~/.ssh/config 加:
  ```
  Host fpga
      HostName 192.168.1.10
      HostKeyAlgorithms +ssh-rsa
      PubkeyAcceptedAlgorithms +ssh-rsa
  ```
- 板上 XADC(iio:device0,设备名 xadc)读温度/电压:`(raw+offset)*scale/1000`;实测结温 55°C 空闲,各电源轨正常
- 教训: 串口工具要在**上电前**开始监听;拔插 type-C 会让 /dev/ttyUSB 消失,工具必须能自动重连

## 第 2 章 Zynq 启动链理论(本项目最核心的知识)

```
上电 → BootROM(芯片固化代码)
     → FSBL(First-Stage Boot Loader,~100-400KB,跑在 OCM)
     → U-Boot(跑在 DDR)
     → Linux 内核 → 用户态(rootfs)
```

- **BootROM**:从启动介质读取 BOOT.BIN 格式镜像,把第一个分区(FSBL)搬进 OCM,然后跳转。它**不初始化 DDR**。SD 启动时经极简只读 FAT 在第一个 FAT 分区根目录查找 BOOT.BIN(文件名大小写不敏感)。失败时进入错误循环(JTAG 实测 PC 停在 0xFFFFFF34)
- **FSBL**:灵魂是执行 ps7_init——用几千条寄存器写操作初始化 DDR 时序/时钟树/MIO 引脚复用,这些参数**每块板不同**,来自 Vivado 硬件工程(藏在 hdf 里)。之后从 BOOT.BIN 读后续分区,搬进 DDR,跳到 dest_exec
  - FSBL 是开源的:github.com/Xilinx/embeddedsw,`lib/sw_apps/zynq_fsbl/`(我们用 xilinx-v2018.3 tag)
  - 厂商给的是哑巴版(debug 打印被编译关闭),所以串口全程静默——**"串口没输出"≠"没在跑"**
  - Zynq-7000 的主线 U-Boot SPL 不能替代 FSBL(不携带 DDR 参数);MPSoC 时代才改用 PMUFW+TF-A
- **U-Boot**:通用搬运工,负责从文件系统(FAT/ext4)加载内核。主线 U-Boot 用 distro boot:自动扫描启动介质上的 `/extlinux/extlinux.conf` 或 `/boot.scr`,这是"换内核不用重编 U-Boot"的关键机制
- **跳线必须在 SD 档**:JTAG 档会让 BootROM 空等,症状就是全静默

## 第 3 章 BOOT.BIN 二进制格式(血泪考古成果)

**布局(全部实测确认)**:
```
0x0000  ROM 头(0x8C0 字节):魔术字 0xAA995566 @0x20、FSBL 长度、各种指针
0x08C0  镜像头表(32B):版本、镜像计数 @0x8C4、分区头表偏移(字)、镜像头偏移(字)
0x0900  镜像头 ×N(每 0x40 字节):next 链、分区头偏移、名字(如 "zynq_fsbl.elf")
0x0C80  分区头 ×N(每 0x40 字节)
0x1700  p1 数据 = FSBL 的平铺二进制(注意:不是 ELF!是 objcopy 出来的 flat bin)
紧随    p2 数据 = 下一分区平铺二进制(p1 结尾 0x1700+98312=0x19708,向上对齐到 0x40 边界→0x19740,补 0x38)
```

**分区头 16 个 32 位字(小端)**:
| 字 | 字段 | 常见值 |
|---|---|---|
| w0/w1/w2 | pd_len/ed_len/total_len(字数) | 载荷字节数/4 |
| w3 | dest_load | 装载地址(p2 u-boot 例:0x00400000 或 0x04000000) |
| w4 | dest_exec | 跳转地址(通常=dest_load) |
| w5 | data_off | 数据偏移(字节/4) |
| w6 | attributes | PS 可执行分区=0x10 |
| w7 | section_count | 1 |
| w9 | img_hdr_off | 所属镜像头偏移(字) |
| w15 | **校验和** | **sum(w0..w14) XOR 0xFFFFFFFF(注意:是异或,不是 0xFFFFFFFF-sum!)** |

**分区表结束标记**(FSBL 靠它数分区!):紧跟最后一个真分区头之后的槽位 = **15 个 0x00000000 + 末字 0xFFFFFFFF**。填全 0xFF 是错的,FSBL 会数错分区数、把垃圾当分区加载、掉进 FsblHookFallback 死循环。

**FSBL 对 PS 分区数据是裸拷贝**(image_mover.c: `MoveImage(src, load, ImageWordLen<<2)`):
- ✅ 正确格式:平铺二进制(u-boot-dtb.bin)
- ❌ 错误格式:mkbootimage 的"ELF 节区块编码"(0x040CDA41 这种地址表)、完整 ELF 文件

**FSBL 加载与交接流程**(image_mover.c 源码路径):
1. `GetPartitionCount()`:从 0xC80 起扫描分区头槽位,直到遇到结束标记
2. `PartitionNum=1` 起循环(跳过 p1=FSBL 自己)
3. `ValidateHeader()`:非空 + **XOR 校验和** + ImageWordLen ≤ 0x40000000
4. 裸拷贝到 dest_load
5. 跳 dest_exec;失败则 `FsblFallback()`(0x5364 处 `b 5364` 自旋)

## 第 4 章 为什么最终自写打包器(mkbootimage 之坑)

- Antmicro zynq-mkbootimage(github.com/antmicro/zynq-mkbootimage)输出被 **BootROM 拒收**(PC 停在 ROM 错误循环 0xFFFFFF34)——原因未逐一定位,但它对 ELF 分区做节区块编码,本身就与 FSBL 的裸拷贝语义不符
- 教训:工具生成的镜像要**逐字节对照已知好样本**(厂商 BOOT.BIN)+ **解剖器验证**(exbootimage -d)+ **真机 JTAG 验收**,三者缺一不可
- 最终方案:Python 手写打包器 `code/make-bootbin.py`——以厂商 BOOT.BIN 前 0x19740 字节为模板(ROM 头+镜像头+FSBL 分区原封不动),替换 p2 为我们的 u-boot 平铺二进制,重写 p2 分区头(字数/地址/XOR 校验和),写入结束标记

## 第 5 章 构建三件套(全部在 Ubuntu 24.04 完成,无需 Vivado)

### 5.1 交叉工具链与依赖(apt 一步到位)
```
sudo apt install gcc-arm-linux-gnueabihf device-tree-compiler bison flex bc \
  libssl-dev libgnutls28-dev swig python3-dev libncurses-dev u-boot-tools \
  debootstrap qemu-user-static libelf-dev p7zip-full openocd python3-serial
```
说明:Ubuntu 24.04 的 GCC 13.3 完全够用;交叉编译对编译器版本要求宽松。

### 5.2 U-Boot(主线)
```
git clone --depth 1 https://github.com/u-boot/u-boot.git
# 设备树:arch/arm/dts/zynq-z7-nano.dts(仿 zynq-zed.dts,console=uart0,512MB,PHY@MDIO1+复位MIO46)
# Makefile 注册后:
make O=../build/uboot CROSS_COMPILE=arm-linux-gnueabihf- xilinx_zynq_virt_defconfig
make O=../build/uboot CROSS_COMPILE=arm-linux-gnueabihf- DEVICE_TREE=zynq-z7-nano -j24
# 产物:u-boot-dtb.bin(平铺,给 BOOT.BIN 当 p2)+ u-boot(ELF,给 JTAG 调试用)
```
关键点:2026 年的 U-Boot 已无 zynq_zed_defconfig 单板配置,统一走 `xilinx_zynq_virt_defconfig + DEVICE_TREE=` 覆盖。验证嵌入设备树:`strings u-boot.dtb | grep 型号`。
BOOTCOMMAND="run distro_bootcmd" 默认开启,BOOTDELAY=2。

### 5.3 内核(主线 6.18)
```
# 内核树同样加 zynq-z7-nano.dts(和 U-Boot 版同源,内核树在 arch/arm/boot/dts/xilinx/)
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- multi_v7_defconfig   # 6.12 后无单板 defconfig!
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j24 zImage dtbs modules
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- INSTALL_MOD_PATH=... modules_install
# 验证 .config:ARCH_ZYNQ / SERIAL_XILINX_PS_UART(_CONSOLE) / MACB / REALTEK_PHY / USB_CHIPIDEA / EXT4_FS / CGROUPS 全为 y
```
产物:zImage(11.7MB)、zynq-z7-nano.dtb、899 个 .ko(~120MB)。
踩坑:modules_install 偶发 cp 报错(竞态),重跑即好;模块目录必须是 /lib/modules/<版本>/ 不是 /lib/modules/ 直接装。

### 5.4 Debian 13 rootfs
```
sudo debootstrap --arch=armhf --foreign trixie rootfs https://mirrors.tuna.tsinghua.edu.cn/debian
sudo cp /usr/bin/qemu-arm-static rootfs/usr/bin/
sudo chroot rootfs /debootstrap/debootstrap --second-stage
```
配置(从宿主机直接写文件):sources.list(tuna, trixie main contrib non-free-firmware)、hostname=z7nano、fstab(mmcblk0p2=/, p1=/boot)、systemd-networkd(静态 IP,可改 DHCP)。
进 chroot(qemu 模拟):装 openssh-server/nano/sudo,`echo root:root | chpasswd`,PermitRootLogin yes,enable ssh+networkd。
内核模块拷入 rootfs/lib/modules/6.18.0/(删掉 build/source 软链)。删除 qemu-arm-static。

## 第 6 章 设备树移植要点(zynq-z7-nano.dts)

以主线 zynq-zybo-z7.dts 为模板,改四处:
1. `aliases.serial0 = &uart0`(板子控制台在 uart0,不是 zybo 的 uart1)
2. `memory@0 reg = <0x0 0x20000000>`(512MB)
3. gem0 下 `ethernet-phy@1 { reg = <1>; reset-gpios = <&gpio0 46 GPIO_ACTIVE_LOW>; }`(RTL8211F 在 MDIO 地址 1——不确定时可先写 0,macb 驱动会全总线扫描;PHY 型号可不写,内核按芯片 ID 自动识别)
4. usb_phy0 用 `usb-nop-xceiv` + `dr_mode = "host"`(板上是 USB3320 ULPI)

知识:Zynq-7000 **没有 pinctrl 子系统**——MIO 复用由 FSBL 的 ps7_init 完成,设备树只描述设备不管引脚。
知识:新内核(6.x)给设备起"可预测名"——我们的网口叫 **end0**(en=ethernet, d=device-tree 节点序号)而不是 eth0。想用传统名:内核命令行加 `net.ifnames=0`。systemd-networkd 的 Match 建议同时写两个名字。

## 第 7 章 SD 卡布局与启动文件

```
p1: 512MB FAT32(起始扇区 8192,type=0x0C)  → BOOT.BIN / zImage / zynq-z7-nano.dtb / extlinux/extlinux.conf
p2: 其余 ext4 → Debian rootfs
```
extlinux.conf:
```
label Debian trixie (mainline 6.18) — Z7-Nano
    kernel /zImage
    fdt /zynq-z7-nano.dtb
    append root=/dev/mmcblk0p2 rootwait rw console=ttyPS0,115200 earlycon=cdns,mmio,0xE0000000
```
制卡脚本 `code/make-sd.sh`:安全检查(拒绝 NVMe、要求 RM=1 可移动)、sfdisk 分区、双格式化、拷贝、FAT 分区不能用 `cp -a`(FAT 无属主概念,set -e 会中止)。

## 第 8 章 JTAG 调试方法论(OpenOCD,无需任何 Xilinx 工具)

适配器:板载 FT232H。配置(code/openocd-z7nano.cfg):
```
source [find interface/ftdi/um232h.cfg]   # VID:PID 0403:6014,AD0=TCK AD1=TDI AD2=TDO AD3=TMS
adapter speed 2000
transport select jtag
source [find target/zynq_7000.cfg]
```
核心操作:
```
openocd -f cfg -c "init" -c "targets zynq.cpu0" -c "halt" -c "reg pc" -c "resume" -c "shutdown"
```
三大必知:
1. **默认目标是 cpu1,必须显式 `targets zynq.cpu0`**——FSBL 第一条代码就问"我是几号核",非 0 号核直接进 EndlessLoop0 看戏
2. **OCM 被 BootROM 重映射到 0x0**:JTAG 灌 FSBL 用地址 0x0,不是 0xFFFC0000(后者数据中止)
3. 读内存 `mdw`,如 BOOT_MODE@0xF800025C(=5 即 SD 档)、FSBL 全局变量 PartitionCount@0x1AC38

诊断速查表(PC 值 → 结论):
| PC | 含义 |
|---|---|
| 0xFFFFFFxx(两核都在) | 卡在 BootROM:启动失败/镜像被拒 |
| 0x5364(FSBL 内,自旋 b 5364) | FsblHookFallback:FSBL 加载/交接失败 |
| 0x04000000-0x040FFFFF | 我们的 U-Boot 在跑(TEXT_BASE=0x04000000) |
| 0x1FFxxxxx(DDR 顶端) | U-Boot 已完成 relocation,活着 |
| 0xC0xxxxxx | **Linux 内核虚拟地址,内核在跑!** |

配合反汇编定位函数:`arm-linux-gnueabihf-nm fsbl.elf | sort | awk '$1<="PC值"' | tail -1`,再 objdump -d 看指令。

JTAG 还能直接灌注绕过损坏环节(经典救援):
```
# DDR 未初始化时:先灌 FSBL 跑(ps7_init 会初始化 DDR),再灌 u-boot
load_image /tmp/fsbl.bin 0x0 bin; resume 0x0; sleep 3000; halt
load_image u-boot-dtb.bin 0x4000000 bin; resume 0x4000000
```

## 第 9 章 踩坑全记录(按时间线,每条都是真金)

1. 串口全静默 + 跳线不在 SD 档 → BootROM 找不到启动介质。第一反应查跳线
2. 网口插到 PL ETH:电脑侧有链路、板子 eth0 无载波(NO-CARRIER)→ 换口
3. "串口静默"贯穿全晚的三大真凶:跳线错(ROM 空等)/厂商 FSBL 哑巴(debug 关)/我们自己镜像坏(FSBL fallback)——同一个症状至少三种病因,必须用 JTAG PC 分层定位
4. dropbear 老版本:只认 ssh-rsa,新 OpenSSH 默认禁;ed25519 用户密钥它也不认(RSA 密钥 +ssh-rsa 强制才通;公钥认证还有 PAM 相关坑未解,密码方式可用)
5. 内核 defconfig 合并:6.12+ 无 zynq_defconfig,用 multi_v7_defconfig
6. 设备树 p2 里 PHY MDIO 地址是猜的:写 1 猜对了;更稳的方案是让驱动总线扫描
7. 网卡叫 end0 不叫 eth0:`ip link show eth0` → "does not exist";dmesg 里 "renamed from eth0" 是铁证
8. networkd restart 会清掉手动 ip addr add 的地址(DHCP 无服务器时板子失联)——改配置前先想清楚地址由谁管
9. mkbootimage 输出被 BootROM 拒收;即使过了 ROM,其 ELF 节区编码也不被 FSBL 的裸拷贝接受
10. 分区表结束标记填 0xFF 是错的(要 15×0+0xFFFFFFFF);FSBL 因此数出 3 个分区,把垃圾当 p3 加载
11. 分区头校验和是 XOR 不是 0xFFFFFFFF-sum(两者对厂商样本恰好同值,差 1 被忽略——**验证别人的公式时选好样本,两种算法要能区分**)
12. 拔插 type-C → /dev/ttyUSB 消失 → 串口工具崩溃;监听工具必须自动重连 + 上电前启动
13. FAT 分区上 cp -a 报"无法保留所有权"且 set -e 中断 → 用 cp -r
14. sfdisk 第二分区不写 start 会得到 3MB 怪分区;sudo 下 ~ 展开成 /root → 脚本一律绝对路径
15. lsblk -no RM 输出带前导空格," = 1" 比较失败 → tr -d ' '
16. 板上无 RTC 且实验网无外网 → 系统时间错(uptime 显示 19:40 实际 23:xx),不影响功能
17. UART type-C 线接触不良:CH340 会"干净地"从 USB 总线消失(dmesg 无芯片错误),换线/重插可救;备一根好线

## 第 10 章 Vivado 的定位:哪些环节真的需要它

| 环节 | 需要 Vivado? | 开源替代 |
|---|---|---|
| 编译 U-Boot/内核/Debian | ❌ | apt 交叉工具链 |
| BOOT.BIN 打包 | ❌ | 自写 make-bootbin.py(本仓库)/antmicro mkbootimage(慎用) |
| FSBL | ⚠️ 生成需要(xsdk/xsct),但**可直接复用厂商现成 zynq_fsbl.elf**;想改(如开调试打印)可用 embeddedsw 源码 + arm-none-eabi 手工编译 | embeddedsw 源码 |
| PL 侧 FPGA 开发(逻辑篇/HDMI 等) | ✅ 必须(免费 Standard 版即可,含 XC7Z020) | 无完整替代(Yosys/nextpnr 不支持 Zynq 7000 SoC 流程) |
| JTAG 调试 | ❌ | OpenOCD(本仓库配置) |
| ps7_init/硬件描述(.hdf) | 生成需要;厂商 BSP 里通常有现成的 | 厂商 hdf |

结论:纯 PS 侧移植 Linux **可以 100% 不装 Vivado**;要开垦 PL(学 FPGA 逻辑)才需要。免费版 Vivado ML Standard 完整支持 XC7Z020,安装时只勾 Vivado+Zynq-7000 器件族可控制在 ~15GB 下载。

## 第 11 章 最终可复现流程(收官状态)

1. apt 装工具链(第 5.1 节)
2. 编 U-Boot(5.2)+ 内核(5.3)+ Debian(5.4)
3. `python3 code/make-bootbin.py` 生成 BOOT.BIN(输入:厂商 BOOT.BIN 模板 + u-boot-dtb.bin)
4. `sudo code/make-sd.sh /dev/sdX BOOT.BIN` 制卡
5. 插卡、跳线 SD、上电 → 静默约 3 秒(FSBL)→ U-Boot 横幅 → extlinux → 内核 → z7nano login:
6. 登录 root/root;end0 配 IP(或插到有 DHCP 的网络);ssh root@192.168.1.10

实测成绩:上电到登录提示 ~30 秒;ssh 延迟 ~1.1ms;空闲结温 ~55°C。

## 第 12 章 后续路线图(未做/可做)

1. **响亮 FSBL**:embeddedsw 2018.3 源码 + hdf 里的 ps7_init.c,开 FSBL_DEBUG_INFO 重编——启动过程从此"开口说话",所有静默故障无处遁形
2. MAC 钉死:systemd .link 文件给 end0 固定 MACAddress
3. QSPI 启动:两棵设备树加 QSPI 分区表 + U-Boot QSPI bootcmd(注意 QSPI 容量只够放启动链,rootfs 仍走 SD)
4. JTAG 启动模式:天然支持,Vivado hw manager/xsct 可随时救援
5. PL 开垦:等 Vivado 装完,走厂商教程 Part1 逻辑篇;此后可把 PL 比特流打进 BOOT.BIN 第三分区,上电自动配置 FPGA
6. PYNQ 镜像尝鲜(厂商 demo 包里有现成的)

## 附录 A 本仓库 code/ 目录清单(全部实战验证过)

- `uart.py` — 串口工具(probe/send/listen;自动重连、耐心等待设备;by-id 稳定路径)
- `make-bootbin.py` — BOOT.BIN 打包器(v2,正确版:XOR 校验和 + 结束标记)
- `make-sd.sh` — 制卡脚本(安全检查 + 分区 + 格式化 + 拷贝)
- `zynq-z7-nano.dts`(内核版)与 u-boot 设备树(同源小改)
- `openocd-z7nano.cfg` — JTAG 配置
- `extlinux.conf`、`10-eth.network`、`failed-bootgen-mkbootimage.bif`(失败案例存档)等

## 附录 B 关键文件在原工作机的位置(供追溯)

- 工作区 ~/zynq-mainline/{src,build,rootfs,sd,vendor,tools,scripts}
- 厂商资料 ~/works/fpga-study/Z7-NanoR20-7020-2018.3/(01_开箱检测/7020开箱测试images 有出厂 BOOT.BIN/image.ub;04_demo 的 7z 里有 zynq_fsbl.elf/hdf/ps7_init.tcl)
- FSBL 源码 ~/zynq-mainline/tools/embeddedsw(xilinx-v2018.3)
