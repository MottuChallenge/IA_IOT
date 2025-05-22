# 🔍 Detecção de Placas de Motos em Vídeo com YOLO e OCR

Este projeto tem como objetivo detectar automaticamente motos e identificar suas placas em um vídeo. Ele utiliza **YOLOv8** para detecção de objetos e **EasyOCR** para leitura das placas.

---

## ✅ Tecnologias Utilizadas

- Python 3.8+
- OpenCV (`cv2`)
- Ultralytics YOLOv8 (`ultralytics`)
- EasyOCR (`easyocr`)
- Regex (`re`)
- OS (`os`)

---

## 📦 Instalação

1. Clone este repositório:
   ```bash
   git clone https://github.com/MottuChallenge/QA.git
   cd QA
2. Instale as dependências:
```bash
  pip install opencv-python ultralytics easyocr
```

## ▶️ Como Usar

1. Coloque seu vídeo no diretório do projeto com o nome desejado, por exemplo:
```python
  video_path = "reelsvideo.io_1747704391869.mp4"
```

2. Edite o valor da placa alvo no código:

```python
  placa_alvo = "GBW3B52"
```
3. Execute o script:
```bash
  python findMotorcycle.py
```
4. Prints dos frames com a placa encontrada serão salvos automaticamente em prints_placa/.

## 🧪 Resultados Parciais

O YOLOv8 identifica com sucesso motos no vídeo.

O EasyOCR reconhece as placas nas regiões inferiores da moto.

Se a placa alvo for encontrada:

Um retângulo verde é desenhado sobre ela.

Um print do frame é salvo.

A imagem é exibida com a identificação.

Informações são exibidas no terminal com o número do frame e nome do arquivo salvo.
