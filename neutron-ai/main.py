import json
import os

# Načtení nastavení
def load_settings():
    try:
        with open('settings.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Chyba: Soubor settings.json nebyl nalezen!")
        return None

def run_api_model(prompt, settings):
    api_key = settings.get("api_key")
    if not api_key or api_key == "TVUJ_API_KLIC_ZDE":
        return "Chyba: API klíč není nastaven v settings.json!"
    
    # TODO: Zde doplň kód pro volání API 
    # (např. pomocí knihovny 'requests' nebo 'openai')
    return f"[Simulovaná API Odpověď]: Zpracoval jsem tvůj dotaz '{prompt}' přes API."

def run_offline_model(prompt, settings):
    model_path = settings.get("offline_model_path")
    if not os.path.exists(model_path):
        return f"Chyba: Offline model nebyl nalezen ve složce: {model_path}"
    
    # TODO: Zde doplň kód pro spuštění offline modelu.
    # Doporučuji nainstalovat a použít knihovnu 'llama_cpp' pro .gguf modely.
    # Příklad:
    # from llama_cpp import Llama
    # llm = Llama(model_path=model_path)
    # response = llm(prompt, max_tokens=100)
    
    return f"[Simulovaná Offline Odpověď]: Zpracoval jsem tvůj dotaz '{prompt}' lokálně."

def main():
    print("=== Vítej v Neutron-AI ===")
    settings = load_settings()
    if not settings:
        return

    mode = settings.get("mode", "api")
    print(f"Aktivní režim: {mode.upper()}")
    print("Napiš 'exit' pro ukončení.\n")
    
    while True:
        user_input = input("Ty: ")
        if user_input.lower() in ['exit', 'quit']:
            print("Vypínám Neutron-AI. Ahoj!")
            break
            
        if mode == "api":
            response = run_api_model(user_input, settings)
        elif mode == "offline":
            response = run_offline_model(user_input, settings)
        else:
            response = "Chyba: Neznámý režim v settings.json. Použij 'api' nebo 'offline'."
            
        print(f"Neutron-AI: {response}\n")

if __name__ == "__main__":
    main()
