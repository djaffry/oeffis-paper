import json
import logging
import sys

conf_cache = None  # caches config.json


def get_config():
    """
    Returns a cached `dict` of `config.json`
    If the cached `dict` does not exist, will try to load `config.json` from project root

    :return: cached `dict` of `config.json`
    """
    global conf_cache
    if conf_cache is None:
        with open('config.json', 'r') as f:
            conf_cache = json.load(f)
    return conf_cache


def reload_conf():
    """
    Reloads the cached `dict` of `config.json`

    :return: cached `dict` of `config.json`
    """
    global conf_cache
    conf_cache = None
    return get_config()


def get_logger(name):
    """
    Get a preconfigured logger

    Example logging output
    2019-03-03 12:40:20,025 - INFO - __main__: Application start.sh!

    :param name: Logger name
    :return: preconfigured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s:  %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
