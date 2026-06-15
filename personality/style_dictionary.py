# -*- coding: utf-8 -*-

# =========================
# 📚 STYLE DICTIONARY
# =========================

import json
from pathlib import Path


class StyleDictionary:

    def __init__(self, folder_path="data/style_dictionaries"):

        self.folder_path = Path(folder_path)
        self.terms = {}

        self.load_all()

    def normalize(self, text):

        text = str(text).lower().strip()
        text = text.strip(" .,!?:;\"'“”‘’")
        text = " ".join(text.split())

        return text

    def load_all(self):

        self.terms = {}

        if not self.folder_path.exists():

            self.folder_path.mkdir(parents=True, exist_ok=True)
            print("📚 StyleDictionary: pasta criada, nenhum termo carregado")
            return

        files = sorted(self.folder_path.glob("style_dictionary_*.json"))

        for file_path in files:

            try:

                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

            except Exception as e:

                print("Aviso: erro ao carregar dicionario " + file_path.name + ": " + str(e))
                continue

            if not isinstance(data, dict):
                continue

            for term, info in data.items():

                key = self.normalize(term)

                if not key:
                    continue

                if not isinstance(info, dict):
                    info = {
                        "term": term,
                        "type": "expressao",
                        "meaning": str(info),
                        "recommended_use": ""
                    }

                item = dict(info)
                item["term"] = item.get("term", term)
                item["_source_file"] = file_path.name

                self.terms[key] = item

        print("📚 StyleDictionary: " + str(len(self.terms)) + " termo(s) carregado(s)")

    def get(self, term):

        key = self.normalize(term)

        return self.terms.get(key)

    def has(self, term):

        key = self.normalize(term)

        return key in self.terms

    def search_in_text(self, text):

        text_normalized = self.normalize(text)

        found = []

        for key, info in self.terms.items():

            if key in text_normalized:
                found.append(info)

        return found

    def get_context_for_prompt(self, text, limit=5):

        found = self.search_in_text(text)

        if not found:
            return ""

        linhas = []

        for item in found[:limit]:

            termo = item.get("term", "")
            tipo = item.get("type", "expressao")
            significado = item.get("meaning", "")
            uso = item.get("recommended_use", "")

            linha = "- " + termo + " [" + tipo + "]"

            if significado:
                linha += ": " + significado

            if uso:
                linha += " Uso recomendado: " + uso

            linhas.append(linha)

        if not linhas:
            return ""

        return "\n".join(linhas)

    def all_terms(self):

        return list(self.terms.keys())