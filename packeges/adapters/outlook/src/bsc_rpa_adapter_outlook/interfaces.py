from typing import Self
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable
import os

import win32com.client as win32
from win32com.client.dynamic import CDispatch

logger = logging.getLogger(__name__)

MESSAGE_ID_DASL_NAME = "http://schemas.microsoft.com/mapi/proptag/0x1035001F"


class BaseAttachment(ABC):
    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @property
    @abstractmethod
    def file_name(self) -> str: ...

    @abstractmethod
    def save(self, path: str): ...


class Win32Att(BaseAttachment):
    def __init__(self, attachment_cdispatch: CDispatch) -> None:
        super().__init__()
        self.attachment_cdispatch = attachment_cdispatch

    @property
    def display_name(self) -> str:
        return self.attachment_cdispatch.DisplayName

    @property
    def file_name(self) -> str:
        return self.attachment_cdispatch.FileName

    def save(self, path: str):
        self.attachment_cdispatch.SaveAsFile(path)


class BaseMail[AttType: BaseAttachment](ABC):
    @property
    @abstractmethod
    def body_html(self) -> str: ...

    @property
    @abstractmethod
    def subject(self) -> str: ...

    @property
    @abstractmethod
    def sender(self) -> str: ...

    @property
    @abstractmethod
    def to(self) -> str: ...

    @property
    @abstractmethod
    def cc(self) -> str: ...

    @property
    @abstractmethod
    def bcc(self) -> str: ...

    @property
    @abstractmethod
    def attachments(self) -> list[AttType]: ...

    @abstractmethod
    def reply(
        self,
        body_html: str,
        subject: str | None = None,
        to: str | None = None,
        cc: str | None = None,
        bcc: str | None = None,
        attachments: list[str] | None = None,
    ):
        """**attachments**: list of file paths"""
        ...

    @abstractmethod
    def reply_all(
        self,
        body_html: str,
        subject: str | None = None,
        to: str | None = None,
        cc: str | None = None,
        bcc: str | None = None,
        attachments: list[str] | None = None,
    ):
        """**attachments**: list of file paths"""
        ...


class Win32Mail(BaseMail[Win32Att]):
    def __init__(self, mail_item: CDispatch) -> None:
        super().__init__()
        self.mail_item = mail_item

    @property
    def body_html(self) -> str:
        return self.mail_item.HTMLBody

    @property
    def subject(self) -> str:
        return self.mail_item.Subject

    @property
    def sender(self) -> str:
        return self.mail_item.SenderEmailAddress

    @property
    def to(self) -> str:
        return self.mail_item.To

    @property
    def cc(self) -> str:
        return self.mail_item.CC

    @property
    def bcc(self) -> str:
        return self.mail_item.BCC

    @property
    def attachments(self) -> list[Win32Att]:
        return [Win32Att(att) for att in self.mail_item.Attachments]

    @property
    def message_id(self) -> str:
        return self.mail_item.PropertyAccessor.GetProperty(MESSAGE_ID_DASL_NAME)

    @property
    def received_at(self) -> str:
        return str(self.mail_item.ReceivedTime)

    def reply(
        self,
        body_html: str,
        subject: str | None = None,
        to: str | None = None,
        cc: str | None = None,
        bcc: str | None = None,
        attachments: list[str] | None = None,
    ):
        reply = self.mail_item.Reply()
        reply.HTMLBody = body_html
        if subject is not None:
            reply.Subject = subject
        if to is not None:
            reply.To = to
        if cc is not None:
            reply.CC = cc
        if bcc is not None:
            reply.BCC = bcc
        if attachments is not None:
            atts = reply.Attachments
            for att_path in attachments:
                abs_path = os.path.abspath(att_path)
                if not (os.path.exists(abs_path) and os.path.isfile(abs_path)):
                    raise FileNotFoundError(
                        f"Attachment file at {abs_path!r} not found"
                    )
                atts.Add(abs_path)
        reply.Send()

    def reply_all(
        self,
        body_html: str,
        subject: str | None = None,
        to: str | None = None,
        cc: str | None = None,
        bcc: str | None = None,
        attachments: list[str] | None = None,
    ):
        reply = self.mail_item.ReplyAll()
        reply.HTMLBody = body_html
        if subject is not None:
            reply.Subject = subject
        if to is not None:
            reply.To = to
        if cc is not None:
            reply.CC = cc
        if bcc is not None:
            reply.BCC = bcc
        if attachments is not None:
            atts = reply.Attachments
            for att_path in attachments:
                abs_path = os.path.abspath(att_path)
                if not (os.path.exists(abs_path) and os.path.isfile(abs_path)):
                    raise FileNotFoundError(
                        f"Attachment file at {abs_path!r} not found"
                    )
                atts.Add(abs_path)
        reply.Send()


