#!/usr/bin/env python3
"""
Minecraft Server Sync — controle de sessão + backups automáticos via GitHub

Fluxo:
  python sync.py start
    → git pull
    → verifica status.json (bloqueio distribuído)
    → registra "playing: você" → push
    → sobe o servidor Minecraft como subprocesso
    → thread de backup: a cada N min faz save-all + commit + push
    → servidor para (/stop no console ou Ctrl+C)
    → commit final + status "free" + push
"""

import json
import socket
import struct
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path


def _repo_root() -> Path:
    """Raiz do repositório — compatível com PyInstaller (frozen) e execução normal."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent.resolve()
    return Path(__file__).parent.resolve()


# ─── Git ──────────────────────────────────────────────────────────────────────

def git(args: list, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(
        ["git"] + args, cwd=cwd,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} falhou:\n{r.stderr.strip()}")
    return r


def has_changes(cwd: Path) -> bool:
    return bool(git(["status", "--porcelain"], cwd).stdout.strip())


def commit_push(cwd: Path, message: str, branch: str) -> bool:
    git(["add", "--all"], cwd)
    if not has_changes(cwd):
        return False
    git(["commit", "-m", message], cwd)
    git(["push", "--set-upstream", "origin", branch], cwd)
    return True


def pull(cwd: Path, branch: str):
    git(["pull", "--rebase", "origin", branch], cwd, check=False)


# ─── RCON ─────────────────────────────────────────────────────────────────────

class RCON:
    """Cliente RCON mínimo (sem dependências externas)."""

    AUTH    = 3
    COMMAND = 2

    def __init__(self, host: str, port: int, password: str, timeout: float = 5.0):
        self.host     = host
        self.port     = port
        self.password = password
        self.timeout  = timeout
        self._sock    = None
        self._id      = 1

    def connect(self) -> bool:
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.timeout)
            self._sock.connect((self.host, self.port))
            self._send(self.AUTH, self.password)
            req_id, _, _ = self._recv()
            return req_id != -1
        except OSError:
            self._sock = None
            return False

    def command(self, cmd: str) -> str | None:
        if not self._sock:
            return None
        try:
            self._send(self.COMMAND, cmd)
            _, _, resp = self._recv()
            return resp
        except OSError:
            return None

    def disconnect(self):
        if self._sock:
            try: self._sock.close()
            except OSError: pass
            self._sock = None

    def _send(self, ptype: int, payload: str):
        body   = payload.encode() + b"\x00\x00"
        header = struct.pack("<iii", len(body) + 8, self._id, ptype)
        self._sock.sendall(header + body)
        self._id += 1

    def _recv(self) -> tuple:
        raw = self._recvn(4)
        if not raw:
            return -1, -1, ""
        n            = struct.unpack("<i", raw)[0]
        data         = self._recvn(n)
        req_id, pt   = struct.unpack("<ii", data[:8])
        payload      = data[8:-2].decode("utf-8", errors="replace")
        return req_id, pt, payload

    def _recvn(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                return b""
            buf += chunk
        return buf


# ─── Status (lock distribuído) ────────────────────────────────────────────────

STATUS_FILE = "status.json"

def read_status(repo: Path) -> dict:
    f = repo / STATUS_FILE
    if not f.exists():
        return {"state": "free", "player": None, "since": None}
    with open(f, encoding="utf-8") as fp:
        return json.load(fp)


def write_status(repo: Path, state: str, player: str | None = None):
    data = {
        "state": state,
        "player": player,
        "since": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if state == "playing" else None,
    }
    with open(repo / STATUS_FILE, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=False)
        fp.write("\n")


# ─── Thread de backup periódico ───────────────────────────────────────────────

class BackupThread(threading.Thread):
    """
    A cada `interval` segundos:
      1. RCON save-all flush  → força o servidor escrever no disco
      2. Aguarda arquivos estabilizarem
      3. git commit + push    → backup no GitHub
    """

    def __init__(
        self,
        repo: Path,
        branch: str,
        player: str,
        interval_seconds: int,
        rcon_cfg: dict,
    ):
        super().__init__(daemon=True)
        self.repo     = repo
        self.branch   = branch
        self.player   = player
        self.interval = interval_seconds
        self.rcon_cfg = rcon_cfg
        self._stop    = threading.Event()
        self.count    = 0

    def stop(self):
        self._stop.set()

    def _save_via_rcon(self) -> bool:
        """Pede ao servidor para salvar agora. Retorna True se conseguiu."""
        cfg = self.rcon_cfg
        if not cfg.get("password"):
            return False
        rcon = RCON(cfg.get("host", "127.0.0.1"), cfg.get("port", 25575), cfg["password"])
        if not rcon.connect():
            return False
        try:
            rcon.command("save-all flush")
            time.sleep(3)   # aguarda o servidor escrever no disco
            return True
        finally:
            rcon.disconnect()

    def _wait_files_stable(self, stable_secs: float = 5.0, max_wait: float = 60.0):
        """Aguarda os arquivos .mca pararem de ser modificados."""
        last_change = time.time()
        deadline    = time.time() + max_wait
        prev_mtime  = self._newest_mca()
        while True:
            time.sleep(1)
            cur = self._newest_mca()
            if cur != prev_mtime:
                prev_mtime  = cur
                last_change = time.time()
            elif time.time() - last_change >= stable_secs:
                break
            if time.time() >= deadline:
                print("[backup] ⚠️  Timeout aguardando estabilização — commitando mesmo assim.")
                break

    def _newest_mca(self) -> float:
        newest = 0.0
        for f in self.repo.rglob("*.mca"):
            try:
                newest = max(newest, f.stat().st_mtime)
            except OSError:
                pass
        return newest

    def run(self):
        while not self._stop.wait(timeout=self.interval):
            self.count += 1
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[backup #{self.count}] {ts}")

            saved = self._save_via_rcon()
            if not saved:
                print("[backup] RCON indisponível — aguardando estabilização...")
                self._wait_files_stable()

            try:
                pushed = commit_push(
                    self.repo, self.branch,
                    f"[backup #{self.count}] sessão de {self.player} — {ts}",
                )
                if pushed:
                    print(f"[backup #{self.count}] ✅ Salvo no GitHub.")
                else:
                    print(f"[backup #{self.count}] ℹ️  Sem alterações desde o último backup.")
            except Exception as e:
                print(f"[backup #{self.count}] ❌ Falha ao fazer push: {e}")


# ─── Processo do servidor ─────────────────────────────────────────────────────

class ServerProcess:
    """Gerencia o processo do servidor Minecraft."""

    def __init__(self, server_path: Path, start_command: list[str]):
        self.server_path   = server_path
        self.start_command = start_command
        self._proc: subprocess.Popen | None = None

    def start(self):
        print(f"🚀 Iniciando servidor: {' '.join(self.start_command)}")
        self._proc = subprocess.Popen(
            self.start_command,
            cwd=self.server_path,
            # Não redireciona stdin/stdout — operador interage direto com o console
        )

    def wait(self) -> int:
        if self._proc:
            return self._proc.wait()
        return 0

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def terminate(self):
        if self._proc and self.is_running():
            self._proc.terminate()


# ─── Config ───────────────────────────────────────────────────────────────────

def load_config(path: str = "config.json") -> dict:
    p = Path(path)
    if not p.exists():
        print(f"❌ {p} não encontrado. Copie config.example.json para config.json.")
        sys.exit(1)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def build_start_command(config: dict) -> list[str]:
    return config["start_command"]


# ─── Comandos ─────────────────────────────────────────────────────────────────

def cmd_start(config: dict):
    # repo = raiz do projeto (onde está o .git e o status.json)
    repo        = _repo_root()
    server_path = Path(config["server_path"]).expanduser().resolve()
    player      = config["player_name"]
    branch      = config["git"].get("branch", "main")
    rcon_cfg    = config.get("rcon", {})
    interval    = int(config.get("backup_interval_minutes", 15)) * 60

    if not server_path.exists():
        print(f"❌ Pasta do servidor não encontrada: {server_path}")
        sys.exit(1)

    # 1. Pull
    print("🔄 Sincronizando com o GitHub...")
    pull(repo, branch)

    # 2. Verifica lock
    status = read_status(repo)
    if status["state"] == "playing":
        print()
        print("🔒 Servidor ocupado!")
        print(f"   Jogador : {status['player']}")
        print(f"   Desde   : {status['since']}")
        print()
        print("Aguarde ele terminar. Se travou use: python sync.py force-release")
        sys.exit(0)

    # 3. Reivindica o lock
    print(f"✅ Livre! Registrando sessão de {player}...")
    write_status(repo, "playing", player)
    try:
        commit_push(repo, f"[status] {player} iniciou sessão", branch)
    except Exception as e:
        print(f"⚠️  Não foi possível registrar no GitHub: {e}")

    # Garante liberação do lock em qualquer saída
    def release(reason: str):
        print(f"\n💾 {reason} Fazendo commit final e liberando lock...")
        write_status(repo, "free")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            commit_push(repo, f"[world] sessão de {player} encerrada — {ts}", branch)
            print("✅ Mundo salvo. Outro jogador pode entrar.")
        except Exception as e:
            print(f"❌ Erro ao fazer push final: {e}")
            print("   Execute manualmente: git add -A && git commit -m 'manual' && git push")

    # 4. Inicia o servidor
    start_cmd = build_start_command(config)
    server    = ServerProcess(server_path, start_cmd)

    # 5. Thread de backup periódico (commita no repo raiz)
    backup = BackupThread(repo, branch, player, interval, rcon_cfg)

    try:
        server.start()
        backup.start()

        print()
        print("=" * 55)
        print(f"  Servidor rodando! Amigos conectam pelo IP da LAN.")
        print(f"  Backups automáticos a cada {interval // 60} minutos.")
        print(f"  Para encerrar: digite /stop no console do servidor")
        print(f"  ou pressione Ctrl+C aqui.")
        print("=" * 55)
        print()

        server.wait()   # bloqueia até o servidor parar

    except KeyboardInterrupt:
        print("\n⚠️  Ctrl+C recebido.")
        if server.is_running():
            print("   Aguardando servidor parar...")
            server.terminate()
            server.wait()

    finally:
        backup.stop()
        release("Servidor parado.")


def cmd_status(config: dict):
    repo   = _repo_root()
    branch = config["git"].get("branch", "main")

    print("🔄 Verificando status...")
    pull(repo, branch)

    s = read_status(repo)
    if s["state"] == "free":
        print("✅ Servidor livre — pode jogar!")
    else:
        print(f"🔒 Em uso por: {s['player']}")
        print(f"   Desde: {s['since']}")


def cmd_force_release(config: dict):
    repo   = _repo_root()
    branch = config["git"].get("branch", "main")

    print("⚠️  Forçando liberação...")
    write_status(repo, "free")
    try:
        commit_push(repo, "[status] liberação forçada (crash/emergência)", branch)
        print("✅ Mundo liberado.")
    except Exception as e:
        print(f"❌ {e}")


def cmd_setup(config: dict):
    repo       = Path(__file__).parent.resolve()
    remote_url = config["git"]["remote_url"]
    branch     = config["git"].get("branch", "main")

    if not (repo / ".git").exists():
        print("🔧 Inicializando repositório git...")
        git(["init", "-b", branch], repo)

    remotes = git(["remote", "-v"], repo, check=False).stdout
    if "origin" not in remotes:
        git(["remote", "add", "origin", remote_url], repo)
    else:
        git(["remote", "set-url", "origin", remote_url], repo)
    print(f"🔗 Remote: {remote_url}")

    if not (repo / STATUS_FILE).exists():
        write_status(repo, "free")
        print("📄 status.json criado.")

    if has_changes(repo):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("📦 Fazendo primeiro commit...")
        git(["add", "--all"], repo)
        git(["commit", "-m", f"[setup] snapshot inicial — {ts}"], repo)
        git(["push", "--set-upstream", "origin", branch], repo)
        print("✅ Setup completo!")
    else:
        print("✅ Setup completo (nada para commitar).")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Minecraft Server Sync via GitHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Comandos:
  start          Verifica lock, sobe o servidor, faz backups, salva ao fechar
  status         Mostra quem está jogando (ou se está livre)
  force-release  Libera o lock à força (use se o servidor travou)
  setup          Inicializa o git no servidor e faz o primeiro push
        """,
    )
    parser.add_argument("command", choices=["start", "status", "force-release", "setup"])
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()

    config = load_config(args.config)

    match args.command:
        case "start":         cmd_start(config)
        case "status":        cmd_status(config)
        case "force-release": cmd_force_release(config)
        case "setup":         cmd_setup(config)


if __name__ == "__main__":
    main()
