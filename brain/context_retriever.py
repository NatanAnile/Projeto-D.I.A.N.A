# -*- coding: utf-8 -*-

# =========================
# 🔎 RECUPERAÇÃO DE CONTEXTO
# =========================

import json
import re
import random
import unicodedata
from pathlib import Path

from brain.identity_guard import is_diana_self_target


def _normalizar(texto):

    texto = str(texto or "").lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(char for char in texto if unicodedata.category(char) != "Mn")
    texto = re.sub(r"[^a-z0-9_%+\- ]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    # Correções leves para erros comuns de digitação/STT que afetam roteamento.
    replacements = {
        "mue": "meu",
        "mueu": "meu",
        "tasquihna": "diana",
        "diana": "diana",
        "grappling bram": "grappling beam",
        "grapple bram": "grapple beam",
        "oura tecnica": "outra tecnica"
    }
    for wrong, right in replacements.items():
        texto = re.sub(r"(?<!\w)" + re.escape(wrong) + r"(?!\w)", right, texto)

    return texto.strip()


def _tokens(texto):

    ignorar = {
        "a", "o", "as", "os", "um", "uma", "de", "do", "da", "dos", "das",
        "e", "ou", "que", "como", "qual", "quais", "pra", "para", "por",
        "me", "te", "eu", "voce", "voces", "isso", "isto", "aquele", "aquela",
        "sobre", "alguma", "algum", "coisa"
    }

    return {
        token for token in _normalizar(texto).split()
        if len(token) >= 2 and token not in ignorar
    }


class StyleRetriever:

    def __init__(self, dictionary_folder="data/style_dictionaries", max_results=1):

        self.dictionary_folder = Path(dictionary_folder)
        self.max_results = max_results
        self.entries = []
        self._load()

    def _load(self):

        self.entries = []

        if not self.dictionary_folder.exists():
            return

        for json_file in sorted(self.dictionary_folder.glob("*.json")):

            try:
                with open(json_file, "r", encoding="utf-8") as file:
                    data = json.load(file)
            except Exception as erro:
                print(f"⚠️ Erro ao carregar estilo {json_file.name}: {erro}")
                continue

            self.entries.extend(self._extract_entries(data, json_file.name))

        print(f"🎭 StyleRetriever: {len(self.entries)} entrada(s) disponível(is)")

    def _extract_entries(self, data, source):

        entries = []

        if isinstance(data, list):
            for item in data:
                entry = self._convert_item(item, source)
                if entry:
                    entries.append(entry)
            return entries

        if isinstance(data, dict):

            for key in ["entries", "expressions", "termos", "terms", "items"]:
                if isinstance(data.get(key), list):
                    for item in data[key]:
                        entry = self._convert_item(item, source)
                        if entry:
                            entries.append(entry)
                    return entries

            for key, value in data.items():
                if isinstance(value, dict):
                    item = dict(value)
                    item.setdefault("term", key)
                else:
                    item = {"term": key, "meaning": value}

                entry = self._convert_item(item, source)
                if entry:
                    entries.append(entry)

        return entries

    def _convert_item(self, item, source):

        if isinstance(item, str):
            item = {"term": item, "meaning": item}

        if not isinstance(item, dict):
            return None

        term = self._first(item, ["term", "termo", "name", "nome", "expressao", "expressão"])

        if not term:
            return None

        aliases = self._list(item, ["aliases", "alias", "sinonimos", "sinônimos", "variacoes", "variações"])
        contexts = self._list(item, ["contexts", "contextos", "keywords", "palavras_chave"])
        use_when = self._first(item, ["use_when", "uso", "context", "contexto"])
        meaning = self._first(item, ["meaning", "significado", "definition", "definicao", "definição", "description", "descricao", "descrição"])
        tone = self._first(item, ["tone", "tom", "style", "estilo"])

        searchable = " ".join([str(term), *aliases, *contexts])

        return {
            "term": str(term).strip(),
            "aliases": aliases,
            "contexts": contexts,
            "use_when": str(use_when).strip(),
            "meaning": str(meaning).strip(),
            "tone": str(tone).strip(),
            "searchable_tokens": _tokens(searchable),
            "source": source
        }

    def retrieve(self, user_text):

        text_normalized = _normalizar(user_text)
        query_tokens = _tokens(user_text)

        if not query_tokens or self._is_simple_greeting(text_normalized):
            return []

        ranked = []

        for entry in self.entries:
            term_normalized = _normalizar(entry["term"])
            score = 0

            # O termo/alias escrito literalmente é uma correspondência forte.
            literal_match = False
            names = [term_normalized, *[_normalizar(alias) for alias in entry.get("aliases", [])]]
            for name in names:
                if name and re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text_normalized):
                    literal_match = True
                    score += 100
                    break

            # Contextos só servem como sinal quando há pelo menos dois termos específicos.
            overlap = query_tokens & entry["searchable_tokens"]
            score += len(overlap) * 10

            if literal_match or len(overlap) >= 2:
                ranked.append((score, entry))

        ranked.sort(key=lambda item: item[0], reverse=True)

        return [entry for _, entry in ranked[:self.max_results]]

    def _is_simple_greeting(self, normalized_text):

        greeting_tokens = {
            "oi", "ola", "eai", "fala", "salve", "bom", "dia", "boa", "tarde",
            "noite", "diana", "diana", "tudo", "cima", "beleza"
        }
        tokens = set(normalized_text.split())

        return bool(tokens) and tokens.issubset(greeting_tokens) and len(tokens) <= 7

    def format_context(self, entries):

        if not entries:
            return ""

        lines = [
            "Expressão de estilo opcional recuperada.",
            "Use somente se encaixar naturalmente. Não é obrigatório usar.",
            "Ela altera apenas a forma da fala, nunca os fatos."
        ]

        for entry in entries:
            line = f"- Expressão: {entry['term']}"

            if entry["meaning"]:
                line += f" | significado: {entry['meaning']}"

            if entry["use_when"]:
                line += f" | usar quando: {entry['use_when']}"

            if entry["tone"]:
                line += f" | tom: {entry['tone']}"

            lines.append(line)

        return "\n".join(lines)

    def _first(self, item, keys):

        for key in keys:
            value = item.get(key)

            if value not in [None, ""]:
                return str(value)

        return ""

    def _list(self, item, keys):

        for key in keys:
            value = item.get(key)

            if value in [None, ""]:
                continue

            if isinstance(value, list):
                return [str(part).strip() for part in value if str(part).strip()]

            if isinstance(value, str):
                return [part.strip() for part in value.split(",") if part.strip()]

            return [str(value)]

        return []


