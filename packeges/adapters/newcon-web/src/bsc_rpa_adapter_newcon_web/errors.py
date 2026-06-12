class NewconWebError(RuntimeError):
    """Base exception for errors raised within NewconWeb"""


class NwMfaTimerError(NewconWebError):
    """Raised when NewconWeb MFA times out"""


class NwNavigationError(NewconWebError):
    """Raised when navigation within a NewconWebPage fails"""


class NwPermissionError(NwNavigationError):
    """Raised when navigation within a NewconWebPage fails because of lack of permissions"""


class NwValidationError(NewconWebError):
    """Raised when a NewconWebPage .validate method fails"""


class NwQuotaNotFoundError(NewconWebError):
    """Raised when a quota search fails"""


class NwGetExtratoError(NewconWebError):
    """Raised when getting a quota extrato fails"""


class NwLoggedOutError(NewconWebError):
    """Raised when user is logged out of Newcon Web"""
