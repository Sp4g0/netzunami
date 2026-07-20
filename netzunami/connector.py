import paramiko
import re


def ssh_connect(
    host: str,
    user: str,
    key_path: str | None = None,
    password: str | None = None,
    port: int = 22,
    bastion: dict | None = None,
    timeout: int = 15,
) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if bastion:
        jump = paramiko.SSHClient()
        jump.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        jump_kw = {
            "hostname": bastion["host"],
            "username": bastion.get("user", user),
            "port": bastion.get("port", 22),
        }
        if bastion.get("key"):
            jump_kw["key_filename"] = bastion["key"]
        if password:
            jump_kw["password"] = password
        jump.connect(**jump_kw, timeout=timeout)

        transport = jump.get_transport()
        dest_addr = (host, port)
        local_addr = ("127.0.0.1", 0)
        channel = transport.open_channel(
            "direct-tcpip", dest_addr, local_addr, timeout=timeout
        )

        client_kw = {
            "hostname": host,
            "username": user,
            "sock": channel,
            "timeout": timeout,
        }
        if key_path:
            client_kw["key_filename"] = key_path
        if password:
            client_kw["password"] = password
        client.connect(**client_kw)
    else:
        client_kw = {
            "hostname": host,
            "username": user,
            "port": port,
            "timeout": timeout,
        }
        if key_path:
            client_kw["key_filename"] = key_path
        if password:
            client_kw["password"] = password
        client.connect(**client_kw)

    return client


def run_commands(
    client: paramiko.SSHClient,
    commands: list[str],
    vendor: str = "cisco",
    enable: bool = True,
) -> str:
    shell = client.invoke_shell()
    shell.settimeout(30)

    output = ""
    if vendor == "cisco":
        if enable:
            shell.send("enable\n")
            shell.recv(4096)
            shell.send("terminal length 0\n")
        else:
            shell.send("terminal length 0\n")
        shell.recv(4096)

        for cmd in commands:
            shell.send(f"{cmd}\n")
            import time

            time.sleep(1)
            while True:
                try:
                    data = shell.recv(65535).decode("utf-8", errors="replace")
                    output += data
                    prompt_match = re.search(r"[>#]\s*$", data, re.MULTILINE)
                    if prompt_match:
                        break
                except:
                    break
    else:
        for cmd in commands:
            shell.send(f"{cmd}\n")
            import time

            time.sleep(1)
            try:
                output += shell.recv(65535).decode("utf-8", errors="replace")
            except:
                pass

    shell.close()
    return output
