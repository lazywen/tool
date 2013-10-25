#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

_log = 'stdout'
def loginit():
    logger  = logging.getLogger()
    if _log == 'stdout':
        handler = logging.StreamHandler()
    else:
        handler = logging.FileHandler(_log)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.NOTSET)
    return logger
log = loginit()
