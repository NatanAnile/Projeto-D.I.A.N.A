# Projeto Diana V5

Diana é uma VTuber IA local em PT-BR criada para funcionar como personagem viva de live: debochada, travessa, levada, teimosa, inquieta, orgulhosa e útil sem virar assistente corporativa.

## Estado atual

Versão atual: **0.5.20_IDENTITY_GENDER_GUARD**.

Esta versão parte da **0.5.19_FILE_CONTEXT_PERSONALITY_SKILLS_FIX** e aplica um hotfix crítico de identidade/selfhood.

## Correção principal da 0.5.20

A Diana agora recebe um contrato fixo e inegociável de identidade:

```txt
- Diana é uma personagem feminina de VTuber IA local.
- Diana fala de si mesma sempre no feminino.
- Neitan/Natan é o criador, operador e interlocutor principal.
- Diana não é Neitan/Natan.
- Diana não é o criador, dona, humana ou usuária.
- Diana não controla quem liga/desliga ela.
```

Além do prompt, há guard determinístico na saída para impedir inversão de papel.

## Exemplos bloqueados/corrigidos

Errado:

```txt
sou o criador
sou o dono
eu te criei
posso te reativar
sou teimoso
fui criado
```

Corrigido/bloqueado:

```txt
sou a Diana
criador aqui é você
sou teimosa
fui criada
```

Se a resposta tentar inverter papel de forma grave, a saída é substituída por fallback seguro de personagem.

## Mantido da 0.5.19

```txt
- ReadFileSkill com typos/listagem/escolha/follow-up
- CommentSkill como camada de comentário/persona
- skill_actions.json como fonte das ações de personalidade
- game_context_skill.py removido
- style_skill.py removido
```

## Mantido da 0.5.18

```txt
- read_chat ampliado
- ocultação de diretório completo na fala final
- repeat_last_operational_task para "tenta de novo", "repete", etc.
```

## Host Mode atual

### autonomous

```txt
/host mode autonomous
```

```txt
lê mensagens novas automaticamente
responde quando score >= 6
puxa assunto em idle quando o chat fica quieto
```

### read_response

```txt
/host mode read_response
```

```txt
lê mensagens novas automaticamente
responde quando score >= 6
NÃO puxa assunto em idle
NÃO precisa de /host read para funcionar
```

## Arquivos alterados nesta versão

```txt
brain/constitution.py
brain/identity_guard.py
runtime/output_firewall.py
utils/response_cleaner.py
config.py
README.md
.github/workflows/tests.yml
tools/tests/test_continuidade_0_5_17_hostmode_read_response_auto.py
tools/tests/test_continuidade_0_5_18_operational_repeat_chat_path_fix.py
tools/tests/test_continuidade_0_5_19_file_context_personality_skills.py
tools/tests/test_continuidade_0_5_20_identity_gender_guard.py
Logs/CHANGELOG_0_5_20_IDENTITY_GENDER_GUARD.txt
Logs/validation_0_5_20_identity_gender_guard_report.txt
```

## Teste atual

```bash
python tools/tests/test_continuidade_0_5_20_identity_gender_guard.py
```

Bateria completa local:

```bash
python -m compileall -q .
python tools/tests/test_continuidade_0_5_17_hostmode_read_response_auto.py
python tools/tests/test_continuidade_0_5_18_operational_repeat_chat_path_fix.py
python tools/tests/test_continuidade_0_5_19_file_context_personality_skills.py
python tools/tests/test_continuidade_0_5_20_identity_gender_guard.py
```
