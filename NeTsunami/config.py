from pathlib import Path
import yaml
from dataclasses import dataclass, field


@dataclass
class BastionConfig:
    host: str = ""
    user: str = ""
    key: str = ""
    port: int = 22


@dataclass
class Config:
    bastion: BastionConfig = field(default_factory=BastionConfig)
    data_dir: str = str(Path.home() / ".netsunami")
    model_name: str = "all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 64

    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        if path is None:
            path = str(Path.home() / ".netsunami" / "config.yaml")
        cfg = cls()
        try:
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
            if "bastion" in raw:
                cfg.bastion = BastionConfig(**raw["bastion"])
            if "data_dir" in raw:
                cfg.data_dir = raw["data_dir"]
            if "model_name" in raw:
                cfg.model_name = raw["model_name"]
            if "chunk_size" in raw:
                cfg.chunk_size = raw["chunk_size"]
            if "chunk_overlap" in raw:
                cfg.chunk_overlap = raw["chunk_overlap"]
        except FileNotFoundError:
            pass
        return cfg
