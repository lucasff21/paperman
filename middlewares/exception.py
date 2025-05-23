import logging

from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from exceptions import BusinessException, DatabaseTimeoutException, DependencyException


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except BusinessException as e:
            logging.error(e)
            return JSONResponse(
                status_code=e.status_code, 
                content={
                    "error": e.__class__.__name__, 
                    "message": e.message
                }
            )
        except DependencyException as e:
            logging.error(e)
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": e.__class__.__name__, 
                    "message": e.message
                }
            )
        except DatabaseTimeoutException as e:
            logging.error(e)
            return JSONResponse(
                status_code=HTTPStatus.FAILED_DEPENDENCY,
                content={
                    "error": e.__class__.__name__, 
                    "message": e.message
                }
            )
        except Exception as e:
            logging.error(e)
            return JSONResponse(
                status_code=500, 
                content={
                    "error": e.__class__.__name__, 
                    "messages": e.args
                }
            )