from copy import deepcopy
from time import sleep
from datetime import datetime
import re
from typing import Literal, Self
from abc import ABC, abstractmethod
import logging

from playwright.sync_api import expect, Locator, Page

from .errors import (
    AstraCredentialsError,
    AstraValidationError,
    AstraDealerNotFoundError,
    AstraOpenFinancialsError,
    AstraReportingPeriodError,
    MissingFinancialFieldsError,
)

logger = logging.getLogger(__name__)

# Types, constants and utils

type CountryID = Literal["CO", "CL", "PE"]
type ReportingPeriodAttributes = Literal["Unaudited", "Internal Oper. Stmt."]

_COUNTRY_NAME: dict[CountryID, str] = {"CO": "Colombia", "CL": "Chile", "PE": "Peru"}
_EXPECT_TIMEOUT = 30_000  # milliseconds
_VALIDATE_TIMEOUT = 30_000  # milliseconds


def _regex_eq(text: str) -> re.Pattern[str]:
    return re.compile(r"^\s*" + re.escape(text) + r"\s*$", re.IGNORECASE)


# Base AstraPage


class AstraPage(ABC):
    @abstractmethod
    def _validate(self, timeout_ms: int) -> None: ...

    def __init__(self, page: Page, validate_at_init: bool = True) -> None:
        self.page: Page = page
        self._elements()
        if validate_at_init:
            self.validate()

    @abstractmethod
    def _elements(self) -> None:
        """Define this page's elements. Called on `self.__init__` before `self.validate`"""

    def validate(self, timeout_ms: int | None = None):
        if timeout_ms is None:
            timeout_ms = _VALIDATE_TIMEOUT
        try:
            self._validate(timeout_ms)
        except AssertionError as e:
            raise AstraValidationError(f"{type(self)} validation failed.") from e


# CHD Pages


class LoginPage(AstraPage):
    def _elements(self) -> None:
        page = self.page
        self.input_user: Locator = page.locator("input#username")
        self.input_pass: Locator = page.locator("input#password")
        self.button_login: Locator = page.locator("button#submitlogin")
        self.span_login_error: Locator = page.locator("span.loginErrorMessage")

    def _validate(self, timeout_ms: int) -> None:
        expect(self.input_user).to_be_editable(timeout=timeout_ms)

    def login(self, username: str, password: str) -> "SearchPage":
        self.input_user.fill(username)
        self.input_pass.fill(password)
        self.button_login.click()

        expect(self.button_login).not_to_contain_text(
            "processing", timeout=_EXPECT_TIMEOUT
        )

        logged_page = LoggedPage(self.page, validate_at_init=False)

        expect(self.span_login_error.or_(logged_page.link_astra).first).to_be_visible(
            timeout=_EXPECT_TIMEOUT
        )

        if self.span_login_error.is_visible():
            raise AstraCredentialsError(
                " | ".join(self.span_login_error.all_text_contents())
            )

        self.page.wait_for_load_state("load")
        logged_page.validate()

        return SearchPage(self.page)


class LoggedPage(AstraPage):
    def _elements(self) -> None:
        page = self.page
        self.link_astra: Locator = page.locator("a[title='ASTRA System']")

    def _validate(self, timeout_ms: int) -> None:
        expect(self.link_astra).to_be_visible(timeout=timeout_ms)


class SearchPage(AstraPage):
    def _elements(self) -> None:
        page = self.page
        self.link_search: Locator = page.locator("li#searchMenuDropdown > a").first
        self.input_search: Locator = page.locator("input#clientsearchId")

    def div_result(self, dealer_id: str, country_id: CountryID) -> Locator:
        page = self.page
        country_name = _COUNTRY_NAME[country_id]
        return (
            page.locator("li#searchMenuDropdown div")
            .filter(
                has=page.locator(
                    ":scope > div:nth-child(1) > span:nth-child(2)",
                    has_text=_regex_eq(dealer_id),
                )
            )
            .filter(
                has=page.locator(
                    ":scope > div:nth-child(2) > span:nth-child(1)",
                    has_text=_regex_eq(country_name),
                )
            )
        )

    def _validate(self, timeout_ms: int) -> None:
        expect(self.link_search).to_be_visible(timeout=timeout_ms)

    def search_dealer(
        self, dealer_id: str, country_id: CountryID
    ) -> "ClientSidebarPage":
        self.link_search.click()
        self.input_search.fill(dealer_id)
        div_result = self.div_result(dealer_id, country_id)

        try:
            expect(div_result).to_be_visible(timeout=_EXPECT_TIMEOUT)
        except AssertionError:
            raise AstraDealerNotFoundError(
                f"Dealer with ID '{dealer_id}' and country '{country_id}' not found."
            )

        div_result.click()
        ClientFoundPage(self.page)  # Validate client found page opened
        self.page.wait_for_load_state("load")

        return ClientSidebarPage(self.page)


