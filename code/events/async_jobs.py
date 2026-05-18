# events/async_jobs.py

"""Async SCIM request handling (RFC 9967 §2.5.1) — Phase 2."""


def submit_async_job(*_args, **_kwargs):
    raise NotImplementedError(
        "Asynchronous SCIM requests (Prefer: respond-async) are planned for Phase 2."
    )
