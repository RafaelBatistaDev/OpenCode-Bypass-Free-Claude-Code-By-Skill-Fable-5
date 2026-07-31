# Análise Comparativa: 9Router vs OmniRouter vs OpenCode-Bypass

## Contexto

No ecossistema de bypass e roteamento de APIs de IA, três soluções se destacam para conectar clientes compatíveis com a API Anthropic a provedores alternativos (OpenAI, OpenCode, etc.). Este documento analisa **9Router**, **OmniRouter** e a abordagem híbrida do **OpenCode-Bypass**.

---

## 1. 9Router (N9Router)

### O que é

9Router (anteriormente conhecido como N9Router) é um middleware de roteamento que traduz chamadas da API Anthropic para o formato OpenAI. Foi uma das primeiras soluções a permitir o uso de clientes Anthropic com backends não-Anthropic.

### Arquitetura

```
Cliente → 9Router (única camada) → Provider (OpenAI/OpenCode)
```

### Pontos Fortes

- **Simplicidade**: Roteador único, sem dependências externas
- **Leve**: Implementação minimalista em JavaScript
- **Histórico**: Pioneiro na categoria, bem documentado pela comunidade

### Limitações

| Aspecto | Limitação |
|---------|-----------|
| **Manutenção** | Frequentemente abandona atualizações; breaking changes do Claude Code quebram o roteador |
| **Streaming** | Suporte limitado — falha em respostas longas com tool calls |
| **Ferramentas** | Tradução parcial de tool calls e tool results |
| **Logging** | Nenhum — debug requer intervenção manual |
| **Configuração** | Apenas via variáveis de ambiente ou args de CLI; sem interface |
| **Atualizações** | Lento para acompanhar mudanças no protocolo Anthropic |

---

## 2. OmniRouter

### O que é

OmniRouter é um roteador moderno que substitui o 9Router. Tradução completa bidirecional entre formatos Anthropic ↔ OpenAI, com suporte robusto a ferramentas, streaming e gerenciamento de contexto.

### Arquitetura

```
Cliente → OmniRouter (única camada) → Provider (OpenCode/OpenAI)
```

### Pontos Fortes

- **Tradução completa**: Suporte nativo a tool calls, tool results, system messages com estrutura complexa
- **Streaming robusto**: SSE (Server-Sent Events) funcional com retransmissão correta de eventos
- **Dashboard**: Interface web para monitoramento em `http://localhost:20128`
- **Gerenciamento**: Comando CLI `omniroute` para start/stop/status
- **Ativo**: Mantido e atualizado regularmente

### Limitações

| Aspecto | Limitação |
|---------|-----------|
| **Personalização** | Caixa-preta — o usuário não pode interceptar ou modificar requisições |
| **Controle de Acesso** | Nenhum — qualquer processo na máquina pode usá-lo |
| **Model Mapping** | Rígido — não permite fallback entre modelos livremente |
| **Logging Detalhado** | Apenas nível básico via dashboard; sem logs estruturados para análise offline |
| **Dependência Pesada** | Ecossistema npm completo; instalação global obrigatória |

---

## 3. OpenCode-Bypass (Este Projeto)

### O que é

Uma **arquitetura híbrida em duas camadas** que combina um micro-proxy personalizável (escrito em Bun) com o OmniRouter por baixo. O proxy **intercepta, traduz e aumenta** as requisições antes de enviá-las ao OmniRouter, dando ao usuário controle total sobre o pipeline.

### Arquitetura

```
Cliente Code → Seu Proxy (20129) → OmniRouter (20128) → OpenCode
                    ↓                    ↓
              Controle total       Tradução completa
              + Logging            + Ferramentas
              + Personalização     + Streaming
```

### Inovações e Melhorias

#### 1. 🏗️ **Arquitetura em Duas Camadas**

| Recurso | 9Router | OmniRouter | **OpenCode-Bypass** |
|---------|:-------:|:----------:|:-------------------:|
| Camadas de roteamento | 1 | 1 | **2** |
| Separação de responsabilidades | ❌ | ❌ | **✅** |
| Proxy substituível | ❌ | ❌ | **✅** |

A camada extra não é redundância — é uma **separação de responsabilidades**:
- **Proxy Layer (20129)**: Interceptação, logging, controle de acesso, mapeamento de modelos, transformação
- **Router Layer (20128)**: OmniRouter faz o que faz de melhor — tradução completa e ferramentas

#### 2. 📝 **Logging Estruturado e Detalhado**

```bash
# Exemplo de log do OpenCode-Bypass
[INFO] Requisição recebida - Stream: false
[REQ] Enviando requisição para OmniRouter (oc/deepseek-v4-flash-free)...
[OK] Resposta processada (15234 chars).
```

Enquanto 9Router não faz logging e OmniRouter tem logging mínimo, o OpenCode-Bypass:
- Loga **cada requisição** com modelo, tamanho e status
- Arquivo `proxy.log` persistente para análise offline
- Facilita debug sem precisar acessar dashboard

#### 3. 🎯 **Controle e Personalização do Proxy**

Diferente de 9Router e OmniRouter (ambos caixa-preta), o micro-proxy é **100% customizável**:

