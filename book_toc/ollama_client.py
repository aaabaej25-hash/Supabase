def ollama_chat(model: str, prompt: str) -> str:
    try:
        import ollama
        resp = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        return resp["message"]["content"]
    except Exception as e:
        raise RuntimeError(
            f"Ollama 호출 실패. 'ollama serve' 실행 및 'ollama pull {model}' 확인: {e}"
        )
