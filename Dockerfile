FROM python:3.11-slim-bookworm
RUN useradd -m -u 10001 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /home/user/app
COPY --chown=user:user . /home/user/app
RUN pip install --no-cache-dir --user -r requirements.txt
EXPOSE 8080
CMD exec gunicorn -w 1 --threads 4 -b 0.0.0.0:${PORT:-8080} --timeout 120 app:app
