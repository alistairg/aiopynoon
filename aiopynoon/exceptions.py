""" Exceptions thrown by PyNoon """

class NoonException(Exception):

    pass


class NoonAuthenticationError(NoonException):

    pass


class NoonInvalidParametersError(NoonException):

    pass


class NoonInvalidJsonError(NoonException):

    pass


class NoonDuplicateIdError(NoonException):

    pass


class NoonUnknownError(NoonException):

    pass

class NoonProtocolError(NoonException):

    pass

class NoonEvent(object):

    pass