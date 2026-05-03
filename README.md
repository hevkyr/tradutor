# Screen Translator MVP (Windows)

Ferramenta em Python para capturar uma área da tela, rodar OCR, traduzir o texto e exibir uma sobreposição transparente.

## Recursos
- Seleção de área da tela
- OCR contínuo com Tesseract
- Tradução automática para português
- Janela overlay sempre no topo
- Cache simples para evitar retraduções desnecessárias

## Requisitos
- Windows 10 ou 11
- Python 3.10+
- Tesseract OCR instalado e adicionado ao PATH

## Instalação
```bash
pip install -r requirements.txt
```

Instale o Tesseract:
- Windows: baixe em [UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- Depois confirme no terminal:
```bash
tesseract --version
```

## Execução
```bash
python main.py
```

## Como usar
1. Clique em **Selecionar área**.
2. Arraste o mouse para marcar a região da tela.
3. Clique em **Iniciar tradução**.
4. O texto reconhecido será traduzido e mostrado em uma janela transparente.
5. Clique em **Parar** para interromper.

## Melhorias sugeridas
- Detectar idioma automaticamente e escolher o modelo OCR correto.
- Tornar a janela click-through no Windows.
- Substituir Tesseract por Windows OCR ou EasyOCR.
- Ancorar cada bloco traduzido próximo ao texto original.
- Adicionar hotkeys globais.
