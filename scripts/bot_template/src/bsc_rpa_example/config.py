from dataclasses import dataclass
from pathlib import Path

from bsc_rpa_core.config import BaseConfig
from bsc_rpa_core.reporting import ReportingConfig, NotifBodyConfig, SummaryConfig

@dataclass
class IoCfg:
    # input / output directories, outlook accounts and folders, etc.
    log_folder: Path

@dataclass
class Config(BaseConfig):
    # Probably also some system-specific config (url, user, password), etc.
    io: IoCfg
    reporting: ReportingConfig

NOTIF_BODY_CONFIG = NotifBodyConfig(bot_name='{botName}', summaries=[
    # Example e-mail summary config
    SummaryConfig(
        header="Processed entries by status",
        query="""--sql
        SELECT
            status || ': ' || COUNT(*)
        FROM tasks;
        """
    ),
])