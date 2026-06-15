
# 🚀 Neutron-AI

Neutron-AI je lehký a flexibilní AI klient, který ti umožňuje komunikovat s umělou inteligencí dvěma způsoby:
1. **Přes cloudové API** (např. OpenAI, Anthropic).
2. **Plně offline** pomocí lokálních modelů, které ti běží přímo na tvém počítači.

## 📂 Jak to funguje?

Celý projekt je navržen tak, aby byl co nejjednodušší na nastavení. O všechno se stará soubor `settings.json` a složka `offline-models`.

### 🌐 Režim API
Pokud chceš využívat cloudové modely, stačí do souboru `settings.json` vložit svůj API klíč.

### 🔌 Režim Offline
Záleží ti na soukromí nebo nemáš internet? 
1. Stáhni si libovolný AI model ve formátu `.gguf` (najdeš je například na HuggingFace).
2. Hoď tento soubor přímo do složky `offline-models/`.
3. Uprav cestu k modelu v `settings.json`.

## 🛠️ Instalace a spuštění

1. Naklonuj nebo stáhni tento projekt.
2. Nainstaluj potřebné závislosti pomocí Pythonu:
   ```bash
   pip install -r requirements.txt
