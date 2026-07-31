# Guia para Agentes de Código — OpenCode-Bypass

> Diretrizes para agentes de código (Claude, Copilot, Cursor, Devin) ao trabalhar neste repositório.

---

## 📋 Stack do Projeto

```
Runtime JS      : Bun (ESM modules)
Proxy           : JavaScript (Bun.serve)
Setup           : Python 3 (pathlib, subprocess)
Router          : OmniRouter (npm)
API Alvo        : OpenCode (modelos gratuitos)
SO Suportados   : Linux (Ubuntu/Debian/Fedora/Arch), Windows 11, WSL, macOS
```

## 🌐 Suporte Cross-Platform

| Plataforma | Shell | Package Manager | Bun | OmniRouter |
|------------|-------|----------------|-----|------------|
| Linux (apt) | bash | apt | ✅ | ✅ |
| Linux (dnf) | bash | dnf | ✅ | ✅ |
| Linux (pacman) | bash | pacman | ✅ | ✅ |
| Windows 11 | PowerShell | winget/choco | ✅ | ✅ |
| WSL 1/2 | bash | apt (Ubuntu on WSL) | ✅ | ✅ |
| macOS | zsh | brew | ✅ | ✅ |

## 📁 Estrutura de Diretórios

```
OpenCode-Bypass/
├── Proxy/                    # 🖥️ Camada de proxy
│   ├── micro_proxy_opencode.js   # Servidor HTTP (Bun)
│   ├── iniciar.sh / iniciar.bat  # Start scripts
│   └── parar.sh / parar.bat      # Stop scripts
├── scripts/                  # ⚙️ Scripts auxiliares
├── docs/                     # 📚 Documentação
└── setup_opencode.py         # 🚀 Setup universal
```

## 🔧 Regras de Desenvolvimento

### Python (`setup_opencode.py`)

```python
# ✅ Boas práticas
import sys
from pathlib import Path

HOME = Path.home()  # ✅ Usar Path.home()
BINDIR = HOME / ".local" / "bin"  # ✅ Usar pathlib

# ❌ Evitar
# home = "/home/user"  # Hardcoded!
# BINDIR = os.path.join(os.path.expanduser("~"), ".local", "bin")  # os.path.join!
```

**Regras:**
- `pathlib.Path` obrigatório; proibido `os.path.join()`
- `Path.home()` — nunca hardcodar caminhos de usuário
- Type hints obrigatórios
- Identação: 4 espaços
- Detectar SO com `platform.system()` e `platform.uname().release`
- Idempotência com marcadores

### JavaScript — Proxy (`micro_proxy_opencode.js`)

```javascript
// ✅ Boas práticas
import process from "node:process";
import fs from "node:fs";

const PORT = Number(process.env.PROXY_PORT) || 20129;

Bun.serve({
  port: PORT,
  async fetch(req) {
    // handler
  },
});
```

**Regras:**
- ESM (`import`/`export`) — nunca CommonJS (`require`)
- `Bun.serve()` — nunca `http.createServer()`
- `Bun.file()` para ler arquivos
- Não usar `child_process`; preferir `Bun.$`
- Logs em português com prefixos: `[INFO]`, `[REQ]`, `[OK]`, `[ERRO]`

### Bash Scripts

```bash
#!/bin/bash
# ✅ Verificar comandos antes de usar
if ! command -v omniroute &> /dev/null; then
    echo "❌ OmniRouter não encontrado"
    exit 1
fi
```

**Regras:**
- Verificar dependências com `command -v`
- Usar `lsof` ou `fuser` para verificar portas (fallback entre ambos)
- Mensagens com emojis (🚀, ✅, ❌, 📦, ℹ️)
- Caminhos relativos com `"$(cd "$(dirname "$0")" && pwd)"`

## 🚀 Comandos Úteis

```bash
# Setup completo (detecta SO automaticamente)
python3 setup_opencode.py

# Iniciar proxy
cd Proxy && ./iniciar.sh         # Linux/macOS/WSL
cd Proxy && iniciar.bat          # Windows

# Parar proxy
cd Proxy && ./parar.sh

# Ver logs
tail -f Proxy/proxy.log

# Dashboard OmniRouter
# http://localhost:20128
```

## 🧪 Testando seu Código

### Proxy (`micro_proxy_opencode.js`)
- Após modificar, reinicie com `./parar.sh && ./iniciar.sh`
- Verifique os logs em `proxy.log`
- Teste com curl:
  ```bash
  curl -s -X POST http://localhost:20129/v1/messages \
    -H "Content-Type: application/json" \
    -d '{"model":"oc/deepseek-v4-flash-free","messages":[{"role":"user","content":"Olá"}],"max_tokens":50}'
  ```

### Setup (`setup_opencode.py`)
- O script é idempotente: remova marcadores para refazer passos
  ```bash
  rm -rf ~/.local/share/setup-opencode-markers/
  python3 setup_opencode.py
  ```
- Teste em diferentes SO se possível (WSL, Ubuntu, Windows)

## 🔍 Troubleshooting

**Proxy não responde na porta 20129**
```bash
# Verificar se está rodando
lsof -i :20129 || fuser 20129/tcp
# Ver logs
tail -20 Proxy/proxy.log
```

**OmniRouter não está rodando**
```bash
omniroute serve --port 20128 --daemon
```

**Bun não encontrado no Windows**
```bash
# Verificar PATH
where bun
# Reinstalar
powershell -c "iwr bun.sh/install -useb | iex"
```

## 📝 Convenções

- **Commits**: Português brasileiro
- **Prefixo de commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- **Código**: Comentários em português, identificadores em inglês
- **Docstrings**: Google Style em inglês
- **Logs**: Em português para o usuário final
