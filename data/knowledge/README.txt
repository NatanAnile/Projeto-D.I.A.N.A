# BASE DE CONHECIMENTO LOCAL

Esta pasta guarda conhecimento editável em JSON.

Princípio:
- A base pode crescer livremente.
- O sistema NÃO injeta todos os arquivos no prompt.
- KnowledgeRetriever busca apenas entradas relacionadas à mensagem atual.
- Conhecimento recuperado define os fatos.
- StyleDictionary altera somente a forma de falar.
- Imagens ficam em data/knowledge/super_metroid/images e são referenciadas por visual_references.json.

Estrutura inicial:
- super_metroid/: conhecimento principal do jogo
- speedrun/: termos gerais de apoio

Campos recomendados:
id, name, aliases, definition, keywords, type e campos específicos de cada assunto.
