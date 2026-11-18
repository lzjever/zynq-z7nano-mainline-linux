# Zynq Z7-Nano 主线 Linux 实战手册

> 一天之内,把一块 2018 年出厂的 Zynq-7020 开发板,换成 2026 年的主线 U-Boot + Linux 6.18 + Debian 13——
> 从零到全自主启动,踩过的每一个坑都变成了教材。

[**📖 打开手册网站(site/index.html)**](site/index.html)

## 这是什么

一套**新手可跟做**的完整实战记录:硬件验收 → 启动链理论 → 交叉构建 → 制卡 → 首次启动 → 深夜 JTAG 排雷 → 成功。不是"环境教程"的搬运,而是一次真实移植的全部决策链、失败现场与修复过程。

**适用硬件**:微相科技 Z7-Nano R20(Xilinx Zynq XC7Z020)——方法论适用于所有 Zynq-7000 板卡(设备树差异按板调整即可)。

## 仓库结构

```
site/       手册网站(纯静态 HTML,零依赖,GitHub Pages 直接可托管)
code/       全部实战代码(逐字节验证过)
  ├─ make-bootbin.py        Zynq BOOT.BIN 打包器(按官方格式手写,含格式注释)
  ├─ make-sd.sh             SD 制卡脚本(带安全检查)
  ├─ uart.py                串口工具(自动重连/耐心等待,踩坑淬炼版)
  ├─ openocd-z7nano.cfg     JTAG 调试配置(板载 FT232H)
  ├─ zynq-z7-nano-*.dts     设备树(内核版 / U-Boot 版)
  └─ extlinux.conf 等        启动与网络配置
build/      文档构建素材(权威素材库 DIGEST.md + 页面模板)
```

## 快速开始(三行核心)

```bash
# 1. 打包启动镜像(输入:厂商原厂 BOOT.BIN 模板 + 你编译的 u-boot-dtb.bin)
python3 code/make-bootbin.py --template 厂商.BIN --uboot u-boot-dtb.bin -o BOOT.BIN
# 2. 制卡
sudo code/make-sd.sh /dev/sdX BOOT.BIN
# 3. 插卡上电,30 秒后:z7nano login:
```

完整构建流程(U-Boot/内核/Debian rootfs)见手册第 3-5 章。

## 战果速览

| 指标 | 数值 |
|---|---|
| 上电 → 登录提示 | ~30 秒(全自主,无需 JTAG) |
| 内核 | 主线 Linux 6.18(multi_v7) |
| 用户态 | Debian 13 (trixie) armhf |
| 网络 | 千兆 RTL8211F(end0),ssh 直连 |
| 踩坑记录 | 17 条,全部收入第 7 章 |
| Vivado 依赖 | **零**(纯 PS 移植;PL 开发才需要) |

## 许可

- 文档与网站:**CC BY 4.0**
- 代码:**MIT**

## 致谢

感谢每一位在深夜串口前不肯说"算了"的工程师。
