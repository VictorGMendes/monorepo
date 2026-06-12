from typing import Any, Callable
from enum import StrEnum
from time import time
import logging

from niquests import Response
from bs4 import BeautifulSoup

from .session import NewconWebSession

from .errors import (
    NwNavigationError,
    NwPermissionError,
    NwValidationError,
    NwMfaTimerError,
    NwQuotaNotFoundError,
    NwGetExtratoError,
    NwLoggedOutError,
)

logger = logging.getLogger(__name__)


class FrmPath(StrEnum):
    # "Basic" frames
    LOGIN = "/NewconWeb/frmCorCCCnsLogin.aspx"
    MAIN = "/NewconWeb/frmMain.aspx"
    CONAT_SEARCH = "/NewconWeb/CONAT/frmConAtSrcConsorciado.aspx"

    # "Consorciado" frames - has some consorciado context (group/quota/version)
    CONAT_MAIN = "/NewconWeb/CONAT/frmConAtCnsAtendimento.aspx"

    CONAT_EXTRATO = "/NewconWeb/CONAT/frmConAtRelExtrato.aspx"
    CONCM_IMPRESSAO = "/NewconWeb/CONCM/frmConCmImpressao.aspx"

    CONAG_NOVA_OC = "/NewconWeb/CONAG/frmConAgNovaOcorrencia.aspx"
    CONAG_PRC_OC = "/NewconWeb/CONAG/frmConAgPrcOcorrencia.aspx"


# Base NewconWebPage


class NewconWebPage:
    def __init__(self, session: NewconWebSession) -> None:
        self.session: NewconWebSession = session
        self.validate()

    @property
    def soup(self) -> BeautifulSoup:
        return BeautifulSoup(
            ""
            if (self.session.last_response is None)
            else (self.session.last_response.text or ""),
            features="lxml",
        )

    def __init_subclass__(cls, frm_path: FrmPath) -> None:
        super().__init_subclass__()
        cls.frm_path = frm_path

    def validate(self) -> None:
        if self.session.path != self.frm_path:
            e = NwValidationError(
                f"NewconWebSession is not in expected page. Expected page path: '{self.frm_path}', actual page path: '{self.session.path}'"
            )
            if self.session.path == FrmPath.LOGIN:
                raise NwLoggedOutError("User was logged out of Newcon Web") from e
            raise e

    def populate_payload(self, data: dict[str, Any] | None = None) -> dict[str, Any]:
        if data is None:
            data = {}
        form = self.soup.find("form")
        if form is None:
            return data
        tags = form.find_all("input", {"type": "hidden"})
        tags_dict = {
            t.get("name", ""): t.get("value", "") for t in tags if t.get("name")
        }
        return tags_dict | data  # ty: ignore[invalid-return-type]

    def request_at_current_frame(
        self, payload: dict[str, Any] | None = None
    ) -> Response:
        request_url = self.session.url
        if request_url is None:
            raise NwNavigationError("NewconWebSession has not navigated yet")
        return self.session.request(
            method="POST",
            url=request_url,
            headers={"Referer": request_url},
            data=self.populate_payload(payload),
        )

    def request_frame_change(self, frame_path: str) -> Response:
        origin_url = self.session.url
        destiny_url = f"{self.session.base_url}{frame_path}"
        return self.session.request(
            method="GET", url=destiny_url, headers={"Referer": origin_url}
        )


# NewconWeb Pages


