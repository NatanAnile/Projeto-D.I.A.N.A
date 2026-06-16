# Projeto Diana V5

Diana é uma VTuber IA local em PT-BR criada para funcionar como personagem viva de live: debochada, travessa, levada, teimosa, inquieta, orgulhosa e útil sem virar assistente corporativa.

## Estado atual

Versão atual: **0.5.19_FILE_CONTEXT_PERSONALITY_SKILLS_FIX**.

Esta versão parte da **0.5.18_OPERATIONAL_REPEAT_CHAT_PATH_FIX** e corrige dois blocos importantes:

```txt
1. leitura/listagem/follow-up de arquivos
2. camada de comentário/persona baseada em skill_actions.json
```

A regra central continua:

```txt
skill operacional executa primeiro
personalidade comenta junto
LLM não inventa arquivo, chat ou fonte externa
```

## Correções principais da 0.5.19

### Arquivos e continuidade

Agora pedidos como estes devem cair em `ReadFileSkill`:

```txt
resume o arrtigo cientifico pra mim
mas e arquivos? quais tem?
ecolhe um arquivo pra ler, criatura!
me fala uma rquivo que você tem na pasta read_files
Agora me diga o que você entendeu desse arquivo
```

Comportamento esperado:

```txt
- typos comuns são recuperados
- artigo científico sem a palavra "arquivo" ativa leitura de arquivo
- listagem mostra nomes reais da pasta data/read_files
- "escolhe um arquivo" escolhe um arquivo real e lê no mesmo turno
- follow-up usa o último arquivo lido como contexto
- CommentSkill não engole tarefa operacional ambígua
```

### CommentSkill reinterpretado

`CommentSkill` agora é a camada/sistema de comentário. Ele não é mais tratado como “a skill de personalidade” em si.

Correto:

```txt
🧩 Skill de personalidade executada -> improvisar_caos
```

Errado:

```txt
🧩 Skill de personalidade: CommentSkill -> improvisar_caos
```

As ações reais de personalidade ficam em:

```txt
skills/skill_actions.json
```

Exemplos de ações:

```txt
improvisar_caos
fazer_comentario_curto
comentario_com_gancho
assumir_chute
discordar_de_forma_absurda
brigar_de_brincadeira
elogiar_ironicamente
reclamar_dramaticamente
pedir_algo
chamar_de_velho
zoar_chat
```

O objetivo é deixar a Diana mais dinâmica em live, evitando vício em uma ou duas ações.

### Skills obsoletas removidas

Removidos do fluxo e dos arquivos:

```txt
skills/game_context_skill.py
skills/style_skill.py
```

Motivo:

```txt
- game_context_skill.py não agregava valor real
- style_skill.py ficou obsoleto sem autonomia de salvar estilos
```

## Host Mode atual

### autonomous

```txt
/host mode autonomous
```

Comportamento:

```txt
lê mensagens novas automaticamente
responde quando score >= 6
puxa assunto em idle quando o chat fica quieto
```

### read_response

```txt
/host mode read_response
```

Comportamento correto:

```txt
lê mensagens novas automaticamente
responde quando score >= 6
NÃO puxa assunto em idle
NÃO precisa de /host read para funcionar
```

### /host read

Agora é só um comando manual de força:

```txt
lê agora, independente do tick/cooldown
```

Não é obrigatório para o `read_response` funcionar.

## Score do Host Mode

```txt
score >= 10 = prioridade
score >= 6  = responde
score < 6   = ignora
```

## Formato de resposta

```txt
usuario: mensagem — pensamento da Diana
```

Exemplo:

```txt
stelyn: Ele vai continuar. — Acho que ele desiste antes de tentar.
```

## Continuidade operacional

Comandos curtos de repetição reutilizam a última skill operacional registrada:

```txt
tenta de novo
faz de novo
repete
mais uma vez
```

Exemplo esperado:

```txt
Neitan: le o chat pra mim
Diana: Ainda não encontrei mensagens recentes do chat. Arquivo lido: live_chat.txt

Neitan: tenta de novo
Diana: Ainda não encontrei mensagens recentes do chat. Arquivo lido: live_chat.txt
```

## Segurança de caminho de arquivo

A Diana pode usar caminhos absolutos internamente em logs/debug, mas a fala final só deve mostrar o nome do arquivo, por exemplo:

```txt
live_chat.txt
```

Nunca:

```txt
C:\Users\...\live_chat.txt
```

## Arquivos alterados nesta versão

```txt
Diana.py
config.py
README.md
.github/workflows/tests.yml
runtime/input_firewall.py
runtime/intent_router.py
utils/response_cleaner.py
skills/comment_skill.py
skills/read_file_skill.py
skills/skill_actions.json
skills/skill_system.py
skills/game_context_skill.py [removido]
skills/style_skill.py [removido]
tools/tests/test_continuidade_0_5_17_hostmode_read_response_auto.py
tools/tests/test_continuidade_0_5_18_operational_repeat_chat_path_fix.py
tools/tests/test_continuidade_0_5_19_file_context_personality_skills.py
Logs/CHANGELOG_0_5_19_FILE_CONTEXT_PERSONALITY_SKILLS_FIX.txt
Logs/validation_0_5_19_compile_report.txt
Logs/validation_0_5_19_file_context_personality_skills_report.txt
```

## Teste atual

```bash
python tools/tests/test_continuidade_0_5_19_file_context_personality_skills.py
```

Bateria completa local:

```bash
python -m compileall -q .
python tools/tests/test_continuidade_0_5_17_hostmode_read_response_auto.py
python tools/tests/test_continuidade_0_5_18_operational_repeat_chat_path_fix.py
python tools/tests/test_continuidade_0_5_19_file_context_personality_skills.py
```