class BaseOutlook[MailType: BaseMail](ABC):
    """Abstract base class for Outlook interaction"""

    @abstractmethod
    def get_emails(self, account: str, folder: str) -> list[MailType]: ...

    @abstractmethod
    def send_email(
        self,
        body_html: str,
        subject: str,
        to: str,
        cc: str = "",
        bcc: str = "",
        attachments: list[str] | None = None,
    ):
        """**attachments**: list of file paths"""
        ...

    @abstractmethod
    def move_email(self, email: MailType, folder: str, account: str): ...


class Win32Outlook(BaseOutlook[Win32Mail]):
    """This should be used as a context manager to free the Outlook application after use"""

    def __init__(self):
        logger.info("Initializing Win32Outlook object")
        self.app_obj: CDispatch = win32.Dispatch("Outlook.Application")
        logger.debug("Initialized Win32Outlook object")

    def __enter__(self) -> Self:
        return self

    def __exit__(self, type, value, traceback):
        logger.info("Stopping Win32Outlook object")
        self.app_obj = None  # ty: ignore[invalid-assignment]
        del self.app_obj
        logger.debug("Stopped Win32Outlook object")
        return False

    def _get_account(self, email_account: str) -> CDispatch | None:
        namespace = self.app_obj.GetNamespace("MAPI")
        for account in namespace.Accounts:
            if account.DisplayName == email_account:
                return account
        return None

    def _get_folder(self, email_account: str, folder_path: str) -> CDispatch | None:
        "**folder_path** must be separeted by backward slash (\\), starting from the root folder in the account"
        account = self._get_account(email_account)
        if account is None:
            return None
        root = account.DeliveryStore.GetRootFolder()

        folder = root
        for folder_name in folder_path.split("\\"):
            for aux_folder in folder.folders:
                if aux_folder.FolderPath == f"{folder.FolderPath}\\{folder_name}":
                    folder = aux_folder
                    break
            else:
                return None

        return folder

    def get_emails(
        self, account: str, folder: str, filter: str | None = None
    ) -> list[Win32Mail]:
        "**folder** must be separeted by backward slash (\\), starting from the root folder in the account"
        folder_cdispatch = self._get_folder(account, folder)
        if folder_cdispatch is None:
            return []
        mail_items = folder_cdispatch.Items
        if filter is not None:
            mail_items = mail_items.Restrict(filter)
        return [Win32Mail(mail_item) for mail_item in mail_items]

    def find_email(self, account: str, folder: str, filter: str) -> Win32Mail | None:
        "**folder** must be separeted by backward slash (\\), starting from the root folder in the account"
        folder_cdispatch = self._get_folder(account, folder)
        if folder_cdispatch is None:
            return None
        mail_items = folder_cdispatch.Items
        mail_item = mail_items.Find(filter)
        if mail_item is not None:
            return Win32Mail(mail_item)

    def get_email_by_message_id(
        self, account: str, folder: str, message_id: str
    ) -> Win32Mail | None:
        "**folder** must be separeted by backward slash (\\), starting from the root folder in the account"
        folder_cdispatch = self._get_folder(account, folder)
        if folder_cdispatch is None:
            return None
        mail_items = folder_cdispatch.Items
        filter_str = f"@SQL=\"{MESSAGE_ID_DASL_NAME}\" = '{message_id}'"
        found_items = mail_items.Restrict(filter_str)
        for mail_item in found_items:
            return Win32Mail(mail_item)
        return None

    def send_email(
        self,
        body_html: str,
        subject: str,
        to: str,
        cc: str = "",
        bcc: str = "",
        attachments: Iterable[str] | None = None,
    ):
        email = self.app_obj.CreateItem(0)
        email.HTMLBody = body_html
        email.Subject = subject
        email.To = to
        if cc is not None:
            email.CC = cc
        if bcc is not None:
            email.BCC = bcc
        if attachments is not None:
            atts = email.Attachments
            for att_path in attachments:
                atts.Add(att_path)
        email.Send()

    def move_email(self, email: Win32Mail, folder: str, account: str):
        mail_item = email.mail_item
        folder_cdispatch = self._get_folder(account, folder)
        if folder_cdispatch is None:
            raise ValueError(f"Folder {folder!r} not found in account {account!r}")
        mail_item.Move(folder_cdispatch)
