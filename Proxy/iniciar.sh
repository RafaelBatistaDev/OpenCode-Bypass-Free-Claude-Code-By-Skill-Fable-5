#!/bin/bash

# Script para iniciar o Proxy com OmniRouter
# Funciona em: Linux (Ubuntu/Debian/Fedora/Arch), macOS e WSL

echo "🚀 Iniciando Proxy com OmniRouter..."

DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$DIR/proxy.log"

# ─── Rotação automática de logs ─────────────────────────────────
# Limita o tamanho do log em 10MB, mantém últimos 5 backups (gzip).
rotate_logs() {
    MAX_SIZE=10485760   # 10MB em bytes
    MAX_BACKUPS=5

    # Verifica se o log existe e seu tamanho
    if [ ! -f "$LOG_FILE" ]; then
        return 0
    fi

    # Obtém tamanho de forma cross-platform (Linux/macOS)
    if command -v stat &> /dev/null; then
        SIZE=$(stat -c%s "$LOG_FILE" 2>/dev/null || stat -f%z "$LOG_FILE" 2>/dev/null || echo 0)
    else
        SIZE=$(wc -c < "$LOG_FILE" 2>/dev/null || echo 0)
    fi

    # Se ainda não atingiu o limite, nada a fazer
    if [ "$SIZE" -lt "$MAX_SIZE" ]; then
        return 0
    fi

    echo "📦 Rotacionando logs (tamanho: $SIZE bytes)..."
    # Remove o backup mais antigo
    if [ -f "$LOG_FILE.$MAX_BACKUPS.gz" ]; then
        rm -f "$LOG_FILE.$MAX_BACKUPS.gz"
    fi
    # Desloca os backups existentes (4->5, 3->4, ...)
    for i in $(seq $((MAX_BACKUPS - 1)) -1 1); do
        if [ -f "$LOG_FILE.$i.gz" ]; then
            mv "$LOG_FILE.$i.gz" "$LOG_FILE.$((i + 1)).gz"
        fi
    done
    # Comprime o log atual como backup 1 e limpa o arquivo
    if command -v gzip &> /dev/null; then
        gzip -c "$LOG_FILE" > "$LOG_FILE.1.gz" && > "$LOG_FILE"
        echo "✅ Logs rotacionados (comprimidos com gzip)"
    else
        mv "$LOG_FILE" "$LOG_FILE.1"
        > "$LOG_FILE"
        echo "✅ Logs rotacionados (gzip não disponível)"
    fi
}

# Roda a rotação antes de iniciar o proxy
rotate_logs

# Verificar se o OmniRouter está instalado
if ! command -v omniroute &> /dev/null; then
    echo "❌ OmniRouter não encontrado. Instalando..."
    if command -v bun &> /dev/null; then
        bun install -g omniroute
    else
        echo "❌ Bun não encontrado. Execute: python3 setup_opencode.py"
        exit 1
    fi
fi

# Verificar se o OmniRouter está rodando
if curl -s http://localhost:20128/health > /dev/null 2>&1; then
    echo "✅ OmniRouter já está rodando (porta 20128)"
else
    echo "📦 Iniciando OmniRouter na porta 20128..."
    omniroute serve --port 20128 --daemon
    sleep 3
    echo "✅ OmniRouter iniciado"
fi

# Verificar se nosso proxy está rodando
if command -v lsof &> /dev/null; then
    if lsof -i :20129 > /dev/null 2>&1; then
        echo "🛑 Parando proxy antigo na porta 20129..."
        pkill -f "micro_proxy_opencode" 2>/dev/null
        sleep 2
    fi
elif command -v fuser &> /dev/null; then
    if fuser 20129/tcp > /dev/null 2>&1; then
        echo "🛑 Parando proxy antigo na porta 20129..."
        fuser -k 20129/tcp 2>/dev/null
        sleep 2
    fi
fi

# Iniciar nosso proxy
echo "📦 Iniciando proxy na porta 20129..."
cd "$DIR" || exit 1
nohup bun run micro_proxy_opencode.js > "$LOG_FILE" 2>&1 &
PID=$!

sleep 2

# Verificar se subiu
if kill -0 "$PID" 2>/dev/null; then
    echo "✅ Proxy iniciado com sucesso!"
    echo "📋 Log: $DIR/proxy.log"
    echo ""
    echo "🔧 Configuração:"
    echo "   OmniRouter: http://localhost:20128"
    echo "   Seu Proxy:  http://localhost:20129"
    echo "   Métricas:   http://localhost:20129/metrics"
    echo ""
    echo "📝 Para usar com Claude Code:"
    echo "   export ANTHROPIC_BASE_URL=http://localhost:20129"
    echo "   export ANTHROPIC_API_KEY=dummy"
    echo "   claude"
else
    echo "❌ Falha ao iniciar proxy. Verifique o log:"
    tail -10 "$LOG_FILE"
fi
