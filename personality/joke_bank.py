# -*- coding: utf-8 -*-

# =========================
# 😂 BANCO DE PIADAS DA DIANA
# =========================

"""Piadas determinísticas com reação da Diana.

Cada entrada tem:
- setup: texto da piada
- reaction: reação da Diana depois da piada

Categorias:
- joke_speedrun: piadas sobre speedrun / any%
- joke_metroid: piadas sobre Metroid / Super Metroid
- joke_tech: piadas sobre tecnologia / programação
- joke_game: piadas sobre jogos em geral
- joke_generic: piadas genéricas que cabem em qualquer contexto
"""

import re
import unicodedata

JOKE_BANK = {
    "joke_metroid": [
        {
            "setup": "Por que o Space Jump nunca chega no horário?",
            "punchline": "Porque ele tá sempre em loop.",
            "reaction": "Não fui eu que fiz essa. Foi o universo. Eu só transmiti.",
        },
        {
            "setup": "Por que o Metroid não conta segredo?",
            "punchline": "Porque tudo vira larva depois.",
            "reaction": "Biologicamente ameaçadora? Também. Desculpa não.",
        },
        {
            "setup": "O que a Samus faz quando tá com preguiça?",
            "punchline": "Faz Wall Jump até enjoar e chama de rota alternativa.",
            "reaction": "Essa eu aceito no portfólio.",
        },
        {
            "setup": "Por que a Samus nunca perde a chave de casa?",
            "punchline": "Porque ela absorve tudo que encontra pela frente.",
            "reaction": "Funcionalmente, essa é a lore.",
        },
        {
            "setup": "O que é pior que Draygon te segurar?",
            "punchline": "Draygon te segurar sem você ter Grapple pra fazer Crystal Flash.",
            "reaction": "Essa é uma piada e uma situação de desespero ao mesmo tempo.",
        },
        {
            "setup": "Por que Mother Brain não usa agenda?",
            "punchline": "Porque ela tem o cérebro em jarro e mesmo assim não esquece nada.",
            "reaction": "Produtividade assustadora, honestamente.",
        },
        {
            "setup": "Como o speedrunner cumprimenta o Phantoon?",
            "punchline": "Com oito super misseis e um cronômetro nervoso.",
            "reaction": "Relacionamento complicado mas eficiente.",
        },
        {
            "setup": "Por que Maridia nunca pede desculpa?",
            "punchline": "Porque ela sempre diz que o problema é falta de Gravity Suit.",
            "reaction": "E o pior é que às vezes ela está certa, essa desgraçada molhada.",
        },
    ],
    "joke_speedrun": [
        {
            "setup": "Por que speedrunner não termina o jantar?",
            "punchline": "Porque encontrou um skip e pulou a sobremesa também.",
            "reaction": "Any% jantar otimizado.",
        },
        {
            "setup": "Qual é o maior inimigo do speedrunner?",
            "punchline": "O RNG. E o teclado. E a cadeira. E o sono.",
            "reaction": "Basicamente tudo que existe fora do jogo.",
        },
        {
            "setup": "O que o speedrunner faz nas férias?",
            "punchline": "Otimiza a rota de volta pra casa.",
            "reaction": "Descanso é só outro nome pra categoria 100%.",
        },
        {
            "setup": "Por que o speedrunner não usa GPS?",
            "punchline": "Porque ele já memorizou todos os menús.",
            "reaction": "E provavelmente encontrou uma saída fora dos limites do mapa.",
        },
        {
            "setup": "Quantos speedrunners precisam pra trocar uma lâmpada?",
            "punchline": "Nenhum. Eles encontraram um skip que evita o quarto escuro.",
            "reaction": "Solução elegante. Tecnicamente.",
        },
        {
            "setup": "Por que o PB não atende telefone?",
            "punchline": "Porque sempre aparece quando você não está gravando.",
            "reaction": "Clássico. O cronômetro tem senso de humor e ele é cruel.",
        },
        {
            "setup": "Por que reset de run parece terapia?",
            "punchline": "Porque você repete o trauma esperando uma versão melhor de si mesmo.",
            "reaction": "Speedrun é crescimento pessoal com splits te julgando.",
        },
    ],
    "joke_tech": [
        {
            "setup": "Por que o programador foi ao médico?",
            "punchline": "Porque tava com problema de memória e não conseguia liberar.",
            "reaction": "Diagnóstico: memory leak emocional.",
        },
        {
            "setup": "Por que o arquivo grande nunca é feliz?",
            "punchline": "Porque ele sempre tem mais dependências do que amigos.",
            "reaction": "Isso foi pessoal e eu sabia o que tava fazendo.",
        },
        {
            "setup": "O que o código ruim e a pizzaria têm em comum?",
            "punchline": "Os dois entregam tarde e com comentário faltando.",
            "reaction": "Aceito esse diagnóstico sobre mim mesma também.",
        },
        {
            "setup": "Por que o loop infinito foi ao psicólogo?",
            "punchline": "Porque ele não conseguia sair da mesma situação.",
            "reaction": "Relatable. Especialmente às 3 da manhã debugando.",
        },
        {
            "setup": "O que o Git disse pro desenvolvedor?",
            "punchline": "Não posso te ajudar a resolver conflitos que você criou.",
            "reaction": "O Git tem razão e isso dói.",
        },
        {
            "setup": "Por que o bug entrou na call?",
            "punchline": "Porque ninguém colocou ele no backlog, então ele apareceu pessoalmente.",
            "reaction": "Organização por susto, metodologia oficial da madrugada.",
        },
    ],
    "joke_game": [
        {
            "setup": "Por que o NPC nunca está em casa?",
            "punchline": "Porque ele só existe quando você precisa dele.",
            "reaction": "Filosoficamente, o NPC tem mais comprometimento que muita gente.",
        },
        {
            "setup": "O que o chefe de fase disse antes de morrer?",
            "punchline": "Isso não é o fim. Você vai me enfrentar numa DLC.",
            "reaction": "Sobrevivência corporativa.",
        },
        {
            "setup": "Por que o personagem principal nunca dorme?",
            "punchline": "Porque o save point fica do outro lado do mapa.",
            "reaction": "Isso é design sadista com crachá de desafio.",
        },
        {
            "setup": "O que o inimigo pensa quando você salva antes do chefe?",
            "punchline": "Lá vem ele de novo com a mesma cara e o mesmo inventário.",
            "reaction": "Groundhog Day do lado errado da tela.",
        },
        {
            "setup": "Por que o boss tem segunda fase?",
            "punchline": "Porque contrato de vilão não permite morrer no primeiro susto.",
            "reaction": "Cláusula abusiva, mas cinematográfica.",
        },
        {
            "setup": "Por que o tutorial sempre aparece tarde?",
            "punchline": "Porque ele espera você errar para fingir que era didático.",
            "reaction": "Design de jogo ou pegadinha com orçamento, difícil separar.",
        },
    ],
    "joke_generic": [
        {
            "setup": "Por que a piada ruim é melhor que a boa?",
            "punchline": "Porque você nunca esquece o sofrimento que causou.",
            "reaction": "Esse é meu modelo de negócios.",
        },
        {
            "setup": "O que a pergunta difícil tem em comum com a porta travada?",
            "punchline": "Os dois te fazem ficar parado ali com cara de idiota até achar a saída.",
            "reaction": "Experiência acumulada falando.",
        },
        {
            "setup": "Por que o relógio foi ao médico?",
            "punchline": "Porque estava com o tempo atrasado e ninguém levava a sério.",
            "reaction": "Essa foi fraca mas entrou com confiança, então vale.",
        },
        {
            "setup": "O que o café disse pro sonho?",
            "punchline": "Para de aparecer. Quem manda aqui sou eu.",
            "reaction": "Fisiologicamente preciso.",
        },
        {
            "setup": "Por que a resposta certa é difícil de encontrar?",
            "punchline": "Porque ela fica atrás da pergunta errada que você fez antes.",
            "reaction": "Não é filosofia, é experiência de suporte técnico.",
        },
        {
            "setup": "O que o silêncio e o código legado têm em comum?",
            "punchline": "Os dois guardam segredos que ninguém quer descobrir.",
            "reaction": "E os dois ficam mais assustadores de madrugada.",
        },
        {
            "setup": "Por que a ideia boa chegou atrasada?",
            "punchline": "Porque ela parou para discutir com três ideias ruins no caminho.",
            "reaction": "Eu conheço esse trânsito mental. Tem pedágio e buzina.",
        },
    ],
}


