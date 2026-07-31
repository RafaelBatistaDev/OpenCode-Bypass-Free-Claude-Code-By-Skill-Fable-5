// ═══════════════════════════════════════════════════════════════
// MICRO-PROXY CLAUDE -> OMNIROUTER -> OPENCODE
// Melhorias: timeouts, retry, cache LRU, métricas, health check,
//            gerenciamento de memória e graceful shutdown
// ═══════════════════════════════════════════════════════════════

// 1. Strict Imports (ESM)
import process from "node:process";
import { createHash } from "node:crypto";

// 2. Constants / Types
const LOCAL_PORT = 20129; // Mudamos para 20129 para não conflitar com OmniRouter
const OMNIROUTE_URL = "http://localhost:20128"; // OmniRouter roda na 20128

// ── 1.1 Timeouts configuráveis (em milissegundos) ──────────────
const TIMEOUT_CONEXAO = 10000;  // 10s — timeout de conexão
const TIMEOUT_LEITURA = 30000;  // 30s — timeout de leitura
const TIMEOUT_TOTAL   = 60000;  // 60s — timeout total da requisição
const TIMEOUT_HEALTH  = 5000;   // 5s  — timeout do health check

// ── 1.2 Retry com backoff exponencial ──────────────────────────
const MAX_RETRIES = 3;          // máximo de 3 retries por requisição
const RETRY_BASE_MS = 1000;     // backoff: base * 2^attempt (1s, 2s, 4s)

// ── 1.3 Cache inteligente (LRU) ────────────────────────────────
const CACHE_TTL = 5 * 60 * 1000;       // 5 minutos de vida para respostas
const CACHE_MAX_SIZE = 100;            // limite de 100 entradas no cache

// ── 1.5 Health check e memória ─────────────────────────────────
const HEALTH_CHECK_INTERVAL = 60 * 1000;  // verificar OmniRouter a cada 60s
const MEMORY_CHECK_INTERVAL = 5 * 1000;   // verificar memória a cada 5s
const MEMORIA_LIMITE_GC_MB = 400;         // GC manual se memória > 400MB
const MEMORIA_LIMITE_ALERTA_MB = 500;     // alerta se memória > 500MB

// ── Auto-shutdown por inatividade ──────────────────────────────
const IDLE_TIMEOUT = 30 * 60 * 1000;  // 30 minutos sem requisições
const IDLE_CHECK_INTERVAL = 60 * 1000; // verificação a cada 60s

// 3. Configuration (Colors / Logging)
const logInfo = (msg) => console.info(`[INFO] ${msg}`);
const logError = (msg) => console.error(`[ERRO] ${msg}`);
const logWarn = (msg) => console.warn(`[AVISO] ${msg}`);

// ═══════════════════════════════════════════════════════════════
// 1.3 SISTEMA DE CACHE LRU
// ═══════════════════════════════════════════════════════════════
// Map preserva ordem de inserção — perfeito para LRU.
// Acesso a uma chave a move para o fim; quando chega ao limite,
// removemos a entrada mais antiga (início do Map).
const cache = new Map();

/**
 * Gera uma chave estável para o cache a partir do payload.
 * @param {object} body - Corpo da requisição (model, system, messages)
 * @returns {string} hash SHA-256 do conteúdo serializado
 */
function generateCacheKey(body) {
  const relevant = {
    model: body.model || "",
    system: body.system || "",
    messages: body.messages || [],
    max_tokens: body.max_tokens || null,
    temperature: body.temperature ?? null,
  };
  return createHash("sha256").update(JSON.stringify(relevant)).digest("hex");
}

/**
 * Busca uma entrada no cache e a move para o fim (LRU).
 * @param {string} key - Chave gerada por generateCacheKey
 * @returns {object|null} resposta cacheada ou null (miss/expirado)
 */
function getFromCache(key) {
  const entry = cache.get(key);
  if (!entry) return null;

  // Expiração por TTL
  if (Date.now() - entry.insertedAt > CACHE_TTL) {
    cache.delete(key);
    return null;
  }

  // Move a entrada para o fim (mais recente)
  cache.delete(key);
  cache.set(key, entry);
  return entry.value;
}

/**
 * Insere (ou atualiza) uma resposta no cache respeitando o limite LRU.
 * @param {string} key - Chave gerada por generateCacheKey
 * @param {object} value - Resposta Anthropic a ser cacheada
 */
