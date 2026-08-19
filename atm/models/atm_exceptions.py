# -*- coding: utf-8 -*-
"""Exceptions this module raises on purpose.

Kept in their own file so both the exchange engine and the crash reporter can
import them without importing each other.
"""


class AtmDataError(ValueError):
    """The incoming data cannot be used, and that is not a bug in the module.

    Raised when a record refers to something this database does not have -- a
    product that was never imported, a partner that does not exist yet. The
    record is counted as failed and the run carries on.

    It exists as a class of its own so the crash reporter can tell it apart.
    A plain ``ValueError`` would be indistinguishable from a genuine bug, and
    the queue would fill with "the other side sent us a product we do not know"
    until a real defect could no longer be seen in it. Subclasses ``ValueError``
    so anything already catching that keeps working.
    """
