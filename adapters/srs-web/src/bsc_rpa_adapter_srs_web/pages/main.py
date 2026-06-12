from typing import Self, Literal

from playwright.sync_api import expect, Locator, FrameLocator

from ..errors import (
    SrsWebCredentialsError,
    SrsWebAdhocSearchError,
)

from .base import _EXPECT_TIMEOUT, _regex_eq, expect_dialog_or, SrsWebPage, DialogResult
from .payslip import MainPayslipPage


class LoginPage(SrsWebPage):
    def _elements(self) -> None:
        page = self.page
        self.input_user: Locator = page.locator("input#User_ID")
        self.input_pass: Locator = page.locator("input#TxtPWD")
        self.select_country: Locator = page.locator("select#showCountryid")
        self.link_login: Locator = page.locator("a[onclick*='fnValidateLocked']")

    def _validate(self, timeout_ms: int) -> None:
        expect(self.input_user).to_be_editable(timeout=timeout_ms)

    def login(
        self, username: str, password: str, country: Literal["BRAZIL"]
    ) -> "HomePage":
        self.input_user.click()
        self.input_user.fill(username)

        self.input_pass.click()
        self.input_pass.fill(password)

        def other_waiter(timeout_ms: int) -> bool:
            try:
                expect(self.select_country.get_by_text(country)).to_be_attached(
                    timeout=timeout_ms
                )
                return True
            except AssertionError:
                return False

        with expect_dialog_or(
            self.page,
            dialog_predicate=lambda dialog: "Invalid" in dialog.message,
            other_waiter=other_waiter,
        ) as result_info:
            self.input_pass.press("Tab")

        result = result_info.value
        assert result is not None

        match result.kind:
            case "dialog":
                assert isinstance(result, DialogResult)
                raise SrsWebCredentialsError(result.dialog.message)

            case "other":
                pass

            case "timeout":
                raise SrsWebCredentialsError(
                    f"Country {country!r} not available for user {username!r}"
                )

        self.select_country.select_option(label=country)
        self.link_login.click()

        return HomePage(self.page)


class HomePage(SrsWebPage):
    def _elements(self) -> None:
        page = self.page
        self.frame_screencode: FrameLocator = page.frame_locator("iframe#idScreenCode")
        self.input_screencode: Locator = self.frame_screencode.locator(
            "input[name='lbxScreenCode']"
        )
        self.button_go: Locator = self.frame_screencode.locator(
            "button[name='btnScreenMove']", has_text=_regex_eq("Go")
        )

    def _validate(self, timeout_ms: int) -> None:
        expect(self.input_screencode).to_be_editable(timeout=timeout_ms)

    def goto_adhoc_search(self) -> "AdhocSearchPage":
        self.input_screencode.fill("ADS")
        self.button_go.click()
        return AdhocSearchPage(self.page)


class AdhocSearchPage(SrsWebPage):
    __WAIT_FOR_RESULT_TIMEOUT = 15_000  # ms
    __MAX_SEARCH_TRIES = 3

    def _elements(self) -> None:
        page = self.page
        self.form_search: Locator = page.locator("form[name='SearchForm']")
        self.td_header: Locator = self.form_search.locator(
            "td.clsToolBarCell", has_text=_regex_eq("Adhoc Search")
        )
        self.input_loanid: Locator = self.form_search.locator("input#txtLoanId")
        self.button_search: Locator = self.form_search.locator(
            "button[name='btnSearch']"
        )
        self.table_results: Locator = self.form_search.locator("table.collTableBorder")
        self.link_result: Locator = self.table_results.locator(
            "tr:not(.tdHeader) > td:nth-child(1) > a"
        )

    def link_result_with_loanid(self, loanid: str) -> Locator:
        return self.link_result.filter(has_text=_regex_eq(loanid))

    def _validate(self, timeout_ms: int) -> None:
        expect(self.td_header).to_be_visible(timeout=timeout_ms)

    def clear_form(self) -> Self:
        self.input_loanid.clear()
        return self

    def search_by_loanid(self, loanid: str) -> tuple[Self, "ContractPage"]:
        self.clear_form()

        link_result = self.link_result_with_loanid(loanid)

        counter: int = 0
        while not link_result.is_visible():
            self.clear_form()
            self.input_loanid.fill(loanid)
            self.button_search.click()

            try:
                link_result.wait_for(
                    timeout=self.__WAIT_FOR_RESULT_TIMEOUT, state="visible"
                )
                break
            except TimeoutError:
                if counter >= self.__MAX_SEARCH_TRIES:
                    raise SrsWebAdhocSearchError(
                        f"Contract with loanid={loanid} not found"
                    )
            counter += 1

        with self.page.context.expect_page(timeout=_EXPECT_TIMEOUT) as new_page_info:
            link_result.click()

        new_page = new_page_info.value
        new_page.wait_for_load_state("load")
        new_page.set_viewport_size({"width": 1920, "height": 1080})
        return (self, ContractPage(new_page))


class ContractPage(SrsWebPage):
    def _elements(self) -> None:
        page = self.page
        self.form_telecall: Locator = page.locator("form[name='Telecall']")
        self.td_header: Locator = self.form_telecall.locator(
            "td.clsToolBarCell", has_text=_regex_eq("Contact Recording")
        )
        self.button_payslip: Locator = self.form_telecall.locator(
            "button[name='butPaySlip']"
        )
        self.td_dpd_header: Locator = self.form_telecall.locator(
            "td.colHeader", has_text=_regex_eq("DPD")
        )
        self.td_dpd_value: Locator = self.form_telecall.locator(
            "tr", has=self.td_dpd_header
        ).locator("td.collNumeric")

    def _validate(self, timeout_ms: int) -> None:
        expect(self.td_header).to_be_visible(timeout=timeout_ms)

    def goto_to_payslip(self) -> tuple[Self, "MainPayslipPage"]:
        with self.page.context.expect_page(timeout=_EXPECT_TIMEOUT) as new_page_info:
            self.button_payslip.click()

        new_page = new_page_info.value
        new_page.wait_for_load_state("load")
        new_page.set_viewport_size({"width": 1920, "height": 1080})
        return (self, MainPayslipPage(new_page))

    def get_dpd(self) -> int:
        return int(self.td_dpd_value.inner_text())
