#!/bin/bash

# Script para parar o Proxy
# Funciona em: Linux (todas as distros), macOS e WSL

echo "🛑 Parando Proxy..."

# Parar nosso proxy
if command -v lsof &> /dev/null; then
    if lsof -i :20129 > /dev/null 2>&1; then
        pkill -f "micro_proxy_opencode" 2>/dev/null
        echo "✅ Proxy parado (porta 20129)"
    else
        echo "ℹ️  Proxy não estava rodando"
    fi
elif command -v fuser &> /dev/null; then
    if fuser 20129/tcp > /dev/null 2>&1; then
        fuser -k 20129/tcp 2>/dev/null
        echo "✅ Proxy parado (porta 20129)"
    else
        echo "ℹ️  Proxy não estava rodando"
    fi
else
    pkill -f "micro_proxy_opencode" 2>/dev/null && echo "✅ Proxy parado" \
        || echo "ℹ️  Proxy não estava rodando"
fi

# Perguntar se quer parar o OmniRouter também
read -p "Deseja parar o OmniRouter também? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    if command -v omniroute &> /dev/null; then
        omniroute stop
        echo "✅ OmniRouter parado"
    else
        echo "ℹ️  OmniRouter não está instalado"
    fi
fi
