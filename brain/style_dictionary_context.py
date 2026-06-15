# =========================
# 📚 STYLE DICTIONARY CONTEXT
# =========================

import json
import re
import unicodedata
from pathlib import Path


class StyleDictionaryContext:
    def __init__(self, dictionary_folder="data/style_dictionaries", max_entries=6, max_chars_per_entry=550):
        self.dictionary_folder = Path(dictionary_folder)
        self.max_entries = max_entries
        self.max_chars_per_entry = max_chars_per_entry
        self.entries = []
        self.loaded = False

    def carregar(self):
        self.entries = []

        if not self.dictionary_folder.exists():
            print(f"⚠️ Pasta de dicionários não encontrada: {self.dictionary_folder}")
            self.loaded = True
            return

        json_files = sorted(self.dictionary_folder.glob("*.json"))

        if not json_files:
            print(f"⚠️ Nenhum dicionário .json encontrado em: {self.dictionary_folder}")
            self.loaded = True
            return

        for json_file in json_files:
            self._carregar_arquivo_json(json_file)

        self.loaded = True
        print(f"📚 StyleDictionary carregado: {len(self.entries)} entradas em {len(json_files)} arquivo(s)")

    def buscar_contexto(self, texto_usuario):
        if not self.loaded:
            self.carregar()

        texto_normalizado = self._normalizar(texto_usuario)

        if not texto_normalizado:
            return ""

        resultados = []

        for entry in self.entries:
            score = self._calcular_score(entry, texto_normalizado)

            if score > 0:
                resultados.append({
                    "score": score,
                    "entry": entry
                })

        if not resultados:
            return ""

        resultados.sort(key=lambda item: item["score"], reverse=True)

        escolhidos = []
        usados = set()

        for item in resultados:
            entry = item["entry"]
            chave = entry["term_normalized"]

            if chave in usados:
                continue

            usados.add(chave)
            escolhidos.append(entry)

            if len(escolhidos) >= self.max_entries:
                break

        return self._montar_contexto(escolhidos)

    def _carregar_arquivo_json(self, json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as file:
                data = json.load(file)

            entradas = self._extrair_entradas(data, source=json_file.name)

            for entry in entradas:
                if entry["term"]:
                    self.entries.append(entry)

        except Exception as erro:
            print(f"⚠️ Erro ao carregar dicionário {json_file.name}: {erro}")

    def _extrair_entradas(self, data, source):
        entradas = []

        if isinstance(data, list):
            for item in data:
                entrada = self._converter_item_para_entrada(item, source)
                if entrada:
                    entradas.append(entrada)

            return entradas

        if isinstance(data, dict):
            possible_lists = [
                "entries",
                "termos",
                "terms",
                "items",
                "dictionary",
                "dicionario",
                "style_dictionary"
            ]

            for key in possible_lists:
                if key in data and isinstance(data[key], list):
                    for item in data[key]:
                        entrada = self._converter_item_para_entrada(item, source)
                        if entrada:
                            entradas.append(entrada)

                    return entradas

            for key, value in data.items():
                entrada = self._converter_chave_valor_para_entrada(key, value, source)
                if entrada:
                    entradas.append(entrada)

            return entradas

        return entradas

    def _converter_item_para_entrada(self, item, source):
        if isinstance(item, str):
            return self._criar_entrada(
                term=item,
                aliases=[],
                category="",
                meaning=item,
                examples=[],
                tone="",
                source=source
            )

        if not isinstance(item, dict):
            return None

        term = self._primeiro_valor(item, [
            "term",
            "termo",
            "palavra",
            "name",
            "nome",
            "slug",
            "expressao",
            "expressão",
            "title",
            "titulo",
            "título"
        ])

        if not term:
            return None

        aliases = self._lista_valores(item, [
            "aliases",
            "alias",
            "sinonimos",
            "sinônimos",
            "variacoes",
            "variações",
            "formas",
            "keywords",
            "palavras_chave"
        ])

        contexts = self._lista_valores(item, [
            "contexts",
            "contextos",
            "keywords",
            "palavras_chave"
        ])

        category = self._primeiro_valor(item, [
            "category",
            "categoria",
            "type",
            "tipo",
            "grupo",
            "contexto",
            "context"
        ])

        meaning = self._primeiro_valor(item, [
            "meaning",
            "significado",
            "definition",
            "definicao",
            "definição",
            "description",
            "descricao",
            "descrição",
            "explicacao",
            "explicação",
            "uso",
            "use",
            "notes",
            "notas"
        ])

        examples = self._lista_valores(item, [
            "examples",
            "exemplos",
            "frases",
            "samples"
        ])

        tone = self._primeiro_valor(item, [
            "tone",
            "tom",
            "estilo",
            "style"
        ])

        if not meaning:
            meaning = self._compactar_objeto(item)

        return self._criar_entrada(
            term=term,
            aliases=aliases,
            category=category,
            contexts=contexts,
            meaning=meaning,
            examples=examples,
            tone=tone,
            source=source
        )

    def _converter_chave_valor_para_entrada(self, key, value, source):
        term = str(key).strip()

        if not term:
            return None

        aliases = []
        contexts = []
        category = ""
        examples = []
        tone = ""

        if isinstance(value, dict):
            aliases = self._lista_valores(value, [
                "aliases",
                "alias",
                "sinonimos",
                "sinônimos",
                "variacoes",
                "variações",
                "keywords",
                "palavras_chave"
            ])

            contexts = self._lista_valores(value, [
                "contexts",
                "contextos",
                "keywords",
                "palavras_chave"
            ])

            category = self._primeiro_valor(value, [
                "category",
                "categoria",
                "type",
                "tipo",
                "contexto",
                "context"
            ])

            meaning = self._primeiro_valor(value, [
                "meaning",
                "significado",
                "definition",
                "definicao",
                "definição",
                "description",
                "descricao",
                "descrição",
                "explicacao",
                "explicação",
                "uso",
                "use",
                "notes",
                "notas"
            ])

            examples = self._lista_valores(value, [
                "examples",
                "exemplos",
                "frases",
                "samples"
            ])

            tone = self._primeiro_valor(value, [
                "tone",
                "tom",
                "estilo",
                "style"
            ])

            if not meaning:
                meaning = self._compactar_objeto(value)

        else:
            meaning = self._compactar_objeto(value)

        return self._criar_entrada(
            term=term,
            aliases=aliases,
            category=category,
            contexts=contexts,
            meaning=meaning,
            examples=examples,
            tone=tone,
            source=source
        )

    def _criar_entrada(self, term, aliases, category, contexts, meaning, examples, tone, source):
        term = str(term).strip()
        aliases = [str(alias).strip() for alias in aliases if str(alias).strip()]
        contexts = [str(context).strip() for context in contexts if str(context).strip()]
        examples = [str(example).strip() for example in examples if str(example).strip()]
        secondary_text = " ".join([str(category or ""), str(meaning or ""), str(tone or ""), *contexts, *examples])

        return {
            "term": term,
            "term_normalized": self._normalizar(term),
            "aliases": aliases,
            "aliases_normalized": [self._normalizar(alias) for alias in aliases],
            "contexts": contexts,
            "secondary_normalized": self._normalizar(secondary_text),
            "category": str(category).strip() if category else "",
            "meaning": str(meaning).strip() if meaning else "",
            "examples": examples,
            "tone": str(tone).strip() if tone else "",
            "source": source
        }

    def _tokens_busca(self, texto_normalizado):
        ignorar = {
            "a", "o", "as", "os", "um", "uma", "de", "do", "da", "dos", "das",
            "e", "ou", "que", "como", "qual", "quais", "pra", "para", "por",
            "me", "te", "eu", "voce", "isso", "isto", "aquele", "aquela", "sobre"
        }
        return {token for token in str(texto_normalizado or "").split() if len(token) >= 3 and token not in ignorar}

    def _calcular_score(self, entry, texto_normalizado):
        score = 0

        termo = entry["term_normalized"]

        if termo and self._contem_termo(texto_normalizado, termo):
            score += 100 + min(len(termo), 30)

        for alias in entry["aliases_normalized"]:
            if alias and self._contem_termo(texto_normalizado, alias):
                score += 80 + min(len(alias), 25)

        query_tokens = self._tokens_busca(texto_normalizado)
        secondary_tokens = self._tokens_busca(entry.get("secondary_normalized", ""))
        overlap = query_tokens & secondary_tokens
        if overlap:
            score += len(overlap) * 5

        return score

    def _contem_termo(self, texto_normalizado, termo_normalizado):
        if len(termo_normalizado) < 2:
            return False

        pattern = r"(?<!\w)" + re.escape(termo_normalizado) + r"(?!\w)"
        return re.search(pattern, texto_normalizado) is not None

    def _montar_contexto(self, entries):
        linhas = []
        linhas.append("Contexto recuperado dos dicionários de estilo/termos:")
        linhas.append("Use estas informações para entender termos, gírias, speedrun, games e lives.")
        linhas.append("Não copie literalmente se não precisar. Use como contexto para responder com mais precisão.")

        for entry in entries:
            bloco = self._formatar_entrada(entry)
            linhas.append(bloco)

        return "\n".join(linhas).strip()

    def _formatar_entrada(self, entry):
        partes = []

        partes.append(f"- Termo: {entry['term']}")

        if entry["category"]:
            partes.append(f"  Categoria/contexto: {entry['category']}")

        if entry.get("contexts"):
            partes.append("  Contextos de busca: " + ", ".join(entry["contexts"][:8]))

        if entry["meaning"]:
            significado = entry["meaning"]

            if len(significado) > self.max_chars_per_entry:
                significado = significado[:self.max_chars_per_entry].rstrip() + "..."

            partes.append(f"  Significado/uso: {significado}")

        if entry["aliases"]:
            aliases = ", ".join(entry["aliases"][:8])
            partes.append(f"  Variações/sinônimos: {aliases}")

        if entry["examples"]:
            exemplos = " | ".join(entry["examples"][:3])
            partes.append(f"  Exemplos: {exemplos}")

        if entry["tone"]:
            partes.append(f"  Tom sugerido: {entry['tone']}")

        partes.append(f"  Fonte: {entry['source']}")

        return "\n".join(partes)

    def _primeiro_valor(self, item, keys):
        for key in keys:
            if key in item and item[key] not in [None, ""]:
                value = item[key]

                if isinstance(value, list):
                    return ", ".join(str(v) for v in value)

                if isinstance(value, dict):
                    return self._compactar_objeto(value)

                return str(value)

        return ""

    def _lista_valores(self, item, keys):
        for key in keys:
            if key not in item:
                continue

            value = item[key]

            if value in [None, ""]:
                return []

            if isinstance(value, list):
                return [str(v) for v in value]

            if isinstance(value, str):
                return [parte.strip() for parte in value.split(",") if parte.strip()]

            return [str(value)]

        return []

    def _compactar_objeto(self, value):
        if value is None:
            return ""

        if isinstance(value, str):
            return value

        if isinstance(value, list):
            return " | ".join(self._compactar_objeto(item) for item in value)

        if isinstance(value, dict):
            partes = []

            for key, item in value.items():
                if item in [None, ""]:
                    continue

                partes.append(f"{key}: {self._compactar_objeto(item)}")

            return " / ".join(partes)

        return str(value)

    def _normalizar(self, texto):
        if texto is None:
            return ""

        texto = str(texto).lower().strip()
        texto = unicodedata.normalize("NFD", texto)
        texto = "".join(char for char in texto if unicodedata.category(char) != "Mn")
        texto = re.sub(r"\s+", " ", texto)

        return texto