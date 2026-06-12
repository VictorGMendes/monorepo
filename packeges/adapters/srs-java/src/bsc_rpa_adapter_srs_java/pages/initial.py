from jab_rpa.locator import LocatorNotFound
from jab_rpa import Locator

from ..errors import SrsJavaCredentialsError, SrsJavaLoginTimeoutError

from .base import SrsJavaPage, _STD_STATES, _WAIT_FOR_TIMEOUT, _WAIT_FOR_SLICE


class LoginPage(SrsJavaPage):
    def _locators(self) -> None:
        self.frm_login: Locator = self.driver.locator(
            f"internal_frame.modal.{_STD_STATES}[name~='Login']"
        )
        self.txt_userid: Locator = self.frm_login.locator(
            f"text.{_STD_STATES}[name~='USERID']"
        )
        self.txt_passwd: Locator = self.frm_login.locator(
            f"password_text.{_STD_STATES}[name~='PASSWD']"
        )
        self.btn_ok_login: Locator = self.frm_login.locator(
            f"push_button.{_STD_STATES}[name~='OK']"
        )

        # Appears on successful login
        self.frm_ack: Locator = self.driver.locator(
            f"internal_frame.modal.{_STD_STATES}[name~='Acknowledge']"
        )
        self.btn_ok_ack: Locator = self.frm_ack.locator(
            f"push_button.{_STD_STATES}[name~='OK']"
        )

        # Appears on failed login
        self.frm_forms: Locator = self.driver.locator(
            f"internal_frame.modal.{_STD_STATES}[name~='Forms']"
        )
        self.btn_ok_forms: Locator = self.frm_forms.locator(
            f"push_button.{_STD_STATES}[name~='OK']"
        )

    def _validate(self, timeout_ms: int, slice_ms: int) -> None:
        self.frm_login.wait_for(timeout_ms, slice_ms)

    def login(self, username: str, password: str) -> "InitialSectionsPage":
        self.txt_userid.first_matching().click_and_type(username, 2)
        self.txt_passwd.first_matching().click_and_type(password, 3)
        self.btn_ok_login.first_matching().accessible_click()

        try:
            self.frm_ack.wait_for(_WAIT_FOR_TIMEOUT, _WAIT_FOR_SLICE)
        except LocatorNotFound as e:
            if self.frm_forms.exists():
                failure_desc = self.frm_forms.first_matching().description

                try:
                    self.btn_ok_forms.first_matching().accessible_click()
                except LocatorNotFound:
                    pass

                raise SrsJavaCredentialsError(
                    f"Failed to login into SRS: {failure_desc}"
                ) from e

            raise SrsJavaLoginTimeoutError(
                "Failed to login into SRS: Login acknowledgement "
                f"didn't appear within {_WAIT_FOR_TIMEOUT} seconds"
            ) from e

        self.btn_ok_ack.first_matching().accessible_click()
        return InitialSectionsPage(self.driver)


class InitialSectionsPage(SrsJavaPage):
    def _locators(self) -> None:
        self.frm_sections: Locator = self.driver.locator(
            f"internal_frame.modal.{_STD_STATES}[name~='Section']"  # :has(:scope combo_box.{_STD_STATES})"
        )
        self.btn_lms: Locator = self.frm_sections.locator(
            f"push_button.{_STD_STATES}[name~='LMS']"
        )

    def _validate(self, timeout_ms: int, slice_ms: int) -> None:
        self.btn_lms.wait_for(timeout_ms, slice_ms)

    def goto_lms(self) -> "LmsSectionsPage":
        self.btn_lms.first_matching().accessible_click()
        return LmsSectionsPage(self.driver)


class LmsSectionsPage(SrsJavaPage):
    def _locators(self) -> None:
        self.frm_sections: Locator = self.driver.locator(
            f"internal_frame.modal.{_STD_STATES}[name~='Section']"  # :not(:has(:scope combo_box.{_STD_STATES}))"
        )
        self.btn_lending: Locator = self.frm_sections.locator(
            f"push_button.{_STD_STATES}:nth-child(3)"
        )

    def _validate(self, timeout_ms: int, slice_ms: int) -> None:
        self.btn_lending.wait_for(timeout_ms, slice_ms)

    def goto_lending(self) -> "LendingPage":
        self.btn_lending.first_matching().accessible_click()
        return LendingPage(self.driver)


class LendingPage(SrsJavaPage):
    def _locators(self) -> None:
        self.menu_bar: Locator = self.driver.locator("menu_bar.enabled.visible.showing")
        self.btn_exit: Locator = self.menu_bar.locator(
            f"> menu_item.{_STD_STATES}[name^='Exit']"
        )

        # TODO: Write back full selectors after fix on jab-rpa

        submenu_states = "enabled.visible.focusable"
        self.btn_css_view_agr: Locator = self.driver.locator(  # .menu_bar.locator(
            # f"> menu.{_STD_STATES}[name^='Customer Services'] "
            f"menu.{submenu_states}[name^='Viewers'] "
            f"> menu_item.{submenu_states}[name^='Agreement']"
        )
        self.btn_css_pde: Locator = self.driver.locator(  # .menu_bar.locator(
            f"menu.{_STD_STATES}[name^='Customer Services'] "
            f"> menu_item.{submenu_states}[name^='Post Disbursal Edits']"
        )
        self.btn_loan_sett_mpr: Locator = self.driver.locator(  # .menu_bar.locator(
            # f"> menu.{_STD_STATES}[name^='Loan Processing'] "
            f"menu.{submenu_states}[name^='Settlements'] "
            f"> menu_item.{submenu_states}[name^='Manual Payment Receipt']"
        )

    def _validate(self, timeout_ms: int, slice_ms: int) -> None:
        self.btn_exit.wait_for(timeout_ms, slice_ms)

    def goto_css_view_agr(self):
        self.btn_css_view_agr.first_matching().accessible_click()

    def goto_css_pde(self):
        self.btn_css_pde.first_matching().accessible_click()

    def goto_loan_sett_mpr(self):
        self.btn_loan_sett_mpr.first_matching().accessible_click()
