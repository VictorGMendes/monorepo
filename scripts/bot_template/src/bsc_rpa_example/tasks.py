import logging

from bsc_rpa_core.reporting import task

logger = logging.getLogger(__name__)

@task(record_args=("filename", "dealer_id",), record_out=True)
def example_task(
    arg_1: int,
    arg_2: str,
) -> str:
    logger.debug(f"Starting task with arg_1={arg_1!r}, arg_2={arg_2!r}")

    # Some processing
    out = str(arg_1) + arg_2

    logger.debug(f"Task with arg_1={arg_1!r}, arg_2={arg_2!r} successful")

    return out