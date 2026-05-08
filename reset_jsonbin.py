#!/usr/bin/env python3
"""
reset_jsonbin.py - Zera o JSONBin para reiniciar as avaliações.
Coloque as variáveis de ambiente antes de rodar:
  $env:JSONBIN_BIN_ID="seu_bin_id"
  $env:JSONBIN_MASTER_KEY="sua_master_key"
"""
import os, urllib.request, json

BIN_ID     = os.getenv("JSONBIN_BIN_ID")
MASTER_KEY = os.getenv("JSONBIN_MASTER_KEY")

if not BIN_ID or not MASTER_KEY:
    print("ERRO: Configure as variáveis de ambiente primeiro:")
    print('  $env:JSONBIN_BIN_ID="seu_bin_id"')
    print('  $env:JSONBIN_MASTER_KEY="sua_master_key"')
    exit(1)

url = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
payload = json.dumps({}).encode("utf-8")
req = urllib.request.Request(
    url,
    data=payload,
    method="PUT",
    headers={
        "Content-Type": "application/json",
        "X-Master-Key": MASTER_KEY,
    }
)

with urllib.request.urlopen(req, timeout=15) as r:
    body = json.loads(r.read())

print(f"Status HTTP: {r.status}")
print(f"JSONBin zerado com sucesso!")
print(f"Metadata: {body.get('metadata', {})}")
