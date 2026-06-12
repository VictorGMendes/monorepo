from abc import abstractmethod
from decimal import Decimal
from datetime import datetime
from typing import Self, Literal
import time

from playwright.sync_api import expect, Dialog, Locator

from ..errors import (
    SrsWebInstallmentChkboxDisabledError,
    SrsWebInstallmentValueReadOnlyError,
    SrsWebInvalidInstallmentValueError,
    SrsWebPayslipSaveError,
    SrsWebPayslipButtonDisabledError,
    SrsWebPayslipResendError,
    SrsWebPayslipSendError,
)

from .base import _EXPECT_TIMEOUT, _regex_eq, SrsWebPage, logger


class Installment:
    def __init__(self, tr: Locator) -> None:
        self.chkbox: Locator = tr.locator("td:nth-child(1) input")
        self.input_slip_no: Locator = tr.locator("td:nth-child(2) input")
        self.input_due_date: Locator = tr.locator("td:nth-child(3) input.txtBackColor")
        self.input_description: Locator = tr.locator(
            "td:nth-child(4) input.txtBackColor"
        )
        self.input_total_amt: Locator = tr.locator("td:nth-child(5) input.txtBackColor")
        self.input_pending_amt: Locator = tr.locator(
            "td:nth-child(6) input.txtBackColor"
        )
        self.input_alloc_amt: Locator = tr.locator("td:nth-child(7) input")
        self.input_rebate: Locator = tr.locator("td:nth-child(8) input")
        self.input_late_charges_calc: Locator = tr.locator("td:nth-child(9) input")
        self.input_late_charges_alloc: Locator = tr.locator("td:nth-child(10) input")
        self.input_iof: Locator = tr.locator("td:nth-child(11) input")
        self.input_total_receivable: Locator = tr.locator("td:nth-child(12) input")

    def update_values(self) -> None:
        self.input_slip_no.click()

    def is_selected(self) -> bool:
        return self.chkbox.is_checked()

    def is_chkbox_enabled(self) -> bool:
        return self.chkbox.is_enabled()

    def select(self) -> None:
        if (not self.is_selected()) and (not self.is_chkbox_enabled()):
            raise SrsWebInstallmentChkboxDisabledError(
                f"Can't select installment {self.get_description()!r}: Checkbox is disabled"
            )
        self.chkbox.check()

    def unselect(self) -> None:
        if (self.is_selected()) and (not self.is_chkbox_enabled()):
            raise SrsWebInstallmentChkboxDisabledError(
                f"Can't unselect installment {self.get_description()!r}: Checkbox is disabled"
            )
        self.chkbox.uncheck()

    def get_slip_no(self) -> str:
        return self.input_slip_no.input_value()

    def get_due_date(self) -> datetime:
        return datetime.strptime(self.input_due_date.input_value(), "%d/%m/%Y")

    def get_description(self) -> str:
        return self.input_description.input_value()

    def get_total_amt(self) -> Decimal:
        return Decimal(self.input_total_amt.input_value().replace(",", ""))

    def get_pending_amt(self) -> Decimal:
        return Decimal(self.input_pending_amt.input_value().replace(",", ""))

    def get_alloc_amt(self) -> Decimal:
        return Decimal(self.input_alloc_amt.input_value().replace(",", ""))

    def is_alloc_amt_readonly(self) -> bool:
        return self.input_alloc_amt.evaluate("el => el.readOnly")

    def set_alloc_amt(self, alloc_amt: Decimal) -> None:
        if self.is_alloc_amt_readonly():
            raise SrsWebInstallmentValueReadOnlyError(
                f"Can't set alloc_amt to {alloc_amt} for installment {self.get_description()!r}: "
                "alloc_amt is read-only"
            )

        pending_amt = self.get_pending_amt()
        if not (Decimal("0") <= alloc_amt <= pending_amt):
            raise SrsWebInvalidInstallmentValueError(
                f"Can't set alloc_amt to {alloc_amt} for installment {self.get_description()!r}: "
                f"{alloc_amt} is not between 0 and pending_amt={pending_amt}"
            )

        self.input_alloc_amt.fill(str(alloc_amt))

    def get_rebate(self) -> Decimal:
        return Decimal(self.input_rebate.input_value().replace(",", ""))

    def get_late_charges_calc(self) -> Decimal:
        return Decimal(self.input_late_charges_calc.input_value().replace(",", ""))

    def get_late_charges_alloc(self) -> Decimal:
        return Decimal(self.input_late_charges_alloc.input_value().replace(",", ""))

    def is_late_charges_alloc_readonly(self) -> bool:
        return self.input_late_charges_alloc.evaluate("el => el.readOnly")

    def set_late_charges_alloc(self, late_charges_alloc: Decimal) -> None:
        if self.is_late_charges_alloc_readonly():
            raise SrsWebInstallmentValueReadOnlyError(
                f"Can't set late_charges_alloc to {late_charges_alloc} for installment {self.get_description()!r}: "
                "late_charges_alloc is read-only"
            )

        late_charges_calc = self.get_late_charges_calc()
        if not (Decimal("0") <= late_charges_alloc <= late_charges_calc):
            raise SrsWebInvalidInstallmentValueError(
                f"Can't set late_charges_alloc to {late_charges_alloc} for installment {self.get_description()!r}: "
                f"{late_charges_alloc} is not between 0 and late_charges_calc={late_charges_calc}"
            )

        self.input_late_charges_alloc.fill(str(late_charges_alloc))

    def get_iof(self) -> Decimal:
        return Decimal(self.input_iof.input_value().replace(",", ""))

    def get_total_receivable(self) -> Decimal:
        return Decimal(self.input_total_receivable.input_value().replace(",", ""))

    def __str__(self) -> str:
        return (
            "<Installment data={\n"
            f"  is_selected={self.is_selected()},\n"
            f"  slip_no={self.get_slip_no()},\n"
            f"  due_date={self.get_due_date()},\n"
            f"  description={self.get_description()},\n"
            f"  total_amt={self.get_total_amt()},\n"
            f"  pending_amt={self.get_pending_amt()},\n"
            f"  alloc_amt={self.get_alloc_amt()},\n"
            f"  rebate={self.get_rebate()},\n"
            f"  late_charges_calc={self.get_late_charges_calc()},\n"
            f"  late_charges_alloc={self.get_late_charges_alloc()},\n"
            f"  iof={self.get_iof()},\n"
            f"  total_receivable={self.get_total_receivable()},\n"
            "}>"
        )

    def __repr__(self) -> str:
        return (
            "<Installment data={\n"
            f"  is_selected={self.is_selected()!r},\n"
            f"  slip_no={self.get_slip_no()!r},\n"
            f"  due_date={self.get_due_date()!r},\n"
            f"  description={self.get_description()!r},\n"
            f"  total_amt={self.get_total_amt()!r},\n"
            f"  pending_amt={self.get_pending_amt()!r},\n"
            f"  alloc_amt={self.get_alloc_amt()!r},\n"
            f"  rebate={self.get_rebate()!r},\n"
            f"  late_charges_calc={self.get_late_charges_calc()!r},\n"
            f"  late_charges_alloc={self.get_late_charges_alloc()!r},\n"
            f"  iof={self.get_iof()!r},\n"
            f"  total_receivable={self.get_total_receivable()!r},\n"
            "}>"
        )


