from http import HTTPStatus

from pymongo.errors import ServerSelectionTimeoutError
from starlette.middleware.base import BaseHTTPMiddleware

from exceptions import DependencyException


class DBTransactionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except ServerSelectionTimeoutError:
            raise DependencyException(dependency="db", status_code=HTTPStatus.FAILED_DEPENDENCY)
