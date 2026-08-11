from dataclasses import dataclass

from .errors import ServiceError


@dataclass(frozen=True)
class DemoUser:
    user_id: str
    role: str


USERS = {
    "demo-rm": DemoUser("demo-rm", "RM"),
    "demo-reviewer": DemoUser("demo-reviewer", "REVIEWER"),
}


def require_user(user_id: str | None) -> DemoUser:
    if not user_id or user_id not in USERS:
        raise ServiceError(
            "UNAUTHORIZED", "A valid X-Demo-User-Id is required.", 401, "Unauthorized"
        )
    return USERS[user_id]


def require_role(user_id: str | None, *roles: str) -> DemoUser:
    user = require_user(user_id)
    if user.role not in roles:
        raise ServiceError(
            "FORBIDDEN", "The demo user is not allowed to perform this action.", 403, "Forbidden"
        )
    return user