class LoginPage(NewconWebPage, frm_path=FrmPath.LOGIN):
    def _login_basic(self, user: str, password: str) -> None:
        self.request_at_current_frame(
            {
                "__EVENTTARGET": "btnLogin",
                "edtUsuario": user,
                "edtSenha": password,
                "hdnTokenRecaptcha": "",
            }
        )

    def _login_mfa(
        self,
        user: str,
        password: str,
        mfa_provider: Callable[[float], str] | None = None,
    ) -> None:
        hnd_timer_token = self.soup.find("input", {"id": "hdnTimerToken"})
        if hnd_timer_token is None:
            raise NwNavigationError("MFA login not available.")

        timer_start = hnd_timer_token["value"]

        if not isinstance(timer_start, str) or not timer_start.isdigit():
            raise NwNavigationError("Invalid timer token value.")

        self.request_at_current_frame(
            {
                "__EVENTTARGET": "btnUsuario",
                "edtUsuarioAD": user,
                "hdnTimerToken": timer_start,
                "hdnTokenRecaptchaAD": "",
            }
        )

        edt_email = self.soup.find("input", {"id": "edtEmail"})
        if edt_email is None:
            raise NwNavigationError("User e-mail not found.")
        censored_email = edt_email["value"]

        self.request_at_current_frame(
            {
                "__EVENTTARGET": "btnEnviaEmail",
                "edtUsuarioAD": user,
                "hdnTimerToken": timer_start,
                "rblAcao": "EMAIL",
                "edtEmail": censored_email,
                "hdnTokenRecaptchaAD": "",
            }
        )

        first_script = self.soup.find("script")
        if first_script is not None:
            first_script_text = first_script.text
            if "alert(" in first_script_text:
                alert = first_script_text.split("');")[0].split("alert('")[-1]
                raise NwNavigationError(f"js alert: {alert}")

        dt_start = time()
        if mfa_provider is None:
            token = input("Please enter the token sent to the user e-mail:")
        else:
            token = mfa_provider(float(timer_start))
        dt_now = time()
        timer_diff = dt_now - dt_start
        timer_now = float(timer_start) - timer_diff

        if timer_now < 0:
            raise NwMfaTimerError("Token timer exceeded.")

        self.request_at_current_frame(
            {
                "__EVENTTARGET": "btnUsuario",
                "edtUsuarioAD": user,
                "hdnTimerToken": str(timer_now),
                "rblAcao": "EMAIL",
                "edtEmail": censored_email,
                "edtToken": token,
                "hdnTokenRecaptchaAD": "",
            }
        )

        self.request_at_current_frame(
            {
                "__EVENTTARGET": "btnLoginUsuario",
                "edtUsuarioAD": user,
                "edtSenhaAD": password,
                "hdnTimerToken": str(timer_now),
                "rblAcao": "EMAIL",
                "edtEmail": censored_email,
                "edtToken": token,
                "hdnTokenRecaptchaAD": "",
            }
        )

    def login(
        self,
        user: str,
        password: str,
        mfa_provider: Callable[[float], str] | None = None,
    ) -> "MainPage":
        hnd_timer_token = self.soup.find("input", {"id": "hdnTimerToken"})
        if hnd_timer_token is None:
            self._login_basic(user, password)
        else:
            self._login_mfa(user, password, mfa_provider)
        return MainPage(self.session)


class MainPage(NewconWebPage, frm_path=FrmPath.MAIN):
    def __init__(
        self, session: NewconWebSession, navigate_on_init: bool = False
    ) -> None:
        if navigate_on_init:
            origin_url = session.url
            destiny_url = f"{session.base_url}{FrmPath.MAIN}"
            session.request(
                method="GET", url=destiny_url, headers={"Referer": origin_url}
            )
        super().__init__(session)

    def go_to_atendimento(self) -> "ConAtSearchPage":
        if self.soup.find("input", {"name": "ctl00$img_Atendimento"}) is None:
            raise NwPermissionError(
                "User doesn't have permission to go to Atendimento page"
            )

        self.request_at_current_frame(
            {"ctl00$img_Atendimento.x": "0", "ctl00$img_Atendimento.y": "0"}
        )
        return ConAtSearchPage(self.session)


