from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
import json
from datetime import datetime
from placa_detector import PlacaDetector

app = Flask(__name__)
CORS(app)  # Permite requisições de qualquer origem

# Configurações
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Instância global do detector
detector = PlacaDetector()

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/buscar-placa', methods=['POST'])
def buscar_placa():
    """
    Endpoint para buscar placa no vídeo
    Recebe JSON: {"placa": "ABC1234", "threshold": 0.8}
    """
    try:
        data = request.get_json()
        
        if not data or 'placa' not in data:
            return jsonify({
                'erro': 'Placa não fornecida',
                'sucesso': False
            }), 400
        
        placa = data['placa'].strip().upper()
        threshold = float(data.get('threshold', 0.8))
        
        # Validação básica da placa
        if len(placa) < 6 or len(placa) > 8:
            return jsonify({
                'erro': 'Placa deve ter entre 6 e 8 caracteres',
                'sucesso': False
            }), 400
        
        print(f"🔍 Iniciando busca por placa: {placa}")
        print(f"📊 Threshold de similaridade: {threshold}")
        
        # Executa a busca
        resultado = detector.buscar_placa(placa, threshold)
        
        # Prepara resposta
        resposta = {
            'sucesso': resultado['sucesso'],
            'placa_pesquisada': resultado['placa_pesquisada'],
            'total_deteccoes': resultado['total_deteccoes'],
            'moto_unicas': resultado.get('moto_unicas', 0),
            'motos_tracks': resultado.get('motos_tracks', []),
            'moto_passadas': resultado.get('moto_passadas', 0),
            'variacoes_buscadas': resultado['variacoes_buscadas'],
            'deteccoes': []
        }
        
        # Processa detecções para envio
        for deteccao in resultado['deteccoes']:
            deteccao_processada = {
                'frame': deteccao['frame'],
                'texto_ocr': deteccao['texto_ocr'],
                'texto_limpo': deteccao['texto_limpo'],
                'similaridade': deteccao['similaridade'],
                'confianca': deteccao['confianca'],
                'timestamp': deteccao['timestamp'],
                'frame_base64': deteccao['frame_base64'],
                'moto_base64': deteccao['moto_base64']
            }
            # Inclui dados de track/posição se disponíveis
            if 'track_id' in deteccao:
                deteccao_processada['track_id'] = deteccao['track_id']
            if 'centroid' in deteccao:
                deteccao_processada['centroid'] = deteccao['centroid']
            # Inclui plate_rank (ordem de confirmação da placa) se disponível
            if 'plate_rank' in deteccao:
                deteccao_processada['plate_rank'] = deteccao['plate_rank']
            resposta['deteccoes'].append(deteccao_processada)
        
        # Log do resultado
        if resultado['sucesso']:
            print(f"✅ Busca concluída: {resultado['total_deteccoes']} detecção(ões) encontrada(s)")
        else:
            print(f"❌ Nenhuma detecção encontrada para a placa {placa}")
        
        return jsonify(resposta)
    
    except Exception as e:
        print(f"❌ Erro na busca: {str(e)}")
        return jsonify({
            'erro': f'Erro interno: {str(e)}',
            'sucesso': False
        }), 500

@app.route('/api/status', methods=['GET'])
def status():
    """Endpoint para verificar status da API"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'video_existe': os.path.exists(detector.video_path),
        'modelo_carregado': detector.model is not None
    })

@app.route('/api/info', methods=['GET'])
def info():
    """Informações sobre a API"""
    return jsonify({
        'nome': 'MottuGrid Placa Detector API',
        'versao': '1.0.0',
        'descricao': 'API para detecção de placas de motos em vídeos',
        'endpoints': {
            '/': 'Interface web',
            '/api/buscar-placa': 'POST - Buscar placa no vídeo',
            '/api/status': 'GET - Status da API',
            '/api/info': 'GET - Informações da API'
        }
    })

@app.route('/prints_placa/<filename>')
def serve_image(filename):
    """Serve imagens salvas"""
    return send_from_directory('prints_placa', filename)

@app.errorhandler(404)
def not_found(error):
    return jsonify({'erro': 'Endpoint não encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'erro': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    # Verifica se o vídeo existe
    if not os.path.exists(detector.video_path):
        print(f"⚠️  AVISO: Vídeo '{detector.video_path}' não encontrado!")
        print("   Certifique-se de que o arquivo existe antes de fazer buscas.")
    
    print("🚀 Iniciando MottuGrid Placa Detector API...")
    print("🌐 Interface web: http://localhost:5000")
    print("📡 API endpoints: http://localhost:5000/api/")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)