class Payslip:
    __MAX_GOTO_TRIES = 3

    def __init__(self, tr: Locator) -> None:
        self.input_slip_no: Locator = tr.locator("td:nth-child(1) input")
        self.input_amount: Locator = tr.locator("td:nth-child(2) input")
        self.input_send_type: Locator = tr.locator("td:nth-child(3) input")
        self.input_request_type: Locator = tr.locator("td:nth-child(4) input")
        self.input_expiry_date: Locator = tr.locator("td:nth-child(5) input")
        self.input_generated_by: Locator = tr.locator("td:nth-child(6) input")
        self.input_generated_date: Locator = tr.locator("td:nth-child(7) input")
        self.input_received_amount: Locator = tr.locator("td:nth-child(8) input")
        self.input_status: Locator = tr.locator("td:nth-child(9) input")
        self.input_file_name: Locator = tr.locator("td:nth-child(10) input")

    def get_slip_no(self) -> str:
        return self.input_slip_no.input_value()

    def get_amount(self) -> Decimal:
        return Decimal(self.input_amount.input_value().replace(",", ""))

    def get_send_type(self) -> str:
        return self.input_send_type.input_value()

    def get_request_type(self) -> str:
        return self.input_request_type.input_value()

    def get_expiry_date(self) -> datetime:
        return datetime.strptime(self.input_expiry_date.input_value(), "%d/%m/%Y")

    def get_generated_by(self) -> str:
        return self.input_generated_by.input_value()

    def get_generated_date(self) -> datetime:
        return datetime.strptime(self.input_generated_date.input_value(), "%d/%m/%Y")

    def get_received_amount(self) -> Decimal:
        return Decimal(self.input_received_amount.input_value().replace(",", ""))

    def get_status(self) -> str:
        return self.input_status.input_value()

    def get_file_name(self) -> str:
        return self.input_file_name.input_value()

    def __str__(self) -> str:
        return (
            "<Payslip data={\n"
            f"    slip_no={self.get_slip_no()},\n"
            f"    amount={self.get_amount()},\n"
            f"    send_type={self.get_send_type()},\n"
            f"    request_type={self.get_request_type()},\n"
            f"    expiry_date={self.get_expiry_date()},\n"
            f"    generated_by={self.get_generated_by()},\n"
            f"    generated_date={self.get_generated_date()},\n"
            f"    received_amount={self.get_received_amount()},\n"
            f"    status={self.get_status()},\n"
            f"    file_name={self.get_file_name()},\n"
            "}>"
        )

    def __repr__(self) -> str:
        return (
            "<Payslip data={\n"
            f"    slip_no={self.get_slip_no()!r},\n"
            f"    amount={self.get_amount()!r},\n"
            f"    send_type={self.get_send_type()!r},\n"
            f"    request_type={self.get_request_type()!r},\n"
            f"    expiry_date={self.get_expiry_date()!r},\n"
            f"    generated_by={self.get_generated_by()!r},\n"
            f"    generated_date={self.get_generated_date()!r},\n"
            f"    received_amount={self.get_received_amount()!r},\n"
            f"    status={self.get_status()!r},\n"
            f"    file_name={self.get_file_name()!r},\n"
            "}>"
        )

    def goto(self) -> "ExistingPayslipPage":
        self.input_slip_no.click()
        existing_payslip_page = ExistingPayslipPage(
            self.input_slip_no.page, validate_at_init=False
        )

        counter: int = 0

        def validated() -> bool:
            try:
                existing_payslip_page.validate()
                return True
            except AssertionError:
                return False

        while not validated():
            self.input_slip_no.click()

            counter += 1
            if counter > self.__MAX_GOTO_TRIES:
                break

        existing_payslip_page.validate()
        return existing_payslip_page


