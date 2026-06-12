import logging
import argparse
from pathlib import Path

from bsc_rpa_core.logs import configure_logging, log_func_call
from bsc_rpa_core.reporting import start_run

from bsc_rpa_adapter_outlook import Win32Outlook

from .config import Config, NOTIF_BODY_CONFIG
from .tasks import example_task

logger = logging.getLogger(__name__)

def cli():
    parser = argparse.ArgumentParser(
        prog="RPA {botName}",
        description="RPA {botName}"
        " is a bot that ..."
    )

    parser.add_argument(
        '--config', '-c',
        help='Path to the config file. Defaults to \'config.yaml\'.',
        required=False
    )

    args = parser.parse_args()

    config_path = args.config or 'config.yaml'
    
    config = Config.load(config_path)

    config.io.log_folder.mkdir(exist_ok=True, parents=True)
    log_path = config.io.log_folder / Path('log.jsonl')

    configure_logging(
        log_path.as_posix(),
        # If urllib3 is being used (probably indirectly via requests or playwright)
        # The line bellow is usually a good ideia
        # Suppressing DEBUG-level urllib3 logs since they polute the logs a lot
        # {'loggers': {'urllib3': {'level': 'INFO'}}}
    )

    main(config)

@log_func_call(logger, logging.INFO)
def main(config: Config):
    with (
        # Probably some system-specific sessions here
        Win32Outlook() as outlook,
        start_run("bsc-rpa-{botNameLower}", config.reporting, NOTIF_BODY_CONFIG, outlook)
    ):
        for arg_1 in range(10):
            example_task(arg_1, 'This is arg_2')

if __name__ == "__main__":
    cli()