import logging


class CustomSocketIOLogger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

    def handle(self, record):
        if self.should_log(record):
            super().handle(record)

    def should_log(self, record):
        if 'Invalid session' in record.getMessage():
            return False
        if 'Client is gone, closing socket' in record.getMessage():
            return False
        if 'Sending packet PING data None' in record.getMessage():
            return False
        return True


logging.setLoggerClass(CustomSocketIOLogger)
logger = logging.getLogger('socketio')
logger.setLevel(logging.INFO)