function setToCache(key, value) {
  cache.delete(key); // remove se já existia, para reinserir como mais recente
  cache.set(key, { value, insertedAt: Date.now() });

  // Evita estourar o limite: remove a entrada mais antiga
  if (cache.size > CACHE_MAX_SIZE) {
    const oldest = cache.keys().next().value;
    if (oldest !== undefined) cache.delete(oldest);
  }
}

/**
 * Limpa entradas expiradas do cache (chamado periodicamente).
 */
function cleanupCache() {
  const now = Date.now();
  for (const [key, entry] of cache) {
    if (now - entry.insertedAt > CACHE_TTL) cache.delete(key);
  }
}

// ═══════════════════════════════════════════════════════════════
// 1.4 SISTEMA DE MÉTRICAS EM TEMPO REAL
// ═══════════════════════════════════════════════════════════════
const metricas = {
  requests: { total: 0, success: 0, error: 0 },
  latency: { sum_ms: 0, samples: 0 },      // média móvel simples
  errorsByType: {},
  cache: { hits: 0, misses: 0 },
  memory: { max_usage_mb: 0, current_mb: 0 },
  inicio: Date.now(),
  omniHealthy: false,
};

/**
 * Registra o resultado de uma requisição nas métricas.
 * @param {boolean} ok - Se a requisição foi bem-sucedida
 * @param {string} [errorType] - Tipo do erro, quando aplicável
 * @param {number} [ms] - Tempo de resposta em milissegundos
 */
function registrarRequisicao(ok, errorType, ms) {
  metricas.requests.total++;
  if (ok) {
    metricas.requests.success++;
  } else {
    metricas.requests.error++;
    metricas.errorsByType[errorType || "desconhecido"] =
      (metricas.errorsByType[errorType || "desconhecido"] || 0) + 1;
  }
  if (typeof ms === "number") {
    metricas.latency.sum_ms += ms;
    metricas.latency.samples++;
  }
}

/**
 * Atualiza métricas de memória e devolve uso em MB.
 * @returns {number} uso de memória RSS em MB
 */
function atualizarMetricasMemoria() {
  const rssBytes = process.memoryUsage().rss;
  const mb = rssBytes / 1024 / 1024;
  metricas.memory.current_mb = Math.round(mb * 100) / 100;
  if (mb > metricas.memory.max_usage_mb) metricas.memory.max_usage_mb = Math.round(mb * 100) / 100;
  return mb;
}

/**
 * Serializa as métricas para o endpoint /metrics.
 * @returns {object} objeto de métricas formatado
 */
function snapshotMetricas() {
  const total = metricas.requests.total;
  return {
    requests: {
      total,
      success: metricas.requests.success,
      error: metricas.requests.error,
      success_rate: total ? Math.round((metricas.requests.success / total) * 10000) / 100 : 0,
    },
    latency: {
      avg_ms: metricas.latency.samples
        ? Math.round((metricas.latency.sum_ms / metricas.latency.samples) * 100) / 100
        : 0,
      total_samples: metricas.latency.samples,
    },
    cache: {
      hits: metricas.cache.hits,
      misses: metricas.cache.misses,
      hit_rate: metricas.cache.hits + metricas.cache.misses
        ? Math.round((metricas.cache.hits / (metricas.cache.hits + metricas.cache.misses)) * 10000) / 100
        : 0,
      size: cache.size,
      max_size: CACHE_MAX_SIZE,
      ttl_sec: CACHE_TTL / 1000,
    },
    memory: metricas.memory,
    errors_by_type: metricas.errorsByType,
    omni_healthy: metricas.omniHealthy,
    uptime_sec: Math.round((Date.now() - metricas.inicio) / 1000),
  };
}

// ═══════════════════════════════════════════════════════════════
// 1.2 SISTEMA DE RETRY COM BACKOFF EXPONENCIAL
// ═══════════════════════════════════════════════════════════════

/**
 * Executa fetch com timeout configurável via AbortController.
 * @param {string} url - URL de destino
 * @param {RequestInit} options - Opções do fetch
 * @param {number} timeoutMs - Timeout em milissegundos
 * @returns {Promise<Response>}
 */
