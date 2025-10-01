# 🏍️ MottuGrid - Detector Inteligente de Placas

## 📋 Descrição do Projeto

O **MottuGrid** é um sistema completo de detecção de placas de motocicletas em vídeos, utilizando **Visão Computacional** e **Inteligência Artificial**. O sistema oferece uma interface web moderna onde você pode buscar placas específicas e visualizar os resultados encontrados no vídeo.

### 🎯 Funcionalidades Principais

- ✅ **Interface Web Moderna**: Digite a placa e veja os resultados instantaneamente
- ✅ **Detecção Inteligente**: YOLOv8 para detectar motocicletas no vídeo
- ✅ **Reconhecimento de Placas**: OCR avançado para leitura de placas brasileiras
- ✅ **Sistema de Variações**: Compensa erros de OCR automaticamente
- ✅ **API REST**: Endpoints para integração com outros sistemas
- ✅ **Visualização Completa**: Mostra frame completo e moto recortada
- ✅ **Precisão Ajustável**: Configure o nível de similaridade desejado
- ✅ **Resultados em Tempo Real**: Processamento e exibição instantâneos

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vídeo de      │    │   Sistema de    │    │   Interface     │
│   Entrada       │───▶│   Detecção IA   │───▶│   Web           │
│   (teste.mp4)   │    │   (YOLO + OCR)  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   API Flask     │
                       │   Backend       │
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Resultados    │
                       │   + Imagens     │
                       └─────────────────┘
```

---

## 🛠️ Tecnologias Utilizadas

### 🔧 Backend & API
- **Flask** - Servidor web para API REST
- **Flask-CORS** - Suporte a requisições cross-origin

### 🤖 Inteligência Artificial
- **YOLOv8** (Ultralytics) - Detecção de motocicletas
- **EasyOCR** - Reconhecimento de placas
- **OpenCV** - Processamento de vídeos
- **NumPy** - Computação científica

### 🎨 Frontend
- **HTML5/CSS3** - Interface responsiva e moderna
- **JavaScript** - Interatividade e requisições AJAX
- **Font Awesome** - Ícones profissionais

---

## 📦 Requisitos e Instalação

### 1. 🐍 Pré-requisitos
- **Python 3.8 ou superior** - [Download aqui](https://www.python.org/downloads/)
- **pip** (já incluído com Python)
- **4GB+ de RAM** (recomendado)
- **Arquivo de vídeo** (`teste.mp4`) na pasta raiz

### 2. 📥 Dependências Python

Instale todas as dependências necessárias:

```bash
pip install flask==2.3.3
pip install flask-cors==4.0.0
pip install opencv-python==4.8.1.78
pip install ultralytics==8.0.196
pip install easyocr==1.7.0
pip install torch==2.0.1
pip install torchvision==0.15.2
pip install pillow==10.0.0
pip install numpy==1.24.3
```

### 3. 📁 Estrutura do Projeto
```
MottuGrid-IA/
├── app.py                    # 🌐 Servidor Flask principal
├── placa_detector.py         # 🔍 Classe de detecção
├── busca_placa_brasileira.py # 📜 Script original
├── teste.mp4               # 🎥 Vídeo para análise
├── yolov8n.pt             # 🤖 Modelo YOLO (baixado automaticamente)
├── templates/
│   └── index.html          # 🎨 Interface web
├── static/
│   ├── css/style.css       # 🎨 Estilos
│   └── js/script.js        # ⚡ JavaScript
└── prints_placa/           # 📷 Imagens salvas (criado automaticamente)
```

---

## 🚀 Como Executar

### 🌟 **Método 1: Interface Web (RECOMENDADO)**

1. **Abra o terminal/PowerShell** na pasta do projeto
2. **Execute o servidor:**
   ```bash
   python app.py
   ```
3. **Acesse no navegador:**
   ```
   http://localhost:5000
   ```
4. **Digite a placa** que deseja buscar (ex: `TAT9G95`)
5. **Ajuste a precisão** usando o slider (80% é recomendado)
6. **Clique em "Buscar Placa"** e aguarde os resultados

### � **Método 2: Script Original**

Para usar o script original sem interface web:
```bash
python busca_placa_brasileira.py
```

---------

## 💻 Usando a Interface Web

### 🎯 **Passo a Passo:**

1. **📝 Digite a Placa**
   - Formato: `ABC1234` ou `ABC-1234`
   - Exemplo: `TAT9G95`

2. **⚙️ Ajuste a Precisão**
   - **100%**: Apenas matches exatos
   - **80%**: Permite pequenas variações (recomendado)
   - **60%**: Busca mais ampla

3. **🔍 Clique em "Buscar Placa"**
   - O sistema processará o vídeo
   - Pode levar alguns minutos

4. **📊 Visualize os Resultados**
   - **Frame Completo**: Moto marcada no vídeo
   - **Moto Recortada**: Apenas a região da moto
   - **Dados Técnicos**: Similaridade, confiança, frame

5. **🖼️ Amplie as Imagens**
   - Clique em qualquer imagem para visualizar em tamanho maior

---

## 🎯 Exemplos de Uso

### � **Sistema de Variações Automáticas**
O sistema gera automaticamente variações da placa para compensar erros de OCR:
- **Original**: `TAT9G95`
- **Variações**: `TAT9695`, `TAT9895`, `TAT9995`, `TAT695`, etc.
- **Comum**: G confundido com 6, 8, 9, 0

### � **Interpretando os Resultados**
- **🎯 Similaridade 100%**: Match exato encontrado
- **📊 Similaridade 80-99%**: Match muito provável
- **📈 Similaridade 60-79%**: Match possível
- **❌ Similaridade < 60%**: Provavelmente não é a placa