class ClientFoundPage(AstraPage):
    def _elements(self) -> None:
        page = self.page
        self.link_main: Locator = page.locator("a#main")

    def _validate(self, timeout_ms: int) -> None:
        expect(self.link_main).to_be_visible(timeout=timeout_ms)


class ClientSidebarPage(AstraPage):
    __N_TRIES_TO_OPEN_FINANCIALS = 6
    __SLEEP_TRIES_TO_OPEN_FINANCIALS = 1  # seconds

    def _elements(self) -> None:
        page = self.page
        self.link_financials: Locator = page.locator(
            "a", has_text=_regex_eq("Financials")
        )
        self.li_financials_open: Locator = page.locator(
            "li.open", has=self.link_financials
        )

    def link_section(
        self,
        section_name: Literal["Point of Entry", "Balance Sheet", "Income Statement"],
    ) -> Locator:
        page = self.page
        return page.locator("a", has_text=_regex_eq(section_name))

    def _validate(self, timeout_ms: int) -> None:
        expect(self.link_financials).to_be_visible(timeout=timeout_ms)

    def _goto_financials_section(
        self,
        section_name: Literal["Point of Entry", "Balance Sheet", "Income Statement"],
    ) -> "FinancialsSectionPage":
        self.link_financials.scroll_into_view_if_needed()

        for _ in range(self.__N_TRIES_TO_OPEN_FINANCIALS):
            if self.li_financials_open.is_visible():
                break
            self.link_financials.click()
            sleep(self.__SLEEP_TRIES_TO_OPEN_FINANCIALS)
        else:
            raise AstraOpenFinancialsError(
                f"Could not open Financials section {section_name!r} in Astra."
            )

        self.link_section(section_name).click()
        financials_section_page = FinancialsSectionPage(self.page)
        self.page.wait_for_load_state("load")

        return financials_section_page

    def goto_point_of_entry(self) -> "PointOfEntryPage":
        self._goto_financials_section("Point of Entry")
        return PointOfEntryPage(self.page)

    def goto_balance_sheet(self) -> "BalanceSheetPage":
        self._goto_financials_section("Balance Sheet")
        return BalanceSheetPage(self.page)

    def goto_income_statement(self) -> "IncomeStatementPage":
        self._goto_financials_section("Income Statement")
        return IncomeStatementPage(self.page)


class FinancialsSectionPage(AstraPage):
    def _elements(self) -> None:
        page = self.page
        self.strong_reporting_period: Locator = page.locator(
            "strong", has_text=_regex_eq("Reporting Period")
        )

    def _validate(self, timeout_ms: int) -> None:
        expect(self.strong_reporting_period).to_be_visible(timeout=timeout_ms)

    def sidebar(self) -> ClientSidebarPage:
        return ClientSidebarPage(self.page)


