class StateParent:
    def __init__(self):
        self.VERIFY_RETURN_VALUES = True
        self.VERIFY_EVENTS = True

    ### FUNDAMENTAL VERIFY METHODS ###
    def verifyReturnValue(self, tx, expected):
        if self.VERIFY_RETURN_VALUES:
            self.verifyValue("return value", expected, tx.return_value)

    def verifyValue(self, msg, expected, actual):
        if expected != actual:
            self.value_failure = True
            raise AssertionError(
                "{} : expected value {}, actual value was {}".format(
                    msg, expected, actual
                )
            )

    def verifyEvent(self, tx, eventName, data):
        if self.VERIFY_EVENTS:
            if not eventName in tx.events:
                raise AssertionError(
                    "{}: event was not fired".format(eventName)
                )
            ev = tx.events[eventName]
            for k in data:
                if not k in ev:
                    raise AssertionError(
                        "{}.{}: absent event data".format(eventName, k)
                    )
                self.verifyValue("{}.{}".format(eventName, k), data[k], ev[k])