import re
from .models import ConfigLine, ConfigBlock


BLOCK_HEADERS = {
    "cisco": [
        r"^interface\s",
        r"^router\s",
        r"^vlan\s",
        r"^port-channel\s",
        r"^line\s",
        r"^ip\s+access-list\s",
        r"^route-map\s",
        r"^prefix-list\s",
        r"^community-list\s",
        r"^class-map\s",
        r"^policy-map\s",
        r"^control-plane\s",
        r"^spanning-tree\s",
        r"^snmp-server\s",
        r"^ntp\s",
        r"^logging\s",
        r"^banner\s",
        r"^username\s",
        r"^aaa\s",
        r"^crypto\s",
    ],
}


def parse_cisco(config_text: str) -> list[ConfigBlock]:
    blocks: list[ConfigBlock] = []
    current_block: ConfigBlock | None = None
    lines = config_text.splitlines()

    patterns = BLOCK_HEADERS["cisco"]
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("!"):
            continue

        is_header = any(p.match(stripped) for p in compiled)

        if is_header:
            if current_block and current_block.lines:
                blocks.append(current_block)
            current_block = ConfigBlock(name=stripped)
            current_block.lines.append(
                ConfigLine(number=i + 1, text=stripped, indent=0)
            )
        elif current_block is not None:
            indent = len(line) - len(line.lstrip())
            current_block.lines.append(
                ConfigLine(number=i + 1, text=stripped, indent=indent)
            )

    if current_block and current_block.lines:
        blocks.append(current_block)

    return blocks


def parse_running_config(config_text: str, vendor: str = "cisco") -> list[ConfigBlock]:
    if vendor == "cisco":
        return parse_cisco(config_text)
    return parse_cisco(config_text)
