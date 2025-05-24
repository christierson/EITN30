import functools


def socket_safe(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception as e:
            try:
                self.close()
            except Exception:
                pass
            raise e

    return wrapper