class BasePayslipPage(SrsWebPage):
    def _elements(self) -> None:
        page = self.page
        self.form_payslip: Locator = page.locator("form[name='SecondPaymentfrm']")
        self.td_header: Locator = self.form_payslip.locator(
            "td.clsToolBarCell", has_text=_regex_eq("Payment Slip")
        )

        self.button_clear: Locator = self.form_payslip.locator("button#clear")
        self._state_elements()

    @abstractmethod
    def _state_elements(self) -> None: ...

    def _validate(self, timeout_ms: int) -> None:
        expect(self.td_header).to_be_visible(timeout=timeout_ms)
        self._state_validate(timeout_ms)

    @abstractmethod
    def _state_validate(self, timeout_ms: int) -> None: ...

    def clear(self) -> "MainPayslipPage":
        try:
            expect(self.button_clear).to_be_enabled(timeout=_EXPECT_TIMEOUT)
        except AssertionError as e:
            raise SrsWebPayslipButtonDisabledError(
                "Tried to clear payslip, but clear button is disabled"
            ) from e

        self.button_clear.click()

        return MainPayslipPage(self.page)


class MainPayslipPage(BasePayslipPage):
    __MAX_NEW_PAYSLIP_TRIES = 3

    def _state_elements(self) -> None:
        self.input_pmt_date: Locator = self.form_payslip.locator("input#payment_date")
        self.radio_pmt_type_normal: Locator = self.form_payslip.locator("input#normal")
        self.radio_pmt_type_partial: Locator = self.form_payslip.locator(
            "input#partial"
        )
        self.radio_pmt_type_full: Locator = self.form_payslip.locator("input#full")

        self.table_payslips: Locator = self.form_payslip.locator(
            "div#gridtable table.collTableBorder#lastgrid"
        )

        self.tr_payslip: Locator = self.table_payslips.locator("tr")

    def _state_validate(self, timeout_ms: int) -> None:
        pass

    def wait_for_payslips(self) -> None:
        try:
            self.tr_payslip.first.wait_for()
        except TimeoutError as e:
            logger.warning(f"Timeout while wait for payslips: {e}", exc_info=True)

    def existing_payslips(self) -> list[Payslip]:
        self.wait_for_payslips()
        payslips: list[Payslip] = []

        for tr in self.tr_payslip.all():
            payslips.append(Payslip(tr))

        return payslips

    def create_new_payslip(
        self,
        payment_date: datetime | None = None,
        payment_type: Literal["Normal", "Partial Rebate", "Full Rebate"] | None = None,
    ) -> "NewPayslipPage":
        new_payslip_page = NewPayslipPage(self.page, validate_at_init=False)

        if payment_date is not None:
            self.input_pmt_date.fill("")
            self.input_pmt_date.press_sequentially(payment_date.strftime("%d%m%Y"))

        match payment_type:
            case "Normal":
                self.radio_pmt_type_normal.click()
            case "Partial Rebate":
                self.radio_pmt_type_partial.click()
            case "Full Rebate":
                self.radio_pmt_type_full.click()

        counter: int = 0

        def first_installment_visible() -> bool:
            try:
                expect(new_payslip_page.tr_installment.first).to_be_visible(
                    timeout=_EXPECT_TIMEOUT
                )
                return True
            except AssertionError:
                return False

        while not first_installment_visible():
            if payment_date is not None:
                self.input_pmt_date.fill("")
                self.input_pmt_date.press_sequentially(payment_date.strftime("%d%m%Y"))

            match payment_type:
                case "Normal":
                    self.radio_pmt_type_normal.click()
                case "Partial Rebate":
                    self.radio_pmt_type_partial.click()
                case "Full Rebate":
                    self.radio_pmt_type_full.click()

            counter += 1
            if counter > self.__MAX_NEW_PAYSLIP_TRIES:
                break

        new_payslip_page.validate()
        return new_payslip_page


