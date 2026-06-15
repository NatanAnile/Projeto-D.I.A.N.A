# Projeto Diana V5

Diana é uma VTuber IA local em PT-BR criada para funcionar como personagem viva de live: debochada, travessa, levada, teimosa, inquieta, orgulhosa e útil sem virar assistente corporativa de sapatinho liso.

## Estado atual

Versão atual: **0.5.1_INPUT_FIREWALL_STT_SANITY**.

A linha 0.5.x marca a Diana pós-renome: identidade nova, entrada `Diana.py`, brain `brain/diana_brain.json` e foco em reduzir dependência do LLM para atos simples.

O foco desta versão foi:

- `runtime/input_firewall.py` cria a primeira triagem central antes do LLM;
- lixo comum de STT, como encerramento de vídeo, é bloqueado antes de virar prompt;
- variantes como `Manga um piada` e `manda um piada` viram `manda uma piada`;
- microentradas como `Aí.`, `opa`, `hm` e `uhum` viram `micro_ping` com resposta direta;
- `allow_llm`, `allow_memory` e `allow_retrieval` passam pelo contexto do turno;
- `request_joke` continua fast-path determinístico pelo `joke_bank`;
- CI/teste atualizados para v15.

## Nome técnico

```txt
D.I.A.N.A.
Delta Intelligence for Assisted Navigation & Any% Analysis
```

`Diana` é o nome curto da personagem. `D.I.A.N.A.` é o nome técnico/acrônimo do sistema.

## Estrutura principal

```txt
Diana.py                     # loop principal/runtime atual
runtime/                     # firewall de entrada e tipos leves de runtime
brain/                       # contexto, memória, roteamento, prompt e diálogo
personality/                 # prompt/persona/style engine/response bank/joke bank
skills/                      # skills diretas
stt/                         # motores STT
tts/                         # motores TTS
integrations/                # integrações externas e Host Mode
data/                        # contexto, chat fake, read_files, style dictionaries
Logs/                        # changelogs e notas de evolução
.github/workflows/           # testes automáticos do GitHub Actions
```

## Configuração rápida

1. Crie um ambiente Python.
2. Instale dependências:

```bash
pip install -r requirements.txt
```

3. Copie `.env.example` para `.env` e ajuste conforme seu ambiente.
4. Garanta que o Ollama esteja rodando com o modelo configurado em `config.py`.
5. Inicie:

```bash
python Diana.py
```

## Teste atual

```bash
python test_continuidade_0_5_1_v15_input_firewall_stt_sanity.py
```

O GitHub Actions também roda esse teste automaticamente a cada push/pull request.

## Comandos locais

No terminal da Diana, use `/comandos` para ver a lista. A exibição é compacta, separada por `|`.

## Roadmap curto

- **0.5.2**: extrair `CommandRegistry` e reduzir mais o `Diana.py`, sem mexer em comportamento.
- **0.5.3**: preparar interface de Knowledge com `current_state.json`, delta de estado e notas estruturadas de Super Metroid.
- **0.5.4**: Host Mode runtime com fontes/eventos melhor separados.
- **0.5.5**: fila/interrupção de TTS e fluxo mais não-bloqueante.
- **Depois**: calibração STT v3 e ponte Discord interna.

## Observação sobre Knowledge

O Knowledge completo está pausado enquanto a base estabiliza. A direção futura é estruturada: estado real/telemetria, `current_state.json`, `room_notes.json` e injeção por delta, não textão solto no prompt.
