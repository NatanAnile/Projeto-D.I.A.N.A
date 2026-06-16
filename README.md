# Projeto Diana V5

Diana é uma VTuber IA local em PT-BR criada para funcionar como personagem viva de live: debochada, travessa, levada, teimosa, inquieta, orgulhosa e útil sem virar assistente corporativa.

## Estado atual

Versão atual: **0.5.17_HOSTMODE_READ_RESPONSE_AUTO_FIX**.

Esta versão parte da **0.5.16_HOSTMODE_SCORE_CONTEXT_FIX** e corrige o comportamento do modo `read_response`.

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

Comportamento correto nesta versão:

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

## Teste atual

```bash
python tools/tests/test_continuidade_0_5_17_hostmode_read_response_auto.py
```