class PointOfEntryPage(AstraPage):
    __BIG_SLEEP = 5  # seconds
    __SMALL_SLEEP = 1  # seconds
    __TIMEOUT_AFTER_SAVE = 150_000  # milliseconds
    __FILL_FINANCIALS_MAX_RETRIES = 5

    def _elements(self) -> None:
        page = self.page
        self.select_reporting_period: Locator = page.locator("select#ratingPeriod")
        self.button_new_period: Locator = page.locator("button#btnNewPeriod")
        self.li_point_of_entry: Locator = page.locator(
            "div#breadCrumbRow li", has_text=_regex_eq("point of entry")
        )
        self.div_account_description: Locator = page.locator(
            "div#contentContainer div", has_text=_regex_eq("Account Description")
        )

        self.viewport_financial_table: Locator = page.locator(
            "cdk-virtual-scroll-viewport"
        )
        self.div_viewport_row: Locator = page.locator(
            "cdk-virtual-scroll-viewport > div > div"
        )
        self.button_both: Locator = page.locator("button#btnBothView")
        self.button_save: Locator = page.locator("button#btnSave")
        self.div_loading: Locator = page.locator("div.loading-text")

    def input_field_mtd(self, field_name: str) -> Locator:
        page = self.page
        return self.viewport_financial_table.locator(
            "div",
            has=page.locator(
                ":scope > div > div > div:nth-child(3)", has_text=_regex_eq(field_name)
            ),
        ).locator(
            "div:nth-child(2) > div:nth-child(1)"
            "> div:nth-child(1) > div:nth-child(1)"
            "> input"
        )

    def input_field_ytd(self, field_name: str) -> Locator:
        page = self.page
        return self.viewport_financial_table.locator(
            "div",
            has=page.locator(
                ":scope > div > div > div:nth-child(3)", has_text=_regex_eq(field_name)
            ),
        ).locator(
            "div:nth-child(2) > div:nth-child(1)"
            "> div:nth-child(2) > div:nth-child(1)"
            "> input"
        )

    def _validate(self, timeout_ms: int) -> None:
        expect(self.li_point_of_entry).to_be_visible(timeout=timeout_ms)

    def create_reporting_period(
        self,
        new_period: datetime,
        country_id: CountryID,
        attributes: ReportingPeriodAttributes,
    ) -> Self:
        expect(self.select_reporting_period).to_have_text(
            re.compile(r".+"),
            timeout=_EXPECT_TIMEOUT,
        )

        last_reporting_period = datetime.strptime(
            self.select_reporting_period.inner_text().strip()[:10], "%d/%m/%Y"
        )

        if last_reporting_period == new_period:
            logger.info(
                f"New reporting period '{new_period.strftime('%d/%m/%Y')}' "
                f"is equal to last reporting period '{last_reporting_period.strftime('%d/%m/%Y')}'. "
                "Skipping creation of new reporting period"
            )
            return self

        if new_period < last_reporting_period:
            raise AstraReportingPeriodError(
                f"New reporting period '{new_period.strftime('%d/%m/%Y')}' "
                f"is older than last reporting period '{last_reporting_period.strftime('%d/%m/%Y')}'."
            )

        self.button_new_period.click()

        NewReportingPeriodPage(self.page).fill_and_save(
            new_period,
            country_id,
            attributes,
        )

        return self

    def fill_financials_both_and_save(
        self, financials_mtd_arg: dict[str, int], financials_ytd_arg: dict[str, int]
    ) -> Self:
        def try_fill_fields() -> tuple[bool, str]:
            financials_mtd = deepcopy(financials_mtd_arg)
            financials_ytd = deepcopy(financials_ytd_arg)

            sleep(self.__BIG_SLEEP)

            expect(self.div_account_description).to_be_visible(timeout=_EXPECT_TIMEOUT)

            self.button_both.click()
            sleep(self.__BIG_SLEEP)
            expect(self.div_viewport_row.first).to_be_visible(
                timeout=3 * _EXPECT_TIMEOUT
            )
            sleep(2 * self.__BIG_SLEEP)

            self.viewport_financial_table.evaluate("el => el.scrollTo(0, 0)")

            scroll_height: int = self.viewport_financial_table.evaluate(
                "el => el.scrollHeight"
            )
            client_height: int = self.viewport_financial_table.evaluate(
                "el => el.clientHeight"
            )
            scroll_top: int = self.viewport_financial_table.evaluate(
                "el => el.scrollTop"
            )

            max_scrolls = 3 * (
                scroll_height / client_height
            )  # just in case, to avoid infinite loop
            scrolls = 0

            while (
                scroll_top + client_height < scroll_height
            ) and scrolls <= max_scrolls:
                fin_mtd_cpy = financials_mtd.copy()
                fin_ytd_cpy = financials_ytd.copy()

                for field_name, field_value in fin_mtd_cpy.items():
                    field_locator = self.input_field_mtd(field_name)
                    if field_locator.is_visible():
                        field_locator.fill(str(field_value))
                        financials_mtd.pop(field_name)
                        # sleep(_SMALL_SLEEP)

                for field_name, field_value in fin_ytd_cpy.items():
                    field_locator = self.input_field_ytd(field_name)
                    if field_locator.is_visible():
                        field_locator.fill(str(field_value))
                        financials_ytd.pop(field_name)
                        # sleep(_SMALL_SLEEP)

                sleep(self.__SMALL_SLEEP)

                self.viewport_financial_table.evaluate(
                    "el => el.scrollTo(0, el.scrollTop + (el.clientHeight/2))"
                )

                sleep(self.__SMALL_SLEEP)

                client_height: int = self.viewport_financial_table.evaluate(
                    "el => el.clientHeight"
                )
                scroll_top: int = self.viewport_financial_table.evaluate(
                    "el => el.scrollTop"
                )
                scrolls += 1

            return (not financials_mtd) and (not financials_ytd), ", ".join(
                [field_name + " (MTD)" for field_name in financials_mtd.keys()]
                + [field_name + " (YTD)" for field_name in financials_ytd.keys()]
            )

        fill_fields_tries: int = 0
        all_financials_filled: bool = False
        missing_fields: str = ""
        while (not all_financials_filled) and (
            fill_fields_tries < self.__FILL_FINANCIALS_MAX_RETRIES
        ):
            all_financials_filled, missing_fields = try_fill_fields()
            if not all_financials_filled:
                self.page.reload(timeout=2 * _EXPECT_TIMEOUT)
            fill_fields_tries += 1

        if not all_financials_filled:
            raise MissingFinancialFieldsError(
                f"Could not fill financials: {missing_fields}"
            )

        self.button_save.click()

        sleep(self.__BIG_SLEEP)
        expect(self.div_loading).to_be_hidden(timeout=self.__TIMEOUT_AFTER_SAVE)

        expect(self.div_account_description).to_be_visible(timeout=_EXPECT_TIMEOUT)

        return self

    def sidebar(self) -> ClientSidebarPage:
        return ClientSidebarPage(self.page)