```javascript
// Exemplo: você pode expandir o mapeamento de modelos facilmente
let finalModel = "oc/deepseek-v4-flash-free";
if (typeof body.model === "string") {
  if (body.model.includes("ling"))
    finalModel = "oc/ling-3.0-flash-free";
  else if (body.model.includes("north"))
    finalModel = "oc/north-mini-code-free";
  else if (body.model.includes("oc/"))
    finalModel = body.model;
}
```

**Possibilidades de expansão**:
- Rate limiting por IP
- Cache de respostas
- Mapeamento inteligente de modelos (fallback automático)
- Filtragem de conteúdo
- Estatísticas de uso
- Autenticação

#### 4. 🚀 **Setup Automatizado com Idempotência**

| Aspecto | 9Router | OmniRouter | **OpenCode-Bypass** |
|---------|:-------:|:----------:|:-------------------:|
| Setup automático | ❌ | ❌ | **✅** (`setup_opencode.py`) |
| Idempotente | N/A | N/A | **✅** (marcadores por passo) |
| Scripts start/stop | Manual | Manual | **✅** (`iniciar.sh` / `parar.sh`) |

O script `setup_opencode.py` instala tudo que é necessário com um comando:
```bash
python3 setup_opencode.py
```

Ele usa **marcadores idempotentes** — rode quantas vezes quiser, passos já concluídos são pulados automaticamente.

#### 5. 🔌 **Suporte a Múltiplos Modelos Gratuitos**

Diferente de soluções genéricas, o OpenCode-Bypass é pré-configurado para modelos **free-tier** do OpenCode:

| Modelo | Identificador |
|--------|---------------|
| DeepSeek V4 Flash Free | `oc/deepseek-v4-flash-free` |
| Ling 3.0 Flash Free | `oc/ling-3.0-flash-free` |
| North Mini Code Free | `oc/north-mini-code-free` |

#### 6. 🧹 **Normalização Inteligente de Conteúdo**

O micro-proxy implementa um serializador robusto que lida com **formatos complexos** de conteúdo Anthropic:

| Tipo de Bloco | 9Router | OmniRouter | **OpenCode-Bypass** |
|--------------|:-------:|:----------:|:-------------------:|
| `text` | ✅ Básico | ✅ | **✅** Completo |
| `tool_use` | ⚠️ Parcial | ✅ | **✅** Serializado |
| `tool_result` | ❌ | ✅ | **✅** Com suporte a array de conteúdo |
| `reasoning_content` | ❌ | ❌ | **✅** Extraído e preservado |

#### 7. 🔒 **Segurança por Design**

- **Sem exposição externa**: Todos os serviços rodam em `localhost`
- **API keys dummy**: Nenhuma chave real trafega ou é armazenada
- **Separação de portas**: Proxy (20129) e Router (20128) são isolados
- **Modo stealth**: Sem telemetria ou chamadas externas não solicitadas

---

## 📊 Tabela Comparativa Geral

| Característica | 9Router | OmniRouter | **OpenCode-Bypass** |
|---------------|:-------:|:----------:|:-------------------:|
| Tradução Anthropic → OpenAI | ✅ Parcial | ✅ Completa | **✅ Completa** |
| Streaming (SSE) | ⚠️ Limitado | ✅ | **✅** (via OmniRouter + camada extra) |
| Tool Calls / Ferramentas | ⚠️ Parcial | ✅ | **✅** |
| Logging Estruturado | ❌ | ⚠️ Mínimo | **✅ Detalhado** |
| Customização do Proxy | ❌ | ❌ | **✅ 100%** |
| Dashboard Web | ❌ | ✅ | **✅** (via OmniRouter) |
| Setup Automático | ❌ | ❌ | **✅** |
| Scripts Start/Stop | ❌ | Manual | **✅** |
| Model Mapping Flexível | ❌ | ❌ | **✅** |
| Rate Limiting | ❌ | ❌ | **✅ Potencial** |
| Cache | ❌ | ❌ | **✅ Potencial** |
| Suporte a Modelos Free | Manual | Manual | **✅ Pré-configurado** |
| Idempotência | ❌ | ❌ | **✅** |
| Código-Fonte Aberto | ✅ | ✅ | **✅** |
| Manutenção Ativa | ❌ | ✅ | **✅** |

---

## 🔮 Roadmap: O Que o OpenCode-Bypass Possibilita

A arquitetura em duas camadas abre portas que 9Router e OmniRouter sozinhos não oferecem:

1. **Balanceamento de Carga** — Distribuir requisições entre múltiplos providers (OmniRouter + OpenAI + OpenCode)
2. **Cache Inteligente** — Cachear respostas idênticas e evitar reprocessamento
3. **Fallback Automático** — Se `oc/deepseek-v4-flash-free` falhar, tentar `oc/ling-3.0-flash-free`
4. **Auditoria de Uso** — Coletar métricas de tokens, latência e modelos usados
5. **Plugins** — Middleware pluginável para transformar requisições/respostas
6. **Filtragem de Conteúdo** — Sanitizar ou enriquecer mensagens antes de enviar ao provider
7. **Modo Multi-tenant** — Diferentes usuários com diferentes configurações de proxy

---

> **Conclusão:** Enquanto 9Router foi o pioneiro e OmniRouter elevou o nível com tradução completa, o **OpenCode-Bypass** combina o melhor de ambos com uma **camada de controle personalizável** que nenhum dos dois oferece. É a evolução natural do conceito: não apenas rotear, mas dar ao desenvolvedor **controle total sobre o pipeline** de IA.
