# OpenCode-Bypass — Guia para Agentes de Código

## 📋 Identidade e Stack

- **Linguagens**: Python 3, JavaScript (Bun), Bash
- **Runtime JS**: Bun (não Node.js)
- **Proxy**: `Proxy/micro_proxy_opencode.js` — servidor HTTP em Bun
- **Setup**: `setup_opencode.py` — script Python idempotente
- **Router**: OmniRouter (npm) — tradução Anthropic ↔ OpenAI
- **API**: OpenCode (modelos gratuitos: deepseek-v4-flash-free, etc.)
- **Sistema**: Linux (Fedora Kinoite/COSMIC), macOS, WSL2
- **Idioma**: Código em inglês, comentários/documentação em português brasileiro

## 📁 Estrutura do Projeto

```
OpenCode-Bypass/
├── Proxy/                        # 🖥️ Camada de proxy
│   ├── micro_proxy_opencode.js   #    Proxy principal (Bun)
│   ├── iniciar.sh                #    Start dos serviços
│   └── parar.sh                  #    Stop dos serviços
├── scripts/                      # ⚙️ Scripts auxiliares
│   ├── apply-claude-config.sh    #    Configura ~/.claude.json
│   └── apply-secrets-config.sh   #    Configura secrets.env
├── docs/                         # 📚 Documentação
│   ├── quickstart.md             #    Guia rápido
│   ├── comparative-analysis.md   #    Análise comparativa
│   └── agent-guide.md            #    Diretrizes para agentes
├── setup_opencode.py             # 🚀 Setup automático
├── README.md                     #    Documentação principal
├── LICENSE                       #    Licença MIT
└── CLAUDE.md                     #    Este arquivo
```

## 🔧 Regras de Desenvolvimento

### Proxy (`micro_proxy_opencode.js`)
1. Usar **ESM** (import/export), não CommonJS
2. Servidor via `Bun.serve()`, nunca `http.createServer()`
3. Logs em português: `[INFO]`, `[REQ]`, `[OK]`, `[ERRO]`
4. Manter compatibilidade com formato Anthropic e OpenAI
5. Não expor portas externas (localhost apenas)

### Scripts Python (`setup_opencode.py`)
1. Usar `pathlib.Path` — nunca `os.path.join()`
2. Usar `Path.home()` — nunca hardcodar `/home/user`
3. Idempotência com marcadores em `~/.local/share/setup-opencode-markers/`
4. Cores ANSI padronizadas (G/B/Y/R/C/N)
5. Type hints e docstrings Google Style

### Scripts Bash
1. Shebang `#!/bin/bash`
2. Verificar dependências antes de executar (`command -v`, `lsof`)
3. Mensagens com emojis indicativos (🚀, ✅, ❌, 📦)

### Commits
- Mensagens em português brasileiro
- Prefixos: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- Incluir `Co-Authored-By: Claude <noreply@anthropic.com>`

## 🚀 Comandos Úteis

```bash
# Setup completo
python3 setup_opencode.py

# Iniciar proxy
cd Proxy && ./iniciar.sh

# Parar proxy
cd Proxy && ./parar.sh

# Ver logs
tail -f Proxy/proxy.log

# Ver dashboard
# http://localhost:20128
```

## 🔍 Troubleshooting

**Proxy não responde na porta 20129**
```bash
lsof -i :20129
tail -20 Proxy/proxy.log
```

**OmniRouter não está rodando**
```bash
omniroute serve --port 20128 --daemon
```

**Refazer passo do setup**
```bash
rm ~/.local/share/setup-opencode-markers/NOME_DO_PASSO
python3 setup_opencode.py
```