class ConAtSearchPage(NewconWebPage, frm_path=FrmPath.CONAT_SEARCH):
    def search_quota(self, group: str, quota: str, version: str) -> "ConAtMainPage":
        self.request_at_current_frame(
            {
                "ctl00$Conteudo$edtGrupo": group,
                "ctl00$Conteudo$edtCota": quota,
                "ctl00$Conteudo$edtVersao": version,
                "ctl00$Conteudo$btnLocalizar": "Localizar",
            }
        )

        search_failed_tag = self.soup.find_all(attrs={"class": "errmsg"})
        search_failed_texts = [tag.get_text(strip=True) for tag in search_failed_tag]

        if not not search_failed_texts:
            raise NwQuotaNotFoundError(
                f"Search failed. Message: {' | '.join(search_failed_texts)}"
            )

        return ConAtMainPage(self.session)


class ConAtMainPage(NewconWebPage, frm_path=FrmPath.CONAT_MAIN):
    def go_to_extrato(self) -> "ConAtExtratoPage":
        self.request_frame_change(FrmPath.CONAT_EXTRATO)
        return ConAtExtratoPage(self.session)

    def go_to_new_ocorrencia(self) -> "ConAgNovaOcPage":
        self.request_at_current_frame(
            {
                "ctl00$Conteudo$lblOcorrencia": "",
                "ctl00$Conteudo$lblObservacao": "",
                "ctl00$Conteudo$btnNovaOcorrencia.x": "0",
                "ctl00$Conteudo$btnNovaOcorrencia.y": "0",
                "ctl00$Conteudo$AbaSelecionada": "1",
            }
        )
        return ConAgNovaOcPage(self.session)


class ConAtExtratoPage(NewconWebPage, frm_path=FrmPath.CONAT_EXTRATO):
    def return_to_conat_main(self) -> "ConAtMainPage":
        self.request_frame_change(FrmPath.CONAT_MAIN)
        return ConAtMainPage(self.session)

    def get_extrato(self) -> bytes:
        self.request_at_current_frame(
            {
                "ctl00$hdnID_Modulo": "",
                "ctl00$Conteudo$cbxModeloImpressao": "1",
                "ctl00$Conteudo$cblOpcoesExtrato$0": "ckDados_Cadastrais",
                "ctl00$Conteudo$cblOpcoesExtrato$1": "ckEndereco_correspondencia",
                "ctl00$Conteudo$cblOpcoesExtrato$2": "ckFiliacao",
                "ctl00$Conteudo$cblOpcoesExtrato$3": "ckDados_Plano",
                "ctl00$Conteudo$cblOpcoesExtrato$4": "ckDados_Percentuais_Mensal",
                "ctl00$Conteudo$cblOpcoesExtrato$5": "ckComtemplacao",
                "ctl00$Conteudo$cblOpcoesExtrato$6": "ckListaBensAlienados",
                "ctl00$Conteudo$cblOpcoesExtrato$7": "ckConta_Corrente",
                "ctl00$Conteudo$cblOpcoesExtrato$8": "ckLancamentos_Estornados",
                "ctl00$Conteudo$cblOpcoesExtrato$10": "ckPendencia",
                "ctl00$Conteudo$cblOpcoesExtrato$11": "ckHistograma",
                "ctl00$Conteudo$cblOpcoesExtrato$12": "ckLegenda",
                "ctl00$Conteudo$cblOpcoesExtrato$13": "ckPercentuais_pagos",
                "ctl00$Conteudo$cblOpcoesExtrato$14": "ckNegociacoes",
                "ctl00$Conteudo$cblOpcoesExtrato$16": "ckValoresPagos",
                "ctl00$Conteudo$cblOpcoesExtrato$17": "ckMensagens",
                "ctl00$Conteudo$btnImprimir": "Imprimir",
            }
        )

        if "window.open('../CONCM/frmConCmImpressao.aspx'" not in self.soup.text:
            self.request_at_current_frame(
                {
                    "__EVENTTARGET": "ctl00$Conteudo$grdHistoricoSituacao",
                    "__EVENTARGUMENT": "Select$0",
                    "ctl00$hdnID_Modulo": "",
                    "ctl00$Conteudo$cbxModeloImpressao": "1",
                    "ctl00$Conteudo$cblOpcoesExtrato$0": "ckDados_Cadastrais",
                    "ctl00$Conteudo$cblOpcoesExtrato$1": "ckEndereco_correspondencia",
                    "ctl00$Conteudo$cblOpcoesExtrato$2": "ckFiliacao",
                    "ctl00$Conteudo$cblOpcoesExtrato$3": "ckDados_Plano",
                    "ctl00$Conteudo$cblOpcoesExtrato$4": "ckDados_Percentuais_Mensal",
                    "ctl00$Conteudo$cblOpcoesExtrato$5": "ckComtemplacao",
                    "ctl00$Conteudo$cblOpcoesExtrato$6": "ckListaBensAlienados",
                    "ctl00$Conteudo$cblOpcoesExtrato$7": "ckConta_Corrente",
                    "ctl00$Conteudo$cblOpcoesExtrato$8": "ckLancamentos_Estornados",
                    "ctl00$Conteudo$cblOpcoesExtrato$10": "ckPendencia",
                    "ctl00$Conteudo$cblOpcoesExtrato$11": "ckHistograma",
                    "ctl00$Conteudo$cblOpcoesExtrato$12": "ckLegenda",
                    "ctl00$Conteudo$cblOpcoesExtrato$13": "ckPercentuais_pagos",
                    "ctl00$Conteudo$cblOpcoesExtrato$14": "ckNegociacoes",
                    "ctl00$Conteudo$cblOpcoesExtrato$16": "ckValoresPagos",
                    "ctl00$Conteudo$cblOpcoesExtrato$17": "ckMensagens",
                }
            )

        res_extrato = self.request_frame_change(FrmPath.CONCM_IMPRESSAO)
        self.request_frame_change(FrmPath.CONAT_EXTRATO)

        content_type = str(res_extrato.headers.get("content-type", "").lower())
        if (res_extrato.status_code != 200) or ("application/pdf" not in content_type):
            raise NwGetExtratoError(f"""Couldn't print quota's extrato.
Response status code: {res_extrato.status_code},
Response headers: {res_extrato.headers},
Response content: {res_extrato.content}
""")

        return res_extrato.content or b""


