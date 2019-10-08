import time
from functools import partial

from levin.core.component import Component
from levin.utils.profile import SimpleProfile, print_result


class Profile(Component):
    name = "profile"

    def __init__(self, trashhold=0.1, get_time=time.time, depth=1):
        self.__trashhold = trashhold
        self._targets = []
        self._results = []
        self._get_time = get_time
        self._depth = depth

    async def middleware(self, request, handler, call_next):
        if handler in self._targets:
            self._targets.remove(handler)
            profile = SimpleProfile(depth=self._depth, memory=True)
            handler = partial(profile.run, handler)
            try:
                return await call_next(request, handler)
            finally:
                profile.stop()
                print_result(profile)
        start = self._get_time()
        try:
            return await call_next(request, handler)
        finally:
            if (self._get_time() - start) > self.__trashhold:
                self._targets.append(handler)


class ProfileMiddlewares(Component):
    name = "profile"

    def __init__(self, trashhold=0.1, get_time=time.time):
        self.__trashhold = trashhold
        self._targets = []
        self._results = []
        self._get_time = get_time
        self._depth = 3

    async def middleware(self, request, handler, call_next):
        if handler in self._targets:
            self._targets.remove(handler)
            profile = SimpleProfile(depth=self._depth, memory=True)
            try:
                return await profile.run(call_next, request, handler)
            finally:
                print_result(profile)
        start = self._get_time()
        try:
            return await call_next(request, handler)
        finally:
            if (self._get_time() - start) > self.__trashhold:
                self._targets.append(handler)
                print("APPENDED")