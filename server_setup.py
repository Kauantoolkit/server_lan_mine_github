#!/usr/bin/env python3
"""
server_setup.py — Prepara o servidor dedicado NeoForge.

Executa uma vez antes do primeiro start:
  1. Instala o NeoForge (roda o installer que estiver em server/)
  2. Aceita a EULA
  3. Cria server.properties
  4. Verifica se os mods estão no lugar
"""

import subprocess
import sys
from pathlib import Path

# ─── Caminhos ─────────────────────────────────────────────────────────────────

ROOT   = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
SERVER = ROOT / "server"


# ─── NeoForge installer ───────────────────────────────────────────────────────

def find_installer() -> Path | None:
    """Procura pelo jar do installer NeoForge dentro de server/."""
    jars = sorted(SERVER.glob("neoforge-*-installer.jar"))
    return jars[0] if jars else None


def neoforge_installed() -> bool:
    """Retorna True se o NeoForge já foi instalado (pasta libraries existe)."""
    return (SERVER / "libraries").exists()


def install_neoforge():
    if neoforge_installed():
        print("ℹ️  NeoForge já instalado — pulando.")
        return

    installer = find_installer()
    if not installer:
        print("❌ Installer do NeoForge não encontrado em server/")
        print("   Coloque o arquivo neoforge-*-installer.jar dentro da pasta server/")
        print("   e rode este programa novamente.")
        sys.exit(1)

    print(f"   Installer encontrado: {installer.name}")
    print("   Instalando NeoForge... (pode demorar alguns minutos)")
    print()

    result = subprocess.run(
        ["java", "-jar", str(installer), "--installServer"],
        cwd=SERVER,
    )

    if result.returncode != 0:
        print()
        print("❌ Falha na instalação do NeoForge.")
        print("   Verifique se o Java 21 está instalado corretamente.")
        sys.exit(1)

    print()
    print("✅ NeoForge instalado.")


# ─── eula.txt ─────────────────────────────────────────────────────────────────

def accept_eula():
    eula = SERVER / "eula.txt"
    if eula.exists() and "eula=true" in eula.read_text(encoding="utf-8"):
        print("ℹ️  eula.txt já aceito.")
        return
    eula.write_text("eula=true\n", encoding="utf-8")
    print("✅ eula.txt criado.")


# ─── server.properties ────────────────────────────────────────────────────────

def create_server_properties():
    props = SERVER / "server.properties"
    if props.exists():
        print("ℹ️  server.properties já existe — não sobrescrevendo.")
        return

    props.write_text(
        "# Gerado pelo server_setup\n"
        "server-port=25565\n"
        "online-mode=false\n"
        "max-players=10\n"
        "view-distance=10\n"
        "simulation-distance=8\n"
        "enable-rcon=true\n"
        "rcon.port=25575\n"
        "rcon.password=troqueisso\n"
        "broadcast-rcon-to-ops=false\n"
        "difficulty=normal\n"
        "spawn-protection=0\n"
        "level-name=world\n",
        encoding="utf-8",
    )
    print("✅ server.properties criado.")
    print("   ⚠️  Troque rcon.password em server/server.properties antes de iniciar!")


# ─── Filtro de mods client-only ───────────────────────────────────────────────
# Esses mods crasham o servidor dedicado (renderização, shaders, HUD, etc.)

CLIENT_ONLY = {
    # Sodium / renderização OpenGL
    "sodium-neoforge", "sodiumdynamiclights", "sodiumextras",
    "sodiumoptionsapi", "sodiumoptionsmodcompat", "reeses-sodium-options",
    # Iris / shaders
    "iris-neoforge", "oculus_for_simpleclouds",
    # Texturas / modelos de entidades
    "entity_model_features", "entity_texture_features",
    # Otimizações de renderização
    "entityculling", "ImmediatelyFast", "dynamic-fps",
    # HUD / câmera / UI
    "BetterThirdPerson", "MouseTweaks", "Controlling", "Searchables",
    "abridged", "Loot Beams Refork",
    # Minimap
    "xaerominimap",
    # HUD de vida
    "torohealth",
    # Nuvens visuais
    "simpleclouds",
    # Skin renderer
    "skinrestorer",
    # CurseForge client integration
    "cfwinfo",
}


def is_client_only(jar_name: str) -> bool:
    lower = jar_name.lower()
    return any(pattern.lower() in lower for pattern in CLIENT_ONLY)


# ─── Verifica e limpa mods ────────────────────────────────────────────────────

def check_mods():
    mods_dir = SERVER / "mods"
    if not mods_dir.exists() or not any(mods_dir.glob("*.jar")):
        print()
        print("⚠️  Nenhum mod encontrado em server/mods/")
        print("   Coloque os arquivos .jar dos mods lá antes de iniciar o servidor.")
        return

    removed = []
    kept    = []

    for jar in sorted(mods_dir.glob("*.jar")):
        if is_client_only(jar.name):
            jar.unlink()
            removed.append(jar.name)
        else:
            kept.append(jar.name)

    print(f"✅ {len(kept)} mod(s) mantido(s) em server/mods/")
    if removed:
        print(f"🗑️  {len(removed)} mod(s) client-only removido(s):")
        for name in removed:
            print(f"   - {name}")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  Setup do servidor NeoForge 1.21.1")
    print("=" * 55)

    SERVER.mkdir(exist_ok=True)

    print("\n[1/4] Instalando NeoForge...")
    install_neoforge()

    print("\n[2/4] Aceitando EULA...")
    accept_eula()

    print("\n[3/4] Criando server.properties...")
    create_server_properties()

    print("\n[4/4] Verificando mods...")
    check_mods()

    print()
    print("=" * 55)
    print("  Pronto! Próximos passos:")
    print()
    print("  1. Edite server/server.properties")
    print("     → troque rcon.password por uma senha real")
    print()
    print("  2. Edite config.json (copie config.example.json)")
    print("     → coloque player_name, a mesma senha e a URL do repo")
    print()
    print("  3. Inicie o servidor:")
    print("     sync.exe setup   (primeira vez)")
    print("     sync.exe start   (uso normal)")
    print("=" * 55)


if __name__ == "__main__":
    main()
