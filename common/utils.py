
import sys
import logging


def init_log(log_path="", level=logging.INFO):
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