class KnowledgeRetriever:

    COLLECTION_PATTERNS = {
        "techniques": [r"\btecnic", r"\bmovimento", r"\bmanobra"],
        "glitches": [r"\bglitch", r"\bexploit"],
        "items": [r"\bitem", r"\bequipamento", r"\bupgrade", r"\bpickup"],
        "rooms": [r"\bsala\b", r"\broom\b"],
        "enemies": [r"\binimigo", r"\benemy"],
        "bosses": [r"\bchefe", r"\bboss"],
        "routes": [r"\brota", r"\broute", r"\bcaminho"],
        "categories": [r"\bcategoria", r"\bcategorias"]
    }

    FIELD_PATTERNS = {
        "area": [r"\barea\b", r"\bregiao\b", r"\bem que area\b", r"\bqual area\b"],
        "room": [r"\bsala\b", r"\broom\b", r"\bem qual sala\b", r"\bque sala\b"],
        "requirements": [r"\brequisit", r"\bprecisa para pegar\b", r"\bo que precisa\b", r"\bexige\b", r"\btodos os requisitos\b"],
        "boss": [r"\bchefe\b", r"\bboss\b", r"\bderrotar para\b"],
        "effect": [r"\bo que faz\b", r"\befeit", r"\bfuncao\b", r"\bserve para\b"],
        "uses": [r"\bo que da para fazer\b", r"\busos?\b", r"\butilidade\b"],
        "acquisition": [r"\bcomo pega\b", r"\bcomo conseguir\b", r"\bcomo adquirir\b", r"\baquisicao\b"]
    }

    GENERIC_TOKENS = {
        "tecnica", "tecnicas", "movimento", "manobra", "super", "metroid",
        "explica", "explique", "ensina", "mostra", "mostrar", "uma", "um",
        "outra", "outro", "diferente", "qualquer", "coisa", "usar", "use",
        "usa", "com", "que", "me", "fala", "sobre", "agora"
    }

    EXACT_MATCH_BLOCKED_ALIASES = {
        "super", "missile", "ball", "beam", "speed", "ice", "wave",
        "charge", "gravity", "power", "item", "upgrade", "tank", "scope"
    }

    STRONG_SHORT_ALIASES = {"cf", "ibj", "rta", "igt", "tas", "g-mode", "r-mode"}

    FEEDBACK_MARKERS = [
        "esta correto", "estao corretas", "informacoes anteriores", "vamos deixar passar",
        "boa", "certo", "entendi", "beleza", "perfeito", "voce errou", "voce inventou",
        "inventou isso", "alucinou", "buscou", "nao era isso", "nao foi isso",
        "precisa ser precisa", "seja precisa", "primeiro precisa", "depois criativa"
    ]

    CORRECTION_MARKERS = [
        "voce errou", "voce inventou", "inventou isso", "alucinou",
        "nao era isso", "nao foi isso", "buscou errado"
    ]

    TOPIC_CHANGE_MARKERS = [
        "vamos mudar de assunto", "muda de assunto", "mudando de assunto",
        "outro assunto", "troca de assunto"
    ]

    def __init__(self, knowledge_folder="data/knowledge", max_results=4):
        self.knowledge_folder = Path(knowledge_folder)
        self.max_results = max_results
        self.entries = []
        self.last_collection = ""
        self.last_entry = None
        self._active_query_plan = {}
        self._load()

    def _load(self):
        self.entries = []
        if not self.knowledge_folder.exists():
            return

        for json_file in sorted(self.knowledge_folder.rglob("*.json")):
            try:
                with open(json_file, "r", encoding="utf-8") as file:
                    data = json.load(file)
            except Exception as erro:
                print(f"⚠️ Erro ao carregar conhecimento {json_file}: {erro}")
                continue

            relative_source = str(json_file.relative_to(self.knowledge_folder))
            self.entries.extend(self._extract_entries(data, relative_source))

        print(f"📚 KnowledgeRetriever: {len(self.entries)} entrada(s) indexada(s)")

    def _extract_entries(self, data, source):
        if not isinstance(data, dict):
            return []

        collection = str(data.get("collection") or "").strip()
        raw_entries = data.get("entries")

        # Compatibilidade temporária com arquivos antigos.
        if not isinstance(raw_entries, list):
            for key in ["rooms", "techniques", "glitches", "items", "enemies", "bosses", "routes", "categories", "references", "visual_references"]:
                if isinstance(data.get(key), list):
                    collection = collection or key
                    raw_entries = data[key]
                    break

        if not isinstance(raw_entries, list):
            return []

        entries = []
        for item in raw_entries:
            entry = self._convert_entry(item, source, collection)
            if entry:
                entries.append(entry)
        return entries

    def _convert_entry(self, item, source, collection=""):
        if not isinstance(item, dict):
            return None

        name = str(item.get("name") or item.get("nome") or item.get("id") or "").strip()
        if not name:
            return None

        aliases = self._list(item, ["aliases", "alias", "sinonimos", "sinônimos"])
        entry_type = str(item.get("entry_type") or item.get("type") or collection or "").strip()
        if entry_type and not entry_type.endswith("s"):
            type_to_collection = {
                "item": "items", "technique": "techniques", "room": "rooms", "boss": "bosses",
                "enemy": "enemies", "route": "routes", "category": "categories", "glitch": "glitches"
            }
            collection = type_to_collection.get(entry_type, collection or entry_type)
        else:
            collection = collection or entry_type

        summary = str(item.get("summary") or item.get("description") or item.get("definition") or "").strip()
        searchable_values = [name, *aliases, summary]
        for key in ["area", "room", "effects", "uses", "tags", "requirements", "acquisition", "base_name"]:
            searchable_values.append(self._compact(item.get(key)))

        searchable = " ".join(v for v in searchable_values if v)
        name_variants = self._name_variants(name, aliases)

        return {
            "id": str(item.get("id") or _normalizar(name).replace(" ", "_")),
            "name": name,
            "aliases": aliases,
            "definition": summary,
            "details": self._compact(item),
            "type": collection,
            "source": source,
            "raw": item,
            "searchable_tokens": _tokens(searchable),
            "name_normalized": _normalizar(name),
            "aliases_normalized": sorted(name_variants - {_normalizar(name)})
        }

    def _name_variants(self, name, aliases):

        variants = {_normalizar(name)}
        for alias in aliases:
            normalized_alias = _normalizar(alias)
            if normalized_alias:
                variants.add(normalized_alias)

        # Nomes como "Mockball (Machball)" passam a aceitar ambos os nomes.
        for value in [name, *aliases]:
            value = str(value or "").strip()
            if not value:
                continue

            base = re.sub(r"\s*\([^)]*\)\s*", " ", value).strip()
            if base:
                variants.add(_normalizar(base))

            for group in re.findall(r"\(([^)]*)\)", value):
                for part in re.split(r"[/,|]", group):
                    part = part.strip()
                    if part:
                        variants.add(_normalizar(part))

        return {variant for variant in variants if variant}

    def infer_collection(self, user_text):
        normalized = _normalizar(user_text)
        for collection, patterns in self.COLLECTION_PATTERNS.items():
            if any(re.search(pattern, normalized) for pattern in patterns):
                return collection
        return ""

    def infer_requested_fields(self, user_text):
        normalized = _normalizar(user_text)
        found = []
        order = ["room", "area", "requirements", "boss", "effect", "uses", "acquisition"]

        for field in order:
            if any(re.search(pattern, normalized) for pattern in self.FIELD_PATTERNS[field]):
                found.append(field)

        # "Onde pega" pede localização; retorna área e sala quando ambas existirem.
        if re.search(r"\bonde (eu )?pego\b|\bonde pega\b|\bonde fica\b", normalized):
            for field in ["area", "room"]:
                if field not in found:
                    found.append(field)

        return found

    def infer_requested_field(self, user_text):
        fields = self.infer_requested_fields(user_text)
        return fields[0] if fields else ""

    def source_is_required(self, user_text, collection=""):
        normalized = _normalizar(user_text)
        explicit = any(marker in normalized for marker in [
            "na sua base", "da sua base", "nos seus arquivos", "no seu conhecimento local",
            "que esteja na base", "que voce tenha na base"
        ])
        domain_specific = "super metroid" in normalized and bool(collection)
        return explicit or domain_specific

    def retrieve(self, user_text, history_text="", query_plan=None):
        normalized = _normalizar(user_text)
        query_plan = query_plan or {}
        self._active_query_plan = query_plan

        # Mudança explícita de assunto encerra o contexto factual ativo.
        if self._is_topic_change(normalized):
            self.last_entry = None
            self.last_collection = ""
            return self._result([], "", "topic_change", set(), user_text)

        # Abrir um tópico não é pedir uma consulta específica.
        if self._is_topic_setup_only(normalized):
            return self._result([], "", "topic_setup", set(), user_text)

        # Confirmações e broncas sem uma pergunta nova não são consultas.
        if self._is_feedback_only(normalized):
            correction = any(marker in normalized for marker in self.CORRECTION_MARKERS)
            if correction:
                self.last_entry = None
                self.last_collection = ""
            return self._result([], "", "correction" if correction else "feedback", set(), user_text)

        if query_plan.get("should_query") is False:
            return self._result([], "", "skipped", set(), user_text)

        planned_collection = str(query_plan.get("collection", "")).strip().lower()
        planned_operation = str(query_plan.get("operation", "")).strip().lower()
        planned_field = str(query_plan.get("field", "")).strip().lower()
        requested_fields = [planned_field] if planned_field else self.infer_requested_fields(user_text)
        requested_fields = [field for field in requested_fields if field]
        requested_field = requested_fields[0] if requested_fields else ""

        same_request = planned_operation in {"same", "reformulate"} or self._asks_for_same(user_text) or self._asks_for_reformulation(user_text)
        another_request = planned_operation == "another" or self._asks_for_another(user_text)

        # Operações estruturais são entendidas antes de procurar uma entidade nominal.
        structural = planned_operation if planned_operation in {"first", "last", "count", "list", "random"} else self._structural_operation(normalized)
        collection = planned_collection or self.infer_collection(user_text)
        candidates = [entry for entry in self.entries if not collection or entry["type"] == collection]

        category_filter = ""
        filters = query_plan.get("filters", {}) if isinstance(query_plan.get("filters", {}), dict) else {}
        category_filter = str(filters.get("category", "")).strip().lower()
        if not category_filter and re.search(r"\b(upgrade|upgrades)\b", normalized):
            category_filter = "major_upgrade"
        if category_filter:
            candidates = [entry for entry in candidates if _normalizar(entry.get("raw", {}).get("category", "")) == _normalizar(category_filter)]

        if structural and candidates:
            if structural == "count":
                return self._result([], collection, "count", set(), user_text, count=len(candidates))
            if structural == "list":
                limit = query_plan.get("limit")
                if not limit:
                    match_limit = re.search(r"\b(\d{1,3})\b", normalized)
                    limit = int(match_limit.group(1)) if match_limit else self.max_results
                selected_entries = candidates[:max(1, int(limit))]
                return self._result(selected_entries, collection, "list", set(), user_text)
            if structural == "random":
                selected = random.choice(candidates)
                self._remember(selected)
                return self._result([selected], selected["type"], "random", set(), user_text)
            selected = candidates[0] if structural == "first" else candidates[-1]
            self._remember(selected)
            return self._result([selected], selected["type"], structural, set(), user_text)

        # Nome do jogo é contexto de domínio, não nome de uma entrada.
        exact_query = re.sub(r"\b(super metroid|do super metroid|de super metroid|em super metroid|no super metroid|sobre super metroid)\b", " ", normalized)
        exact_query = re.sub(r"\s+", " ", exact_query).strip()

        # 1) Nome/alias exato global vence a inferência de coleção.
        global_exact = self._exact_match(exact_query, self.entries, set())
        if global_exact:
            self._remember(global_exact)
            operation = "field" if requested_field else "exact"
            return self._result([global_exact], global_exact["type"], operation, set(), user_text, requested_field=requested_field, requested_fields=requested_fields)

        # 2) Pergunta de campo usa a entrada ativa. "área" não é coleção.
        if requested_field and self.last_entry:
            return self._result([self.last_entry], self.last_entry["type"], "field", set(), user_text, requested_field=requested_field, requested_fields=requested_fields)

        if not collection and (same_request or another_request or self._is_elliptical_knowledge_request(user_text)):
            collection = self.last_collection
            candidates = [entry for entry in self.entries if not collection or entry["type"] == collection]

        if same_request and self.last_entry and (not collection or self.last_entry["type"] == collection):
            return self._result([self.last_entry], self.last_entry["type"], "same", set(), user_text)


        exclude_names = set()
        if another_request and self.last_entry:
            exclude_names.add(self.last_entry["name_normalized"])

        planned_contains = query_plan.get("filters", {}).get("contains", []) if isinstance(query_plan.get("filters", {}), dict) else []
        attribute_terms = {_normalizar(item) for item in planned_contains if _normalizar(item)} or self._attribute_terms(user_text)
        if attribute_terms and candidates:
            filtered = [
                entry for entry in candidates
                if entry["name_normalized"] not in exclude_names
                and self._entry_matches_attributes(entry, attribute_terms)
            ]
            if filtered:
                selected = filtered[0]
                self._remember(selected)
                return self._result([selected], selected["type"], "attribute", exclude_names, user_text)

        query_tokens = _tokens(user_text)
        ranked = []
        for entry in candidates:
            if entry["name_normalized"] in exclude_names:
                continue
            overlap = query_tokens & entry["searchable_tokens"]
            score = len(overlap) * 12
            if score >= 24:
                ranked.append((score, entry))

        ranked.sort(key=lambda item: item[0], reverse=True)
        entries = [entry for _, entry in ranked[:self.max_results]]

        if not entries and collection and self._is_generic_collection_request(user_text) and not attribute_terms:
            for entry in candidates:
                if entry["name_normalized"] not in exclude_names:
                    entries = [entry]
                    break

        if entries:
            self._remember(entries[0])

        return self._result(entries, collection, "search", exclude_names, user_text)

    def _result(self, entries, collection, operation, excluded_names, user_text, count=None, requested_field="", requested_fields=None):
        requested_fields = requested_fields or ([requested_field] if requested_field else [])
        return {
            "entries": entries,
            "collection": collection,
            "operation": operation,
            "count": count,
            "requested_field": requested_field,
            "requested_fields": requested_fields,
            "source_required": bool(getattr(self, "_active_query_plan", {}).get("requires_local_source", False)) or self.source_is_required(user_text, collection),
            "excluded_names": sorted(excluded_names)
        }

    def _remember(self, entry):
        self.last_entry = entry
        self.last_collection = entry.get("type", "") or self.last_collection

    def _exact_match(self, normalized_text, candidates, excluded_names):
        matches = []
        for entry in candidates:
            if entry["name_normalized"] in excluded_names:
                continue
            for name in [entry["name_normalized"], *entry["aliases_normalized"]]:
                if not name:
                    continue
                if name in self.EXACT_MATCH_BLOCKED_ALIASES:
                    continue
                if len(name) <= 3 and name not in self.STRONG_SHORT_ALIASES:
                    continue
                if re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", normalized_text):
                    matches.append((len(name), entry))
                    break
        if not matches:
            return None
        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[0][1]

    def _entry_matches_attributes(self, entry, terms):
        raw = entry.get("raw", {})
        searchable_parts = []
        requirements = raw.get("requirements", {}) if isinstance(raw.get("requirements"), dict) else {}
        for key in ["all_items", "any_items", "techniques", "events"]:
            searchable_parts.append(self._compact(requirements.get(key)))
        searchable_parts.extend([
            self._compact(raw.get("effects")), self._compact(raw.get("uses")),
            self._compact(raw.get("tags")), self._compact(raw.get("area")),
            self._compact(raw.get("room"))
        ])
        attr_tokens = _tokens(" ".join(searchable_parts))
        return terms.issubset(attr_tokens)

    def _attribute_terms(self, user_text):
        normalized = _normalizar(user_text)
        if not re.search(r"\b(use|usa|usar|com|exige|precisa|necessita|requer)\b", normalized):
            return set()
        terms = _tokens(user_text) - self.GENERIC_TOKENS
        return {term for term in terms if len(term) >= 2}

    def _is_feedback_only(self, normalized):
        has_marker = any(marker in normalized for marker in self.FEEDBACK_MARKERS)
        asks_new = bool(re.search(r"\b(o que|qual|quais|onde|como|explica|explique|me fala|mostra|ensina|lista)\b", normalized))
        return has_marker and not asks_new

    def _is_topic_change(self, normalized):
        return any(marker in normalized for marker in self.TOPIC_CHANGE_MARKERS)

    def _is_topic_setup_only(self, normalized):
        # Ex.: "vamos falar de Super Metroid" apenas estabelece o tema.
        setup = bool(re.search(r"\b(vamos|bora|quero) (falar|conversar) (sobre|de)\b", normalized))
        explicit_request = bool(re.search(r"\b(o que|qual|quais|onde|como|explica|explique|fala um|me fala um|mostra|ensina|lista)\b", normalized))
        return setup and not explicit_request

    def _asks_for_another(self, user_text):
        return bool(re.search(r"\b(outra|outro|oura|diferente|mais uma|mais um)\b", _normalizar(user_text)))

    def _asks_for_same(self, user_text):
        return bool(re.search(r"\b(mesma|mesmo|essa|esse|anterior)\b", _normalizar(user_text)))

    def _asks_for_reformulation(self, user_text):
        normalized = _normalizar(user_text)
        return any(marker in normalized for marker in [
            "sem parecer um power point", "sem parecer powerpoint", "sem power point",
            "mais simples", "mais direto", "de forma engracada", "de um jeito engracado",
            "reformula", "explica melhor", "em uma frase", "uma unica frase"
        ])

    def _is_elliptical_knowledge_request(self, user_text):
        normalized = _normalizar(user_text)
        return bool(re.search(r"\b(explica|explique|ensina|mostra|fala)\b", normalized)) and len(_tokens(user_text)) <= 6

    def _structural_operation(self, normalized):
        if re.search(r"\b(lista|liste|listar|todos|todas)\b", normalized):
            return "list"
        if re.search(r"\b(qualquer coisa|aleatori[ao]|escolhe qualquer|uma qualquer|um qualquer)\b", normalized):
            return "random"
        if re.search(r"\bquant(as|os)|quantidade|numero de\b", normalized):
            return "count"
        if re.search(r"\bprimeir[ao]\b", normalized):
            return "first"
        if re.search(r"\bultim[ao]\b", normalized):
            return "last"
        return ""

    def _is_generic_collection_request(self, user_text):
        return bool(re.search(r"\b(uma|alguma|qualquer|aleatoria|aleatorio|escolhe|explique|explica|mostra|ensina)\b", _normalizar(user_text)))

    def get_field_value(self, entry, field):
        raw = entry.get("raw", {}) if isinstance(entry, dict) else {}
        if field == "area":
            value = raw.get("area")
            return self._field_result(value, "known" if value else "unknown")
        if field == "room":
            value = raw.get("room")
            return self._field_result(value, "known" if value else "unknown")
        if field == "requirements":
            data = raw.get("requirements") if isinstance(raw.get("requirements"), dict) else {}
            return {"status": data.get("status", "unknown"), "value": data}
        if field == "boss":
            data = raw.get("acquisition") if isinstance(raw.get("acquisition"), dict) else {}
            boss = data.get("boss") or data.get("miniboss")
            status = data.get("status", "unknown")
            if boss:
                status = "known"
            elif status == "none":
                status = "none"
            else:
                status = "unknown"
            return self._field_result(boss, status)
        if field == "effect":
            effects = raw.get("effects") or []
            return self._field_result(effects, "known" if effects else "unknown")
        if field == "uses":
            uses = raw.get("uses") or []
            return self._field_result(uses, "known" if uses else "unknown")
        if field == "acquisition":
            data = raw.get("acquisition") if isinstance(raw.get("acquisition"), dict) else {}
            return {"status": data.get("status", "unknown"), "value": data}
        return self._field_result(None, "unknown")

    def _field_result(self, value, status):
        return {"status": status, "value": value}

    def format_context(self, result):
        entries = result.get("entries", [])
        operation = result.get("operation")
        if operation == "count":
            return f"CONSULTA ESTRUTURAL RESOLVIDA.\nCOLEÇÃO: {result.get('collection') or 'geral'}\nQUANTIDADE: {result.get('count', 0)}\nUse esse número exatamente."
        if not entries:
            return ""

        lines = [
            "CONSULTA LOCAL RESOLVIDA PELO SISTEMA.",
            "As entradas abaixo são a única fonte factual autorizada para esta resposta.",
            "Não invente campos ausentes. status=unknown significa NÃO INFORMADO; status=none significa que sabemos que não existe.",
            "A personalidade pode mudar apenas o tom, nunca os fatos."
        ]
        requested_fields = result.get("requested_fields", []) or ([result.get("requested_field")] if result.get("requested_field") else [])
        for index, entry in enumerate(entries, start=1):
            raw = entry.get("raw", {})
            lines.extend([f"\nENTRADA {index}", f"NOME: {entry['name']}", f"COLEÇÃO: {entry['type']}"])
            if requested_fields:
                for requested_field in requested_fields:
                    field_data = self.get_field_value(entry, requested_field)
                    lines.append(f"CAMPO SOLICITADO: {requested_field}")
                    lines.append(f"STATUS DO CAMPO: {field_data['status']}")
                    lines.append(f"VALOR DO CAMPO: {self._compact(field_data['value']) or 'não informado'}")
            else:
                for key in ["summary", "area", "room", "requirements", "acquisition", "effects", "uses", "related_entries", "tags"]:
                    value = raw.get(key)
                    if value not in [None, "", [], {}]:
                        lines.append(f"{key.upper()}: {self._compact(value)}")
            lines.append(f"FONTE: {entry['source']}")
        return "\n".join(lines)

    def _compact(self, value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            return " | ".join(self._compact(item) for item in value if item not in [None, ""])
        if isinstance(value, dict):
            return " / ".join(f"{key}: {self._compact(item)}" for key, item in value.items() if item not in [None, "", [], {}])
        return str(value)

    def _list(self, item, keys):
        for key in keys:
            value = item.get(key)
            if value in [None, ""]:
                continue
            if isinstance(value, list):
                return [str(part).strip() for part in value if str(part).strip()]
            if isinstance(value, str):
                return [part.strip() for part in value.split(",") if part.strip()]
            return [str(value)]
        return []



def _is_diana_self_target(text):
    return is_diana_self_target(text)


class OwnerFactsRetriever:

    PREFERENCE_ALIASES = {
        "filme alien": "filme_alien_favorito",
        "meu filme alien": "filme_alien_favorito",
        "alien favorito": "filme_alien_favorito",
        "meu alien": "filme_alien_favorito",
        "filme": "filme_favorito",
        "meu filme": "filme_favorito",
        "comida": "comida_favorita",
        "celular": "celular_favorito",
        "meu celular": "celular_favorito",
        "jogo": "jogo_favorito",
        "meu jogo": "jogo_favorito",
        "serie": "serie_favorita",
        "desenho": "desenho_favorito",
        "banda": "banda_favorita",
        "franquia": "franquia_de_jogo_favorito",
        "franquia de jogo": "franquia_de_jogo_favorito",
        "console": "console_favorito",
        "teclado": "teclado_favorito",
        "monitor": "monitor_favorito",
        "mouse": "mouse_favorito",
        "doom": "doom_favorito",
        "meu doom": "doom_favorito",
        "metroid": "metroid_favorito",
        "meu metroid": "metroid_favorito",
        "zelda": "zelda_favorito",
        "meu zelda": "zelda_favorito"
    }

    def __init__(self, profile_path="data/context/short_profile.json", current_session_path="data/context/current_session.json"):
        self.profile_path = Path(profile_path)
        self.current_session_path = Path(current_session_path)
        self.preferences = {}
        self.session_preferences = {}
        self.last_preference_key = ""
        self._load()

    def _load(self):
        self.preferences = {}
        self.session_preferences = {}

        if self.profile_path.exists():
            try:
                data = json.loads(self.profile_path.read_text(encoding="utf-8"))
                self.preferences = dict(data.get("owner", {}).get("known_preferences", {}))
            except Exception:
                pass

        if self.current_session_path.exists():
            try:
                data = json.loads(self.current_session_path.read_text(encoding="utf-8"))
                self.session_preferences = dict(data.get("owner_session_preferences", {}))
            except Exception:
                pass

    def _all_preferences(self):
        merged = {}
        merged.update(self.preferences or {})
        merged.update(self.session_preferences or {})
        return merged

    def _key_candidates_for_category(self, categoria):
        original = _normalizar(categoria)
        original = re.sub(r"[^a-z0-9_ %+-]+", " ", original)
        original = re.sub(r"\s+", " ", original).strip()

        if not original:
            return []

        filler = r"\b(agora|mesmo|favorito|favorita|favoritos|favoritas|geral|principal|ficou|salvo|salva|anotado|anotada|registrado|registrada|atualizado|atualizada|corrigido|corrigida|correcao|troca|trocado|trocada|troquei|mudanca|mudança|atualizacao|depois|na|real|citei|falei|disse|prefiro|curto|gosto|mais|que|foi|era|eu|tinha|deixei|primeiro)\b"

        def clean_to_key(text):
            text = re.sub(filler, " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            text = re.sub(r"[^a-z0-9_ %+-]+", " ", text)
            text = re.sub(r"\s+", "_", text).strip("_")
            return text

        aliases = {
            "filme_alien": ["filme_alien_favorito"],
            "alien": ["filme_alien_favorito", "filme_favorito"],
            "filme": ["filme_favorito"],
            "comida": ["comida_favorita", "comida_favorito"],
            "celular": ["celular_favorito"],
            "jogo": ["jogo_favorito"],
            "serie": ["serie_favorita", "serie_favorito"],
            "desenho": ["desenho_favorito"],
            "banda": ["banda_favorita", "banda_favorito"],
            "marca": ["marca_favorito", "marca_favorita"],
            "franquia": ["franquia_de_jogo_favorito", "franquia_de_jogo_favorita", "franquia_favorita", "franquia_favorito"],
            "franquia_de_jogo": ["franquia_de_jogo_favorito", "franquia_de_jogo_favorita"],
            "area": ["area_favorito", "area_favorita"],
        }

        variants = []
        full = clean_to_key(original)
        if full:
            variants.append(full)

        # Tenta categorias progressivamente mais gerais:
        # "tipo de live de canal" -> tipo_de_live_de_canal, tipo_de_live, tipo.
        progressive = full
        while progressive:
            match = re.search(r"^(.+?)_(?:de|do|da|dos|das|em|no|na|nos|nas|pra|para|pro)_[^_]+$", progressive)
            if not match:
                break
            progressive = match.group(1).strip("_")
            if progressive and progressive not in variants:
                variants.append(progressive)

        # Também tenta a categoria base antes do primeiro contexto/preposição.
        base = re.split(r"\s+(?:de|do|da|dos|das|em|no|na|nos|nas|pra|para|pro)\s+", original, maxsplit=1)[0].strip()
        base_key = clean_to_key(base)
        if base_key and base_key not in variants:
            variants.append(base_key)

        # Se a pergunta traz contexto extra sem preposição clara,
        # ainda tenta a categoria principal. Ex.: "glitch nessa rota" -> glitch_favorito.
        first_token = full.split("_", 1)[0] if full else ""
        if first_token and first_token not in variants:
            variants.append(first_token)

        candidatos = []
        for categoria_key in variants:
            candidatos.extend(aliases.get(categoria_key, []))
            candidatos.append(categoria_key + "_favorito")
            candidatos.append(categoria_key + "_favorita")

        vistos = set()
        saida = []
        for chave in candidatos:
            if chave and chave not in vistos:
                vistos.add(chave)
                saida.append(chave)
        return saida

    def _first_existing_key(self, candidates):
        prefs = self._all_preferences()
        for key in candidates:
            if key in prefs and prefs.get(key) not in [None, ""]:
                return key
        return candidates[0] if candidates else ""

    def retrieve(self, user_text, history_text="", max_results=2):
        self._load()
        normalized = _normalizar(user_text)

        if _is_diana_self_target(user_text):
            return []

        requested_key = self._requested_preference_key(normalized)

        if not requested_key and self._is_followup(normalized):
            requested_key = self.last_preference_key or self._infer_key_from_history(history_text)

        if not requested_key:
            return []

        value = self.session_preferences.get(requested_key)
        source = "current_session.json"
        if value in [None, ""]:
            value = self.preferences.get(requested_key)
            source = "short_profile.json"

        if value in [None, ""]:
            return []

        self.last_preference_key = requested_key
        return [{
            "path": f"owner.known_preferences.{requested_key}",
            "key": requested_key,
            "value": str(value),
            "source": source
        }]

    def _requested_preference_key(self, normalized_text):

        text = str(normalized_text or "").strip()

        # Específico de Alien/franquia.
        if re.search(r"\b(qual dos filmes|qual desses|meu filme alien|alien favorito|meu alien favorito)\b", text):
            if "alien" in text and "favorit" in text:
                return self._first_existing_key(["filme_alien_favorito"])

        # Follow-up humano: "E o/a <categoria>?" / "E sobre <categoria>?" / "E o/a <categoria> que eu curto?"
        short = re.search(r"^e\s+(?:o|a)\s+([a-z0-9_ %+-]{2,80}?)(?:\s+agora|\s+mesmo|\s+que\s+eu\s+curto|\s+que\s+eu\s+gosto|\s+depois\s+da\s+correcao|\s+atualizado|\s+atualizada|\s+corrigido|\s+corrigida)?\??$", text)
        if short:
            return self._first_existing_key(self._key_candidates_for_category(short.group(1)))

        sobre_short = re.search(r"^e\s+sobre\s+([a-z0-9_ %+-]{2,80})\??$", text)
        if sobre_short:
            return self._first_existing_key(self._key_candidates_for_category(sobre_short.group(1)))

        patterns = [
            r"^qual\s+era\s+mesmo\s+(?:o|a)?\s*([a-z0-9_ %+-]{2,80})\s+que\s+eu\s+(?:prefiro|curto|gosto)\??$",
            r"^sobre\s+([a-z0-9_ %+-]{2,80})\s*,?\s+o\s+que\s+ficou\s+(?:salvo|salva|anotado|anotada|registrado|registrada)\??$",
            r"^(?:que|qual)\s+([a-z0-9_ %+-]{2,80})\s+eu\s+(?:tinha\s+falado|tinha\s+citado|falei|disse|citei|prefiro|curto|troquei)(?:\s+primeiro)?\??$",
            r"^qual\s+([a-z0-9_ %+-]{2,80})\s+eu\s+deixei\s+(?:anotado|anotada|salvo|salva|registrado|registrada)\??$",
            r"^(?:qual|que)\s+([a-z0-9_ %+-]{2,80})\s+ficou\s+(?:salvo|salva|anotado|anotada|registrado|registrada)\??$",
            r"^qual\s+([a-z0-9_ %+-]{2,80})\s+eu\s+falei\s+que\s+era\s+favorit[oa]\??$",
            r"^qual(?:\s+e)?\s+(?:(?:o|a)\s+)?([a-z0-9_ %+-]{2,80})\s+eu\s+(?:prefiro|falei|disse|citei|curto|troquei|gosto)(?:\s+mais)?(?:\s+mesmo)?\??$",
            r"^qual(?:\s+e)?\s+(?:(?:o|a)\s+)?([a-z0-9_ %+-]{2,80})\s+eu\s+disse\s+que\s+prefiro(?:\s+mesmo)?\??$",
            r"^qual(?:\s+e)?\s+(?:(?:o|a)\s+)?([a-z0-9_ %+-]{2,80})\s+favorit[oa]\s+(?:eu\s+falei|eu\s+citei|ficou\s+anotado|ficou\s+anotada|ficou\s+salvo|ficou\s+salva)\??$",
            r"^qual(?:\s+e)?\s+(?:(?:o|a)\s+)?([a-z0-9_ %+-]{2,80})\s+que\s+eu\s+(?:curto\s+mais|gosto\s+mais|prefiro)\??$",
            r"^depois\s+dessa\s+atualizacao\s*,?\s+qual\s+([a-z0-9_ %+-]{2,80})\s+ficou\??$",
            r"^depois\s+da\s+correcao\s*,?\s+qual\s+([a-z0-9_ %+-]{2,80})\s+ficou\??$",
            r"^qual\s+([a-z0-9_ %+-]{2,80})\s+ficou\s+depois\s+d[ao]\s+(?:troca|mudanca|atualizacao|esquece)\??$",
            r"^qual\s+([a-z0-9_ %+-]{2,80})\s+(?:atualizado|atualizada|corrigido|corrigida)\s+ficou(?:\s+salv[oa])?\??$",
            r"^qual\s+([a-z0-9_ %+-]{2,80})\s+ficou\s+na\s+real\??$",
            r"^qual\s+foi\s+o\s+([a-z0-9_ %+-]{2,80})\s+(?:atualizado|corrigido)\??$",
            r"^qual\s+([a-z0-9_ %+-]{2,80})\s+ficou\??$",
        ]
        for padrao in patterns:
            match = re.search(padrao, text)
            if match:
                return self._first_existing_key(self._key_candidates_for_category(match.group(1)))

        # Genérico: "qual é meu/minha X favorito?"
        generic = re.search(r"\b(?:qual(?: que)? (?:e|é) )?(?:o |a )?(?:meu|minha|do pai) ([a-z0-9_ %+-]{2,80}) favorit[oa]\b", text)
        if generic:
            categoria = generic.group(1).strip()
            categoria = re.sub(r"\b(e|o|a|qual|que)\b", " ", categoria)
            categoria = re.sub(r"\s+", " ", categoria).strip()
            return self._first_existing_key(self._key_candidates_for_category(categoria))

        # Aliases explícitos depois do genérico.
        for marker, key in self.PREFERENCE_ALIASES.items():
            if re.search(r"(?<!\w)" + re.escape(marker) + r"(?!\w)", text):
                candidates = self._key_candidates_for_category(marker)
                if key not in candidates:
                    candidates.insert(0, key)
                return self._first_existing_key(candidates)

        return ""

    def _is_followup(self, normalized_text):
        return bool(re.search(r"\b(e o favorito|qual o favorito|qual eu mais curto|isso qual|e qual|e o doom|e o metroid|e o zelda)\b", normalized_text))

    def _infer_key_from_history(self, history_text):
        normalized = _normalizar(history_text)
        positions = []
        for marker, key in self.PREFERENCE_ALIASES.items():
            pos = normalized.rfind(marker)
            if pos >= 0:
                positions.append((pos, key))
        if not positions:
            return ""
        return max(positions, key=lambda item: item[0])[1]

    def format_context(self, facts):
        if not facts:
            return ""
        lines = [
            "Fatos pessoais recuperados de fontes locais.",
            "Os valores abaixo são a resposta factual obrigatória. Não substitua, não relativize e não dê alternativas."
        ]
        for fact in facts:
            lines.append(f"- {fact['path']}: {fact['value']} | fonte: {fact['source']}")
        return "\n".join(lines)


class ContextRetriever:

    def __init__(self, debug=True, mem0_memory=None):
        self.debug = debug
        self.style = StyleRetriever(max_results=1)
        self.knowledge = KnowledgeRetriever(max_results=4)
        self.owner_facts = OwnerFactsRetriever()
        self.mem0_memory = mem0_memory
        self.last_result = None

    def retrieve(self, user_text, history_text="", query_plan=None):
        query_plan = query_plan or {}
        normalized = _normalizar(user_text)
        diana_self_target = _is_diana_self_target(user_text)
        personal_query = (not diana_self_target) and (query_plan.get("source") == "owner" or self._is_personal_fact_query(user_text, history_text))

        # Caminho rápido: cumprimento/zoeira curta não precisa varrer knowledge/style/mem0.
        # Isso reduz latência nas interações de live e evita ruído em memória.
        if self._is_simple_chatter(normalized) and not personal_query:
            knowledge_result = self.knowledge._result([], "", "skipped", set(), user_text)
            result = {
                "personal_query": False,
                "technical_query": False,
                "owner_facts": [],
                "owner_context": "",
                "mem0_memories": [],
                "mem0_context": "",
                "knowledge_entries": [],
                "knowledge_context": "",
                "knowledge_collection": "",
                "knowledge_operation": "skipped",
                "knowledge_count": None,
                "knowledge_requested_field": "",
                "knowledge_requested_fields": [],
                "knowledge_source_required": False,
                "knowledge_excluded_names": set(),
                "style_entries": [],
                "style_context": "",
                "personal_status": "NOT_APPLICABLE",
                "knowledge_status": "NOT_APPLICABLE",
                "query_plan": query_plan
            }
            self.last_result = result
            if self.debug:
                self._print_debug(user_text, result)
            return result

        style_entries = self.style.retrieve(user_text)
        knowledge_result = self.knowledge.retrieve(user_text, history_text=history_text, query_plan=query_plan)
        non_query_operation = knowledge_result.get("operation") in {"feedback", "correction", "topic_change", "topic_setup", "skipped"}
        technical_query = False if non_query_operation else (query_plan.get("source") == "knowledge" or self._is_technical_query(user_text))
        owner_facts = self.owner_facts.retrieve(user_text, history_text=history_text) if personal_query else []
        mem0_memories = self._retrieve_mem0(
            user_text=user_text,
            personal_query=personal_query,
            technical_query=technical_query,
            knowledge_status="FOUND" if (knowledge_result["entries"] or knowledge_result.get("operation") == "count") else "NOT_FOUND"
        )

        result = {
            "personal_query": personal_query,
            "technical_query": technical_query,
            "owner_facts": owner_facts,
            "owner_context": self.owner_facts.format_context(owner_facts),
            "mem0_memories": mem0_memories,
            "mem0_context": self._format_mem0_context(mem0_memories),
            "knowledge_entries": knowledge_result["entries"],
            "knowledge_context": self.knowledge.format_context(knowledge_result),
            "knowledge_collection": knowledge_result["collection"],
            "knowledge_operation": knowledge_result.get("operation", "search"),
            "knowledge_count": knowledge_result.get("count"),
            "knowledge_requested_field": knowledge_result.get("requested_field", ""),
            "knowledge_requested_fields": knowledge_result.get("requested_fields", []),
            "knowledge_source_required": knowledge_result["source_required"],
            "knowledge_excluded_names": knowledge_result["excluded_names"],
            "style_entries": style_entries,
            "style_context": self.style.format_context(style_entries),
            "personal_status": "FOUND" if owner_facts else ("NOT_FOUND" if personal_query else "NOT_APPLICABLE"),
            "knowledge_status": "FOUND" if (knowledge_result["entries"] or knowledge_result.get("operation") == "count") else ("NOT_APPLICABLE" if non_query_operation else ("NOT_FOUND" if technical_query or knowledge_result["source_required"] else "NOT_APPLICABLE")),
            "query_plan": query_plan
        }
        self.last_result = result

        if self.debug:
            self._print_debug(user_text, result)
        return result

    def _print_debug(self, user_text, result):
        print("🔎 Retrieval")
        print(f"   consulta: {user_text}")
        query_plan = result.get("query_plan") or {}
        if "should_query" in query_plan:
            gate_status = "APROVADO" if query_plan.get("should_query") else "IGNORADO"
            print(f"   query gate: {gate_status} | motivo: {query_plan.get('gate_reason', '')}")
        if result["personal_query"]:
            if result["owner_facts"]:
                values = ", ".join(f"{fact['path']}={fact['value']}" for fact in result["owner_facts"])
                print(f"   fatos pessoais: FOUND → {values}")
            else:
                print("   fatos pessoais: NOT_FOUND")
        if result["technical_query"] or result["knowledge_collection"] or result["knowledge_source_required"]:
            collection = result["knowledge_collection"] or "todas"
            names = ", ".join(entry["name"] for entry in result["knowledge_entries"]) or "nenhum"
            op = result.get("knowledge_operation", "search")
            if op == "count":
                names = str(result.get("knowledge_count", 0))
            print(f"   conhecimento: {result['knowledge_status']} | coleção: {collection} | operação: {op} | resultados: {names}")
        if result["style_entries"]:
            print(f"   estilo opcional: {result['style_entries'][0]['term']}")
        if result.get("mem0_memories"):
            print(f"   mem0: {len(result.get('mem0_memories', []))} memória(s) recuperada(s)")

    def _retrieve_mem0(self, user_text, personal_query=False, technical_query=False, knowledge_status="NOT_FOUND"):

        if not self.mem0_memory:
            return []

        if not getattr(self.mem0_memory, "enabled", False):
            return []

        normalized = _normalizar(user_text)

        if not normalized:
            return []

        # Evita usar memória longa como ruído em cumprimentos e respostas muito curtas.
        if self._is_simple_chatter(normalized):
            return []

        # Mem0 entra como memória pessoal/continuidade. Para pergunta técnica já resolvida
        # pela base local, a base local continua sendo a fonte factual principal.
        if technical_query and knowledge_status == "FOUND" and not personal_query:
            return []

        wants_memory = bool(re.search(
            r"\b(lembra|memoria|memória|eu falei|eu disse|meu|minha|sobre mim|quem sou eu|favorit[oa]|gosto|curto)\b",
            normalized
        ))

        followup = bool(re.search(r"\b(e qual|qual mesmo|como assim|por que|porque|e isso|continua|continua dai)\b", normalized))

        if not personal_query and not wants_memory and not followup:
            return []

        try:
            return self.mem0_memory.buscar_memorias(user_text)
        except Exception as erro:
            print("⚠️ Mem0 ignorado no retrieval:", erro)
            return []

    def _format_mem0_context(self, memories):

        if not memories or not self.mem0_memory:
            return ""

        try:
            return self.mem0_memory.formatar_contexto(memories)
        except Exception:
            linhas = ["Memórias longas recuperadas pelo Mem0."]
            for memory in memories:
                if isinstance(memory, dict):
                    linhas.append("- " + str(memory.get("text", "")).strip())
                else:
                    linhas.append("- " + str(memory).strip())
            return "\n".join(linhas)

    def _is_simple_chatter(self, normalized_text):

        tokens = set(str(normalized_text or "").split())
        simple = {
            "oi", "ola", "olá", "e", "ai", "aí", "eai", "eae", "fala", "salve", "bom", "boa", "dia", "tarde", "noite",
            "sim", "nao", "não", "ok", "blz", "beleza", "valeu", "obrigado", "obrigada", "kk", "kkk"
        }

        return bool(tokens) and tokens.issubset(simple) and len(tokens) <= 4

    def _is_personal_fact_query(self, text, history_text=""):
        normalized = _normalizar(text)

        if _is_diana_self_target(text):
            return False

        # Se o resolvedor consegue inferir uma chave de preferência, é pergunta pessoal.
        self.owner_facts._load()
        if self.owner_facts._requested_preference_key(normalized):
            return True

        has_owner_reference = bool(re.search(
            r"\b(meu|minha|meus|minhas|do pai|sobre mim|quem sou eu|eu gosto|eu curto|eu prefiro|eu falei|eu disse|eu citei|ficou salvo|ficou anotado)\b",
            normalized
        ))
        asks_fact = bool(re.search(
            r"\b(qual|quais|quem|sabe|lembra|favorito|favorita|prefiro|gosto|curto|nome|idade|filme|jogo|comida|serie|desenho|banda|franquia|doom|metroid|zelda)\b",
            normalized
        ))
        followup = self.owner_facts._is_followup(normalized) and bool(history_text)
        return (has_owner_reference and asks_fact) or followup

    def _is_technical_query(self, text):
        normalized = _normalizar(text)
        has_query_intent = bool(re.search(
            r"\b(o que e|oque e|como funciona|qual e o nome|qual o nome|explica|explique|"
            r"defina|diferenca|como se chama|como fazer|ensina|mostra|me fala|me diz|"
            r"onde fica|onde pega|lista|liste|quant[ao]s?|qualquer coisa|aleatori[ao])\b",
            normalized
        ))
        if not has_query_intent:
            return False
        collection = self.knowledge.infer_collection(text)
        return bool(collection) or has_query_intent
