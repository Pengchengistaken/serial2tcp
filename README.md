# Serial2TCP Bridge

Bridge a local serial port on Windows (e.g. COM7) to a TCP server. Remote machines (e.g. Linux) can connect to this TCP service and, with tools like **socat**, expose it as a virtual serial device (e.g. `/dev/ttyV0`), so Linux can read from and send commands to the Windows serial device over the network.

## Architecture

- **Windows**: This project runs a small Python program that opens the physical COM port with [pyserial](https://github.com/pyserial/pyserial) and starts a TCP server. Data is forwarded bidirectionally between the COM port and a single TCP client.
- **Linux**: Use **socat** to connect to the Windows TCP server and create a PTY linked to `/dev/ttyV0`. Any program that opens `/dev/ttyV0` (e.g. minicom, screen, or your own app) will talk to the Windows serial port over TCP.

## Windows: Install and Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

Or:

```bash
pip install pyserial
```

### 2. Run the bridge

Default: COM7, 115200 baud, TCP server on `0.0.0.0:5000`.

```bash
python -m serial2tcp
```

Custom port, baud rate, and TCP listen address/port:

```bash
python -m serial2tcp --port COM7 --baud 460800 --listen 0.0.0.0 --tcp-port 5000
```

- `--port`: Serial port name (e.g. COM7).
- `--baud`: Baud rate (default 115200).
- `--listen`: TCP listen address (default 0.0.0.0).
- `--tcp-port`: TCP listen port (default 5000).
- `-v` / `--verbose`: Log connection events and errors (for debugging).

Only one TCP client is served at a time. New connections while one is active are rejected. Stop the bridge with Ctrl+C; the COM port and TCP server are closed on exit.

## Linux: Expose TCP as `/dev/ttyV0` with socat

Install socat if needed (e.g. `sudo apt install socat`). Create a PTY linked to `/dev/ttyV0` that connects to the Windows TCP server.

**推荐（不用 waitslave）** — 启动后立即连 TCP，虚拟串口会马上出现。

需要建在 `/dev/` 时要用 sudo；**不想用 sudo** 时把 link 建到可写目录即可（例如 `/tmp` 或家目录）：

```bash
# 建在 /dev（需 sudo，且部分系统 /dev 下建 link 会失败）
sudo socat pty,link=/dev/ttyV0,raw tcp:192.168.141.228:15000

# 建在 /tmp 或家目录（不需 sudo）
socat pty,link=/tmp/ttyV0,raw tcp:192.168.141.228:15000
# 或
socat pty,link=$HOME/ttyV0,raw tcp:192.168.141.228:15000
```
使用虚拟串口时用对应路径，例如：`minicom -D /tmp/ttyV0` 或 `minicom -D ~/ttyV0`。

**重要**：这个命令必须**一直运行**（不要在该终端按 Ctrl+C）。socat 一退出就会删除 `/dev/ttyV0`。正确用法是：
- **终端 1**：运行上面的 `socat`，保持不动；
- **终端 2**（或另一 SSH 会话）：执行 `ls -la /dev/ttyV0`、或用 minicom/screen 打开 `/dev/ttyV0` 使用。

若希望 socat 在后台跑，可用 `nohup` 或放到 tmux/screen 里，避免被 SIGHUP 杀掉：
```bash
nohup sudo socat pty,link=/dev/ttyV0,raw tcp:192.168.141.228:15000 </dev/null >>/tmp/socat.log 2>&1 &
# 然后另开终端使用 /dev/ttyV0
```

**若 socat 一连接就退出（"socket is at EOF" / "exiting with status 0"）**：  
桥接**只接受一个 TCP 客户端**。若已有别的 socat 或程序连在桥接上，新连上来的会被拒绝并关掉连接，socat 会立刻收到 EOF 然后退出。解决：先停掉所有旧的 socat，再只起一个。在 Linux 上：
```bash
pkill -f "socat.*ttyV0"
# 或按需：kill <PID>
```
确认没有残留：`ps aux | grep socat`。然后再启动新的 socat。

**若终端 2 仍看不到 `/dev/ttyV0`**：  
1）先在终端 2 确认 socat 是否还在跑：`ps aux | grep socat`。若没有 socat 进程，说明终端 1 里 socat 已退出，link 已被删。  
2）若 socat 在跑但 `/dev/ttyV0` 仍不存在，可能是本机 `/dev` 不允许在此创建 symlink（例如 devtmpfs 或只读）。可改用**可写目录**的 link，例如：
```bash
# 终端 1：把 link 建到 /tmp
sudo socat pty,link=/tmp/ttyV0,raw tcp:192.168.141.228:15000
```
终端 2 使用 `/tmp/ttyV0`：`minicom -D /tmp/ttyV0` 或 `screen /tmp/ttyV0 460800`。  
或建到当前目录：`sudo socat pty,link=./ttyV0,raw tcp:192.168.141.228:15000`，再用 `./ttyV0`。

若使用 `waitslave`，部分环境下 socat 会等“有人打开 slave”才去连 TCP，而 slave 就是 `/dev/ttyV0`，若此时 link 尚未创建就会出现“没有 /dev/ttyV0”的死锁，因此**建议本场景不要加 waitslave**。

### If `/dev/ttyV0` does not appear

1. **Start the Windows bridge first.** On Windows, run the bridge and make it listen on the same port (e.g. 15000):
   ```bash
   python -m serial2tcp --tcp-port 15000
   ```
   If socat connects to TCP before the bridge is listening, the connection fails, socat exits, and the PTY link is removed when socat exits — so you never see `/dev/ttyV0`.

2. **Use the command without `waitslave` (recommended).** With `waitslave`, some socat builds only create the link or establish TCP after the slave is opened — but the slave is `/dev/ttyV0`, so you get a chicken-and-egg: no link yet. Use:
   ```bash
   sudo socat pty,link=/dev/ttyV0,raw tcp:192.168.141.228:15000
   ```
   Socat will connect to TCP immediately; `/dev/ttyV0` should appear as soon as the connection is up. If TCP fails, socat exits and the link may be removed.

3. **nc works but socat still doesn’t create `/dev/ttyV0`.** If `nc -zv 192.168.141.228 15000` succeeds but socat with `waitslave` doesn’t create the device, drop `waitslave` and run:
   ```bash
   sudo socat -d pty,link=/dev/ttyV0,raw tcp:192.168.141.228:15000
   ```
   `-d` shows debug output so you can see when the link is created and when TCP connects.

4. **Check firewall on Windows.** Allow inbound TCP on the port you use (e.g. 15000).

5. **Confirm port on Windows.** Ensure the bridge uses the same port (e.g. `--tcp-port 15000`).

### socat 一运行就退出、/dev/ttyV0 看不到

若执行 `sudo socat pty,link=/dev/ttyV0,raw tcp:IP:PORT` 后**立刻回到 shell 提示符**，说明 socat 已经退出；退出时会删掉刚建的 `/dev/ttyV0`，所以之后再 `ls /dev/ttyV0` 会提示不存在。

**排查步骤：**

1. **用 `-d` 看 socat 为何退出**（最重要）  
   在 Linux 上执行并看输出：
   ```bash
   sudo socat -d -d pty,link=/dev/ttyV0,raw tcp:192.168.141.228:15000
   ```
   关注是否有 `open(...) failed`、`Connection refused`、`Connection reset`、`exitcode` 等；这些会说明是连不上、被对端关掉还是本机 PTY 创建失败。

2. **看 Windows 端是否立刻断开**  
   桥接用 `-v` 运行，在 Linux 跑 socat 的同一时刻看 Windows 是否先出现 “TCP client connected” 又很快出现 “TCP client disconnected”。若是，说明 TCP 连上后很快被关掉，可能原因包括：
   - 中间设备（端口转发/NAT）断连或超时；
   - 本机 PTY 或 link 创建失败导致 socat 退出并关掉 TCP。

3. **确认 /dev/ttyV0 是否曾短暂出现**  
   在后台跑 socat 并马上查设备，例如：
   ```bash
   sudo socat pty,link=/dev/ttyV0,raw tcp:192.168.141.228:15000 &
   sleep 1
   ls -la /dev/ttyV0
   jobs
   ```
   若 `ls` 能看到 `/dev/ttyV0` 而 `jobs` 里 socat 已结束，说明连接建立后很快断开、socat 退出并删除了 link。

4. **端口转发场景**  
   若 15000 是转发到 Windows 本机 5000，桥接应监听 5000（`--tcp-port 5000`），Linux 连 `转发地址:15000`。转发设备（路由器/网关）不应主动断开长连接；若有“连接空闲即断”的策略，可能导致 socat 很快退出。

## Debug / 调试方法

### Windows 端

1. **加 `-v` / `--verbose` 看连接事件**  
   运行桥接时加上 `-v`，会打印：串口打开、TCP 监听地址/端口、客户端连接/断开、拒绝多余连接等。
   ```bash
   python -m serial2tcp --tcp-port 15000 -v
   ```
   看到 “TCP server listening on 0.0.0.0:15000” 表示已在监听；Linux 连上时应出现 “TCP client connected: …”。

2. **确认本机是否在监听**  
   PowerShell 里看 15000 端口是否在 LISTEN：
   ```powershell
   netstat -an | findstr 15000
   ```
   或：
   ```powershell
   Get-NetTCPConnection -LocalPort 15000
   ```

3. **确认防火墙**  
   Windows 防火墙需放行入站 TCP（端口 15000）。可在 “高级安全 Windows 防火墙” 里添加入站规则，或临时关闭防火墙做测试。

### Linux 端

1. **先测 TCP 能否连通**  
   在桥接已启动的前提下，用 `nc` 或 `telnet` 测试，避免直接用 socat 时不知道是 TCP 问题还是 PTY 问题。
   ```bash
   nc -zv 192.168.141.228 15000
   # 或
   telnet 192.168.141.228 15000
   ```
   `Connection refused` 表示 Windows 没在监听或防火墙拦了；能连上再跑 socat。

2. **socat 加调试**  
   `-d` 打印调试信息，`-x` 会以十六进制打印经过的数据（数据多时输出会很多）：
   ```bash
   sudo socat -d pty,link=/dev/ttyV0,raw tcp:192.168.141.228:15000
   ```

3. **看是否有 `/dev/ttyV0`**  
   socat 跑起来后（且 TCP 已连上）在另一终端执行：
   ```bash
   ls -la /dev/ttyV0
   ```

### 网络

- **主机是否通**：`ping` 只能测主机是否可达（ICMP），**不能测 TCP 端口**。在 Linux 上：
  ```bash
  ping 192.168.141.228
  ```
- **端口是否通（推荐）**：要确认“端口通不通”，必须用 TCP 连一次。在 Linux 上测 Windows 的 15000 端口：
  ```bash
  nc -zv 192.168.141.228 15000
  ```
  成功会显示 `Connection to 192.168.141.228 15000 port [tcp/*] succeeded!`；`Connection refused` 表示对方没监听或防火墙拦截。
  ```bash
  telnet 192.168.141.228 15000
  ```
  能连上会进入 telnet 会话（可 Ctrl+] 再 `quit` 退出）。若没有 `nc`，可安装：`sudo apt install netcat-openbsd`（或 `netcat`）。
- **Windows 本机 IP**：PowerShell 里 `ipconfig`，确认 Linux 连的 IP 和端口正确。

## Notes

- **Firewall**: On Windows, allow inbound TCP on the port you use (e.g. 5000) so the Linux host can connect.
- **Network**: Ensure the Linux host can reach the Windows machine (correct IP, no blocking routers/firewalls).
- **Single client**: The bridge accepts only one TCP connection at a time; additional connections are closed immediately.