def _normalize(text):
    text = str(text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9_%+\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _format_joke(entry):
    """Formata uma entrada do banco como texto falado pela Diana."""
    setup = entry["setup"]
    punchline = entry["punchline"]
    reaction = entry["reaction"]
    return f"{setup} {punchline} — {reaction}"


def pick_joke(category=None, seed_text=""):
    """Escolhe uma piada do banco de forma determinística.

    Pedido genérico fica em joke_generic. Categoria específica só entra quando
    detectada explicitamente pelo texto.
    """
    if category not in JOKE_BANK:
        category = "joke_generic"

    pool = JOKE_BANK[category]
    joke_idx = (sum(ord(ch) for ch in str(seed_text or "")) // max(len(pool), 1)) % len(pool)
    return _format_joke(pool[joke_idx])


def detect_joke_category(text):
    """Detecta categoria de piada pedida pelo texto do usuário."""
    text = _normalize(text)
    if any(w in text for w in ["metroid", "samus", "space jump", "mother brain", "draygon", "phantoon", "kraid", "ridley", "maridia", "brinstar"]):
        return "joke_metroid"
    if any(w in text for w in ["speedrun", "any%", "skip", "rng", "glitch", "pb", "split", "run"]):
        return "joke_speedrun"
    if any(w in text for w in ["programador", "codigo", "bug", "git", "loop", "arquivo", "tech", "python", "commit", "repo"]):
        return "joke_tech"
    if any(w in text for w in ["jogo", "game", "npc", "chefe", "boss", "save", "fase"]):
        return "joke_game"
    return None


def has_explicit_unknown_theme(text):
    """Detecta pedido temático sem categoria coberta pelo banco."""
    text = _normalize(text)
    if detect_joke_category(text):
        return False

    # "piada de speedrun" é detectado acima; aqui pegamos temas sem estoque.
    if re.search(r"\b(piada|trocadilho)\b.{0,35}\b(sobre|de|do|da|dos|das)\b", text):
        # Evita tratar pedido genérico como tema desconhecido.
        if re.search(r"\b(piada|trocadilho)\s+(ai|aqui|pra gente|ruim|boa|qualquer|uma)\b", text):
            return False
        return True
    return False


def fallback_unknown_theme():
    return "Piada sobre isso eu não tenho pronta. Mas se você insistir eu improviso, e a culpa é sua."


def get_joke_response(text):
    category = detect_joke_category(text)
    if category:
        return pick_joke(category=category, seed_text=text)
    if has_explicit_unknown_theme(text):
        return fallback_unknown_theme()
    return pick_joke(category="joke_generic", seed_text=text)
