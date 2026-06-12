class SrsWebError(Exception):
    """Base exception for errors raised within SRS Web"""


class SrsWebValidationError(SrsWebError, AssertionError):
    """Raised when SRS Web page validation fails"""


class SrsWebCredentialsError(SrsWebError, ValueError):
    """Raised when SRS Web credentials are invalid"""


class SrsWebAdhocSearchError(SrsWebError):
    """Raised when search a contract on Adhoc Search fails"""


class SrsWebInstallmentChkboxDisabledError(SrsWebError):
    """Raised when one tries to select or unselect a installment whose checkbox is disabled on a payslip"""


class SrsWebInstallmentValueReadOnlyError(SrsWebError):
    """Raised when one tries to edit a installment value that is read-only on a payslip"""


class SrsWebInvalidInstallmentValueError(SrsWebError):
    """Raised when one tries to edit a installment value with an invalid amount on a payslip"""


class SrsWebPayslipButtonDisabledError(SrsWebError):
    """Raised when trying to press a disabled button on a payslip"""


class SrsWebPayslipSaveError(SrsWebError):
    """Raised when saving a payslip fails"""


class SrsWebPayslipSendError(SrsWebError):
    """Raised when sending a payslip fails"""


class SrsWebPayslipResendError(SrsWebError):
    """Raised when resending a payslip fails"""


class SrsWebPrintScriptNotFoundError(SrsWebError):
    """Raised when cnsprintarea function declaration is not found inside <script> tag in a generated payslip"""
