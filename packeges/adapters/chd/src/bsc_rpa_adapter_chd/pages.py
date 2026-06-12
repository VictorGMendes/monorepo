from abc import abstractmethod
import logging

from playwright.sync_api import expect, Locator
from bsc_rpa_adapter_playwright import PlaywrightPage

from .errors import ChdValidationError

logger = logging.getLogger(__name__)

# Base ChdPage


class ChdPage(PlaywrightPage):
    @abstractmethod
    def _validate(self, timeout_ms: int | None = None) -> None: ...

    def validate(self, timeout_ms: int | None = None):
        try:
            self._validate(timeout_ms)
        except AssertionError as e:
            raise ChdValidationError(f"{type(self)} validation failed.") from e


# CHD Pages


class LoginUserPage(ChdPage):
    def _elements(self) -> None:
        page = self.session.page
        self.input_username = page.locator("form input[name='username']")
        self.button_next = page.locator("form button")
        self.div_alert = page.locator("div.alert")

    def _validate(self, timeout_ms: int | None = None) -> None:
        expect(self.input_username).to_be_editable(timeout=timeout_ms)


class LoginPasswordPage(ChdPage):
    def _elements(self) -> None:
        page = self.session.page
        self.input_password = page.locator("form input[name='password']")
        self.button_enter = page.locator("form button")
        self.div_alert = page.locator("div.alert")
        self.load_spinner = page.locator("i.fa-spinner")

    def _validate(self, timeout_ms: int | None = None) -> None:
        expect(self.input_password).to_be_editable(timeout=timeout_ms)


class HomePage(ChdPage):
    def _elements(self) -> None:
        page = self.session.page
        self.overlay_load = page.locator("div.overlayLoad")
        self.button_simulador = page.locator("a[id='simulador']")

    def _validate(self, timeout_ms: int | None = None) -> None:
        expect(self.overlay_load).to_have_count(0, timeout=timeout_ms)


class ChooseDealerPage(ChdPage):
    def _elements(self) -> None:
        page = self.session.page
        self.popup_title = page.locator("div.modal-content div.modal-header").and_(
            page.get_by_text("Escolha a concessionária")
        )
        self.select_dealer = page.locator(
            "div.modal-content div.modal-body select[name='dealer']"
        )
        self.button_confirm = page.locator(
            "div.modal-content div.modal-footer button[data-cy='modalButton']"
        )
        self.button_cancel = page.locator(
            "div.modal-content div.modal-footer button[data-cy='modalButtonCancel']"
        )

    def _validate(self, timeout_ms: int | None = None) -> None:
        expect(self.popup_title).to_be_visible(timeout=timeout_ms)


class SimuladorPage(ChdPage):
    def _elements(self) -> None:
        page = self.session.page
        self.div_step = page.locator("ul.steps li div.step")
        self.div_step_on = page.locator("ul.steps li.step-on div.step")
        self.is_invalid = page.locator(".is-invalid")
        self.invalid_feedback = page.locator(".invalid-feedback")
        self.a_dealer_label = page.locator("a.dealerLabel")

    @property
    def max_step(self) -> int:
        return max([int(step) for step in self.div_step.all_inner_texts()])

    @property
    def current_step(self) -> int:
        return max([int(step) for step in self.div_step_on.all_inner_texts()])

    def _validate(self, timeout_ms: int | None = None) -> None:
        expect(self.div_step).to_be_visible(timeout=timeout_ms)


class SimuladorStep1Page(SimuladorPage):
    def _elements(self) -> None:
        super()._elements()
        page = self.session.page

        self.select_model_year = page.locator("select[name='modelYear']")
        self.select_manufacturer_year = page.locator("select[name='manufacturerYear']")
        self.select_model = page.locator("select[name='model']")
        self.select_version = page.locator("select[name='version']")

        self.button_next = page.locator("button[data-cy='submitStepOne']")

    def _validate(self, timeout_ms: int | None = None) -> None:
        super()._validate(timeout_ms)
        assert self.current_step == 1


class SimuladorStep2Page(SimuladorPage):
    def _elements(self) -> None:
        super()._elements()
        page = self.session.page

        self.input_client_document = page.locator("input[name='clientDocument']")
        self.select_finance_type = page.locator("select[name='financeType']")
        self.input_vehicle_value = page.locator("input[name='vehicleValue']")
        self.input_entry_value = page.locator("input[name='entryValue']")

        self.button_calculate = page.locator("button[data-cy='calcular']")

    def _validate(self, timeout_ms: int | None = None) -> None:
        super()._validate(timeout_ms)
        assert self.current_step == 2


class SimuladorStep3Page(SimuladorPage):
    def _elements(self) -> None:
        super()._elements()
        page = self.session.page

        self.div_alert = page.locator("div.alert-danger")

        self.button_next = page.locator("button.btn-primary")

    def checkbox_prazo(self, prazo: str) -> Locator:
        page = self.session.page
        return page.locator(f'label[for="{prazo}"').locator("div.custom-checkbox")

    def td_condition_term(self, prazo: str) -> Locator:
        page = self.session.page
        return page.locator(
            f'tr.new-simulation[data-cy="condition-{prazo}"] td.item-r[data-cy="condition-{prazo}-term"]'
        )

    def _validate(self, timeout_ms: int | None = None) -> None:
        super()._validate(timeout_ms)
        assert self.current_step == 3


class SimuladorStep4Page(SimuladorPage):
    def _elements(self) -> None:
        super()._elements()
        page = self.session.page

        self.button_pre_aprovar = page.locator("button.btn-primary").and_(
            page.get_by_text("Pré-aprovar")
        )
        self.button_salvar = page.locator("button.btn-primary").and_(
            page.get_by_text("Salvar")
        )
        self.button_nova_sim = page.locator("button.btn-primary").and_(
            page.get_by_text("Nova Simulação")
        )

    def _validate(self, timeout_ms: int | None = None) -> None:
        super()._validate(timeout_ms)
        assert self.current_step == 4


class SimuladorStep5Page(SimuladorPage):
    def _elements(self) -> None:
        super()._elements()
        page = self.session.page

        self.input_client_income = page.locator("input[name='clientIncome']")
        self.input_additional_income = page.locator("input[name='additionalIncome']")
        self.button_pre_aprovar = page.locator(
            "button[data-cy='submitPreApprovalStep']"
        )

    def _validate(self, timeout_ms: int | None = None) -> None:
        super()._validate(timeout_ms)
        assert self.current_step == 5


class PreApprovalPage(ChdPage):
    def _elements(self) -> None:
        page = self.session.page
        self.h5_header_preapprove = page.locator("div.modal-header h5").and_(
            page.get_by_text("Pré-aprovação do financiamento")
        )
        self.div_text_preapprove = page.locator("div.modal-body")
        self.button_send_prod = page.locator("div.modal-footer button.btn-primary")
        self.button_close = page.locator("div.modal-footer button.btn-secondary")

    def _validate(self, timeout_ms: int | None = None) -> None:
        expect(self.h5_header_preapprove).to_be_visible(timeout=timeout_ms)
