class ChdError(Exception):
    """Base exception for errors raised within CHD"""


class ChdInvalidCredentials(ChdError):
    """Exception raised when one tries to log in to CHD with invalid credentials."""


class ChdInvalidSimuladorData(ChdError):
    """Exception raised when one tries to fill CHD Simulador with invalid data."""


class ChdNoConditionsFound(ChdError):
    """Exception raised when CHD Simulador finds no conditions for the given data."""


class ChdValidationError(ChdError, AssertionError):
    """Raised when a ChdPage .validate method fails"""
