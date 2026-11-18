#!/usr/bin/env python3
# 双审校修复补丁 — 断言式替换,漏网单独报告
import sys
BASE = "/home/percy/works/zynq-z7nano-mainline-linux/site/"

EDITS = [
# ---------- INDEX ----------
("index.html",
 '<tr><td>软件</td><td>python3 + pyserial</td><td>串口助手 uart.py 的依赖(apt 装 python3-serial 即可)</td></tr>',
 '<tr><td>软件</td><td>python3 + pyserial + xxd(第 02 章解剖实验用,vim-common 包)</td><td>串口助手 uart.py 的依赖与工具(apt 装 python3-serial 即可)</td></tr>\n    <tr><td>本手册仓库</td><td><code>git clone https://github.com/lzjever/zynq-z7nano-mainline-linux</code></td><td>uart.py / make-bootbin.py / make-sd.sh 等全部配套代码在仓库 <code>code/</code> 下;全书命令默认在仓库根目录执行</td></tr>'),
("index.html",
 '<td>虚拟机也行,但 USB 串口要配置透传;磁盘留足源码树与 rootfs 的空间</td>',
 '<td>虚拟机也行,但 USB 串口要配置透传;磁盘建议 ≥40GB,时间预算:内核编译(24 核)约 15 分钟、debootstrap 二阶段半小时上下</td>'),
("index.html",
 '<li>所有路径默认相对于仓库根目录,涉及绝对路径的命令会在注释里说明。</li>',
 '<li>所有路径默认相对于<strong>本手册仓库根目录</strong>(准备清单里 git clone 的目标),涉及绝对路径的命令会在注释里说明。</li>'),
# ---------- CH1 ----------
("ch1-board.html",
 '用仓库里的串口助手(支持自动重连,专为踩坑设计):</p>',
 '用本手册仓库自带的串口助手(支持自动重连,专为踩坑设计;还没克隆仓库的话,回到封面准备清单先 <code>git clone</code> 并 <code>cd</code> 进仓库根目录):</p>'),
("ch1-board.html",
 '<p>跳线确认在 SD 档、出厂 SD 卡插好、监听开着,上电。',
 '<p>跳线确认在 SD 档(跳线是板上丝印 BOOT/SW1 的多位拨码开关,档位含义以板面丝印为准,拿不准就对照厂商《开箱测试》文档)、出厂 SD 卡插好、监听开着,上电。'),
("ch1-board.html", 'enp129s0f0', 'enp129s0'),
("ch1-board.html",
 '(内核可见约 479MB)',
 '(内核可见约 479MB——为何不足 512?内核保留区吃掉了零头,第 04 章 4.5 有交代)'),
# ---------- CH2 ----------
("ch2-bootchain.html",
 '按 BOOT.BIN 格式解析头部(所以它只认这个裸格式,不认识文件系统);</li>',
 '按 BOOT.BIN 格式解析头部。它对文件系统的认知极有限:SD 启动时只会在<strong>第一个 FAT 分区的根目录</strong>里找名为 boot.bin 的文件(只读、大小写不敏感)——这正是引导文件"名字固定、位置固定"的根本原因;</li>'),
("ch2-bootchain.html",
 '紧随    p2 数据 = 下一分区平铺二进制(p1 结尾按 0x78 对齐;\n        例:0x1700 + 98312 = 0x196C8 → 对齐到 0x19740,p2 数据从 0x19740 起)',
 '紧随    p2 数据 = 下一分区平铺二进制(p1 结尾向上对齐到 0x40 边界;\n        例:0x1700 + 98312(=0x18008)= 0x19708 → 对齐到 0x19740,补 0x38 字节;p2 从 0x19740 起)'),
("ch2-bootchain.html",
 '装载地址;常见 0x04000000(也有 0x00400000 的写法),关键是与 U-Boot 的 TEXT_BASE 一致',
 '装载地址;关键是与 U-Boot 的链接地址(TEXT_BASE)严格一致——本手册主线版是 0x04000000,厂商 2018.3 老版是 0x00400000,两者差 16 倍,是不同地址而非写法差异'),
("ch2-bootchain.html",
 '在 SD 卡上它只是 FAT 分区里的一个普通文件,大小很宽松;',
 '在 SD 卡上它是 FAT 分区根目录里文件名固定的一个普通文件(BOOT.BIN),大小很宽松;'),
("ch2-bootchain.html", '第 7 章踩坑 11', '第 7 章坑 12(原 #11)'),
("ch2-bootchain.html", '解剖四步', '解剖六步'),
("ch2-bootchain.html", '上面四步同源', '上面六步同源'),
("ch2-bootchain.html",
 '<strong>第五步(可选):找结束标记。</strong>对我们自制的两分区 BOOT.BIN,',
 '<strong>第五步(可选,留到第 5 章做出自制 BOOT.BIN 后再回来做):找结束标记。</strong>对自制的两分区 BOOT.BIN,'),
("ch2-bootchain.html",
 '<tr><td>0x78</td><td>p1 结尾到 p2 起始的补齐规则(实测 0x196C8 → 0x19740)</td><td>布局实测</td></tr>',
 '<tr><td>0x40</td><td>p1 结尾向上对齐的边界(实测 0x19708 → 0x19740,补 0x38 字节)</td><td>布局实测</td></tr>'),
# ---------- CH3 ----------
("ch3-toolchain.html", 'boot-mkbootimage.bif', 'failed-bootgen-mkbootimage.bif'),
("ch3-toolchain.html",
 'P1_END        = 0x19740  <span class="c"># 模板中 p2 数据起始(= p1 结尾按 0x78 对齐)</span>',
 'P1_END        = 0x19740  <span class="c"># 模板中 p2 数据起始(= p1 结尾 0x19708 向上对齐到 0x40 边界)</span>'),
("ch3-toolchain.html",
 '<td>解厂商资料包(取出 FSBL ELF、hdf)</td><td>第 1 章</td>',
 '<td>解厂商资料包(取出 FSBL ELF、hdf)</td><td>第 4/5 章</td>'),
("ch3-toolchain.html",
 'systemd-networkd 网络配置(DHCP)',
 'systemd-networkd 网络配置(静态 IP,可自行改 DHCP)'),
("ch3-toolchain.html",
 '下面那个 hello 冒烟测试,顺带就把 binfmt 的注册情况也验了。</p>',
 '下面那个 hello 冒烟测试,顺带就把 binfmt 的注册情况也验了。小提醒:hello.c 记得 <code>#include &lt;stdio.h&gt;</code>,否则编译器的 implicit-declaration 警告会吓你一跳。</p>'),
# ---------- CH4 ----------
("ch4-build.html",
 '其一,这个 <code>reg = &lt;1&gt;</code> 是我们从厂商运行时设备树里抄来的——如果手头没有参照,先写 <code>0</code> 更稳妥',
 '其一,这个 <code>reg = &lt;1&gt;</code> 当初是拍脑袋猜的——后来上电,内核日志里的 <code>PHY [...:01]</code> 证实恰好命中。不想猜的话,先写 <code>0</code> 或干脆不写 phy 节点更稳妥'),
("ch4-build.html",
 '<span class="c"># 应看到且只有一个目录: 6.18.0(忘了版本号可用 make ARCH=arm kernelrelease 查)</span>',
 '<span class="c"># 应看到且只有一个目录——版本号取决于你克隆内核的时点,与手册的 6.18.0 不同是正常的!</span>\n<span class="c"># 后续命令统一用变量代替版本号,现在导出它(在内核树顶层执行):</span>\n<span class="k">KVER</span>=$(make ARCH=arm kernelrelease)'),
("ch4-build.html",
 'sudo cp -a $HOME/zynq-mainline/build/modules/lib/modules/6.18.0 rootfs/lib/modules/\nsudo rm -f rootfs/lib/modules/6.18.0/build rootfs/lib/modules/6.18.0/source',
 'sudo cp -a $HOME/zynq-mainline/build/modules/lib/modules/$KVER rootfs/lib/modules/\nsudo rm -f rootfs/lib/modules/$KVER/build rootfs/lib/modules/$KVER/source'),
("ch4-build.html",
 '模块安装的两个坑(第 7 章详录)',
 '模块安装的两个坑(defconfig 的坑在第 7 章坑 6 有详录;modules 竞态重跑一遍即愈)'),
("ch4-build.html",
 '<p>实测 multi_v7_defconfig 下这八项全部为 y,一张表安心。</p>',
 '<p>实测 multi_v7_defconfig 下这八项全部为 y,一张表安心。若你看到某项是 <code>=m</code>(编成模块)也不算错——只要对应的 .ko 确实进了 rootfs 模块目录。</p>'),
("ch4-build.html",
 '<p>四个文件的内容逐一给出:</p>',
 '<div class="box box-step"><div class="box-title">步骤 · rootfs/ 里的文件归 root 所有</div><p>普通编辑器直接创建会遇到 Permission denied,统一用 heredoc 写入(以 sources.list 为例,其余三个同理):</p>\n<pre><code>sudo tee rootfs/etc/apt/sources.list &lt;&lt;\'EOF\'\ndeb https://mirrors.tuna.tsinghua.edu.cn/debian trixie main contrib non-free-firmware\nEOF</code></pre></div>\n  <p>四个文件的内容逐一给出:</p>'),
# ---------- CH5 ----------
("ch5-sdcard.html",
 '<p>还记得第 2 章的 BOOT.BIN 布局吗?',
 '<div class="box box-step"><div class="box-title">步骤 · 先备齐厂商物料</div><p>打包器需要一件输入:<strong>厂商原厂 BOOT.BIN</strong>(当模板)。两个来源任选其一:</p>\n<ol><li><strong>出厂 SD 卡</strong>:插到读卡器,拷出来,顺手做个全卡备份更保险:\n<pre><code>mkdir -p ~/zynq-mainline/vendor\ncp /media/$USER/*/BOOT.BIN ~/zynq-mainline/vendor/   <span class="c"># 挂载路径以实际为准</span>\n<span class="c"># 可选的保险:整卡镜像备份(约 10 分钟)</span>\n<span class="c"># sudo dd if=/dev/sdX of=~/factory-sd.img bs=4M status=progress</span></code></pre></li>\n<li><strong>厂商资料包</strong>(向板卡厂商/客服索取;本项目为 Z7-NanoR20-7020-2018.3 系列):其 demo 压缩包里还有现成的 zynq_fsbl.elf 与 hdf(第 6、8 章要用),一并解到 vendor/ 备用:\n<pre><code>7z e 厂商资料包.7z -o~/zynq-mainline/vendor "*zynq_fsbl.elf" "*.hdf"</code></pre></li></ol></div>\n  <p>还记得第 2 章的 BOOT.BIN 布局吗?'),
("ch5-sdcard.html",
 '因为启动链里每一级(BootROM、U-Boot)都认 FAT,而且',
 '因为启动链里每一级都认 FAT——BootROM 内置的是"只够找到 BOOT.BIN 一个文件"的极简只读 FAT(所以文件名、所在分区和目录都是约定死的),U-Boot 则是完整 FAT 驱动,而且'),
("ch5-sdcard.html",
 '<div class="node"><b>BootROM + FSBL</b>:按扇区裸读 p1 开头的 BOOT.BIN——它们不认识任何文件系统</div>',
 '<div class="node"><b>BootROM + FSBL</b>:在第一 FAT 分区根目录定位 BOOT.BIN 文件,按第 02 章的 BOOT.BIN 格式解析加载</div>'),
("ch5-sdcard.html",
 '拿厂商出厂 SD 卡里的 BOOT.BIN 当前 0x19740 字节的模板',
 '拿厂商出厂 SD 卡里的 BOOT.BIN,截取前 0x19740 字节充当模板'),
("ch5-sdcard.html",
 '(FAT 还大小写敏感):</p>',
 '(boot.bin 大小写不敏感,但文件名与所在目录一个字母都不能错):</p>'),
("ch5-sdcard.html",
 '其中 /lib/modules/6.18.0/ 是模块树',
 '其中 /lib/modules/$KVER/ 是模块树(版本号以你为准,见第 4 章)'),
("ch5-sdcard.html",
 '# 期望:Linux z7nano 6.18.0 … armv7l GNU/Linux',
 '# 期望:Linux z7nano &lt;你的版本号,手册示例 6.18.0&gt; … armv7l GNU/Linux'),
("ch5-sdcard.html",
 'ls /lib/modules/$(uname -r)\n<span class="c"># 应看到 6.18.0 目录;modules_install 时已在里面生成好模块依赖索引</span>',
 'ls /lib/modules/\n<span class="c"># 应看到你的内核版本目录(手册示例 6.18.0);依赖索引已生成</span>'),
("ch5-sdcard.html",
 'python3 code/uart.py listen;用别的工具也行',
 'python3 code/uart.py listen 120;用别的工具也行'),
("ch5-sdcard.html",
 'Host z7\n    HostName 192.168.1.10',
 'Host z7\n    HostName 192.168.1.10\n    User root'),
# ---------- CH6 ----------
("ch6-debug.html",
 '  -c <span class="s">"targets zynq.cpu0"</span> \\  <span class="c"># 关键!见 6.4 坑一</span>',
 '  <span class="c"># 关键!见 6.4 坑一(续行符后不能有任何字符,注释须独立成行)</span>\n  -c <span class="s">"targets zynq.cpu0"</span> \\'),
("ch6-debug.html",
 '<p>两种方式命令完全相同,下文统一按命令串联写。</p>',
 '<p>两种方式命令完全相同,下文统一按命令串联写——即都包在 <code>openocd -f cfg -c "..." -c "..."</code> 的 -c 参数里;若用 telnet 交互,去掉 -c 包装直接输入即可。</p>'),
("ch6-debug.html", '第 7 章坑 #10', '第 7 章坑 11(原 #10)'),
("ch6-debug.html", '第 7 章坑 #9', '第 7 章坑 10(原 #9)'),
("ch6-debug.html", '(坑 #10)', '(坑 11,原 #10)'),
("ch6-debug.html", 'XOR 而非求和,坑 #11', 'XOR 而非求和,坑 12(原 #11)'),
("ch6-debug.html", '(坑 #12 / #17)', '(坑 3 / 坑 4,原 #12 / #17)'),
("ch6-debug.html",
 'arm-linux-gnueabihf-nm</span> fsbl.elf | sort | awk <span class="s">\'$1&lt;="00005364"\'</span> | tail -1',
 'arm-linux-gnueabihf-nm</span> fsbl.elf | sort | awk <span class="s">\'$1&lt;="00005364"\'</span> | tail -1\n<span class="c"># 注:gnueabihf-nm 读裸机 ELF 也没问题(nm 只看符号表不介意 ABI);</span>\n<span class="c"># 真要"编译"裸机代码(第 8 章响亮 FSBL)时才需要 arm-none-eabi 工具链</span>'),
("ch6-debug.html",
 '<span class="k">load_image</span> /tmp/fsbl.bin 0x0 bin',
 '<span class="c"># /tmp/fsbl.bin 来源:厂商 zynq_fsbl.elf 转平铺二进制</span>\n<span class="c"># arm-linux-gnueabihf-objcopy -O binary zynq_fsbl.elf /tmp/fsbl.bin</span>\n<span class="k">load_image</span> /tmp/fsbl.bin 0x0 bin'),
# ---------- CH8 ----------
("ch8-roadmap.html", '做完第 06 章练习的你和不做的你', '把第 6 章灌注救援亲手做过一遍的你和没做过的你'),
("ch8-roadmap.html", '目录下的 10 个文件', '目录下的 9 个文件'),
("ch8-roadmap.html", 'code/ 十件套全部实战验证过', 'code/ 九件套全部实战验证过'),
("ch8-roadmap.html", 'L24-27 布局常量', 'L23-28 布局常量'),
("ch8-roadmap.html", '<td>Linux</td><td>主线 6.18</td>', '<td>Linux</td><td>主线(手册时点为 6.18)</td>'),
("ch8-roadmap.html",
 'end0 配 IP(或插进有 DHCP 的网络)',
 'end0 配静态 IP(配置文件已内置;若插进有 DHCP 服务器的网络则会自动获取)'),
]

ok, fail = 0, []
for fname, old, new in EDITS:
    p = BASE + fname
    try:
        src = open(p).read()
        if old not in src:
            fail.append((fname, old[:60])); continue
        n = src.count(old)
        open(p, "w").write(src.replace(old, new))
        ok += 1
        if n > 1: print(f"  注意: {fname} 中替换了 {n} 处: {old[:40]}...")
    except Exception as e:
        fail.append((fname, str(e)))
print(f"\n完成 {ok}/{len(EDITS)} 处")
if fail:
    print("以下未命中,需手工处理:")
    for f, o in fail: print(f"  [{f}] {o}")