class NewReportingPeriodPage(AstraPage):
    __DEFAULT_KEYPRESS_DELAY = 50  # milliseconds
    __SLEEP = 5  # seconds

    def _elements(self) -> None:
        page = self.page
        self.input_period_date: Locator = page.locator("input#periodDate")
        self.select_statement_type: Locator = page.locator("select#templateId")
        self.select_attributes: Locator = page.locator("select#attributes")
        self.button_save: Locator = page.locator("div.modal-footer button.btn-default")

    def _validate(self, timeout_ms: int) -> None:
        expect(self.input_period_date).to_be_editable(timeout=timeout_ms)

    def fill_and_save(
        self,
        new_period: datetime,
        country_id: CountryID,
        attributes: ReportingPeriodAttributes,
    ) -> "PointOfEntryPage":
        sleep(self.__SLEEP)

        self.input_period_date.press_sequentially(
            new_period.strftime("%d/%m/%Y"), delay=self.__DEFAULT_KEYPRESS_DELAY
        )
        self.select_statement_type.focus()
        self.select_statement_type.select_option(label=f"GM{country_id}")
        self.select_attributes.focus()
        self.select_attributes.select_option(label=attributes)

        self.button_save.click()

        return PointOfEntryPage(self.page)


class BalanceSheetPage(AstraPage):
    def _elements(self) -> None:
        page = self.page
        self.li_balance_sheet: Locator = page.locator(
            "div#breadCrumbRow li", has_text=_regex_eq("balance sheet")
        )
        self.div_row: Locator = page.locator("div.period-body").locator("> div.row")

    def div_cell(self, row_label: str) -> Locator:
        page = self.page
        div_row_label = page.locator(
            ":scope > div:nth-child(1) > div:nth-child(1) > div:nth-child(1)",
            has_text=_regex_eq(row_label),
        )
        div_cell = self.div_row.filter(has=div_row_label).locator(
            "> div:nth-child(2) > div:nth-child(1) > div:nth-child(1)"
        )
        return div_cell

    def _validate(self, timeout_ms: int) -> None:
        expect(self.li_balance_sheet).to_be_visible(timeout=timeout_ms)

    def get_profit_loss(self) -> str:
        return self.div_cell("Net Profit or Loss").inner_text()

    def get_difference(self) -> str:
        return self.div_cell("DIFFERENCE").inner_text()

    def sidebar(self) -> ClientSidebarPage:
        return ClientSidebarPage(self.page)


class IncomeStatementPage(AstraPage):
    def _elements(self) -> None:
        page = self.page
        self.li_income_statement: Locator = page.locator(
            "div#breadCrumbRow li", has_text=_regex_eq("income statement")
        )
        self.div_row: Locator = page.locator("div.period-body").locator("> div.row")

    def div_cell(self, row_label: str) -> Locator:
        page = self.page
        div_row_label = page.locator(
            ":scope > div:nth-child(1) > div:nth-child(1) > div:nth-child(1)",
            has_text=_regex_eq(row_label),
        )
        div_cell = self.div_row.filter(has=div_row_label).locator(
            "> div:nth-child(2) > div:nth-child(1) > div:nth-child(1)"
        )
        return div_cell

    def _validate(self, timeout_ms: int) -> None:
        expect(self.li_income_statement).to_be_visible(timeout=timeout_ms)

    def get_profit_loss(self) -> str:
        return self.div_cell("Net Profit/(Loss)").inner_text()

    def sidebar(self) -> ClientSidebarPage:
        return ClientSidebarPage(self.page)
