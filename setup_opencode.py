#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de configuração universal do OpenCode-Bypass.

Suporta:
  - Linux (Ubuntu, Debian, Fedora, Arch, e derivados) via apt/pacman/rpm-ostree/dnf
  - Windows 11 nativo (PowerShell + Bun)
  - WSL 1/2 (Windows Subsystem for Linux)
  - macOS (via Homebrew)

Cada passo usa um arquivo marcador em ~/.local/share/setup-opencode-markers/
Se o marcador existe, o passo é pulado — pode rodar quantas vezes quiser.

Uso:
    python3 setup_opencode.py
"""

import os
import sys
import stat
import time
import json
import socket
import shutil
import platform
import subprocess
import urllib.request
from pathlib import Path


# ─────────────────────────────────────────────
# CORES
# ─────────────────────────────────────────────
G = "\033[1;32m"
B = "\033[1;34m"
Y = "\033[1;33m"
R = "\033[1;31m"
C = "\033[1;36m"
M = "\033[1;35m"
N = "\033[0m"

HOME       = Path.home()
BINDIR     = HOME / ".local" / "bin"
MARKER_DIR = HOME / ".local" / "share" / "setup-opencode-markers"
AQUI       = Path(__file__).parent.resolve()
PROXY_DIR  = AQUI / "Proxy"

# ──────────── DETECÇÃO DE SO ────────────────
SISTEMA = platform.system().lower()  # 'linux', 'windows', 'darwin'
IS_WINDOWS = SISTEMA == "windows"
IS_WSL = False
DISTRO = ""      # 'ubuntu', 'debian', 'fedora', 'arch', 'linuxmint', ...
ID_LIKE = ""     # família declarada no os-release: 'ubuntu', 'fedora', ...
FAMILIA = ""     # 'deb', 'rpm', 'arch', 'brew', 'win' — p/ gerenciador de pacotes


def detectar_familia() -> str:
    """
    Resolve a família de gerenciador de pacotes a partir da distro.

    Derivados (Linux Mint, Pop!_OS, Zorin, Kubuntu → ubuntu/debian;
    Nobara, Ultramarine, Rocky, Alma → fedora/rhel) são identificados
    pelo campo ID_LIKE do /etc/os-release.

    Returns:
        'deb' (apt), 'rpm' (dnf/yum), 'arch' (pacman), 'brew' (macOS)
        ou 'win' (Windows nativo).
    """
    global DISTRO, ID_LIKE

    if IS_WINDOWS:
        return "win"

    # Lê ID_LIKE de /etc/os-release quando disponível
    if not ID_LIKE and Path("/etc/os-release").exists():
        try:
            with open("/etc/os-release") as f:
                dados = dict(
                    linha.strip().split("=", 1)
                    for linha in f
                    if "=" in linha.strip()
                )
            ID_LIKE = dados.get("ID_LIKE", "").lower().strip('"')
        except Exception:
            pass

    if DISTRO in ("debian", "ubuntu") or any(p in ID_LIKE for p in ("debian", "ubuntu")):
        return "deb"
    if DISTRO in ("fedora", "rhel", "centos", "rocky", "alma") or any(
        p in ID_LIKE for p in ("fedora", "rhel", "centos")
    ):
        return "rpm"
    if DISTRO == "arch" or "arch" in ID_LIKE:
        return "arch"
    if SISTEMA == "darwin":
        return "brew"
    # Fallback: detecta pelo gerenciador instalado
    if shutil.which("apt"):
        return "deb"
    if shutil.which("dnf") or shutil.which("yum"):
        return "rpm"
    if shutil.which("pacman"):
        return "arch"
    if shutil.which("brew"):
        return "brew"
    return ""


if SISTEMA == "linux":
    # Detecta WSL
    if "microsoft" in platform.uname().release.lower():
        IS_WSL = True
        print(f"  {C}ℹ️  WSL detectado (Windows Subsystem for Linux){N}")

    # Detecta distro Linux
    if Path("/etc/os-release").exists():
        try:
            with open("/etc/os-release") as f:
                dados = dict(
                    linha.strip().split("=", 1)
                    for linha in f
                    if "=" in linha.strip()
                )
            DISTRO = dados.get("ID", "").lower().strip('"')
            ID_LIKE = dados.get("ID_LIKE", "").lower().strip('"')
        except Exception:
            pass
    elif Path("/etc/debian_version").exists():
        DISTRO = "debian"
        ID_LIKE = "debian"
    elif Path("/etc/fedora-release").exists():
        DISTRO = "fedora"
        ID_LIKE = "fedora"

    if not DISTRO and shutil.which("apt"):
        DISTRO = "debian"
        ID_LIKE = "debian"
    elif not DISTRO and shutil.which("dnf"):
        DISTRO = "fedora"
        ID_LIKE = "fedora"
    elif not DISTRO and shutil.which("pacman"):
        DISTRO = "arch"
        ID_LIKE = "arch"

elif SISTEMA == "windows":
    import ctypes

    def _is_admin() -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    IS_ADMIN = _is_admin()
    print(f"  {C}ℹ️  Windows 11 nativo detectado{' (Admin)' if IS_ADMIN else ''}{N}")

# Resolve a família de gerenciador de pacotes (usa ID_LIKE p/ derivados)
FAMILIA = detectar_familia()

# ─────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────
def log(msg):    print(f"{B}[INFO]{N}  {msg}")
def ok(msg):     print(f"{G}[OK]{N}    {msg}")
def aviso(msg):  print(f"{Y}[AVISO]{N} {msg}")
def erro(msg):   print(f"{R}[ERRO]{N}  {msg}")


def tem_comando(nome: str) -> bool:
    """Verifica se um comando existe no PATH (cross-platform)."""
    return shutil.which(nome) is not None


def roda(cmd: list[str], check: bool = True, timeout: int | None = None,
         capture: bool = False, shell: bool = False) -> subprocess.CompletedProcess | bool:
    """
    Executa um comando de forma cross-platform.

    Retorna CompletedProcess se capture=True, senão True/False.
    """
    cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
    log(f"$ {cmd_str}")

    try:
        result = subprocess.run(
            cmd,
            check=check,
            timeout=timeout,
            capture_output=capture,
            text=True,
            shell=shell,
        )
        return result if capture else True
    except subprocess.TimeoutExpired:
        if check:
            erro(f"Comando excedeu timeout ({timeout}s): {cmd_str}")
            sys.exit(1)
        return False
    except subprocess.CalledProcessError as e:
        if check:
            erro(f"Falha (código {e.returncode}): {cmd_str}")
            if e.stderr:
                erro(e.stderr.strip()[:500])
            sys.exit(1)
        return False
    except FileNotFoundError:
        if check:
            erro(f"Comando não encontrado: {cmd[0]}")
            sys.exit(1)
        return False
    except OSError as e:
        if check:
            erro(f"Erro de sistema: {e}")
            sys.exit(1)
        return False


def is_done(nome: str) -> bool:
    """Verifica se o passo já foi concluído pelo marcador."""
    return (MARKER_DIR / nome).exists()


def set_done(nome: str) -> None:
    """Marca o passo como concluído."""
    MARKER_DIR.mkdir(parents=True, exist_ok=True)
    (MARKER_DIR / nome).touch()


def pula_passo(nome: str) -> None:
    """Exibe mensagem de passo já concluído."""
    print(f"  {C}⏭️  {nome} já foi executado antes. Pulando.{N}\n")


def porta_ocupada(porta: int) -> bool:
    """Verifica se uma porta está em uso (cross-platform)."""
    if IS_WINDOWS:
        cmd = ["netstat", "-an"]
        result = roda(cmd, check=False, capture=True)
        if isinstance(result, subprocess.CompletedProcess):
            return f":{porta}" in result.stdout
        return False
    else:
        # Linux/macOS/WSL
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                return s.connect_ex(("127.0.0.1", porta)) == 0
        except Exception:
            return False


def matar_processo_por_porta(porta: int) -> None:
    """Mata processo ocupando uma porta (cross-platform)."""
    if IS_WINDOWS:
        # Windows: netstat + find PID, depois taskkill
        result = roda(
            ["netstat", "-ano"],
            check=False, capture=True
        )
        if isinstance(result, subprocess.CompletedProcess):
            for line in result.stdout.splitlines():
                if f":{porta}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        pid = parts[4]
                        roda(["taskkill", "/PID", pid, "/F"], check=False)
    else:
        # Linux/macOS/WSL: fuser ou lsof
        if tem_comando("fuser"):
            roda(["fuser", "-k", f"{porta}/tcp"], check=False)
        elif tem_comando("lsof"):
            roda(["sh", "-c", f"lsof -ti:{porta} | xargs -r kill -9"], check=False)
        elif tem_comando("ss"):
            pid = roda(
                ["ss", "-tlnp", f"sport = :{porta}"],
                check=False, capture=True, shell=True
            )
            if isinstance(pid, subprocess.CompletedProcess) and pid.stdout.strip():
                roda(["pkill", "-f", f":{porta}"], check=False)


def baixar_script(url: str, timeout: int = 60) -> str:
    """Baixa um script de URL com User-Agent (cross-platform)."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode()


