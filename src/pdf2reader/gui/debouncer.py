from threading import Timer


class Debouncer(object):
    def __init__(self, callback, debounce_interval=0.2):
        self.key_released_timer = None

        self.debounce_interval = debounce_interval
        self.callback = callback


    def _key_released_timer_cb(self, event):
        if self.key_released_timer:
            self.key_released_timer.cancel()
            self.key_released_timer = None

        self.callback(event)


    def process_event(self, event):
        """ Callback for a key being released. """
        # Set a timer. If it is allowed to expire (not reset by another down
        # event), then we know the key has been released for good.
        if self.key_released_timer:
            self.key_released_timer.cancel()
            self.key_released_timer = None

        self.key_released_timer = Timer(self.debounce_interval,
                                        self._key_released_timer_cb, [event])
        self.key_released_timer.start()
