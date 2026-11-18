#!/bin/bash
# Z7-Nano 主线 Linux 制卡脚本
# 用法: sudo ./make-sd.sh /dev/sdX [BOOT.BIN路径]
# 分区布局: p1=512MB FAT32(引导) p2=剩余 ext4(Debian rootfs)
set -e
trap "sudo umount /mnt/sd1 /mnt/sd2 2>/dev/null" EXIT

DISK=$1
BOOTBIN=$2
SD_DIR=/home/percy/zynq-mainline/sd
ROOTFS=/home/percy/zynq-mainline/rootfs

# ---- 安全检查 ----
[ -b "$DISK" ] || { echo "错误: $DISK 不是块设备"; exit 1; }
echo "$DISK" | grep -q "nvme" && { echo "错误: 拒绝操作 NVMe 设备!"; exit 1; }
RM=$(lsblk -no RM "$DISK" | head -1 | tr -d ' ')
[ "$RM" = "1" ] || { echo "错误: $DISK 不是可移动设备(以防误伤系统盘)"; exit 1; }
echo ">>> 目标: $DISK ($(lsblk -no SIZE,MODEL "$DISK" | head -1)),5 秒后开始,Ctrl-C 取消"
sleep 5

# ---- 分区 ----
sudo sfdisk --wipe always "$DISK" <<EOF
label: dos
start=8192, size=1048576, type=c
start=1056768, type=83
EOF
sudo partprobe "$DISK" || true
sleep 1
P1="${DISK}1"; P2="${DISK}2"

# ---- 格式化 ----
sudo mkfs.vfat -F 32 -n ZNANOBOOT "$P1"
sudo mkfs.ext4 -q -L rootfs "$P2"

# ---- 拷贝 ----
sudo mkdir -p /mnt/sd1 /mnt/sd2
sudo mount "$P1" /mnt/sd1 && sudo mount "$P2" /mnt/sd2
sudo cp -r $SD_DIR/boot/. /mnt/sd1/
if [ -n "$BOOTBIN" ]; then
    sudo cp "$BOOTBIN" /mnt/sd1/BOOT.BIN && echo "BOOT.BIN 已装入"
else
    echo "警告: 未提供 BOOT.BIN(第二参数),此卡无法启动!"
fi
sudo cp -a $ROOTFS/. /mnt/sd2/
sudo rm -f /mnt/sd2/usr/bin/qemu-arm-static

# ---- 收尾 ----
sync
sudo umount /mnt/sd1 /mnt/sd2
echo "=== 制卡完成 ==="
