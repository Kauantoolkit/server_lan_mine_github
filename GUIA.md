# Guia de uso — Minecraft Server Sync

---

## Estrutura de pastas

```
server_lan_mine_github/               ← repositório git (esta pasta)
│
├── sync.py                           ← script que gerencia o servidor
├── server_setup.py                   ← script de setup inicial (roda uma vez)
├── config.json                       ← sua config local (você cria, não vai pro git)
├── status.json                       ← lock de sessão (vai pro git)
│
└── server/                           ← tudo relacionado ao servidor
    │
    ├── minecraft server 1.21.1/      ← instância CurseForge (você coloca aqui)
    │   ├── mods/                     ← mods do cliente
    │   └── config/                   ← configs dos mods
    │
    ├── mods/                         ← criado pelo server_setup.py (não vai pro git)
    ├── config/                       ← criado pelo server_setup.py (vai pro git)
    ├── world/                        ← mundo gerado pelo servidor (vai pro git)
    ├── libraries/                    ← NeoForge runtime (não vai pro git)
    ├── server.jar                    ← NeoForge jar (não vai pro git)
    ├── run.bat / run.sh
    ├── server.properties
    └── user_jvm_args.txt
```

---

## Setup inicial (primeira vez)

### Pré-requisitos
- Python 3.8+
- Git
- Java 21
- NeoForge server instalado em `server/`
- Instância CurseForge do modpack colocada em `server/minecraft server 1.21.1/`

---

### Passo 1 — Colocar o modpack no lugar certo

Copie (ou mova) a pasta da sua instância CurseForge para dentro de `server/`:

```
server/
└── minecraft server 1.21.1/    ← nome exato da pasta
    ├── mods/
    ├── config/
    └── ...
```

> No CurseForge, clique com botão direito na instância → **Abrir Pasta** para achar o caminho.

---

### Passo 2 — Instalar dependências Python

```bat
pip install -r requirements.txt
```

---

### Passo 3 — Criar o config.json

```bat
copy config.example.json config.json
```

Abra o `config.json` e preencha:

```json
{
  "player_name": "SeuNome",
  "server_path": "./server",
  "start_command": ["java", "@user_jvm_args.txt", "@libraries/net/neoforged/neoforge/21.1.218/win_args.txt", "nogui"],
  "backup_interval_minutes": 15,
  "rcon": {
    "host": "127.0.0.1",
    "port": 25575,
    "password": "suasenha"
  },
  "git": {
    "remote_url": "https://github.com/SEU_USUARIO/SEU_REPO.git",
    "branch": "main"
  }
}
```

> A senha do RCON deve ser a mesma que está em `server/server.properties` no campo `rcon.password`.

---

### Passo 4 — Copiar mods para o servidor

```bat
python server_setup.py
```

Isso vai:
- Copiar os mods da instância CurseForge para `server/mods/` (filtrando os client-only)
- Copiar `config/` dos mods
- Criar `eula.txt` e `server.properties`

---

### Passo 5 — Inicializar o repositório git

```bat
python sync.py setup
```

---

### Passo 6 — Iniciar o servidor

```bat
python sync.py start
```

O script vai verificar o lock, subir o servidor, fazer backups automáticos e salvar no GitHub quando você parar.

---

## Uso do dia a dia

### Antes de jogar
```bat
python sync.py start
```

### Ver quem está jogando
```bat
python sync.py status
```

### Se o servidor travou e o lock ficou preso
```bat
python sync.py force-release
```

---

## Outro jogador quer jogar (segundo PC)

### Primeira vez
```bat
git clone https://github.com/SEU_USUARIO/SEU_REPO.git
cd server_lan_mine_github
```

Depois:
1. Instalar NeoForge server em `server/` (baixar o installer e rodar)
2. Colocar a instância CurseForge em `server/minecraft server 1.21.1/`
3. Rodar `python server_setup.py` para copiar os mods
4. Criar `config.json` com seu nome e senha RCON
5. Rodar `python sync.py start`

### Nas próximas vezes
```bat
python sync.py start
```

O pull já é feito automaticamente no início do `start`.

---

## Regra de ouro

> Sempre use `python sync.py start` para iniciar o servidor.  
> Nunca suba o servidor direto pelo `run.bat` — o lock não será registrado e o mundo não será salvo no GitHub.
