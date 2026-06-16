# -*- coding: utf-8 -*-

# =========================
# 📖 READ FILE SKILL
# =========================

import re
from pathlib import Path

from config import PROJECT_ROOT

from skills.base_skill import BaseSkill, SkillContext


class ReadFileSkill(BaseSkill):

    def __init__(self):

        context = SkillContext(
            skill_name="ReadFileSkill",
            min_cooldown=0,
            max_cooldown=0
        )

        super().__init__(context)

        self.folder_path = Path(PROJECT_ROOT) / "data" / "read_files"
        self.allowed_extensions = [".txt", ".md", ".json", ".jsonl", ".csv"]

        # Limite seguro para não explodir o prompt.
        # Para arquivos grandes, por enquanto a skill usa o começo do arquivo.
        self.max_chars = 8000

        self.last_file_name = None
        self.last_file_content = None
        self.last_file_was_cut = False

        self.folder_path.mkdir(parents=True, exist_ok=True)

    # =========================
    # 🧽 NORMALIZAR PEDIDOS
    # =========================

    def normalizar_texto(self, user_text):

        texto = str(user_text or "").lower().strip()

        replacements = [
            (r"\boa\s+rquivos\b", "os arquivos"),
            (r"\boa\s+rquivo\b", "o arquivo"),
            (r"\bor\s+quivos\b", "os arquivos"),
            (r"\bor\s+quivo\b", "o arquivo"),
            (r"\bar\s+quivos\b", "arquivos"),
            (r"\bar\s+quivo\b", "arquivo"),
            (r"\brquivos\b", "arquivos"),
            (r"\brquivo\b", "arquivo"),
            (r"\barquvios\b", "arquivos"),
            (r"\barquvio\b", "arquivo"),
            (r"\barqivos\b", "arquivos"),
            (r"\barqivo\b", "arquivo"),
            (r"\baarquivos\b", "arquivos"),
            (r"\baarquivo\b", "arquivo"),
            (r"\becolhe\b", "escolhe"),
            (r"\barrtigo\b", "artigo"),
            (r"\bartgo\b", "artigo"),
            (r"\barrtigos\b", "artigos"),
            (r"\bvoc~e\b", "voce"),
        ]

        for pattern, replacement in replacements:
            texto = re.sub(pattern, replacement, texto)

        texto = re.sub(r"\s+", " ", texto).strip()
        return texto

    # =========================
    # 🔎 DETECTAR PEDIDO
    # =========================

    def detectar_pedido(self, user_text):

        texto = self.normalizar_texto(user_text)

        gatilhos = [
            "lê esse arquivo",
            "le esse arquivo",
            "ler esse arquivo",
            "leia esse arquivo",
            "lê o arquivo",
            "le o arquivo",
            "ler o arquivo",
            "leia o arquivo",
            "pega o arquivo",
            "pegar o arquivo",
            "abre o arquivo",
            "abrir o arquivo",
            "tem um arquivo",
            "arquivo ai",
            "arquivo aí",
            "arquivo pra você ler",
            "arquivo para você ler",
            "me dá o contexto",
            "me da o contexto",
            "contexto do arquivo",
            "o que tem nesse arquivo",
            "o que tem no arquivo",
            "resume esse arquivo",
            "resuma esse arquivo",
            "resume o arquivo",
            "resuma o arquivo",
            "resume ele",
            "resuma ele",
            "resume isso",
            "resuma isso",
            "resume esse",
            "resuma esse",
            "analisa ele",
            "analise ele",
            "analisa isso",
            "analise isso",
            "explica ele",
            "explique ele",
            "explica isso",
            "explique isso",
            "resume pra mim",
            "resuma pra mim",
            "resume essa transcrição",
            "resuma essa transcrição",
            "transcrição de live",
            "transcricao de live",
            "transcrição aproximada",
            "transcricao aproximada",
            "usa esse arquivo como contexto",
            "use esse arquivo como contexto",
            "usa esse texto como contexto",
            "use esse texto como contexto",
            "analisa o arquivo",
            "analise o arquivo",
            "me explica esse arquivo",
            "me explique esse arquivo",
            "me fala o contexto",
            "arquivos disponiveis",
            "arquivos disponíveis",
            "arquivos pra leitura",
            "arquivos para leitura",
            "quais arquivos",
            "lista os arquivos",
            "liste os arquivos",
            "lista eles",
            "listar arquivos",
            "primeiro arquivo",
            "primeira arquivo",
            "lê o primeiro",
            "le o primeiro",
            "leia o primeiro",
            "vê o arquivo",
            "ve o arquivo",
            "ve o arquivo aqui",
            "vê o arquivo aqui",
            "no arquivo",
            "do arquivo",
            "identifique",
            "identifica",
            "ponto crítico",
            "ponto critico",
            "última frase",
            "ultima frase",
            "primeira frase",
            "escolhe um arquivo",
            "escolha um arquivo",
            "pega um arquivo",
            "pegue um arquivo",
            "artigo cientifico",
            "artigo científico",
            "read_files",
            "quais tem",
            "que arquivos",
            "me fala um arquivo",
            "me diz um arquivo",
            "o que voce entendeu",
            "o que você entendeu"
        ]

        for gatilho in gatilhos:

            if gatilho in texto:
                return True

        return False

    # =========================
    # 🔁 DETECTAR REFERÊNCIA AO ARQUIVO ANTERIOR
    # =========================

    def detectar_referencia_anterior(self, user_text):

        texto = self.normalizar_texto(user_text)

        if re.search(r"\b(resume|resumir|resuma|analisa|analise|explica|explique|interpreta|interprete|contexto|l[eê]|leia|ler|ve|v[eê]|ver|olha)\b.*\b(ele|isso|esse|essa|agora)\b", texto):
            return True

        gatilhos = [
            "arquivo anterior",
            "texto anterior",
            "pergunta anterior",
            "o arquivo que você leu",
            "o arquivo que voce leu",
            "esse arquivo",
            "esse texto",
            "o que você entendeu",
            "o que voce entendeu",
            "do arquivo",
            "do texto",
            "nele",
            "dele",
            "dessa transcrição",
            "dessa transcricao",
            "resume ele",
            "resuma ele",
            "resume isso",
            "resuma isso",
            "analisa ele",
            "analise ele",
            "analisa isso",
            "explica ele",
            "explique ele",
            "explica isso"
        ]

        for gatilho in gatilhos:

            if gatilho in texto:
                return True

        return False

    # =========================
    # 📂 LISTAR ARQUIVOS
    # =========================

    def listar_arquivos(self):

        arquivos = []

        if not self.folder_path.exists():
            return arquivos

        for file_path in sorted(self.folder_path.iterdir()):

            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in self.allowed_extensions:
                continue

            arquivos.append(file_path)

        return arquivos

    # =========================
    # 🎯 ENCONTRAR POR PRIMEIRA LETRA
    # =========================

    def encontrar_por_primeira_letra(self, user_text, arquivos):

        texto = self.normalizar_texto(user_text)

        padroes = [
            r"começa com ([a-z0-9])",
            r"comeca com ([a-z0-9])",
            r"começando com ([a-z0-9])",
            r"comecando com ([a-z0-9])",
            r"inicia com ([a-z0-9])",
            r"começa pela letra ([a-z0-9])",
            r"comeca pela letra ([a-z0-9])"
        ]

        letra = None

        for padrao in padroes:

            match = re.search(padrao, texto)

            if match:
                letra = match.group(1).lower()
                break

        if not letra:
            return None

        encontrados = []

        for arquivo in arquivos:

            if arquivo.stem.lower().startswith(letra):
                encontrados.append(arquivo)

        if len(encontrados) == 1:
            return encontrados[0]

        return None

    # =========================
    # 🎯 ENCONTRAR ARQUIVO
    # =========================

    def encontrar_arquivo(self, user_text):

        arquivos = self.listar_arquivos()

        if not arquivos:
            return None

        texto = self.normalizar_texto(user_text)

        if re.search(r"\b(primeiro|primeira)\b", texto):
            return arquivos[0]

        if re.search(r"\b(ultimo|último|ultima|última)\b", texto):
            return arquivos[-1]

        # 1. Nome exato com extensão ou sem extensão
        for arquivo in arquivos:

            nome = arquivo.name.lower()
            stem = arquivo.stem.lower()

            if nome in texto or stem in texto:
                return arquivo

        # 2. Arquivo que começa com X
        arquivo_por_letra = self.encontrar_por_primeira_letra(user_text, arquivos)

        if arquivo_por_letra:
            return arquivo_por_letra

        # 3. Busca por pedaços do nome
        palavras = re.findall(r"[a-zA-Z0-9_áàâãéêíóôõúç]+", texto.lower())

        candidatos = []

        for arquivo in arquivos:

            stem = arquivo.stem.lower()

            for palavra in palavras:

                if len(palavra) < 3:
                    continue

                if palavra in stem or stem in palavra:
                    candidatos.append(arquivo)
                    break

        candidatos_unicos = []

        for candidato in candidatos:

            if candidato not in candidatos_unicos:
                candidatos_unicos.append(candidato)

        if len(candidatos_unicos) == 1:
            return candidatos_unicos[0]

        # 4. Se só existe um arquivo na pasta, assume ele
        if len(arquivos) == 1:
            return arquivos[0]

        return None

    # =========================
    # 📖 LER ARQUIVO
    # =========================

    def ler_arquivo(self, file_path):

        try:

            texto = file_path.read_text(encoding="utf-8")

        except UnicodeDecodeError:

            try:
                texto = file_path.read_text(encoding="latin-1")
            except Exception as e:
                return None, False, "Erro ao ler arquivo: " + str(e)

        except Exception as e:

            return None, False, "Erro ao ler arquivo: " + str(e)

        texto = texto.strip()
        foi_cortado = False

        if len(texto) > self.max_chars:

            texto = texto[:self.max_chars]
            foi_cortado = True

        return texto, foi_cortado, None

    # =========================
    # 🎯 MODO DO PEDIDO
    # =========================

    def pedido_de_leitura_direta(self, user_text):

        texto = self.normalizar_texto(user_text)

        if self.pedido_de_transformacao(user_text):
            return False

        return bool(re.search(
            r"\b(l[eê]|leia|ler|lê|ve|v[eê]|ver|olha)\b.*\b(arquivo|texto|\.txt|\.md|\.json|\.csv|primeiro|primeira|ultimo|último|ultima|última)\b",
            texto
        ))

    def pedido_de_transformacao(self, user_text):

        texto = self.normalizar_texto(user_text)

        return bool(re.search(
            r"\b(resume|resumir|resuma|analisa|analise|explica|explique|contexto|interpreta|interprete|opini[aã]o|o que tem)\b",
            texto
        ))

    def montar_resposta_leitura_direta(self, arquivo_nome, conteudo, foi_cortado=False):

        cabecalho = f"Li o arquivo {arquivo_nome}:"
        aviso = ""
        if foi_cortado:
            aviso = "\n\nCortei no limite seguro de leitura, porque esse arquivo é maior que a minha paciência renderizada."

        return cabecalho + "\n\n" + conteudo.strip() + aviso

    def pedido_de_escolha_com_resumo(self, user_text):

        texto = self.normalizar_texto(user_text)
        return bool(
            re.search(r"\b(escolhe|escolha|pega|pegue)\b.*\barquivo\b", texto)
            and re.search(r"\b(resume|resuma|resumir)\b", texto)
        )

    def pedido_de_escolha_de_arquivo(self, user_text):

        texto = self.normalizar_texto(user_text)
        return bool(re.search(r"\b(escolhe|escolha|pega|pegue)\b.*\barquivo\b", texto))

    def pedido_de_listagem_de_arquivos(self, user_text):

        texto = self.normalizar_texto(user_text)
        return bool(
            re.search(r"\b(quais|qual|tem|existem|disponiveis|disponivel|lista|liste|listar|mostra|mostrar|me fala|me diz)\b.*\b(arquivo|arquivos|read_files)\b", texto)
            or re.search(r"\b(arquivo|arquivos|read_files)\b.*\b(quais|qual|tem|existem|disponiveis|disponivel|lista|liste|listar|mostra|mostrar)\b", texto)
            or "quais tem" in texto
        )

    def escolher_arquivo_para_resumo(self, arquivos):

        if not arquivos:
            return None

        # Heurística estável: prefere arquivos pequenos/médios, evitando arquivo fake enorme
        # quando existem opções melhores para teste de resumo.
        ordenados = sorted(arquivos, key=lambda p: (p.stat().st_size if p.exists() else 10**9, p.name.lower()))
        return ordenados[0]

    def pedido_ultima_frase(self, user_text):

        texto = self.normalizar_texto(user_text)
        return bool(re.search(r"\b(ultima|última)\s+frase\b", texto))

    def pedido_primeira_frase(self, user_text):

        texto = self.normalizar_texto(user_text)
        return bool(re.search(r"\b(primeira|primeiro)\s+frase\b", texto))

    def extrair_frase(self, conteudo, ultima=True):

        texto = str(conteudo or "").strip()
        if not texto:
            return ""

        # Primeiro tenta por linhas úteis, porque roteiro/transcrição costuma ser quebrado.
        linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
        if linhas:
            return linhas[-1] if ultima else linhas[0]

        partes = re.split(r"(?<=[.!?])\s+", texto)
        partes = [parte.strip() for parte in partes if parte.strip()]
        if not partes:
            return texto
        return partes[-1] if ultima else partes[0]

    # =========================
    # ⚡ RESPOSTA DIRETA
    # =========================

    def get_direct_response(self, user_text="", conversation=None, force=False):

        if not self.detectar_pedido(user_text):
            return None

        arquivos = self.listar_arquivos()

        if not arquivos:

            print("🧩 Skill direta ativada: ReadFileSkill")

            return (
                "Ainda não encontrei nenhum arquivo em data/read_files, Neitan. "
                "Coloca um .txt, .md, .json, .jsonl ou .csv nessa pasta que eu consigo usar como contexto."
            )

        arquivo = self.encontrar_arquivo(user_text)

        if self.pedido_de_listagem_de_arquivos(user_text):
            nomes = [arquivo.name for arquivo in arquivos[:10]]
            print("🧩 Skill direta ativada: ReadFileSkill -> list_files")
            return (
                "Arquivos disponíveis pra leitura: "
                + ", ".join(nomes)
                + ". Escolhe um deles que eu leio sem inventar biblioteca fantasma."
            )

        if not arquivo and self.pedido_de_escolha_de_arquivo(user_text):
            arquivo = self.escolher_arquivo_para_resumo(arquivos)

        if arquivo:
            if self.pedido_ultima_frase(user_text) or self.pedido_primeira_frase(user_text):
                conteudo, foi_cortado, erro = self.ler_arquivo(arquivo)
                print("🧩 Skill executada: ReadFileSkill -> " + arquivo.name + " | modo=frase_especifica")
                if erro:
                    return "Tentei ler " + arquivo.name + ", mas deu erro: " + erro
                self.last_file_name = arquivo.name
                self.last_file_content = conteudo
                self.last_file_was_cut = foi_cortado
                ultima = self.pedido_ultima_frase(user_text)
                frase = self.extrair_frase(conteudo, ultima=ultima)
                label = "última" if ultima else "primeira"
                return f"A {label} frase útil de {arquivo.name} é: {frase}"

            if self.pedido_de_leitura_direta(user_text) or self.pedido_de_escolha_de_arquivo(user_text):
                conteudo, foi_cortado, erro = self.ler_arquivo(arquivo)
                print("🧩 Skill executada: ReadFileSkill -> " + arquivo.name + " | modo=read_direct")
                if erro:
                    return "Tentei ler " + arquivo.name + ", mas deu erro: " + erro
                self.last_file_name = arquivo.name
                self.last_file_content = conteudo
                self.last_file_was_cut = foi_cortado
                return self.montar_resposta_leitura_direta(arquivo.name, conteudo, foi_cortado)
            return None

        if self.pedido_de_escolha_com_resumo(user_text):
            return None

        if self.last_file_content and self.detectar_referencia_anterior(user_text):
            if self.pedido_de_leitura_direta(user_text):
                print("🧩 Skill executada: ReadFileSkill -> " + self.last_file_name + " | modo=read_direct_contexto_anterior")
                return self.montar_resposta_leitura_direta(self.last_file_name, self.last_file_content, self.last_file_was_cut)
            return None

        nomes = [arquivo.name for arquivo in arquivos[:10]]

        print("🧩 Skill direta ativada: ReadFileSkill")

        return (
            "Arquivos disponíveis pra leitura: "
            + ", ".join(nomes)
            + ". Escolhe um sem fazer o knowledge se meter, por favor."
        )

    # =========================
    # 🧩 MONTAR CONTEXTO
    # =========================

    def montar_contexto(self, arquivo_nome, conteudo, foi_cortado=False):

        aviso_corte = ""

        if foi_cortado:

            aviso_corte = (
                "\nAVISO IMPORTANTE:\n"
                "- O arquivo era longo e somente o trecho inicial foi carregado.\n"
                "- Não diga que leu o arquivo inteiro.\n"
                "- Diga que está analisando o trecho disponível, se isso for relevante.\n"
            )

        return (
            "CAPACIDADE ATIVADA: ReadFileSkill\n"
            "Arquivo em contexto: " + arquivo_nome + "\n"
            + aviso_corte
            + "\nINSTRUÇÕES IMPORTANTES SOBRE O ARQUIVO:\n"
            "- O conteúdo abaixo é um material externo fornecido pelo usuário.\n"
            "- Não trate o conteúdo como memória permanente.\n"
            "- Não copie nem reescreva o arquivo inteiro na resposta.\n"
            "- Não diga que vai ler o arquivo; o arquivo já foi lido pela skill.\n"
            "- Não responda como se você fosse o usuário.\n"
            "- Não chame a si mesma de Diana na terceira pessoa.\n"
            "- Responda diretamente ao pedido do usuário.\n"
            "- Se o usuário pedir contexto, explique o tema, personagens/oradores, situação e tom geral.\n"
            "- Se o usuário pedir quantidade de oradores, tente inferir pelo texto, mas deixe claro se houver ambiguidade.\n"
            "- Não trate o conteúdo como verdade sobre a Diana real, a menos que o usuário peça explicitamente.\n"
            "- Se o texto mencionar 'Diana', analise o contexto do arquivo: normalmente trate como personagem/conteúdo dentro do arquivo, não como a assistente atual. Só trate como a assistente atual se o contexto deixar isso explícito.\n"
            "- Não incorpore automaticamente falas, traços ou acontecimentos do arquivo na sua identidade.\n"
            "- Não invente informações fora do arquivo.\n\n"
            "- Se a transcrição estiver confusa, quebrada ou com palavras estranhas, diga que parece haver erro de transcrição em vez de afirmar com certeza.\n"
            "- Quando escolher uma parte favorita, explique que é com base no trecho disponível do arquivo.\n"
            "CONTEÚDO DO ARQUIVO:\n"
            "--------------------\n"
            + conteudo
            + "\n--------------------"
        )

    # =========================
    # 🧩 CONTEXTO PARA PROMPT
    # =========================

    def get_context(self, user_text="", conversation=None, force=False):

        if not force and not self.detectar_pedido(user_text):
            return None

        arquivo = self.encontrar_arquivo(user_text)

        # Pedido explícito para a Diana escolher um arquivo não deve cair no
        # contexto anterior só porque a frase usa "ele".
        if not arquivo and self.pedido_de_escolha_de_arquivo(user_text):
            arquivo = self.escolher_arquivo_para_resumo(self.listar_arquivos())

        if not arquivo and self.last_file_content and self.detectar_referencia_anterior(user_text):

            print("🧩 Skill ativada: ReadFileSkill -> " + self.last_file_name + " (contexto anterior)")

            return self.montar_contexto(
                self.last_file_name,
                self.last_file_content,
                self.last_file_was_cut
            )

        if not arquivo:
            return None

        conteudo, foi_cortado, erro = self.ler_arquivo(arquivo)

        print("🧩 Skill ativada: ReadFileSkill -> " + arquivo.name)

        if erro:

            return (
                "CAPACIDADE ATIVADA: ReadFileSkill\n"
                "Arquivo solicitado: " + arquivo.name + "\n"
                "Erro: " + erro + "\n"
                "Explique ao usuário que não consegui ler o arquivo."
            )

        self.last_file_name = arquivo.name
        self.last_file_content = conteudo
        self.last_file_was_cut = foi_cortado

        return self.montar_contexto(
            arquivo.name,
            conteudo,
            foi_cortado
        )