import logging


_log = logging.getLogger("kotkotool")


def dbg(*args, **kwargs):
    _log.debug(*args, **kwargs, stacklevel=2)


def inf(*args, **kwargs):
    _log.info(*args, **kwargs, stacklevel=2)


def wrn(*args, **kwargs):
    _log.warning(*args, **kwargs, stacklevel=2)


def err(*args, **kwargs):
    _log.error(*args, **kwargs, stacklevel=2)
