#!/bin/bash
set -e
cd /service/frontend
npm install
npm run build
rsync -av --delete dist/ /service/frontend/dist/
nginx -s reload
echo "Frontend deployed."