class PayslipSendTypeComponent:
    def __init__(self, form_payslip: Locator):
        self.chkbox_email: Locator = form_payslip.locator("input#Email")
        self.input_email: Locator = form_payslip.locator("input#emailid")
        self.chkbox_sms: Locator = form_payslip.locator("input#Sms")
        self.input_sms: Locator = form_payslip.locator("input#smsno")

    def fill_send_type(
        self,
        send_email: bool | None = None,
        send_sms: bool | None = None,
        email: str | None = None,
        sms: int | None = None,
    ) -> None:
        if send_email is not None:
            if send_email:
                self.chkbox_email.check()
            else:
                self.chkbox_email.uncheck()

        if send_sms is not None:
            if send_sms:
                self.chkbox_sms.check()
            else:
                self.chkbox_sms.uncheck()

        if email is not None:
            self.input_email.fill(email)

        if sms is not None:
            self.input_sms.fill(str(sms))


class NewPayslipPage(BasePayslipPage):
    def _state_elements(self) -> None:
        self.chkbox_dummy: Locator = self.form_payslip.locator("input#dummypayslip")
        self.chkbox_outbound: Locator = self.form_payslip.locator("input#outboundcall")

        self.input_msg2: Locator = self.form_payslip.locator("input#msg2")
        self.input_msg3: Locator = self.form_payslip.locator("input#msg3")
        self.input_msg4: Locator = self.form_payslip.locator("input#msg4")

        self.input_fee: Locator = self.form_payslip.locator("input#agencyfee")

        self.component_send_type: PayslipSendTypeComponent = PayslipSendTypeComponent(
            self.form_payslip
        )

        self.button_save: Locator = self.form_payslip.locator("button#Savebtn")

        self.table_installments: Locator = self.form_payslip.locator(
            "table.collTableBorder#mainTable"
        )
        self.tr_installment: Locator = self.table_installments.locator("tr")

    def installments(self) -> list[Installment]:
        installments: list[Installment] = []

        for tr in self.tr_installment.all():
            installments.append(Installment(tr))

        return installments

    def _state_validate(self, timeout_ms: int) -> None:
        expect(self.button_save).to_be_enabled(timeout=timeout_ms)

    def save(self) -> "GenSendPayslipPage | GenResendPayslipPage":
        try:
            expect(self.button_save).to_be_enabled(timeout=_EXPECT_TIMEOUT)
        except AssertionError as e:
            raise SrsWebPayslipButtonDisabledError(
                "Tried to save payslip, but save button is disabled"
            ) from e

        with self.page.expect_event("dialog") as dialog_info:
            self.button_save.click()

        dialog: Dialog = dialog_info.value
        dialog.dismiss()

        if "Record Has Been Saved Successfully" in dialog.message:
            logger.info(
                f"Payslip saved successfully: Dialog message: {dialog.message!r}"
            )
            return GenSendPayslipPage(self.page)
        elif "Payslip already exists with the same condition" in dialog.message:
            logger.info(f"Payslip already exists: Dialog message: {dialog.message!r}")
            return GenResendPayslipPage(self.page)
        else:
            raise SrsWebPayslipSaveError(dialog.message)

    def fill_form_details(
        self,
        outbound_call: bool | None = None,
        dummy_payslip: bool | None = None,
        msg2: str | None = None,
        msg3: str | None = None,
        msg4: str | None = None,
        fee: Decimal | None = None,
    ) -> Self:
        if outbound_call is not None:
            if outbound_call:
                self.chkbox_outbound.check()
            else:
                self.chkbox_outbound.uncheck()

        if dummy_payslip is not None:
            if dummy_payslip:
                self.chkbox_dummy.check()
            else:
                self.chkbox_dummy.uncheck()

        if msg2 is not None:
            self.input_msg2.fill(msg2)

        if msg3 is not None:
            self.input_msg3.fill(msg3)

        if msg4 is not None:
            self.input_msg4.fill(msg4)

        if fee is not None:
            self.input_fee.fill(str(fee))

        return self

    def fill_send_type(
        self,
        send_email: bool | None = None,
        send_sms: bool | None = None,
        email: str | None = None,
        sms: int | None = None,
    ) -> Self:
        self.component_send_type.fill_send_type(send_email, send_sms, email, sms)
        return self


