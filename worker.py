import threading


class Worker(threading.Thread):
    """
    Worker Wrapper, runs on own thread
    Calls api.update() on thread.start()
    """

    def __init__(self, name, api):
        threading.Thread.__init__(self)
        self.name = name
        self.api = api

    def run(self):
        self.api.update()
