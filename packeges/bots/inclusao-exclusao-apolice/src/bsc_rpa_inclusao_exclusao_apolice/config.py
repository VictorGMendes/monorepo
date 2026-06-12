from dataclasses import dataclass
from pathlib import Path

from bsc_rpa_core.config import BaseConfig
from bsc_rpa_core.reporting import ReportingConfig, NotifBodyConfig


@dataclass
class IoCfg:
    log_folder: Path
    screenshot_folder: Path


@dataclass
class PlaywrightCfg:
    headless: bool = False
    timeout_ms: int = 30000
    trace: bool = False


@dataclass
class GMFleetCfg:
    base_url: str
    username: str
    password: str


@dataclass
class Config(BaseConfig):
    io: IoCfg
    playwright: PlaywrightCfg
    gmfleet: GMFleetCfg
    reporting: ReportingConfig


NOTIF_BODY_CONFIG = NotifBodyConfig(
    bot_name="InclusaoExclusaoApolice",
    summaries=[]
)