class SendPayslipComponent:
    def __init__(self, form_payslip: Locator):
        self.button_send: Locator = form_payslip.locator("button#SendtoCustomet")

    def validate(self, timeout_ms: int) -> None:
        expect(self.button_send).to_be_enabled(timeout=timeout_ms)

    def send(self) -> None:
        try:
            expect(self.button_send).to_be_enabled(timeout=_EXPECT_TIMEOUT)
        except AssertionError as e:
            raise SrsWebPayslipButtonDisabledError(
                "Tried to send payslip, but send payslip button is disabled"
            ) from e

        with self.button_send.page.expect_event("dialog") as dialog_info:
            self.button_send.click()

        dialog: Dialog = dialog_info.value
        dialog.dismiss()

        if "Payslip has been sent" not in dialog.message:
            raise SrsWebPayslipSendError(dialog.message)


class ResendPayslipComponent:
    def __init__(self, form_payslip: Locator):
        self.button_resend: Locator = form_payslip.locator("button#ResendPayslip")

    def validate(self, timeout_ms: int) -> None:
        expect(self.button_resend).to_be_enabled(timeout=timeout_ms)

    def resend(self) -> None:
        try:
            expect(self.button_resend).to_be_enabled(timeout=_EXPECT_TIMEOUT)
        except AssertionError as e:
            raise SrsWebPayslipButtonDisabledError(
                "Tried to resend payslip, but resend payslip button is disabled"
            ) from e

        with self.button_resend.page.expect_event("dialog") as dialog_info:
            self.button_resend.click()

        dialog: Dialog = dialog_info.value
        dialog.dismiss()

        if "Payslip has been sent" not in dialog.message:
            raise SrsWebPayslipResendError(dialog.message)