async function fetchComTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (err) {
    if (err?.name === "AbortError") {
      const e = new Error(`Timeout após ${timeoutMs}ms`);
      e.cause = "timeout";
      throw e;
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Faz a requisição ao OmniRouter com retry e backoff exponencial.
 * @param {string} url - Endpoint do OmniRouter
 * @param {RequestInit} options - Opções do fetch
 * @returns {Promise<Response>}
 */
async function fetchWithRetry(url, options) {
  let lastError = null;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const response = await fetchComTimeout(url, options, TIMEOUT_TOTAL);

      // Não retenta em erros 4xx (problema do cliente)
      if (response.status >= 400 && response.status < 500) {
        return response;
      }
      // 5xx ou 429: retorna como está (o chamador decide)
      if (response.ok) return response;

      // Falhou (5xx): prepara retry se ainda houver tentativas
      if (attempt < MAX_RETRIES) {
        const wait = RETRY_BASE_MS * Math.pow(2, attempt);
        logWarn(`Resposta ${response.status} — retry ${attempt + 1}/${MAX_RETRIES} em ${wait}ms`);
        await new Promise((r) => setTimeout(r, wait));
        continue;
      }
      return response;
    } catch (err) {
      lastError = err;
      // Falha de rede/timeout: sempre retenta até o limite
      if (attempt < MAX_RETRIES) {
        const wait = RETRY_BASE_MS * Math.pow(2, attempt);
        logWarn(`Falha de conexão (${err.message}) — retry ${attempt + 1}/${MAX_RETRIES} em ${wait}ms`);
        await new Promise((r) => setTimeout(r, wait));
        continue;
      }
      throw err;
    }
  }
  throw lastError || new Error("Falha sem erro capturado");
}

// ═══════════════════════════════════════════════════════════════
// 1.5 HEALTH CHECK PERIÓDICO
// ═══════════════════════════════════════════════════════════════

/**
 * Verifica a saúde do OmniRouter e atualiza as métricas.
 * Usa /v1/models (o OmniRouter é um app Next.js; /health não existe).
 * Também limpa cache expirado.
 */
async function healthCheck() {
  try {
    const resp = await fetchComTimeout(`${OMNIROUTE_URL}/v1/models`, {}, TIMEOUT_HEALTH);
    // 401 significa servidor vivo mas autenticação exigida — ainda é "saudável"
    metricas.omniHealthy = resp.ok || resp.status === 401;
  } catch {
    metricas.omniHealthy = false;
  }
  cleanupCache();
}

/**
 * Monitora uso de memória; dispara GC manual e alerta quando necessário.
 */
function monitorarMemoria() {
  const mb = atualizarMetricasMemoria();
  if (mb > MEMORIA_LIMITE_GC_MB) {
    logWarn(`Memória em ${mb.toFixed(1)}MB — executando GC manual`);
    if (typeof Bun !== "undefined" && typeof Bun.gc === "function") {
      Bun.gc(true);
    }
  }
  if (mb > MEMORIA_LIMITE_ALERTA_MB) {
    logError(`ALERTA: uso de memória alto (${mb.toFixed(1)}MB)`);
  }
}

// ═══════════════════════════════════════════════════════════════
// TIMERS GLOBAIS (controlados no graceful shutdown)
// ═══════════════════════════════════════════════════════════════
let healthTimer = null;
let memoryTimer = null;
let idleTimer = null;
let ultimaRequisicao = Date.now();

/**
 * Atualiza a última requisição e reinicia o timer de inatividade.
 */
function resetarIdleTimer() {
  ultimaRequisicao = Date.now();
}

/**
 * Desliga o servidor se ficou inativo além do limite.
 */
function checkIdle() {
  if (Date.now() - ultimaRequisicao > IDLE_TIMEOUT) {
    logWarn(`Auto-shutdown ativado: servidor parará após ${IDLE_TIMEOUT / 1000}s de inatividade`);
    shutdown("idle");
  }
}

// ═══════════════════════════════════════════════════════════════
// 1.7 GRACEFUL SHUTDOWN
// ═══════════════════════════════════════════════════════════════
let serverRef = null;
let shuttingDown = false;

/**
 * Encerra o servidor de forma ordenada: limpa timers e fecha conexões.
 * @param {string} motivo - razão do encerramento
 */
function shutdown(motivo) {
  if (shuttingDown) return;
  shuttingDown = true;
  logInfo(`Encerrando servidor (${motivo})...`);
  clearInterval(healthTimer);
  clearInterval(memoryTimer);
  clearInterval(idleTimer);
  try {
    if (serverRef) serverRef.stop(true);
  } catch {
    /* processo já pode estar finalizando */
  }
  process.exit(0);
}

// 4. Core Logic
/**
 * Trata e serializa blocos de conteúdo do protocolo Anthropic para o formato OpenAI.
 * @param {Array|string} content
 * @returns {string}
 */
