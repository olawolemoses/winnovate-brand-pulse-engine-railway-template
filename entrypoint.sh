#!/bin/bash
set -e

chown -R openclaw:openclaw /data
chmod 700 /data

if [ ! -d /data/.linuxbrew ]; then
  cp -a /home/linuxbrew/.linuxbrew /data/.linuxbrew
fi

rm -rf /home/linuxbrew/.linuxbrew
ln -sfn /data/.linuxbrew /home/linuxbrew/.linuxbrew

echo "[init] Syncing workspace from /app to /data"
mkdir -p /data/workspace/skills /data/workspace/tools
if [ -d /app/workspace ]; then
  cp -rn /app/workspace/. /data/workspace/
fi
chown -R openclaw:openclaw /data/workspace

exec gosu openclaw node src/server.js