class GeneratePayslipComponent:
    def __init__(self, form_payslip: Locator):
        self.button_generate: Locator = form_payslip.locator("button#GeneratePayslip")

    def validate(self, timeout_ms: int) -> None:
        expect(self.button_generate).to_be_enabled(timeout=timeout_ms)

    def generate_payslip(self) -> "PrintPayslipPage":
        try:
            expect(self.button_generate).to_be_enabled(timeout=_EXPECT_TIMEOUT)
        except AssertionError as e:
            raise SrsWebPayslipButtonDisabledError(
                "Tried to generate payslip, but generate payslip button is disabled"
            ) from e

        with self.button_generate.page.context.expect_page(
            timeout=_EXPECT_TIMEOUT
        ) as new_page_info:
            self.button_generate.click()

        new_page = new_page_info.value
        new_page.wait_for_load_state("load")
        new_page.set_viewport_size({"width": 1920, "height": 1080})

        return PrintPayslipPage(new_page)


class ExistingPayslipPage(BasePayslipPage):
    def _state_elements(self) -> None:
        self.component_send_type: PayslipSendTypeComponent = PayslipSendTypeComponent(
            self.form_payslip
        )
        self.component_resend: ResendPayslipComponent = ResendPayslipComponent(
            self.form_payslip
        )
        self.table_installments: Locator = self.form_payslip.locator(
            "table.collTableBorder#mainTable"
        )
        self.tr_installment: Locator = self.table_installments.locator("tr")

    def installments(self) -> list[Installment]:
        installments: list[Installment] = []

        for tr in self.tr_installment.all():
            installments.append(Installment(tr))

        return installments

    def _state_validate(self, timeout_ms: int) -> None:
        expect(self.tr_installment.first).to_be_visible(timeout=timeout_ms)

    def fill_send_type(
        self,
        send_email: bool | None = None,
        send_sms: bool | None = None,
        email: str | None = None,
        sms: int | None = None,
    ) -> Self:
        self.component_send_type.fill_send_type(send_email, send_sms, email, sms)
        return self

    def is_resend_enabled(self) -> bool:
        return self.component_resend.button_resend.is_enabled()

    def try_resend(self) -> Self:
        self.component_resend.resend()
        return self


class GenSendPayslipPage(BasePayslipPage):
    def _state_elements(self):
        self.component_generate: GeneratePayslipComponent = GeneratePayslipComponent(
            self.form_payslip
        )
        self.component_send: SendPayslipComponent = SendPayslipComponent(
            self.form_payslip
        )
        self.component_send_type: PayslipSendTypeComponent = PayslipSendTypeComponent(
            self.form_payslip
        )

    def _state_validate(self, timeout_ms: int) -> None:
        self.component_generate.validate(timeout_ms)
        self.component_send.validate(timeout_ms)

    def send(self) -> "ResendPayslipPage":
        self.component_send.send()
        return ResendPayslipPage(self.page)

    def generate_payslip(self) -> tuple[Self, "PrintPayslipPage"]:
        return self, self.component_generate.generate_payslip()

    def fill_send_type(
        self,
        send_email: bool | None = None,
        send_sms: bool | None = None,
        email: str | None = None,
        sms: int | None = None,
    ) -> Self:
        self.component_send_type.fill_send_type(send_email, send_sms, email, sms)
        return self