function serializeAnthropicContent(content) {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return String(content);

  return content
    .map((block) => {
      if (block.type === "text") {
        return block.text;
      }
      if (block.type === "tool_use") {
        return `[Tool Call: ${block.name} with input: ${JSON.stringify(block.input)}]`;
      }
      if (block.type === "tool_result") {
        const resultText = Array.isArray(block.content)
          ? block.content.map(c => c.text || "").join("\n")
          : block.content;
        return `[Tool Result for ${block.tool_use_id}]:\n${resultText}`;
      }
      return JSON.stringify(block);
    })
    .join("\n");
}

/**
 * Intercepta requisições do Claude Code e traduz bidirecionalmente.
 * @param {Request} req
 * @returns {Promise<Response>}
 */
async function handleRequest(req) {
  resetarIdleTimer();

  // ── Endpoint de métricas ────────────────────────────────────
  if (req.method === "GET" && req.url.includes("/metrics")) {
    return new Response(JSON.stringify(snapshotMetricas(), null, 2), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  // ── Endpoint de health check do próprio proxy ───────────────
  if (req.method === "GET" && req.url.includes("/health")) {
    const healthy = {
      status: metricas.omniHealthy ? "ok" : "degraded",
      omni_healthy: metricas.omniHealthy,
      uptime_sec: Math.round((Date.now() - metricas.inicio) / 1000),
    };
    return new Response(JSON.stringify(healthy), {
      status: metricas.omniHealthy ? 200 : 503,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (req.method === "POST" && req.url.includes("/v1/messages")) {
    const inicioReq = Date.now();
    try {
      const body = await req.json();

      logInfo(`[REQ] Requisição recebida - Stream: ${body.stream || false}`);

      // ── 1.3 Cache LRU: checa antes de chamar o upstream ──────
      const cacheKey = generateCacheKey(body);
      const cacheado = getFromCache(cacheKey);
      if (cacheado) {
        metricas.cache.hits++;
        registrarRequisicao(true, null, Date.now() - inicioReq);
        logInfo(`[OK] Cache hit (${(Date.now() - inicioReq).toFixed(0)}ms)`);
        return new Response(JSON.stringify(cacheado), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      metricas.cache.misses++;

      // 4.1. Normalização de Mensagens e Instruções do Sistema
      const openAiMessages = [];

      // Preserva todas as instruções de sistema
      if (body.system) {
        const systemText = Array.isArray(body.system)
          ? body.system.map(s => (typeof s === "string" ? s : s.text || "")).join("\n")
          : String(body.system);
        openAiMessages.push({ role: "system", content: systemText });
      }

      // Processa o histórico de mensagens
      if (Array.isArray(body.messages)) {
        for (const msg of body.messages) {
          const textContent = serializeAnthropicContent(msg.content);
          openAiMessages.push({ role: msg.role, content: textContent });
        }
      }

      // 4.2. Mapeamento do Modelo Operacional
      // OmniRouter exige prefixo de provider
      let finalModel = "oc/deepseek-v4-flash-free";
      if (typeof body.model === "string") {
        if (body.model.includes("ling")) finalModel = "oc/ling-3.0-flash-free";
        else if (body.model.includes("north")) finalModel = "oc/north-mini-code-free";
        else if (body.model.includes("oc/")) finalModel = body.model; // Já tem prefixo
      }

      const openAiPayload = {
        model: finalModel,
        messages: openAiMessages,
        max_tokens: body.max_tokens || 4096,
        temperature: body.temperature ?? 0.7,
        stream: false  // Forçando stream=false por enquanto
      };

      logInfo(`[REQ] Enviando requisição para OmniRouter (${finalModel})...`);

      // 4.3. Disparo HTTP para o OmniRouter (que chama OpenCode)
      // com retry + timeout (1.2 e 1.1)
      const response = await fetchWithRetry(OMNIROUTE_URL + "/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "User-Agent": "Mozilla/5.0 (Linux; Fedora) Bun/1.0",
          "x-api-key": "dummy" // OmniRouter não precisa de API key real
        },
        body: JSON.stringify(openAiPayload)
      });

      if (!response.ok) {
        const errorText = await response.text();
        logError(`HTTP ${response.status}: ${errorText.substring(0, 500)}`);
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const rawResponseText = await response.text();
      let openAiData;
      try {
        openAiData = JSON.parse(rawResponseText);
      } catch (parseError) {
        logError(`[DEBUG] Resposta bruta: ${rawResponseText.substring(0, 500)}`);
        logError(`[DEBUG] Tamanho: ${rawResponseText.length} chars`);
        throw new Error(`Resposta remota da OpenCode não é um JSON válido. Conteúdo: ${rawResponseText.substring(0, 200)}`);
      }

      // 4.4. Extração do Texto Gerado
      let extractedText = "";
      if (openAiData.choices && openAiData.choices.length > 0) {
        const choice = openAiData.choices[0];
        if (choice.message && choice.message.content) {
          extractedText = choice.message.content;
        }
        // OpenCode pode retornar conteúdo em reasoning_content
        if (choice.message && choice.message.reasoning_content) {
          if (extractedText) {
            extractedText += "\n\n" + choice.message.reasoning_content;
          } else {
            extractedText = choice.message.reasoning_content;
          }
        }
        if (!extractedText && choice.delta && choice.delta.content) {
          extractedText = choice.delta.content;
        }
        if (!extractedText && typeof choice.text === "string") {
          extractedText = choice.text;
        }
      } else if (typeof openAiData.response === "string") {
        extractedText = openAiData.response;
      }

      if (!extractedText) {
        extractedText = "OK";
      }

      // 4.5. Construção dos Blocos de Conteúdo Anthropic
      const anthropicResponse = {
        id: `msg_${Date.now()}`,
        type: "message",
        role: "assistant",
        model: body.model || finalModel,
        content: [
          {
            type: "text",
            text: extractedText
          }
        ],
        stop_reason: "end_turn",
        stop_sequence: null,
        usage: {
          input_tokens: body.messages ? body.messages.length * 15 : 100,
          output_tokens: Math.ceil(extractedText.length / 4)
        }
      };

      // ── 1.3 Cache LRU: salva a resposta ──────────────────────
      setToCache(cacheKey, anthropicResponse);

      const durMs = Date.now() - inicioReq;
      registrarRequisicao(true, null, durMs);
      logInfo(`[OK] Resposta processada (${extractedText.length} chars, ${durMs}ms).`);

      return new Response(JSON.stringify(anthropicResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      });
    } catch (err) {
      const durMs = Date.now() - inicioReq;
      const erroMsg = err instanceof Error ? err.message : String(err);
      registrarRequisicao(false, err?.cause === "timeout" ? "timeout" : "api_error", durMs);
      logError(`Falha na requisição: ${erroMsg}`);
      return new Response(
        JSON.stringify({ error: { type: "api_error", message: erroMsg } }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    }
  }

  return new Response("Not Found", { status: 404 });
}

// 5. Error Handling & Execution
if (import.meta.main) {
  try {
    logInfo(`Iniciando Micro-Proxy Claude->OmniRouter->OpenCode na porta ${LOCAL_PORT}`);
    logInfo(`OmniRouter deve estar rodando na porta 20128`);
    logInfo(`Timeouts: conexão ${TIMEOUT_CONEXAO / 1000}s, leitura ${TIMEOUT_LEITURA / 1000}s, total ${TIMEOUT_TOTAL / 1000}s`);
    logInfo(`Retry ativo: máximo ${MAX_RETRIES} com backoff exponencial`);
    logInfo(`Cache LRU ativo: ${CACHE_MAX_SIZE} entradas, TTL ${CACHE_TTL / 1000}s`);
    logInfo(`Health check do OmniRouter a cada ${HEALTH_CHECK_INTERVAL / 1000}s`);
    logInfo(`Auto-shutdown ativado: servidor parará após ${IDLE_TIMEOUT / 1000}s de inatividade`);

    // Health check inicial imediato + periódico
    healthCheck();
    healthTimer = setInterval(healthCheck, HEALTH_CHECK_INTERVAL);
    memoryTimer = setInterval(monitorarMemoria, MEMORY_CHECK_INTERVAL);
    idleTimer = setInterval(checkIdle, IDLE_CHECK_INTERVAL);

    serverRef = Bun.serve({
      port: LOCAL_PORT,
      async fetch(req) {
        try {
          return await handleRequest(req);
        } catch (err) {
          logError(`Falha na requisição: ${err instanceof Error ? err.message : String(err)}`);
          return new Response(
            JSON.stringify({ error: { type: "api_error", message: err.message } }),
            { status: 500, headers: { "Content-Type": "application/json" } }
          );
        }
      }
    });

    // 1.7 Graceful shutdown em SIGINT e SIGTERM
    process.on("SIGINT", () => shutdown("SIGINT"));
    process.on("SIGTERM", () => shutdown("SIGTERM"));
  } catch (erro) {
    logError("Falha fatal ao iniciar o servidor proxy:");
    logError(erro instanceof Error ? erro.message : String(erro));
    process.exit(1);
  }
}
