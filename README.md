# Serial2TCP Bridge

把 Windows 上的串口（如 COM7）转成 TCP 服务；Linux 用 **socat** 连上后得到虚拟串口，即可远程读写该串口。

- **Windows**：Python + [pyserial](https://github.com/pyserial/pyserial)，串口与 TCP 双向转发，只接受一个客户端。
- **Linux**：socat 连接 Windows 的 TCP，创建 PTY（如 `/tmp/ttyV0`），用 minicom/screen 打开即可。

## Windows

```bash
pip install pyserial
python -m serial2tcp --port COM7 --baud 460800 --tcp-port 5000
```

常用参数：`--port` 串口名，`--baud` 波特率，`--tcp-port` 监听端口，`-v` 打印连接日志。

## Linux

先启动 Windows 桥接，再在 Linux 上（将 IP 和端口换成你的）：

```bash
socat pty,link=/tmp/ttyV0,raw tcp:WINDOWS_IP:PORT
```

保持该命令运行；在**另一终端**用 `minicom -D /tmp/ttyV0` 或 `screen /tmp/ttyV0 460800`。link 建在 `/tmp` 或 `$HOME` 可不用 sudo；建在 `/dev/ttyV0` 需 sudo（部分系统会失败）。

**注意**：桥接只接受一个连接。若新 socat 一连接就退出（"socket is at EOF"），说明已有客户端占着，先 `pkill -f "socat.*ttyV0"` 再起一个。

## Troubleshooting

- Windows 先起桥接，再在 Linux 跑 socat；否则连接被拒，socat 会退出并删掉 link。
- 端口不通时用 `nc -zv WINDOWS_IP PORT` 测；放行 Windows 防火墙入站。
- 调试：Windows 加 `-v`；socat 加 `-d`。