class GenResendPayslipPage(BasePayslipPage):
    def _state_elements(self):
        self.component_generate: GeneratePayslipComponent = GeneratePayslipComponent(
            self.form_payslip
        )
        self.component_resend: ResendPayslipComponent = ResendPayslipComponent(
            self.form_payslip
        )
        self.component_send_type: PayslipSendTypeComponent = PayslipSendTypeComponent(
            self.form_payslip
        )

    def _state_validate(self, timeout_ms: int) -> None:
        self.component_generate.validate(timeout_ms)
        self.component_resend.validate(timeout_ms)

    def resend(self) -> Self:
        self.component_resend.resend()
        return self

    def generate_payslip(self) -> tuple[Self, "PrintPayslipPage"]:
        return self, self.component_generate.generate_payslip()

    def fill_send_type(
        self,
        send_email: bool | None = None,
        send_sms: bool | None = None,
        email: str | None = None,
        sms: int | None = None,
    ) -> Self:
        self.component_send_type.fill_send_type(send_email, send_sms, email, sms)
        return self


class ResendPayslipPage(BasePayslipPage):
    def _state_elements(self):
        self.component_resend: ResendPayslipComponent = ResendPayslipComponent(
            self.form_payslip
        )
        self.component_send_type: PayslipSendTypeComponent = PayslipSendTypeComponent(
            self.form_payslip
        )

    def _state_validate(self, timeout_ms: int) -> None:
        self.component_resend.validate(timeout_ms)

    def resend(self) -> Self:
        self.component_resend.resend()
        return self

    def fill_send_type(
        self,
        send_email: bool | None = None,
        send_sms: bool | None = None,
        email: str | None = None,
        sms: int | None = None,
    ) -> Self:
        self.component_send_type.fill_send_type(send_email, send_sms, email, sms)
        return self


class PrintPayslipPage(SrsWebPage):
    def _elements(self) -> None:
        page = self.page
        self.button_print: Locator = page.locator("button[name='Printbtn']")

    def _validate(self, timeout_ms: int) -> None:
        expect(self.button_print).to_be_visible(timeout=timeout_ms)

    def as_pdf(self) -> bytes:
        block_time = time.monotonic_ns()
        context = self.page.context

        context.add_init_script(f"""
        (() => {{
            if (window.__DISABLE_PRINT_CLOSE_BLOCKING_{block_time}__) return;

            window.__OLD_PRINT_{block_time}__ = window.print;
            window.__OLD_CLOSE_{block_time}__ = window.close;

            window.print = () => {{
                console.log('window.print() was called and blocked.');
            }};
            window.close = () => {{
                console.log('window.close() was called and blocked.');
            }};
        }})();
        """)

        with context.expect_page() as new_page_info:
            self.button_print.click()

        context.add_init_script(f"""
        (() => {{
            window.__DISABLE_PRINT_CLOSE_BLOCKING_{block_time}__ = true;

            if (window.__OLD_PRINT_{block_time}__) (() => {{ window.print = window.__OLD_PRINT_{block_time}__; }})();
            if (window.__OLD_CLOSE_{block_time}__) (() => {{ window.close = window.__OLD_CLOSE_{block_time}__; }})();
        }})();
        """)

        pdf_page = new_page_info.value
        pdf_page.wait_for_load_state("domcontentloaded")
        time.sleep(2)
        pdf_bytes = pdf_page.pdf()
        pdf_page.close()

        return pdf_bytes