def _executar_arquivo_config(arquivo: str, descricao: str) -> None:
    """
    Executa um dos arquivos de configuração (1-claude_config ou 2-claude_config).

    Os arquivos contêm comandos ``bun -e '...'`` inline, executados via Bash.
    Falhas não interrompem o setup — apenas exibem aviso.
    """
    caminho = AQUI / arquivo
    if not caminho.exists():
        aviso(f"{descricao}: arquivo '{arquivo}' não encontrado em {AQUI}")
        return

    if not tem_comando("bun"):
        aviso(f"{descricao}: Bun é necessário — pulando")
        return

    if not tem_comando("bash"):
        aviso(f"{descricao}: Bash é necessário — pulando")
        return

    log(f"Aplicando {descricao}...")
    try:
        result = subprocess.run(
            ["bash", str(caminho)],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            saida = result.stdout.strip()
            if saida:
                ok(f"{descricao}: {saida[:200]}")
            else:
                ok(f"{descricao} concluído!")
        else:
            aviso(f"{descricao} retornou código {result.returncode}")
            if result.stderr:
                aviso(result.stderr.strip()[:200])
    except subprocess.TimeoutExpired:
        aviso(f"{descricao} excedeu timeout (30s)")
    except OSError as e:
        aviso(f"{descricao} falhou: {e}")


# ─────────────────────────────────────────────
# 1. VERIFICAR DEPENDÊNCIAS DO SISTEMA
# ─────────────────────────────────────────────
def passo_verificar_sistema():
    nome = "VERIFICAR_SISTEMA"
    if is_done(nome):
        pula_passo("Verificação do sistema")
        return

    print(f"\n{M}═══ 1. Verificando dependências do sistema ═══{N}\n")

    # Dependências por plataforma
    if IS_WINDOWS:
        # Windows 11 nativo: PowerShell, Bun
        obrigatorios = []
        Opcionais = ["git"]
        tudo_ok = True

        # Verificar PowerShell
        ps_ok = tem_comando("powershell") or tem_comando("pwsh")
        if ps_ok:
            ok("PowerShell encontrado")
        else:
            erro("PowerShell não encontrado — essencial no Windows")
            tudo_ok = False

        # Verificar winget (opcional, para instalar Bun)
        if tem_comando("winget"):
            ok("winget encontrado (instalador de pacotes)")
        else:
            aviso("winget não encontrado — instalaremos Bun manualmente")

    elif IS_WSL:
        # WSL é basicamente Linux (usa a distro instalada no WSL)
        obrigatorios = ["curl"]
        Opcionais = ["git", "lsof", "fuser"]
        tudo_ok = True

        if DISTRO and FAMILIA:
            ok(f"Distro no WSL: {DISTRO} (família: {FAMILIA})")
        else:
            ok("WSL detectado — distro interna não identificada")

        for cmd in obrigatorios:
            if tem_comando(cmd):
                ok(f"{cmd} encontrado")
            else:
                erro(f"{cmd} não encontrado — essencial para o setup")
                tudo_ok = False

        for cmd in Opcionais:
            if tem_comando(cmd):
                ok(f"{cmd} encontrado")
            else:
                aviso(f"{cmd} não encontrado — opcional")

        # Aviso de dependências da distro dentro do WSL (derivados incluídos)
        if FAMILIA == "deb":
            aviso("No WSL com Ubuntu/Debian: sudo apt install -y build-essential curl git")
        elif FAMILIA == "rpm":
            aviso("No WSL com Fedora: sudo dnf groupinstall 'Development Tools'")
        elif FAMILIA == "arch":
            aviso("No WSL com Arch: sudo pacman -S --needed base-devel curl git")

    else:
        # Linux nativo (Ubuntu, Debian, Fedora, Arch e derivados)
        obrigatorios = ["curl"]
        Opcionais = ["git", "lsof", "fuser"]

        # Apresenta distro + família (derivados via ID_LIKE)
        if DISTRO and FAMILIA:
            ok(f"Distro detectada: {DISTRO} (família: {FAMILIA})")
        else:
            ok(f"Distro detectada: {DISTRO or 'desconhecida'}")
        tudo_ok = True

        for cmd in obrigatorios:
            if tem_comando(cmd):
                ok(f"{cmd} encontrado")
            else:
                erro(f"{cmd} não encontrado — essencial para o setup")
                tudo_ok = False

        for cmd in Opcionais:
            if tem_comando(cmd):
                ok(f"{cmd} encontrado")
            else:
                aviso(f"{cmd} não encontrado — opcional")

        # Aviso sobre dependências do sistema por família de pacotes
        # (cobre derivados: Mint/Pop!_OS/Zorin→apt, Nobara/Rocky/Alma→dnf)
        if FAMILIA == "deb":
            aviso("Certifique-se de ter build-essential: sudo apt install -y build-essential curl git")
        elif FAMILIA == "rpm":
            if shutil.which("rpm-ostree"):
                aviso("Sistema imutável (rpm-ostree): use sudo rpm-ostree install --idempotent gcc make")
            else:
                aviso("Certifique-se de ter @development-tools: sudo dnf groupinstall 'Development Tools'")
        elif FAMILIA == "arch":
            aviso("Certifique-se de ter base-devel: sudo pacman -S --needed base-devel curl git")

    print()
    if tudo_ok:
        ok("Sistema pronto para o setup.")
        set_done(nome)
    else:
        erro("Dependências essenciais faltando. Instale-as e tente novamente.")
        sys.exit(1)


# ─────────────────────────────────────────────
# 2. INSTALAR BUN
# ─────────────────────────────────────────────
def passo_instalar_bun():
    nome = "INSTALAR_BUN"
    if is_done(nome):
        pula_passo("Bun")
        return

    print(f"\n{M}═══ 2. Instalando Bun (runtime JS necessário) ═══{N}\n")

    if tem_comando("bun"):
        ok("Bun já instalado no PATH")
        set_done(nome)
        return

    if IS_WINDOWS:
        # Windows 11 nativo: instalação via PowerShell
        log("Instalando Bun via PowerShell...")
        ps_cmd = (
            'powershell -Command "'
            '[System.Net.ServicePointManager]::SecurityProtocol = 3072; '
            'iex ((New-Object System.Net.WebClient).DownloadString(\'https://bun.sh/install\'))"'
        )
        roda(ps_cmd, check=True, timeout=120, shell=True)

        # Adicionar ao PATH
        bun_path = HOME / ".bun" / "bin"
        if bun_path.exists():
            BINDIR.mkdir(parents=True, exist_ok=True)
            link = BINDIR / "bun"
            if not link.exists():
                try:
                    link.symlink_to(bun_path / "bun")
                except (OSError, NotImplementedError):
                    # Symlink pode não funcionar no Windows sem admin
                    shutil.copy2(bun_path / "bun", BINDIR / "bun.exe")
            os.environ["PATH"] = str(BINDIR) + os.pathsep + os.environ.get("PATH", "")
    else:
        # Linux / macOS / WSL
        aviso("Baixando e instalando Bun via script oficial...")
        script = baixar_script("https://bun.sh/install")
        subprocess.run(["sh"], input=script, capture_output=True, text=True, check=True)

        bun_bin = HOME / ".bun" / "bin" / "bun"
        if bun_bin.exists():
            BINDIR.mkdir(parents=True, exist_ok=True)
            link = BINDIR / "bun"
            if not link.exists():
                link.symlink_to(bun_bin)
            os.environ["PATH"] = str(BINDIR) + ":" + os.environ.get("PATH", "")
        else:
            erro("Bun não foi instalado corretamente")
            sys.exit(1)

    if tem_comando("bun"):
        ok(f"Bun instalado com sucesso ({HOME / '.bun'})")
        set_done(nome)
    else:
        erro("Falha ao instalar Bun. Tente manualmente: curl -fsSL https://bun.sh/install | bash")
        sys.exit(1)


# ─────────────────────────────────────────────
# 3. INSTALAR OMNIROUTER
# ─────────────────────────────────────────────
def passo_instalar_omnirouter():
    nome = "INSTALAR_OMNIROUTER"
    if is_done(nome):
        pula_passo("OmniRouter")
        return

    print(f"\n{M}═══ 3. Instalando OmniRouter ═══{N}\n")

    if tem_comando("omniroute"):
        ok("OmniRouter já instalado no PATH")
        set_done(nome)
        return

    if not tem_comando("bun"):
        erro("Bun é necessário para instalar OmniRouter")
        sys.exit(1)

    aviso("Instalando OmniRouter via Bun (pode levar alguns instantes)...")
    if IS_WINDOWS:
        roda(["bun", "install", "-g", "omniroute"], timeout=120)
    else:
        roda(["bun", "install", "-g", "omniroute"], timeout=120)

    if tem_comando("omniroute"):
        ok("OmniRouter instalado com sucesso!")
        set_done(nome)
    else:
        erro("Falha ao instalar OmniRouter. Tente manualmente:")
        erro("   bun install -g omniroute")
        sys.exit(1)


# ─────────────────────────────────────────────
# 4. GARANTIR EXECUTÁVEIS DO PROXY
# ─────────────────────────────────────────────
def passo_preparar_proxy():
    nome = "PREPARAR_PROXY"
    if is_done(nome):
        pula_passo("Preparação do proxy")
        return

    print(f"\n{M}═══ 4. Preparando scripts do Proxy ═══{N}\n")

    if not PROXY_DIR.exists():
        erro(f"Diretório do proxy não encontrado: {PROXY_DIR}")
        sys.exit(1)

    # No Windows, scripts .sh não são executáveis — criamos atalhos .bat
    if IS_WINDOWS:
        _criar_bat_scripts()

    # No Linux/macOS/WSL, dar permissão de execução
    if not IS_WINDOWS:
        for s in ["iniciar.sh", "parar.sh"]:
            caminho = PROXY_DIR / s
            if caminho.exists():
                modo_atual = caminho.stat().st_mode
                caminho.chmod(modo_atual | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
                ok(f"{s} pronto (executável)")
            else:
                erro(f"Script não encontrado: {caminho}")
                sys.exit(1)

    proxy_js = PROXY_DIR / "micro_proxy_opencode.js"
    if proxy_js.exists():
        ok(f"Proxy JS encontrado ({proxy_js.stat().st_size} bytes)")
    else:
        erro(f"Arquivo do proxy não encontrado: {proxy_js}")
        sys.exit(1)

    # Garantir arquivo de log
    log_file = PROXY_DIR / "proxy.log"
    log_file.touch(exist_ok=True)
    ok("Arquivo de log pronto")

    set_done(nome)


def _criar_bat_scripts():
    """Cria scripts .bat equivalentes para Windows nativo."""
    # iniciar.bat
    iniciar_bat = PROXY_DIR / "iniciar.bat"
    if not iniciar_bat.exists():
        iniciar_bat.write_text(
            "@echo off\r\n"
            "echo 🚀 Iniciando Proxy com OmniRouter...\r\n"
            "\r\n"
            ":: Verificar se omniroute existe\r\n"
            "where omniroute >nul 2>nul\r\n"
            "if %errorlevel% neq 0 (\r\n"
            "    echo ❌ OmniRouter nao encontrado. Instale primeiro.\r\n"
            "    exit /b 1\r\n"
            ")\r\n"
            "\r\n"
            ":: Iniciar OmniRouter em background\r\n"
            "echo 📦 Iniciando OmniRouter na porta 20128...\r\n"
            "start /B omniroute serve --port 20128\r\n"
            "timeout /t 3 >nul\r\n"
            "\r\n"
            ":: Iniciar micro-proxy\r\n"
            "echo 📦 Iniciando proxy na porta 20129...\r\n"
            "start /B bun run micro_proxy_opencode.js\r\n"
            "timeout /t 2 >nul\r\n"
            "\r\n"
            "echo ✅ Proxy iniciado! Use as variaveis:\r\n"
            "echo    set ANTHROPIC_BASE_URL=http://localhost:20129\r\n"
            "echo    set ANTHROPIC_API_KEY=dummy\r\n"
            "echo    claude\r\n"
        )
        ok("iniciar.bat criado")

    # parar.bat
    parar_bat = PROXY_DIR / "parar.bat"
    if not parar_bat.exists():
        parar_bat.write_text(
            "@echo off\r\n"
            "echo 🛑 Parando Proxy...\r\n"
            "\r\n"
            ":: Matar micro-proxy\r\n"
            "taskkill /F /IM bun.exe 2>nul\r\n"
            "echo ✅ Proxy parado (porta 20129)\r\n"
            "\r\n"
            ":: Perguntar se quer parar OmniRouter\r\n"
            "set /p DETENER=\"Deseja parar o OmniRouter também? (s/n): \"\r\n"
            "if /I \"%DETENER%\"==\"s\" (\r\n"
            "    taskkill /F /IM node.exe 2>nul\r\n"
            "    echo ✅ OmniRouter parado\r\n"
            ")\r\n"
        )
        ok("parar.bat criado")


# ─────────────────────────────────────────────
# 5. CRIAR SECRETS (Cross-platform)
# ─────────────────────────────────────────────
def passo_secrets():
    nome = "CRIAR_SECRETS"
    if is_done(nome):
        pula_passo("Secrets")
        return

    print(f"\n{M}═══ 5. Configurando variáveis de ambiente ═══{N}\n")

    if IS_WINDOWS:
        # Windows: criar script .bat de ambiente
        win_env = HOME / ".opencode" / "env.bat"
        win_env.parent.mkdir(parents=True, exist_ok=True)

        if not win_env.exists():
            win_env.write_text(
                "@echo off\r\n"
                ":: OpenCode-Bypass - Variaveis de ambiente\r\n"
                "set ANTHROPIC_BASE_URL=http://localhost:20129\r\n"
                "set ANTHROPIC_API_KEY=dummy\r\n"
                "set CLAUDE_CODE_MODEL=oc/deepseek-v4-flash-free\r\n"
            )
            win_env.chmod(0o600)
            ok(f"Script de ambiente criado: {win_env}")
            aviso("Execute: call ~/.opencode/env.bat antes de usar o Claude Code")
        else:
            ok(f"Arquivo de ambiente já existe: {win_env}")

        # Tentar configurar variáveis de usuário no Windows
        try:
            # Adiciona ao PATH do usuário via PowerShell (não persistente)
            aviso("Para persistir as variáveis, execute como Admin:")
            aviso('  setx ANTHROPIC_BASE_URL "http://localhost:20129"')
            aviso('  setx ANTHROPIC_API_KEY "dummy"')
            aviso('  setx CLAUDE_CODE_MODEL "oc/deepseek-v4-flash-free"')
        except Exception:
            pass

    else:
        # Linux / macOS / WSL: template secrets.env
        SECRETS = HOME / ".config" / "secrets.env"
        SECRETS.parent.mkdir(parents=True, exist_ok=True)

        if not SECRETS.exists():
            template = """# ~/.config/secrets.env — OpenCode-Bypass
# Use com: source ~/.config/secrets.env
export ANTHROPIC_BASE_URL="http://localhost:20129"
export ANTHROPIC_API_KEY="dummy"
export CLAUDE_CODE_MODEL="oc/deepseek-v4-flash-free"
"""
            SECRETS.write_text(template)
            SECRETS.chmod(0o600)
            ok(f"secrets.env criado: {SECRETS}")
            aviso("Edite se necessário: nano ~/.config/secrets.env")
            aviso("Ative com: source ~/.config/secrets.env")
        else:
            ok(f"secrets.env já existe: {SECRETS}")

    # Aplicar configurações adicionais via 2-claude_config
    _executar_arquivo_config(
        "2-claude_config",
        "Configurações adicionais de secrets (2-claude_config)"
    )

    set_done(nome)


# ─────────────────────────────────────────────
# 6. CONFIGURAR CLAUDE (quando disponível)
# ─────────────────────────────────────────────
def passo_configurar_claude():
    nome = "CONFIGURAR_CLAUDE"
    if is_done(nome):
        pula_passo("Configuração do Claude Code")
        return

    print(f"\n{M}═══ 6. Configurando Claude Code ═══{N}\n")

    if not tem_comando("claude"):
        aviso("Claude Code CLI não encontrado. Instale primeiro:")
        if IS_WINDOWS:
            aviso("   npm install -g @anthropic-ai/claude-code")
        else:
            aviso("   curl -sL https://claude-ai.com/install | bash")
        aviso("Após instalar, rode este script novamente.")
        set_done(nome)
        return

    if not tem_comando("bun"):
        aviso("Bun necessário para configurar. Instalando primeiro...")
        passo_instalar_bun()

    # Configurar ~/.claude.json
    config_path = HOME / ".claude.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
        except (json.JSONDecodeError, Exception):
            config = {}

        config["primaryApiKey"] = "sk-bypass"
        config["openRouterApiKey"] = "sk-bypass"
        config["additionalModelOptionsCache"] = [
            {"value": "oc/deepseek-v4-flash-free", "label": "DeepSeek V4 Flash Free",
             "description": "DeepSeek flash free model with reasoning"},
            {"value": "oc/ling-3.0-flash-free", "label": "Ling 3.0 Flash Free",
             "description": "Ling flash free model with reasoning"},
            {"value": "oc/north-mini-code-free", "label": "North Mini Code Free",
             "description": "North mini code free model"},
        ]

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        ok(f"Configuração aplicada em: {config_path}")

        # Aplicar configurações avançadas via 1-claude_config
        _executar_arquivo_config(
            "1-claude_config",
            "Configurações avançadas do Claude Code (1-claude_config)"
        )
    else:
        aviso("Arquivo ~/.claude.json não encontrado — crie manualmente ou instale o Claude Code primeiro")

    set_done(nome)


# ─────────────────────────────────────────────
# 7. INICIAR SERVIÇOS
# ─────────────────────────────────────────────
def passo_iniciar():
    nome = "INICIAR_PROXY"
    if is_done(nome):
        pula_passo("Inicialização do proxy")
        return

    print(f"\n{M}═══ 7. Iniciando proxy ═══{N}\n")

    PORTA_OMNI = 20128
    PORTA_PROXY = 20129

    # Verificar se OmniRouter está rodando
    omni_ok = porta_ocupada(PORTA_OMNI)

    if not omni_ok:
        if not tem_comando("omniroute"):
            erro("OmniRouter não está instalado. Execute o setup novamente.")
            sys.exit(1)

        log("Iniciando OmniRouter...")
        if IS_WINDOWS:
            log("OmniRouter iniciado em janela separada.")
            subprocess.Popen(
                ["start", "/B", "omniroute", "serve", "--port", str(PORTA_OMNI)],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                ["omniroute", "serve", "--port", str(PORTA_OMNI)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        # Aguardar OmniRouter
        for _ in range(15):
            time.sleep(1)
            if porta_ocupada(PORTA_OMNI):
                ok(f"OmniRouter rodando na porta {PORTA_OMNI}")
                break
        else:
            aviso("OmniRouter pode ainda estar iniciando")
    else:
        ok("OmniRouter já estava rodando")

    # Iniciar proxy
    proxy_ok = porta_ocupada(PORTA_PROXY)
    if proxy_ok:
        log(f"Parando proxy existente na porta {PORTA_PROXY}...")
        matar_processo_por_porta(PORTA_PROXY)
        time.sleep(1)

    log("Iniciando micro-proxy...")
    proxy_js = PROXY_DIR / "micro_proxy_opencode.js"

    if IS_WINDOWS:
        # Windows: inicia com Bun
        subprocess.Popen(
            ["bun", "run", str(proxy_js)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=PROXY_DIR,
        )
    else:
        # Linux/macOS/WSL: via script ou direto
        subprocess.Popen(
            ["bun", "run", str(proxy_js)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(PROXY_DIR),
        )

    # Aguardar proxy
    for _ in range(10):
        time.sleep(1)
        if porta_ocupada(PORTA_PROXY):
            ok(f"Proxy rodando na porta {PORTA_PROXY}")
            break
    else:
        aviso("Proxy pode ainda estar iniciando. Verifique o log:")
        aviso(f"   tail -f {PROXY_DIR}/proxy.log")

    set_done(nome)


# ─────────────────────────────────────────────
# RESUMO FINAL
# ─────────────────────────────────────────────
def passo_resumo():
    print(f"\n{M}═══════════ RESUMO DA INSTALAÇÃO ═══════════{N}\n")

    ferramentas = {
        "Bun (runtime JS)": tem_comando("bun"),
        "OmniRouter (roteador)": tem_comando("omniroute"),
        "Proxy (micro_proxy.js)": (PROXY_DIR / "micro_proxy_opencode.js").exists(),
    }

    if IS_WINDOWS:
        ferramentas["Script (iniciar.bat)"] = (PROXY_DIR / "iniciar.bat").exists()
        ferramentas["Script (parar.bat)"] = (PROXY_DIR / "parar.bat").exists()
        ferramentas["Ambiente (.opencode/env.bat)"] = (HOME / ".opencode" / "env.bat").exists()
    else:
        ferramentas["Script (iniciar.sh)"] = (PROXY_DIR / "iniciar.sh").exists()
        ferramentas["Script (parar.sh)"] = (PROXY_DIR / "parar.sh").exists()
        ferramentas["secrets.env"] = (HOME / ".config" / "secrets.env").exists()

    for nome_f, status in ferramentas.items():
        icone = f"{G}✅{N}" if status else f"{R}❌{N}"
        print(f"  {icone} {nome_f}")

    # Verificar portas
    for nome_p, porta in [("OmniRouter", 20128), ("Proxy", 20129)]:
        ativo = porta_ocupada(porta)
        icone = f"{G}🟢{N}" if ativo else f"{R}🔴{N}"
        print(f"  {icone} {nome_p} (porta {porta})")

    # Mostrar marcadores
    print()
    print(f"  {C}📌 Passos executados:{N}")
    passos = [
        ("VERIFICAR_SISTEMA", "Verificação do sistema"),
        ("INSTALAR_BUN", "Instalação do Bun"),
        ("INSTALAR_OMNIROUTER", "Instalação do OmniRouter"),
        ("PREPARAR_PROXY", "Preparação do proxy"),
        ("CRIAR_SECRETS", "Configuração de ambiente"),
        ("CONFIGURAR_CLAUDE", "Configuração do Claude Code"),
        ("INICIAR_PROXY", "Inicialização do proxy"),
    ]
    for chave, desc in passos:
        feito = is_done(chave)
        icone = f"{G}✅{N}" if feito else f"{Y}⬜{N}"
        print(f"    {icone} {desc}")

    # Instruções finais por plataforma
    print(f"\n{G}╔══════════════════════════════════════════════════╗{N}")
    print(f"{G}║  ✅ SETUP CONCLUÍDO!                             ║{N}")
    print(f"{G}╚══════════════════════════════════════════════════╝{N}\n")

    if IS_WINDOWS:
        print(f"  Para usar o Claude Code com o proxy no Windows:")
        print(f"    1. Execute: call ~/.opencode/env.bat")
        print(f"    2. Ou exporte manualmente:")
        print(f"       {C}set ANTHROPIC_BASE_URL=http://localhost:20129{N}")
        print(f"       {C}set ANTHROPIC_API_KEY=dummy{N}")
        print(f"       {C}set CLAUDE_CODE_MODEL=oc/deepseek-v4-flash-free{N}")
        print(f"    3. Execute o Claude:")
        print(f"       {C}claude{N}")
        print(f"\n  Para iniciar manualmente:")
        print(f"    {C}cd {PROXY_DIR} && iniciar.bat{N}")
    else:
        print(f"  Para usar o Claude Code com o proxy:")
        print(f"    1. {C}source ~/.config/secrets.env{N}")
        print(f"    2. {C}claude{N}")
        print(f"\n  Para iniciar manualmente:")
        print(f"    {C}cd {PROXY_DIR} && ./iniciar.sh{N}")
        print(f"\n  Para parar:")
        print(f"    {C}cd {PROXY_DIR} && ./parar.sh{N}")

    print(f"\n  Logs do proxy:")
    print(f"    {C}tail -f {PROXY_DIR}/proxy.log{N}")
    print(f"\n  Dashboard OmniRouter:")
    print(f"    {C}http://localhost:20128{N}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print(f"""{M}
╔═══════════════════════════════════════════════════════╗
║  🚀 OpenCode-Bypass — Setup Universal                 ║
║  Platforma: {SISTEMA.upper()}{" | WSL" if IS_WSL else ""}{" | " + (DISTRO + " (" + FAMILIA + ")") if DISTRO and FAMILIA else ""}{N}{M:<33}║
║  Passos já concluídos são pulados automaticamente    ║
╚═══════════════════════════════════════════════════════╝{N}
""")

    passo_verificar_sistema()
    passo_instalar_bun()
    passo_instalar_omnirouter()
    passo_preparar_proxy()
    passo_secrets()
    passo_configurar_claude()
    passo_iniciar()
    passo_resumo()


if __name__ == "__main__":
    main()
