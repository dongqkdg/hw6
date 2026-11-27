FROM python:3.12-slim

WORKDIR /app
COPY app /app/app

ARG APP_COMMIT_SHA=unknown
ENV APP_COMMIT_SHA=$APP_COMMIT_SHA

EXPOSE 8080
CMD ["python", "-m", "app.server"]
