
import sys
import logging
import datetime
from collections.abc import Callable


def init_log(log_path="", level=logging.INFO) -> None:
    log_formatter = logging.Formatter("%(asctime)s %(process)s %(thread)s %(filename)s [%(levelname)-5.5s] %(message)s")
    # 1. file handler
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler('%smain.log' % log_path, when='midnight')
    file_handler.suffix = '%Y_%m_%d.log'
    file_handler.setFormatter(log_formatter)
    # 2. stream handler
    std_handler = logging.StreamHandler(sys.stdout)
    std_handler.setFormatter(log_formatter)
    logger = logging.getLogger()
    # 3. add handler
    logger.addHandler(file_handler)
    logger.addHandler(std_handler)
    logger.setLevel(level)
    logging.debug('init logging succ')


def now_ts() -> float:
    return datetime.datetime.now().timestamp()


def wrap_log_ts(func: Callable) -> None:
    def inner(*args, **kwargs):
        ts = now_ts()
        re = func(*args, **kwargs)
        logging.info(f"{func.__name__} cost {format(now_ts()-ts, '.3f')}s")
        return re
    return inner


def wrap_log_ts_async(func: Callable) -> None:
    async def inner(*args, **kwargs):
        ts = now_ts()
        re = await func(*args, **kwargs)
        logging.info(f"{func.__name__} cost {format(now_ts()-ts, '.3f')}s")
        return re
    return inner


def lru_pop(*arrays: list, max_length: int=10) -> None:
    for array in arrays:
        while len(array) > max_length: array.pop(0)
