"""User-facing errors. Anything raised as InputError is shown to the user as-is."""


class InputError(ValueError):
    """The input cannot produce a video. The message says how to fix it."""
