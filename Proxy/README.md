# 🖥️ Proxy Layer — OpenCode-Bypass

Camada de proxy personalizável que intercepta requisições do Claude Code e as encaminha para o OmniRouter.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `micro_proxy_opencode.js` | 🧩 Servidor proxy em Bun (porta 20129) |
| `iniciar.sh` | 🚀 Inicia OmniRouter + micro-proxy |
| `parar.sh` | 🛑 Para serviços |

## Como Funciona

```
Claude Code (Anthropic fmt) → Proxy (20129) → OmniRouter (20128) → OpenCode
```

1. **Proxy (20129)**: Traduz formato Anthropic para OpenAI, loga, mapeia modelos
2. **OmniRouter (20128)**: Tradução completa, ferramentas, streaming
3. **OpenCode**: API final com modelos gratuitos

## Uso Rápido

```bash
# Iniciar
./iniciar.sh

# Parar
./parar.sh

# Ver logs
tail -f proxy.log
```

## Personalização

Edite `micro_proxy_opencode.js` para:

- **Adicionar rate limiting** por IP
- **Cache de respostas** para reduzir latência
- **Fallback de modelos** (tentar B se A falhar)
- **Filtros de conteúdo** (sanitizar/enriquecer mensagens)
- **Métricas** de uso por modelo ou usuário

---

**Status:** ✅ Funcionando | **Portas:** Proxy 20129 → OmniRouter 20128
