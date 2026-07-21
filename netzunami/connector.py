import paramiko
import re
import time

VENDOR_PROMPTS = {
    "cisco": r"[>#]\s*$",
    "huawei": r"[>#]\s*$",
    "aethra": r"[>#]\s*$",
    "juniper": r"%\s*$",
}


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


def _recv_until_prompt(shell, prompt_re: str, timeout_sec: int = 15) -> str:
    output = ""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            data = shell.recv(65535).decode("utf-8", errors="replace")
            output += data
            if re.search(prompt_re, data, re.MULTILINE):
                break
        except:
            break
    return output


def detect_vendor(shell) -> str:
    shell.send("\n")
    time.sleep(1)
    try:
        banner = shell.recv(4096).decode("utf-8", errors="replace").lower()
    except:
        banner = ""

    if "huawei" in banner or "vrp" in banner:
        return "huawei"
    if "aethra" in banner:
        return "aethra"
    if "junos" in banner or "junipers" in banner or "juniper" in banner:
        return "juniper"
    return "cisco"


def _enable_and_wait(shell, prompt_re: str, enable_password: str | None = None):
    shell.send("enable\n")
    output = _recv_until_prompt(shell, prompt_re)
    if "password" in output.lower() and enable_password:
        shell.send(f"{enable_password}\n")
        output += _recv_until_prompt(shell, prompt_re)
    return output


def run_commands(
    client: paramiko.SSHClient,
    commands: list[str],
    vendor: str | None = None,
    enable: bool = True,
    enable_password: str | None = None,
) -> str:
    shell = client.invoke_shell()
    shell.settimeout(30)
    output = ""

    if vendor is None:
        vendor = detect_vendor(shell)

    prompt_re = VENDOR_PROMPTS.get(vendor, r"[>#]\s*$")

    if vendor == "huawei":
        shell.send("screen-length 0 temporary\n")
        _recv_until_prompt(shell, prompt_re)
        for cmd in commands:
            shell.send(f"{cmd}\n")
            output += _recv_until_prompt(shell, prompt_re)
        shell.send("quit\n")
        shell.close()
        return output

    if vendor == "aethra":
        if enable:
            output += _enable_and_wait(shell, prompt_re, enable_password)
        shell.send("terminal length 0\n")
        _recv_until_prompt(shell, prompt_re)
        for cmd in commands:
            shell.send(f"{cmd}\n")
            output += _recv_until_prompt(shell, prompt_re)
        shell.close()
        return output

    if vendor == "juniper":
        shell.send("set cli screen-length 0\n")
        _recv_until_prompt(shell, prompt_re)
        for cmd in commands:
            shell.send(f"{cmd}\n")
            output += _recv_until_prompt(shell, prompt_re)
        shell.close()
        return output

    if vendor == "cisco":
        if enable:
            output += _enable_and_wait(shell, prompt_re, enable_password)
        shell.send("terminal length 0\n")
        _recv_until_prompt(shell, prompt_re)
        for cmd in commands:
            shell.send(f"{cmd}\n")
            output += _recv_until_prompt(shell, prompt_re)

    shell.close()
    return output
