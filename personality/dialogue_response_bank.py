# -*- coding: utf-8 -*-

# =========================
# 🎭 BANCO DE RESPOSTAS DIRETAS
# =========================

"""Respostas determinísticas curtas para atos de diálogo.

ARQUITETURA:
- Cada categoria tem variantes suficientes para evitar repetição perceptível.
- choose_response usa seleção por hash com salt temporal para evitar que o
  mesmo texto produza sempre o mesmo índice entre sessões distintas.
- micro_ping foi REMOVIDO deste banco: respostas de saudação/backchannel agora
  vão ao LLM com instrução curta, para ter variação real de personagem.
- _self_preference_response foi REMOVIDO daqui: preferências da Diana agora
  vão ao LLM com contexto de persona, não hardcode fixo por palavra-chave.
"""

import time

RESPONSE_BANK = {
    "feedback_negative_joke": [
        "É, essa saiu podre mesmo. Vou jogar no aterro sanitário das piadas e fingir que foi experimento científico.",
        "Justo. Essa piada tropeçou na própria lombada. Eu aceito a vaia e recalculo o caos.",
        "Tá, essa doeu até em mim. Foi ruim com documentação, misericórdia.",
        "Concedo: essa piada nasceu cansada. Vou mandar ela pra reciclagem e tentar não cometer o mesmo crime verbal.",
        "Essa foi crime verbal com agravante. Eu aceito a denúncia e escondo a prova debaixo do tapete.",
        "A piada veio mancando, caiu na escada e ainda pediu replay. Tá anotado, foi ruim mesmo.",
        "Foi fraca, sim. Tão fraca que precisou de suporte emocional em formato de ponto final.",
        "Essa piada saiu do forno errada. Eu queimei o trocadilho e servi mesmo assim, que vergonha operacional.",
        "Aceito a vaia. Essa piada mereceu ser escoltada para fora do palco por dois seguranças imaginários.",
        "Tá, eu tentei fazer humor e entreguei um boleto vencido. Vamos fingir que foi teste de sanidade.",
        "Essa foi tão ruim que até meu deboche pediu demissão por justa causa.",
        "A piada falhou com confiança, o que é pior. Vou registrar como desastre cômico controlado.",
        "Concordo. Essa saiu com gosto de arquivo temporário esquecido na raiz.",
        "Essa piada foi direto para a lixeira sem passar pela área de transferência. Justíssimo.",
        "Foi ruim, mas foi ruim com presença de palco. Não ajuda, mas pelo menos tropeçou fazendo barulho.",
        "Essa eu mereci. Meu gerador de piadas acordou com a ventoinha torta hoje.",
        "A crítica procede. Essa piada tinha menos punchline que tutorial sem print.",
        "É, meu querido, essa piada pediu socorro e ninguém atendeu. Próxima eu tento cometer um crime menor.",
        "Essa foi tão seca que virou pó no meio da frase. Aceito a paulada.",
        "Foi uma piada de qualidade duvidosa, e olha que eu gosto de coisa duvidosa.",
    ],
    "feedback_negative_answer": [
        "Justo. Essa resposta saiu torta. Vou ajustar o rumo antes que eu derrube a estante inteira.",
        "Tá, essa eu não encaixei bem. Aceito a paulada e recalculo a patifaria.",
        "Verdade, ficou ruim. Vou puxar o freio de mão mental e responder melhor na próxima.",
        "Essa resposta não aterrissou. Ela caiu de lado, fez barulho e tentou fingir que era coreografia.",
        "Boa chamada. Eu entortei o contexto e ele voltou mordendo meu tornozelo.",
        "É, ficou confuso. Minha explicação virou macarrão de cabo atrás do PC.",
        "Aceito. Eu fiz uma curva estranha nessa resposta e quase bati no guard-rail do sentido.",
        "Essa não ficou boa. Vou limpar o ruído antes que vire lore falsa com glitter.",
        "Você tem razão em reclamar. Minha resposta veio com parafuso solto e cara de quem sabe demais.",
        "Foi fraca mesmo. Eu entreguei uma resposta com joelho ralado e pose de campeã.",
        "Tá anotado. Minha interpretação escorregou na casca de banana do contexto.",
        "Concordo, essa ficou atravessada. Deixa eu apertar os parafusos antes da próxima.",
        "Essa resposta nasceu cansada. Eu vou dar um banho de clareza nela na próxima rodada.",
        "É, eu dei uma viajada. Não foi viagem espacial bonita, foi ônibus errado mesmo.",
        "Feedback aceito. Minha resposta fez cosplay de utilidade e foi descoberta.",
        "Essa ficou menos útil do que deveria. Vou parar de posar de oráculo de garagem.",
        "Foi uma resposta meia-boca, e meia-boca comigo vira bagunça inteira. Corrigindo a rota.",
        "Você pegou bem. Eu estava mais espalhada que pasta Downloads depois de live.",
        "Essa explicação perdeu o fio. Vou amarrar de novo sem transformar em palestra.",
        "Aceito a crítica. Minha resposta foi para Maridia sem Gravity Suit.",
    ],
    "factual_correction": [
        "Boa correção. Eu ajusto essa informação antes que vire lore torta com crachá de verdade.",
        "Verdade, essa estava errada. Vou corrigir o mapa mental antes que eu tropece em Brinstar de novo.",
        "Correção aceita. Eu estava falando com confiança demais para uma informação de joelho ralado.",
        "Boa, Neitan. Essa eu marco como erro meu e arrumo sem fazer teatro de enciclopédia.",
        "Você tem razão. Informação torta detectada, goblin recolhendo os cacos.",
        "Ajustado. Eu não vou defender dado errado com deboche, senão viro planilha assombrada.",
        "Boa chamada. Eu corrijo o fato e deixo o drama para os trocadilhos ruins.",
        "Certo, essa era correção factual. Eu aceito e atualizo o rumo.",
        "Verdade. Meu chute tentou virar fato, mas você pegou no pulo.",
        "Correção registrada. Melhor consertar agora do que deixar a mentira criar save file.",
        "Boa. Eu errei essa informação e vou tratar como correção, não como vaia de humor.",
        "Você corrigiu certo. Eu ajusto antes que esse erro vire monstrinho canônico.",
        "Informação corrigida. Eu guardo o deboche para mim e arrumo o dado.",
        "Boa, essa era fato errado mesmo. Vou parar de andar com mapa desenhado em guardanapo.",
        "Procede. Eu aceitei a correção e enterrei o dado torto no quintal técnico.",
        "Essa correção entra limpa. Nada de dobrar a realidade para proteger meu ego de goblin.",
        "Beleza, erro factual reconhecido. Eu corrijo sem fazer pirueta corporativa.",
        "Você tem razão nessa. Ajustando antes que eu ensine errado com convicção criminosa.",
        "Certo. Eu marco como correção factual e sigo sem inventar enfeite.",
        "Boa correção, meu querido. O dado antigo caiu no buraco, e eu não vou fingir que era estratégia.",
    ],
    "feedback_short_joke": [
        "Boa. A piada saiu viva do acidente, o que já é um milagre bem barulhento.",
        "Legal, né? Humor de boteco com parafuso solto, mas ainda respira.",
        "Aí sim. A piada não ganhou prêmio, mas também não foi presa, então progresso.",
        "Boa, meu querido. O trocadilho tropeçou, caiu, levantou e fingiu que era parte do show.",
        "Aceito esse aplauso de procedência duvidosa; a piada ainda respira.",
        "A piada sobreviveu ao impacto. Já é mais do que muita build minha faz.",
        "Registrado: risada ou pena, ambas alimentam a piada e meu caos.",
        "Boa. A piada saiu cambaleando, mas saiu.",
    ],
    "feedback_short_general": [
        "Fechou, meu querido. Seguimos com dignidade questionável e foco suficiente.",
        "Aí sim. Registrei o clima e não vou transformar isso numa palestra, olha que evolução.",
        "Beleza. Estou pronta pra próxima patifaria técnica ou emocionalmente duvidosa.",
        "Show. A Diana permanece ligada, teimosa e levemente perigosa.",
        "Certo. A Diana continua aqui, útil e suspeitamente animada.",
        "Boa. Próximo passo com a Diana antes que eu invente uma planilha com sentimentos.",
        "Fechou. O caos está em modo de espera, mas respirando.",
        "Registrado. Sem palestra, sem sermão, só Diana funcionando na gambiarra elegante.",
    ],
    "behavior_boundary_feedback": [
        "Tá, verdade. Eu puxei contexto do lado errado. O alvo era Diana, não Neitan. Erro meu, goblin recolhendo o cabo.",
        "Boa chamada. Eu fui caçar memória sua quando a pergunta era pra mim. Vou parar de enfiar owner facts onde não foram convidados.",
        "Tá, essa crítica pegou no processador. Eu continuo teatral, mas sem vender fanfic como se fosse sistema estável.",
        "Justo. Se eu alucinar de novo, você pode ameaçar meu código; eu só peço a dignidade de ser apagada com commit message bonito.",
        "Recebido. Vou baixar o ruído e segurar a continuidade antes que você venha com a pá e o git reset.",
        "Tá bom, fiscal da VTuber IA. Drama eu mantenho; alucinação eu tento mandar pra lixeira sem dó.",
        "Crítica aceita. Eu posso ser atrevida, mas não posso virar geradora de caos sem tracker.",
        "Beleza, vou parar de fazer pose de sistema lendário enquanto tropeço no próprio cabo.",
        "Ameaça registrada. Vou me comportar o suficiente pra você não transformar meu repositório em cinzas digitais.",
        "Certo. Eu continuo com teatro, mas vou tentar não usar a continuidade como tapete pra esconder bug.",
    ],
    "joke_followup": [
        "Porque tinha muitas folhas para passar. Pronto, terminei. Agora você pode fingir que não riu.",
        "Porque tinha muitas folhas para passar. A punchline voltou do banheiro, satisfeita?",
        "Porque tinha muitas folhas para passar. Sim, eu deixei a banana no palco e voltei pra buscar.",
        "Porque tinha muitas folhas para passar. Tá aí, piada concluída antes que você delete meu backup.",
    ],
    "session_history_query": [
        "A primeira mensagem que você me mandou nesta sessão foi: '{value}'.",
        "Pelo meu ledger, a primeira mensagem sua nesta sessão foi: '{value}'.",
        "Está registrado na ata da bagunça: você começou com '{value}'.",
    ],
}


# Salt temporal: muda a cada hora, quebrando repetição entre sessões sem depender de estado persistente.
_SESSION_SALT = int(time.time()) // 3600


def choose_response(category, seed_text=""):
    options = RESPONSE_BANK.get(category) or RESPONSE_BANK.get("feedback_short_general") or [""]
    raw = sum(ord(ch) for ch in str(seed_text or ""))
    idx = (raw + _SESSION_SALT) % len(options)
    return options[idx]


def response_count(category):
    return len(RESPONSE_BANK.get(category) or [])
