#!/usr/bin/env python3
"""简易串口助手: 与开发板 UART 交互
用法:
  uart.py probe          发送回车并监听 3 秒(看当前界面)
  uart.py send "文字"    发送一行并监听 5 秒(输入命令/登录)
  uart.py listen 秒数    只监听不发(抓启动 log / 长时间输出)
"""
import sys, time
import serial

PORT = "/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0"
BAUD = 115200

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "probe"
    import time as _t
    ser = None
    # listen 模式耐心等设备出现(用户插拔期间不退出); 其他模式最多等10秒
    _wait_start = _t.time() + (float(sys.argv[2]) if mode == "listen" and len(sys.argv) > 2 else 0) * 0.9
    _wait_start = max(_wait_start, _t.time() + 10)
    while _t.time() < _wait_start:
        try:
            ser = serial.Serial(PORT, BAUD, timeout=0.2)
            break
        except serial.SerialException:
            _t.sleep(0.3)
    if ser is None:
        print("ERROR: serial port not found"); sys.exit(1)

    if mode == "send":
        line = sys.argv[2] if len(sys.argv) > 2 else ""
        wait = float(sys.argv[3]) if len(sys.argv) > 3 else 5
        time.sleep(0.1)
        ser.write((line + "\r").encode())
        ser.flush()
        deadline = time.time() + wait
    elif mode == "listen":
        wait = float(sys.argv[2]) if len(sys.argv) > 2 else 10
        deadline = time.time() + wait
    else:  # probe
        ser.write(b"\r")
        ser.flush()
        deadline = time.time() + 3

    out = b""
    while time.time() < deadline:
        try:
            chunk = ser.read(4096)
            if chunk:
                out += chunk
        except (serial.SerialException, OSError):
            try: ser.close()
            except Exception: pass
            ser = None
            while ser is None and time.time() < deadline:
                try: ser = serial.Serial(PORT, BAUD, timeout=0.2)
                except serial.SerialException: time.sleep(0.2)
    if ser: ser.close()
    sys.stdout.write(out.decode(errors="replace"))
    sys.stdout.flush()

if __name__ == "__main__":
    main()
