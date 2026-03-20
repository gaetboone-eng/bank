#!/bin/bash
cd /var/www/cgr-bank/backend
source venv/bin/activate
exec uvicorn server:app --host 0.0.0.0 --port 8002
