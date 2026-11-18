"""Erros que o front recebe com um status no estilo HTTP (o tratamento atual das telas lê status e corpo)."""


class ApiError(Exception):
    def __init__(self, status: int, data):
        super().__init__(f"{status}: {data}")
        self.status = status
        self.data = data


def bad_request(data) -> ApiError:
    return ApiError(400, data)


def not_found(what: str) -> ApiError:
    return ApiError(404, {"detail": f"No {what} matches the given query."})


def forbidden(detail: str) -> ApiError:
    return ApiError(403, {"detail": detail})
