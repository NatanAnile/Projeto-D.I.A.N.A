# Projeto Diana V5

Diana é uma VTuber IA local em PT-BR criada para funcionar como personagem viva de live: debochada, travessa, levada, teimosa, inquieta, orgulhosa e útil sem virar assistente corporativa de sapatinho liso.

## Estado atual

Versão atual: **0.5.8_OPERATIONAL_SKILL_EXECUTION_FIX**.

Esta versão corrige a execução real de skills operacionais. Na 0.5.6 a skill `ReadFileSkill` era chamada, mas pedidos de leitura direta ainda podiam cair no LLM, que anunciava que iria ler em vez de entregar o conteúdo.

O foco desta versão foi:

- `ReadFileSkill` agora separa leitura direta de resumo/análise;
- pedidos como `le o arquivo aqui pra mim`, `leia o arquivo aqui!.txt` e `lê o primeiro arquivo` retornam o conteúdo no mesmo turno;
- pedidos como `resume o arquivo` ou `analisa o arquivo` continuam usando contexto da skill + LLM;
- novo log: `🧩 Skill executada: ReadFileSkill -> arquivo | modo=read_direct`;
- Knowledge continua removido do runtime principal;
- a ponte de confidence da 0.5.6 continua preservada.

## Nome técnico

```txt
D.I.A.N.A.
Delta Intelligence for Assisted Navigation & Any% Analysis
```

`Diana` é o nome curto da personagem. `D.I.A.N.A.` é o nome técnico/acrônimo do sistema.

## Estrutura principal

```txt
Diana.py                     # orquestrador/runtime atual, em redução gradual
runtime/                     # firewall, intent router, PTT guard, ledger, helpers e retrieval pessoal
brain/                       # constituição, contexto, memória, prompt e diálogo
personality/                 # prompt/persona/style engine/response bank/joke bank
skills/                      # skills diretas: chat, arquivo, tela etc.
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
python test_continuidade_0_5_7_v21_operational_skill_execution_fix.py
```

O GitHub Actions também roda esse teste automaticamente a cada push/pull request.

## Comandos locais úteis

```txt
/stt off
/stt on
/stt status
/ptt status
/ptt reset
/tts off
/tts on
/tts status
```

Use `/ptt reset` se o Windows/keyboard ficar reportando o Control direito como pressionado depois de uma gravação.

## Observação sobre Knowledge

O Knowledge local foi removido do runtime principal na 0.5.5 porque estava competindo com skills, memória e contexto real da sessão. Ele não deve voltar como varredura genérica. Quando retornar, deve ser um módulo explícito, isolado e acionado por intenção clara, preferencialmente baseado em estado estruturado: `current_state.json`, notas de sala, telemetria e fontes com contrato rígido.

## Roadmap curto

- **0.5.8**: CommandRegistry/runtime cleanup para tirar comandos locais do `Diana.py`.
- **0.5.9**: contrato de verdade mais forte para pós-geração.
- **0.5.10**: fila/interrupção de TTS e fluxo mais não-bloqueante.
- **0.5.11**: memória hierárquica: working memory, session summary, episodic summary e semantic facts.
- **Depois**: Knowledge novo, modular, isolado e orientado a estado real.


## 0.5.8 — READFILE_FOLLOWUP_FUZZY_FIX

- Corrige typos de alta confiança em pedidos de arquivo, como `oa rquivo` e `rquivo`.
- Faz `Resume ele agora` usar o último arquivo lido como contexto.
- Evita truncamento pelo ResponseCleaner em leitura direta de arquivo.
