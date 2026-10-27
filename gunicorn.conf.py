"""Production HTTP server; the reverse proxy terminates public HTTPS."""
import os

bind = '0.0.0.0:' + os.environ.get('PORT', '8080')
workers = int(os.environ.get('WEB_CONCURRENCY', '2'))
worker_class = 'gthread'
threads = int(os.environ.get('GUNICORN_THREADS', '2'))
timeout = 120
graceful_timeout = 30
keepalive = 5
accesslog = '-'
errorlog = '-'
# Do not log project/report payloads passed through URL query parameters.
access_log_format = '%(h)s "%(m)s %(U)s %(H)s" %(s)s %(b)s %(L)s'
capture_output = True
max_requests = 1000
max_requests_jitter = 100
