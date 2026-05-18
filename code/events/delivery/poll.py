# events/delivery/poll.py

"""RFC 8936 poll-based SET delivery — planned for Phase 3."""


def deliver_set_poll(*_args, **_kwargs):
    raise NotImplementedError(
        "Poll-based SET delivery (RFC 8936) is not implemented yet. "
        "Use SET_PUSH_URL for push delivery (RFC 8935)."
    )
