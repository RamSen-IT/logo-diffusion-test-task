def client_balance(client_id: str) -> str:
    return f"client:{client_id}:balance"


def generation(generation_id: str) -> str:
    return f"generation:{generation_id}"


def rate_slot(client_id: str) -> str:
    return f"rate:{client_id}:active"


def metrics(name: str) -> str:
    return f"metrics:{name}"
