import logging

import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from middlewares.auth import AuthMiddleware
from middlewares.exception import ExceptionHandlerMiddleware
from routers import auth, publications, qualis, users, venues
from word_embedding.gensim import init_model

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

app.add_middleware(AuthMiddleware)
app.add_middleware(ExceptionHandlerMiddleware)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(publications.router)
app.include_router(users.router)
app.include_router(qualis.router)
app.include_router(venues.router)

app.mount("/static", StaticFiles(directory="static"), name="static")

init_model()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5052, reload=True, log_level='debug')