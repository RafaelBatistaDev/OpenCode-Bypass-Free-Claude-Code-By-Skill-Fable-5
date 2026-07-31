<div align="center">

# 🔓 Claude-Code-Bypass-Free-OpenCode

**Proxy inteligente para usar Claude Code com modelos gratuitos via OpenCode**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Runtime: Bun](https://img.shields.io/badge/Runtime-Bun-14151a?logo=bun)](https://bun.sh)
[![Router: OmniRouter](https://img.shields.io/badge/Router-OmniRouter-8B5CFE)](https://omnirouter.dev)
[![Model: Free Tier](https://img.shields.io/badge/Model-Free_Tier-22c55e)](https://opencode.ai)
[![Status: Estável](https://img.shields.io/badge/Status-Est%C3%A1vel-22c55e)](#)
[![PRs: Bem-vindos](https://img.shields.io/badge/PRs-Bem--vindos-ff69b4)](#)

**Uma arquitetura híbrida em duas camadas que dá a você controle total sobre o pipeline de IA** — sem depender de chaves de API pagas.

</div>

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Arquitetura](#-arquitetura)
- [Comparativo com Alternativas](#-comparativo-com-alternativas)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação Rápida](#-instalação-rápida)
- [Uso](#-uso)
- [Modelos Disponíveis](#-modelos-disponíveis)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Funcionalidades Detalhadas](#-funcionalidades-detalhadas)
- [Roadmap](#-roadmap)
- [Contribuição](#-contribuição)
- [Licença](#-licença)

---

## 🧠 Visão Geral

O **OpenCode-Bypass** resolve um problema simples: usar o Claude Code (que nativamente só fala com a API Anthropic) com modelos gratuitos do OpenCode sem precisar de chaves de API.

Enquanto outras soluções como **9Router** e **OmniRouter** oferecem apenas uma camada de roteamento, este projeto implementa uma **arquitetura em duas camadas** que separa o roteamento (tradução de protocolo) do controle (personalização, logging, segurança).

| Você quer... | OpenCode-Bypass entrega... |
|---|---|
| Usar Claude Code sem pagar | ✅ Proxy gratuito para OpenCode |
| Controlar o pipeline de requisições | ✅ Micro-proxy 100% customizável |
| Logs detalhados de cada chamada | ✅ Logging estruturado em arquivo |
| Setup em segundos | ✅ Script automático idempotente |
| Múltiplos modelos free | ✅ Pré-configurado para 3+ modelos |

---

## 🏗️ Arquitetura

### Diagrama de Fluxo

```
┌─────────────────────────────────────────────────────────────────┐
│                      SEU COMPUTADOR                              │
│                                                                  │
│  ┌────────────┐     ┌──────────────────┐     ┌──────────────┐   │
│  │            │     │                  │     │              │   │
│  │ Claude     │────▶│  Micro Proxy     │────▶│  OmniRouter  │   │
│  │ Code (CLI) │     │  (Porta 20129)   │     │  (Porta 20128)│   │
│  │            │◀────│                  │◀────│              │   │
│  └────────────┘     └──────────────────┘     └──────┬───────┘   │
│       Formato              Tradução                   │          │
│       Anthropic            básica + logs              │          │
│                                                      │          │
│                                           ┌──────────▼────────┐  │
│                                           │                   │  │
│                                           │    OpenCode API   │  │
│                                           │  (Modelos Free)   │  │
│                                           │                   │  │
│                                           └───────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Por que duas camadas?

A separação não é redundância — é **responsabilidade única**:

| Camada | O que faz | Por que separar |
|--------|-----------|-----------------|
| **Proxy** (porta 20129) | Intercepta, loga, mapeia modelos, controla acesso | **Você controla** — pode modificar, expandir, personalizar |
| **Router** (porta 20128) | OmniRouter: tradução completa Anthropic ↔ OpenAI, ferramentas, streaming | **OmniRouter faz isso melhor** que qualquer rewrite caseiro |

> 🔍 **Análise completa**: Veja o [comparativo detalhado](docs/comparative-analysis.md) entre 9Router, OmniRouter e esta solução.

---

## 📊 Comparativo com Alternativas

| Característica | 9Router | OmniRouter | **OpenCode-Bypass** 🏆 |
|---|---|---|---|
| Tradução Anthropic → OpenAI | ⚠️ Parcial | ✅ Completa | ✅ **Completa** |
| Streaming (SSE) | ⚠️ Limitado | ✅ Robusto | ✅ **Robusto** |
| Tool Calls | ⚠️ Parcial | ✅ Completo | ✅ **Completo** |
| Proxy Customizável | ❌ | ❌ | ✅ **100% customizável** |
| Logging Estruturado | ❌ | ⚠️ Mínimo | ✅ **Detalhado em arquivo** |
| Setup Automático | ❌ | ❌ | ✅ **1 comando** |
| Scripts Start/Stop | ❌ | Manual | ✅ `iniciar.sh` / `parar.sh` |
| Mapeamento de Modelos | ❌ | ❌ | ✅ **Flexível** |
| Dashboard Web | ❌ | ✅ | ✅ (via OmniRouter) |
| Configuração Idempotente | ❌ | ❌ | ✅ |
| Modelos Free Pré-configurados | ❌ | ❌ | ✅ |

> 📖 Leia o [guia do agente](docs/agent-guide.md) para diretrizes de desenvolvimento.

---

## ✅ Pré-requisitos

- **Sistema operacional**: Linux (Ubuntu e derivados, Fedora e derivados, Arch; testado no Fedora Kinoite/COSMIC), Windows 11 nativo, WSL 1/2 ou macOS
  - **Ubuntu e derivados**: Ubuntu, Debian, Linux Mint, Pop!_OS, Zorin OS, Kubuntu, Xubuntu, etc. (gerenciador `apt`)
  - **Fedora e derivados**: Fedora, Nobara, Ultramarine, Rocky Linux, AlmaLinux, etc. (gerenciador `dnf`/`rpm-ostree`)
  - **Windows 11 nativo**: usa PowerShell + `winget`/`choco` (scripts `.bat` criados automaticamente)
  - **WSL 1/2**: distribuição Linux (geralmente Ubuntu) com integração nativa
- **curl** e **lsof** (instalados na maioria dos sistemas)
- **Git** (opcional, para clonar)

> ⚡ O Bun e o OmniRouter são instalados automaticamente pelo script de setup.

---

## 🚀 Instalação Rápida

```bash
# Clone o repositório
git clone https://github.com/RafaelBatistaDev/OpenCode-Bypass-Free-Claude-Code-By-Skill-Fable-5.git
cd OpenCode-Bypass-Free-Claude-Code-By-Skill-Fable-5

# Setup completo (instala Bun, OmniRouter, configura tudo)
python3 setup_opencode.py
```

> ✨ **Idempotente**: Pode rodar várias vezes — passos já concluídos são pulados automaticamente.

### Instalação Manual

```bash
# 1. Entre no diretório do proxy
cd Proxy

# 2. Inicie o proxy (inicia OmniRouter + micro-proxy)
./iniciar.sh

# 3. Configure as variáveis de ambiente
export ANTHROPIC_BASE_URL=http://localhost:20129
export ANTHROPIC_API_KEY=dummy
export CLAUDE_CODE_MODEL=oc/deepseek-v4-flash-free
```

---

## 🎮 Uso

### Iniciar o Proxy

```bash
cd Proxy && ./iniciar.sh
```

### Usar com Claude Code

```bash
export ANTHROPIC_BASE_URL=http://localhost:20129
export ANTHROPIC_API_KEY=dummy
export CLAUDE_CODE_MODEL=oc/deepseek-v4-flash-free
claude
```

> 💡 Para persistir as configurações, edite `~/.config/secrets.env` com os valores acima.

### Parar o Proxy

```bash
cd Proxy && ./parar.sh
```

### Ver Logs

```bash
tail -f Proxy/proxy.log
```

### Dashboard OmniRouter

Acesse [http://localhost:20128](http://localhost:20128) no navegador.

---

## 🎯 Modelos Disponíveis

| Modelo | Identificador | Tipo |
|--------|--------------|------|
| **DeepSeek V4 Flash Free** | `oc/deepseek-v4-flash-free` | 🆓 Gratuito (padrão) |
| **Ling 3.0 Flash Free** | `oc/ling-3.0-flash-free` | 🆓 Gratuito |
| **North Mini Code Free** | `oc/north-mini-code-free` | 🆓 Gratuito |
| Outros via OmniRouter | `oc/<modelo>` | ✅ Disponível |

Para usar um modelo diferente:

```bash
export CLAUDE_CODE_MODEL=oc/ling-3.0-flash-free
claude
```

---

## 📁 Estrutura do Projeto

```
OpenCode-Bypass/
│
├── Proxy/                              # 🖥️ Camada de proxy
│   ├── micro_proxy_opencode.js         #    Micro-proxy em Bun (porta 20129)
│   ├── iniciar.sh                      #    Script para iniciar serviços
│   └── parar.sh                        #    Script para parar serviços
│
├── scripts/                            # ⚙️ Scripts auxiliares
│   ├── apply-claude-config.sh          #    Aplica config no ~/.claude.json
│   └── apply-secrets-config.sh         #    Aplica config no secrets.env
│
├── docs/                               # 📚 Documentação
│   ├── quickstart.md                   #    Guia rápido de início
│   ├── comparative-analysis.md         #    Análise: 9Router vs OmniRouter vs Bypass
│   └── agent-guide.md                  #    Diretrizes para agentes de código
│
├── setup_opencode.py                   # 🚀 Setup automático (1 comando)
├── LICENSE                             # 📄 Licença MIT
├── README.md                           #    Este arquivo
└── .gitignore                          #    Arquivos ignorados pelo Git
```

---

## 🔧 Funcionalidades Detalhadas

### 1. Proxy Customizável (`micro_proxy_opencode.js`)

O coração do projeto. Um servidor HTTP em Bun que:

- ✨ **Traduz** formato Anthropic → OpenAI
- 📝 **Loga** cada requisição com modelo, tamanho e status
- 🔄 **Mapeia** modelos automaticamente (deepseek → oc/deepseek, etc.)
- 🧠 **Serializa** conteúdo complexo (tool_calls, tool_results, reasoning)
- 🚦 **Gerencia erros** com respostas padronizadas

### 2. Setup Idempotente (`setup_opencode.py`)

Script Python que:

- ✅ Instala **Bun** (runtime JS) se ausente
- ✅ Instala **OmniRouter** via Bun se ausente
- ✅ Prepara **scripts do proxy** (permite execução)
- ✅ Cria **secrets.env** template
- ✅ Aplica **configurações do Claude**
- ✅ **Verifica** tudo no final com relatório detalhado
- 🔄 **Marcadores**: cada passo concluído é registrado em `~/.local/share/setup-opencode-markers/`

### 3. Scripts de Gerenciamento

| Script | Função |
|--------|--------|
| `iniciar.sh` | Inicia OmniRouter + micro-proxy com verificação de saúde |
| `parar.sh` | Para o micro-proxy e opcionalmente o OmniRouter |

### 4. Configuração Automática do Claude

Os scripts em `scripts/` configuram automaticamente:
- `~/.claude.json`: Adiciona API key dummy e modelos free
- `~/.config/secrets.env`: Configura variáveis de ambiente

---

## 🗺️ Roadmap

### Versão 1.1
- [ ] **Cache inteligente**: Cachear respostas idênticas
- [ ] **Modo streaming**: Suporte completo a SSE no proxy
- [ ] **Rate limiting**: Controle de requisições por período
- [ ] **Fallback automático**: Tentar próximo modelo se o atual falhar

### Versão 2.0
- [ ] **Balanceamento de carga**: Distribuir entre múltiplos providers
- [ ] **Plugins**: Middleware pluginável para transformar payloads
- [ ] **CLI interativa**: Comando `opencode-bypass` com subcomandos
- [ ] **Multi-tenant**: Diferentes usuários com diferentes configurações
- [ ] **Estatísticas de uso**: Dashboard com métricas de tokens e latência

---

## 🤝 Contribuição

Contribuições são **muito bem-vindas**!

1. Faça um **fork** do projeto
2. Crie uma **branch** (`git checkout -b feature/nova-feature`)
3. Faça **commit** das mudanças (`git commit -m 'Adiciona nova feature'`)
4. Faça **push** (`git push origin feature/nova-feature`)
5. Abra um **Pull Request**

### Diretrizes

- Mantenha o código compatível com **Bun** (Node.js não é necessário)
- Siga o estilo existente (ESM, JSDoc)
- Teste com `./iniciar.sh` antes de abrir PR
- Consulte o [guia do agente](docs/agent-guide.md) para diretrizes detalhadas

---

## 📄 Licença

Distribuído sob licença **MIT**. Veja [`LICENSE`](LICENSE) para mais informações.

---

<div align="center">

**Feito com ☕ e 🐍 por [Rafael Batista](https://github.com/RafaelBatistaDev)**

[![GitHub](https://img.shields.io/badge/GitHub-RafaelBatistaDev-181717?logo=github)](https://github.com/RafaelBatistaDev)

</div>