class ConAgNovaOcPage(NewconWebPage, frm_path=FrmPath.CONAG_NOVA_OC):
    def return_to_conat_main(self) -> "ConAtMainPage":
        self.request_at_current_frame(
            {
                "__EVENTTARGET": "ctl00$Conteudo$cbxProcuraGrupo",
                "ctl00$Conteudo$cbxTipoCanal": "A",
                "ctl00$Conteudo$rblBuscaOcorrencia": "PR",
                "ctl00$Conteudo$edtCodigoAtalho": "",
                "ctl00$Conteudo$cbxProcuraGrupo": "0",
                "ctl00$Conteudo$cbxOcorrencia": "0",
                "ctl00$Conteudo$btnCancela": "Cancela",
            }
        )
        return ConAtMainPage(self.session)

    def set_oc_group_and_name(
        self, oc_group: str = "1", oc_name: str = "320|OBSERVAÇÕES DIVERSAS||N"
    ) -> "ConAgPrcOcPage":
        self.request_at_current_frame(
            {
                "__EVENTTARGET": "ctl00$Conteudo$cbxProcuraGrupo",
                "ctl00$Conteudo$cbxTipoCanal": "A",
                "ctl00$Conteudo$rblBuscaOcorrencia": "PR",
                "ctl00$Conteudo$edtCodigoAtalho": "",
                "ctl00$Conteudo$cbxProcuraGrupo": oc_group,
                "ctl00$Conteudo$cbxOcorrencia": "0",
            }
        )
        self.request_at_current_frame(
            {
                "__EVENTTARGET": "ctl00$Conteudo$cbxOcorrencia",
                "ctl00$Conteudo$cbxTipoCanal": "A",
                "ctl00$Conteudo$rblBuscaOcorrencia": "PR",
                "ctl00$Conteudo$edtCodigoAtalho": "",
                "ctl00$Conteudo$cbxProcuraGrupo": oc_group,
                "ctl00$Conteudo$cbxOcorrencia": oc_name,
            }
        )
        self.request_at_current_frame(
            {
                "ctl00$Conteudo$cbxTipoCanal": "A",
                "ctl00$Conteudo$rblBuscaOcorrencia": "PR",
                "ctl00$Conteudo$edtCodigoAtalho": "",
                "ctl00$Conteudo$cbxProcuraGrupo": oc_group,
                "ctl00$Conteudo$cbxOcorrencia": oc_name,
                "ctl00$Conteudo$btnEnviar": "Envia",
            }
        )
        return ConAgPrcOcPage(self.session)


