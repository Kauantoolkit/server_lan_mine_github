# Guia — Minecraft LAN Sync

Sincroniza um mundo singleplayer (aberto para LAN) com o GitHub.  
Usa um arquivo `status.json` no próprio repositório como lock — impede que dois jogadores tentem instanciar o mundo ao mesmo tempo.

---

## Fluxo completo

```
Jogador A roda: python sync.py start
  └── pull do GitHub
  └── lê status.json → "free"
  └── escreve "playing: Kauan" → push
  └── "Abra o mundo no Minecraft agora"
  └── [monitora session.lock]
  └── Minecraft fechado →
        commita o mundo + escreve "free" → push

Jogador B roda: python sync.py start (enquanto A joga)
  └── pull do GitHub
  └── lê status.json → "playing: Kauan"
  └── ❌ "Mundo ocupado por Kauan desde 21:30"
  └── sai sem fazer nada

Jogador B roda: python sync.py start (depois que A terminou)
  └── pull do GitHub
  └── lê status.json → "free"
  └── escreve "playing: Pedro" → push
  └── [joga normalmente]
  └── Minecraft fechado → commita + libera
```

---

## Instalação (uma vez)

### 1. Pré-requisitos
- Python 3.8+ → `python --version`
- Git → `git --version`
- Repositório vazio criado no GitHub

### 2. Dependências
```bat
pip install -r requirements.txt
```

### 3. Config
```bat
copy config.example.json config.json
```

Edite o `config.json`:
```json
{
  "player_name": "Kauan",
  "world_path": "C:/Users/kauan/AppData/Roaming/.minecraft/saves/NomeDoMundo",
  "git": {
    "remote_url": "https://github.com/SEU_USUARIO/SEU_REPO.git",
    "branch": "main"
  }
}
```

**Onde fica o `world_path`?**  
É a pasta do mundo dentro do `.minecraft`. No Windows:
```
C:\Users\SEU_USUARIO\AppData\Roaming\.minecraft\saves\NomeDoMundo
```
Dica rápida: no Minecraft, vá em "Editar Mundo" → "Abrir Pasta do Mundo".

### 4. Primeiro push (só quem cria o repo faz isso)
```bat
python sync.py setup
```

Isso inicializa o git dentro da pasta do mundo, conecta ao GitHub e faz o primeiro push.

---

## Uso do dia a dia

### Antes de jogar
```bat
python sync.py start
```

O script vai:
1. Puxar o estado mais recente do GitHub
2. Verificar se o mundo está livre
3. Registrar sua sessão
4. Pedir pra você abrir o mundo no Minecraft
5. Monitorar até você fechar o jogo
6. Salvar e fazer push automaticamente

### Checar quem está jogando (sem abrir)
```bat
python sync.py status
```

### Se o Minecraft travou e o lock ficou preso
```bat
python sync.py force-release
```

---

## Configuração nos outros PCs

Cada jogador faz isso uma vez:

```bat
git clone https://github.com/SEU_USUARIO/SEU_REPO.git
```

Isso baixa a pasta do mundo. Depois mova/copie ela para:
```
C:\Users\NOME\AppData\Roaming\.minecraft\saves\
```

Configure o `config.json` com o `world_path` apontando para lá, e com o seu próprio `player_name`.

Na hora de jogar: `python sync.py start` — ele já faz pull automático antes de verificar o lock.

---

## O que o script detecta para saber que o jogo fechou?

O Minecraft mantém um arquivo `session.lock` dentro da pasta do mundo **aberto** e o atualiza a cada ~5 segundos enquanto estiver rodando. Quando você fecha o mundo (ou o jogo), o arquivo para de ser atualizado.

O script monitora isso: se o `session.lock` ficar sem atualização por mais de 15 segundos → considera que o jogo fechou → commita.

---

## Estrutura de arquivos

```
.minecraft/saves/NomeDoMundo/   ← repo git fica aqui
  ├── .git/
  ├── .gitignore                ← ignora session.lock e .tmp
  ├── status.json               ← o "lock" — rastreado pelo git
  ├── level.dat                 ← dados do mundo
  ├── region/                   ← chunks
  └── playerdata/               ← dados dos jogadores

server_lan_mine_github/         ← a ferramenta fica aqui (fora do mundo)
  ├── sync.py
  ├── config.json               ← seu config local (gitignored aqui)
  └── requirements.txt
```

---

## Regra de ouro

> **Nunca abra o mundo no Minecraft antes de rodar `python sync.py start`.**  
> Se abrir direto, o lock não vai ser registrado e outra pessoa pode sobrescrever o mundo.
