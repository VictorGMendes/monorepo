class SrsJavaError(Exception):
    """Base exception for errors raised within SRS Java"""


class SrsJavaValidationError(SrsJavaError, AssertionError):
    """Raised when SRS Java page validation fails"""


class SrsJavaCredentialsError(SrsJavaError, ValueError):
    """Raised when SRS Java credentials are invalid"""


class SrsJavaLoginTimeoutError(SrsJavaError, TimeoutError):
    """Raised when SRS Java login passes timeout"""