class ConAgPrcOcPage(NewconWebPage, frm_path=FrmPath.CONAG_PRC_OC):
    def return_to_conat_main(self) -> ConAtMainPage:
        self.request_at_current_frame(
            {
                "__EVENTTARGET": "",
                "ctl00$Conteudo$edtRegistroHistorico": "",
                "ctl00$Conteudo$cbxOrigem": "0",
                "ctl00$Conteudo$txtNM_Contato": "",
                "ctl00$Conteudo$rblOcorrencia": "EC",
                "ctl00$Conteudo$cbxEncerraOcorrencia": "000000",
                "ctl00$Conteudo$AbaSelecionada": "0",
                "ctl00$Conteudo$hdSN_Protocolo_Nova_Ocorrencia": "0",
                "ctl00$Conteudo$hid_SN_Protocolo_Principal": "N",
                "ctl00$Conteudo$hid_Salva_Rascunho": "N",
                "ctl00$Conteudo$selected_tab": "0",
                "ctl00$Conteudo$btnCancelaOcorrencia": "Cancela",
            }
        )
        return ConAtMainPage(self.session)

    def create_oc(self, info: str) -> ConAtMainPage:
        self.request_at_current_frame(
            {
                "__EVENTTARGET": "ctl00$Conteudo$rblOcorrencia$4",
                "ctl00$Conteudo$edtRegistroHistorico": "",
                "ctl00$Conteudo$cbxOrigem": "0",
                "ctl00$Conteudo$txtNM_Contato": "",
                "ctl00$Conteudo$rblOcorrencia": "EC",
                "ctl00$Conteudo$cbxEncerraOcorrencia": "000000",
                "ctl00$Conteudo$AbaSelecionada": "0",
                "ctl00$Conteudo$hdSN_Protocolo_Nova_Ocorrencia": "0",
                "ctl00$Conteudo$hid_SN_Protocolo_Principal": "N",
                "ctl00$Conteudo$hid_Salva_Rascunho": "N",
                "ctl00$Conteudo$selected_tab": "0",
            }
        )
        self.request_at_current_frame(
            {
                "ctl00$Conteudo$edtRegistroHistorico": info,
                "ctl00$Conteudo$cbxOrigem": "0",
                "ctl00$Conteudo$txtNM_Contato": "",
                "ctl00$Conteudo$rblOcorrencia": "EC",
                "ctl00$Conteudo$cbxEncerraOcorrencia": "000001",
                "ctl00$Conteudo$btnConfirmaOcorrencia": "Confirma",
                "ctl00$Conteudo$AbaSelecionada": "0",
                "ctl00$Conteudo$hdSN_Protocolo_Nova_Ocorrencia": "0",
                "ctl00$Conteudo$hid_SN_Protocolo_Principal": "N",
                "ctl00$Conteudo$hid_Salva_Rascunho": "N",
                "ctl00$Conteudo$selected_tab": "0",
            }
        )
        self.request_frame_change(FrmPath.CONAT_MAIN)
        return ConAtMainPage(self.session)
