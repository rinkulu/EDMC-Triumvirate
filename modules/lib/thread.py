# -*- coding: utf-8 -*-
import threading
import time

from ..debug import debug


class BasicThread(threading.Thread):
    """
    Обёртка над Thread'ом с различными
    дополнительными методами для управления
    пулом потоков и с возможностью их останова.
    """
    pool = []
    STOP_ALL = False
    SLEEP_DURATION = 0.25

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        BasicThread.pool.append(self)
        # флаг для сигнализирования потоку, что ему пора бы остановиться
        self.STOP = False

    def sleep(self, secs: float):
        while secs > 0:
            if self.STOP:
                raise ThreadExit()
            time.sleep(min(secs, self.SLEEP_DURATION))
            secs -= self.SLEEP_DURATION

    @classmethod
    def stop_all(cls):
        cls.STOP_ALL = True
        for thread in cls.pool:
            thread.STOP = True

    @classmethod
    def join_all(cls):
        cls.stop_all()
        while cls.list_alive():
            time.sleep(cls.SLEEP_DURATION)

    @classmethod
    def list_alive(cls):
        return [x for x in cls.pool if x.is_alive()]


class Thread(BasicThread):
    def run(self):
        try:
            self.do_run()
            # перехватываем ThreadExit, чтобы он не попадал в лог
        except ThreadExit:
            pass
        debug("Thread {!r} shutted down", self.name)

    def do_run(self):
        raise NotImplementedError()


class ThreadExit(Exception):
    """
    Исключение, которое используется для прерывания потока.
    """
