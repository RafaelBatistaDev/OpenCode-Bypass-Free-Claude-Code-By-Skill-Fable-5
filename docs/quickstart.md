# ⚡ Guia Rápido — OpenCode-Bypass

## PC Novo (Setup Completo)

```bash
python3 setup_opencode.py
```

Isso instala Bun, OmniRouter, configura o proxy e inicia tudo automaticamente.

## Já Configurado (Só Iniciar)

```bash
cd Proxy
./iniciar.sh
```

## Usar com Claude Code

```bash
export ANTHROPIC_BASE_URL=http://localhost:20129
export ANTHROPIC_API_KEY=dummy
claude
```

## Parar

```bash
cd Proxy
./parar.sh
```

## Arquitetura

```
Proxy (20129) → OmniRouter (20128) → OpenCode
```

- **Proxy**: `Proxy/micro_proxy_opencode.js` — seu ponto de controle
- **Router**: OmniRouter (npm) — tradução completa
- **API**: OpenCode — modelos gratuitos

## Dicas

- 📊 Dashboard: http://localhost:20128
- 📝 Logs: `tail -f Proxy/proxy.log`
- 🔄 Modelos: `export CLAUDE_CODE_MODEL=oc/ling-3.0-flash-free`
- 🏷️ Secrets: `~/.config/secrets.env`
