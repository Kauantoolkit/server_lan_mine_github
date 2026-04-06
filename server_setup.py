#!/usr/bin/env python3
"""
server_setup.py — Prepara o servidor dedicado NeoForge
com os mods da instância CurseForge.

Executa uma vez antes do primeiro start.
"""

import shutil
import sys
from pathlib import Path

# ─── Caminhos ─────────────────────────────────────────────────────────────────

ROOT          = Path(__file__).parent
CLIENT        = ROOT / "server" / "minecraft server 1.21.1"
SERVER        = ROOT / "server"

CLIENT_MODS   = CLIENT / "mods"
CLIENT_CONFIG = CLIENT / "config"
SERVER_MODS   = SERVER / "mods"
SERVER_CONFIG = SERVER / "config"

# ─── Mods client-only (não funcionam / crasham servidor dedicado) ─────────────
# Renderização, shaders, HUD, otimizações visuais — o servidor não tem GPU.

CLIENT_ONLY = {
    # Sodium / renderização OpenGL
    "sodium-neoforge",
    "sodiumdynamiclights",
    "sodiumextras",
    "sodiumoptionsapi",
    "sodiumoptionsmodcompat",
    "reeses-sodium-options",
    # Iris / shaders
    "iris-neoforge",
    "oculus_for_simpleclouds",
    # Texturas / modelos de entidades (visuais)
    "entity_model_features",
    "entity_texture_features",
    # Otimizações de renderização
    "entityculling",
    "ImmediatelyFast",
    "dynamic-fps",
    # HUD / câmera / UI
    "BetterThirdPerson",
    "MouseTweaks",
    "Controlling",
    "Searchables",
    "abridged",
    "Loot Beams Refork",
    # Minimap (client-side rendering)
    "xaerominimap",
    # HUD de vida acima dos mobs
    "torohealth",
    # Nuvens visuais
    "simpleclouds",
    # Skin renderer
    "skinrestorer",
    # CurseForge client integration
    "cfwinfo",
}


def is_client_only(jar_name: str) -> bool:
    """Retorna True se o mod é client-only pelo nome do arquivo."""
    lower = jar_name.lower()
    for pattern in CLIENT_ONLY:
        if pattern.lower() in lower:
            return True
    return False


# ─── Copia mods ───────────────────────────────────────────────────────────────

def copy_mods():
    if not CLIENT_MODS.exists():
        print(f"❌ Pasta de mods não encontrada: {CLIENT_MODS}")
        sys.exit(1)

    SERVER_MODS.mkdir(exist_ok=True)

    jars = sorted(CLIENT_MODS.glob("*.jar"))
    copied  = []
    skipped = []

    for jar in jars:
        # Ignora mods desativados (.disabled)
        if jar.suffix == ".disabled":
            skipped.append((jar.name, "desativado"))
            continue

        if is_client_only(jar.name):
            skipped.append((jar.name, "client-only"))
            continue

        dest = SERVER_MODS / jar.name
        shutil.copy2(jar, dest)
        copied.append(jar.name)

    print(f"\n✅ {len(copied)} mods copiados para server/mods/")
    print(f"⏭️  {len(skipped)} ignorados\n")

    if skipped:
        print("─── Ignorados ───────────────────────────────────────")
        for name, reason in skipped:
            print(f"  [{reason}] {name}")
        print()

    return len(copied)


# ─── Copia config ─────────────────────────────────────────────────────────────

def copy_config():
    if not CLIENT_CONFIG.exists():
        print("⚠️  Pasta config/ não encontrada na instância cliente — pulando.")
        return

    if SERVER_CONFIG.exists():
        print("ℹ️  server/config/ já existe — mesclando (arquivos existentes não são sobrescritos).")
        for src in CLIENT_CONFIG.rglob("*"):
            if src.is_file():
                rel  = src.relative_to(CLIENT_CONFIG)
                dest = SERVER_CONFIG / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copy2(src, dest)
    else:
        shutil.copytree(CLIENT_CONFIG, SERVER_CONFIG)
        print("✅ config/ copiado para server/config/")


# ─── eula.txt ─────────────────────────────────────────────────────────────────

def accept_eula():
    eula = SERVER / "eula.txt"
    if not eula.exists():
        eula.write_text("eula=true\n", encoding="utf-8")
        print("✅ eula.txt criado (eula=true)")
    else:
        content = eula.read_text(encoding="utf-8")
        if "eula=true" not in content:
            eula.write_text("eula=true\n", encoding="utf-8")
            print("✅ eula.txt atualizado (eula=true)")
        else:
            print("ℹ️  eula.txt já aceito.")


# ─── server.properties ────────────────────────────────────────────────────────

def create_server_properties():
    props = SERVER / "server.properties"
    if props.exists():
        print("ℹ️  server.properties já existe — não sobrescrevendo.")
        print("   Certifique-se de ter estas linhas para o sync funcionar:")
        print("     enable-rcon=true")
        print("     rcon.port=25575")
        print("     rcon.password=suasenha")
        return

    props.write_text(
        "# Gerado pelo server_setup.py\n"
        "server-port=25565\n"
        "online-mode=false\n"          # false para LAN sem autenticação Mojang
        "max-players=10\n"
        "view-distance=10\n"
        "simulation-distance=8\n"
        "enable-rcon=true\n"
        "rcon.port=25575\n"
        "rcon.password=eosguri\n" # ← troque antes de usar
        "broadcast-rcon-to-ops=false\n"
        "difficulty=normal\n"
        "spawn-protection=0\n"
        "level-name=world\n",
        encoding="utf-8",
    )
    print("✅ server.properties criado.")
    print("   ⚠️  Troque rcon.password em server/server.properties antes de iniciar!")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  Setup do servidor dedicado NeoForge 1.21.1")
    print("=" * 55)

    print("\n[1/4] Copiando mods...")
    copy_mods()

    print("[2/4] Copiando configs dos mods...")
    copy_config()

    print("[3/4] Aceitando EULA...")
    accept_eula()

    print("[4/4] Criando server.properties...")
    create_server_properties()

    print()
    print("=" * 55)
    print("  Pronto! Próximos passos:")
    print()
    print("  1. Edite server/server.properties")
    print("     → troque rcon.password por uma senha real")
    print()
    print("  2. Edite config.json (copie config.example.json)")
    print("     → coloque a mesma senha em rcon.password")
    print()
    print("  3. Inicie o servidor:")
    print("     python sync.py setup   (primeira vez)")
    print("     python sync.py start   (uso normal)")
    print("=" * 55)


if __name__ == "__main__":
    main()
