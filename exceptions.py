from http import HTTPStatus


class UnicornException(Exception):
    def __init__(self, name: str):
        self.name = name
        

class DependencyException(Exception):
    def __init__(self, dependency: str, status_code: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR) -> None:
        self.message = f"Error on dependency: {dependency}"
        self.status_code = status_code
        super().__init__(self.message)
        

class BusinessException(Exception):
    def __init__(self, message: str, status_code: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class DatabaseTimeoutException(Exception):
    def __init__(self) -> None:
        self.message = "Timeout on database connection"
        super().__init__(self.message)
        