import logging
import time

from playwright.sync_api import expect
from bsc_rpa_core.logs import log_func_call
from bsc_rpa_adapter_playwright import PlaywrightSession, select_option_by_text_start

from .pages import (
    LoginUserPage,
    LoginPasswordPage,
    HomePage,
    ChooseDealerPage,
    SimuladorPage,
    SimuladorStep1Page,
    SimuladorStep2Page,
    SimuladorStep3Page,
    SimuladorStep4Page,
    SimuladorStep5Page,
    PreApprovalPage,
)
from .errors import ChdInvalidCredentials, ChdInvalidSimuladorData, ChdNoConditionsFound

logger = logging.getLogger(__name__)


class ChdNavigator:
    def __init__(self, chd_url: str, session: PlaywrightSession) -> None:
        # self._chd_url = chd_url
        session.goto(chd_url)
        self.session = session

    def wait_load(
        self, timeout: float | None = None, padding: float = 1, filling: float = 1.3
    ):
        "Waits for div.overlayLoad not to be present in page"
        div_overlayload = self.session.page.locator("div.overlayLoad")
        time.sleep(padding)
        div_overlayload.first.wait_for(timeout=timeout, state="detached")
        time.sleep(filling)
        div_overlayload.first.wait_for(timeout=timeout, state="detached")
        time.sleep(padding)

    def uncheck_enabled_checkboxes(self):
        checkbox_checked_enabled = self.session.page.get_by_role(
            "checkbox", checked=True, disabled=False
        )
        while checkbox_checked_enabled.count() > 0:
            checkbox_checked_enabled.uncheck()

    @log_func_call(logger, logging.INFO)
    def login(self, username, password):
        login_user_page = LoginUserPage(self.session)
        login_user_page.input_username.fill(username)
        login_user_page.button_next.click()
        self.wait_load()
        if login_user_page.div_alert.count() > 0:
            raise ChdInvalidCredentials(
                f"Alert in ChdNavigator.login: '{login_user_page.div_alert.inner_text()}'"
            )

        login_password_page = LoginPasswordPage(self.session)
        login_password_page.input_password.fill(password)
        login_password_page.button_enter.click()
        login_password_page.load_spinner.first.wait_for(state="detached")
        self.wait_load()
        if login_password_page.div_alert.count() > 0:
            raise ChdInvalidCredentials(
                f"Alert in ChdNavigator.login: '{login_password_page.div_alert.inner_text()}'"
            )

        self.wait_load()

    @log_func_call(logger)
    def go_to_simulador(self):
        home_page = HomePage(self.session)
        home_page.button_simulador.click()
        self.wait_load()

    @log_func_call(logger)
    def change_dealer(self):
        page = SimuladorPage(self.session)
        page.a_dealer_label.click()

    @log_func_call(logger)
    def choose_dealer(self, dealer: str):
        choose_dealer_page = ChooseDealerPage(self.session)
        select_option_by_text_start(choose_dealer_page.select_dealer, dealer)

        try:
            expect(choose_dealer_page.button_confirm).not_to_be_disabled(timeout=50)
        except AssertionError as e:
            raise RuntimeError(
                "Confirm button is disabled in ChdNavigator.choose_dealer"
            ) from e

        choose_dealer_page.button_confirm.click()
        with self.session.page.expect_event("dialog", lambda dialog: dialog.accept()):
            pass
        self.wait_load()

    def assert_in_4_step_simulador(self):
        page = SimuladorPage(self.session)
        assert page.max_step >= 4

    @log_func_call(logger)
    def fill_simulador_step1(
        self, model_year: str, manufacturer_year: str, model: str, version: str
    ):
        page = SimuladorStep1Page(self.session)
        select_option_by_text_start(page.select_model_year, model_year)
        self.wait_load()
        select_option_by_text_start(page.select_manufacturer_year, manufacturer_year)
        self.wait_load()
        select_option_by_text_start(page.select_model, model)
        self.wait_load()
        select_option_by_text_start(page.select_version, version)
        page.button_next.click()

        if page.is_invalid.count() > 0:
            raise ChdInvalidSimuladorData(
                f"Invalid data in Simulador Step 1: {'|'.join(page.invalid_feedback.all_inner_texts())}"
            )

        self.wait_load()

    @log_func_call(logger)
    def fill_simulador_step2(
        self,
        client_document: str,
        finance_type: str,
        vehicle_value: str,
        entry_value: str,
        uncheck_checkboxes: bool = True,
    ):
        page = SimuladorStep2Page(self.session)

        page.input_client_document.fill(client_document)
        self.wait_load()
        select_option_by_text_start(page.select_finance_type, finance_type)
        self.wait_load()
        if uncheck_checkboxes:
            self.uncheck_enabled_checkboxes()
        page.input_vehicle_value.fill(vehicle_value)
        page.input_entry_value.fill(entry_value)
        page.button_calculate.click()

        if page.is_invalid.count() > 0:
            raise ChdInvalidSimuladorData(
                f"Invalid data in Simulador Step 2: {'|'.join(page.invalid_feedback.all_inner_texts())}"
            )

        self.wait_load()

    @log_func_call(logger)
    def fill_simulador_step3(self, prazo: str, uncheck_checkboxes: bool = True):
        page = SimuladorStep3Page(self.session)

        if uncheck_checkboxes:
            self.uncheck_enabled_checkboxes()

        page.button_next.click()
        if page.is_invalid.count() > 0:
            raise ChdInvalidSimuladorData(
                f"Invalid data in Simulador Step 3: {'|'.join(page.invalid_feedback.all_inner_texts())}"
            )

        self.wait_load()
        if page.checkbox_prazo(prazo).count() > 0:
            page.checkbox_prazo(prazo).check()
            self.wait_load()
            if page.div_alert.count() > 0:
                raise ChdNoConditionsFound(
                    f"No conditions found for given simulation: {'|'.join(page.div_alert.all_inner_texts())}"
                )

        page.td_condition_term(prazo).click()
        self.wait_load()

    @log_func_call(logger)
    def pre_aprovar(self, client_income: str, additional_income: str) -> str:
        page_step_4 = SimuladorStep4Page(self.session)
        page_step_4.button_pre_aprovar.click()
        self.wait_load()

        page_step_5 = SimuladorStep5Page(self.session)
        page_step_5.input_client_income.fill(client_income)
        page_step_5.input_additional_income.fill(additional_income)
        page_step_5.button_pre_aprovar.click()
        self.wait_load()

        page_preapproval = PreApprovalPage(self.session)
        result = page_preapproval.div_text_preapprove.inner_text()
        page_preapproval.button_close.click()
        return result
