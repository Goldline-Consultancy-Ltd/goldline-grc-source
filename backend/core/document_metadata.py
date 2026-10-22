"""Goldline GRC: author and company on spreadsheets the app generates.

openpyxl stamps every new workbook with creator "openpyxl" and no company, and
the exports build workbooks in about twenty places (directly and via pandas).
Setting the defaults once here covers all of them. Files that already carry an
author, such as a loaded template, keep it.
"""

from openpyxl.packaging.core import DocumentProperties
from openpyxl.packaging.extended import ExtendedProperties

DOCUMENT_OWNER = "Goldline Consultancy Ltd"


def apply_document_metadata_defaults():
    if getattr(DocumentProperties, "_goldline_defaults", False):
        return

    core_init = DocumentProperties.__init__
    extended_init = ExtendedProperties.__init__

    def core_with_defaults(self, *args, **kwargs):
        core_init(self, *args, **kwargs)
        if not self.creator or self.creator == "openpyxl":
            self.creator = DOCUMENT_OWNER
        if not self.lastModifiedBy:
            self.lastModifiedBy = DOCUMENT_OWNER

    def extended_with_defaults(self, *args, **kwargs):
        extended_init(self, *args, **kwargs)
        if not self.Company:
            self.Company = DOCUMENT_OWNER

    DocumentProperties.__init__ = core_with_defaults
    ExtendedProperties.__init__ = extended_with_defaults
    # openpyxl only writes the elements listed here; Company isn't by default.
    if "Company" not in ExtendedProperties.__elements__:
        ExtendedProperties.__elements__ = ExtendedProperties.__elements__ + ("Company",)
    DocumentProperties._goldline_defaults = True
