#!/bin/sh
set -eu

exec python -m app.workers.rag_worker

