#!/usr/bin/env python3
"""make-bootbin.py — Zynq-7000 BOOT.BIN 打包器(按官方格式手写)

输入:
  1. 模板 BOOT.BIN(推荐:开发板厂商原厂 BOOT.BIN,要求其 FSBL 分区适用于你的板子)
  2. u-boot 平铺二进制(u-boot-dtb.bin,TEXT_BASE 需与分区头 dest_load/dest_exec 一致,默认 0x04000000)

输出:
  两分区 BOOT.BIN:p1=模板里的 FSBL(原封不动) p2=你的 u-boot

格式依据(全部实测+FSBL 源码核对,Xilinx embeddedsw image_mover.c):
  - 分区头 w15 校验和 = sum(w0..w14) XOR 0xFFFFFFFF   ← 是 XOR,不是减法!
  - 分区表结束标记 = 15 个 0x00000000 + 0xFFFFFFFF     ← 填全 FF 是错的!
  - FSBL 对 PS 分区数据是裸拷贝 → 必须给平铺二进制,不能是 ELF/块编码

用法:
  python3 make-bootbin.py --template vendor.BIN --uboot u-boot-dtb.bin --text-base 0x04000000 -o BOOT.BIN
"""
import argparse
import struct
import sys

P1_DATA_OFF = 0x1700          # FSBL 数据固定起始偏移(bootgen 约定)
P1_END = 0x19740              # 模板中 p2 数据起始(= p1 结尾 0x19708 向上对齐到 0x40 边界)
PART_HDR_BASE = 0xC80         # 分区头表起始
PART_HDR_SIZE = 0x40
IMG_HDR2 = 0x940              # 镜像头 #2(u-boot)
IHT_COUNT = 0x8C4             # 镜像头表 - 镜像计数


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True, help="厂商原厂 BOOT.BIN(提供 ROM 头+FSBL)")
    ap.add_argument("--uboot", required=True, help="u-boot-dtb.bin 平铺二进制")
    ap.add_argument("--text-base", default=0x04000000, type=lambda x: int(x, 0),
                    help="u-boot 链接地址(默认 0x04000000,须与 TEXT_BASE 一致)")
    ap.add_argument("-o", "--output", default="BOOT.BIN")
    args = ap.parse_args()

    tpl = open(args.template, "rb").read()
    ub = open(args.uboot, "rb").read()
    if len(tpl) < P1_END:
        sys.exit("模板太小,不是有效 BOOT.BIN")
    if tpl[0x20:0x24] != bytes.fromhex("665599aa"):
        sys.exit("模板缺少 Zynq 魔术字 0xAA995566 @0x20,不是 BOOT.BIN")

    out = bytearray(tpl[:P1_END])          # ROM头 + 镜像头 + 分区头区 + FSBL 数据,原封照抄
    l2 = (len(ub) + 3) & ~3                # p2 载荷 4 字节对齐
    out += ub + b"\x00" * (l2 - len(ub))

    # 1) 镜像头表: 镜像数 -> 2
    out[IHT_COUNT] = 2
    # 2) 镜像头 #2: next_img_off -> 0(成为最后一个)
    out[IMG_HDR2:IMG_HDR2 + 4] = struct.pack("<I", 0)
    # 3) 分区头 #2 重写(u-boot)
    w = [0] * 16
    w[0] = w[1] = w[2] = l2 // 4           # 三个长度字段(单位:32位字)
    w[3] = w[4] = args.text_base           # dest_load = dest_exec
    w[5] = P1_END // 4                     # data_off(单位:字)
    w[6] = 0x10                            # attributes: PS 分区
    w[7] = 1                               # section_count
    w[9] = 0x250                           # img_hdr_off(字)
    w[15] = (sum(w[:15]) & 0xFFFFFFFF) ^ 0xFFFFFFFF   # XOR 校验和!
    out[PART_HDR_BASE + PART_HDR_SIZE:PART_HDR_BASE + 2 * PART_HDR_SIZE] = struct.pack("<16I", *w)
    # 4) 分区表结束标记(p3 槽位): 15×0 + 0xFFFFFFFF
    end = struct.pack("<15I", *([0] * 15)) + struct.pack("<I", 0xFFFFFFFF)
    out[PART_HDR_BASE + 2 * PART_HDR_SIZE:PART_HDR_BASE + 3 * PART_HDR_SIZE] = end

    open(args.output, "wb").write(bytes(out))
    # 自验证
    v = struct.unpack("<16I", out[PART_HDR_BASE + PART_HDR_SIZE:PART_HDR_BASE + 2 * PART_HDR_SIZE])
    assert ((sum(v[:15]) & 0xFFFFFFFF) ^ 0xFFFFFFFF) == v[15], "校验和自检失败"
    e = struct.unpack("<16I", out[PART_HDR_BASE + 2 * PART_HDR_SIZE:PART_HDR_BASE + 3 * PART_HDR_SIZE])
    assert all(x == 0 for x in e[:15]) and e[15] == 0xFFFFFFFF, "结束标记自检失败"
    print(f"OK: {args.output} ({len(out)} 字节)  p2={l2}B @0x{P1_END:X}  base=0x{args.text_base:08X}")


if __name__ == "__main__":
    main()
