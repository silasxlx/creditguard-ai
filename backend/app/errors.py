from dataclasses import dataclass


@dataclass
class ServiceError(Exception):
    code: str
    detail: str
    status: int = 400
    title: str = "Request failed"

    def __str__(self) -> str:
        return self.detail
