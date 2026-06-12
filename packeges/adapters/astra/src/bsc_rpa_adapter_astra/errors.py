class AstraError(Exception):
    """Base exception for errors raised within Astra"""


class AstraValidationError(AstraError, AssertionError):
    """Raised when Astra page validation fails"""


class AstraCredentialsError(AstraError, ValueError):
    """Raised when Astra credentials are invalid"""


class AstraOpenFinancialsError(AstraError):
    """Raised when Astra financials section cannot be opened"""


class AstraDealerNotFoundError(AstraError):
    """Raised when Astra dealer is not found"""


class AstraReportingPeriodError(AstraError):
    """Raised when new reporting period is older than last reporting period"""


class MissingFinancialFieldsError(AstraError):
    """Raised when some financial fields could not be filled"""
