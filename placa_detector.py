import cv2
from ultralytics import YOLO
import easyocr
import re
import os
import difflib
import base64
from datetime import datetime

class PlacaDetector:
    def __init__(self, video_path="empresa_mottu.mp4", save_dir="prints_placa"):
        self.video_path = video_path
        self.save_dir = save_dir
        self.model = YOLO("yolov8n.pt")
        self.reader = easyocr.Reader(['en', 'pt'], gpu=False)
        
        # Cria diretório se não existir
        os.makedirs(save_dir, exist_ok=True)

    def limpa_texto_placa(self, texto: str) -> str:
        """Remove espaços e caracteres especiais"""
        texto = texto.upper().strip()
        texto = re.sub(r'[^A-Z0-9]', '', texto)
        return texto

    def converte_numeros_para_letras(self, texto: str) -> str:
        """Converte números que podem ser letras confundidas pelo OCR"""
        conversoes = {
            '0': 'O',  # Zero -> O
            '6': 'G',  # 6 -> G (muito comum!)
            '8': 'B',  # 8 -> B
            '5': 'S',  # 5 -> S
            '1': 'I',  # 1 -> I
            '2': 'Z'   # 2 -> Z
        }
        
        resultado = ""
        for char in texto:
            resultado += conversoes.get(char, char)
        return resultado

    def gera_variacoes_placa(self, placa_base: str) -> list:
        """Gera todas as variações possíveis de uma placa considerando erros de OCR"""
        placa_limpa = self.limpa_texto_placa(placa_base)
        
        if len(placa_limpa) != 7:
            return [placa_limpa]
        
        # Padrão brasileiro: AAA#A##
        letras_inicio = placa_limpa[:3]    # TAT
        numero_meio = placa_limpa[3]       # 9
        letra_meio = placa_limpa[4]        # G
        numeros_fim = placa_limpa[5:]      # 58
        
        variacoes = set()
        
        # Variação original
        variacoes.add(placa_limpa)
        
        # Variações com letra G confundida com números
        if letra_meio == 'G':
            # G pode ser lido como 6, 8, 9, 0
            for num_substituto in ['6', '8', '9', '0']:
                variacao = f"{letras_inicio}{numero_meio}{num_substituto}{numeros_fim}"
                variacoes.add(variacao)
                
                # Também adiciona sem o número do meio (caso OCR junte tudo)
                variacao_junta = f"{letras_inicio}{num_substituto}{numeros_fim}"
                variacoes.add(variacao_junta)
        
        # Variações com números confundidos com letras
        letra_convertida = self.converte_numeros_para_letras(letra_meio)
        if letra_convertida != letra_meio:
            variacao = f"{letras_inicio}{numero_meio}{letra_convertida}{numeros_fim}"
            variacoes.add(variacao)
        
        # Variações com espaços (como OCR pode ler)
        variacoes.add(f"{letras_inicio} {numero_meio}{letra_meio}{numeros_fim}")
        variacoes.add(f"{letras_inicio}{numero_meio} {letra_meio}{numeros_fim}")
        variacoes.add(f"{letras_inicio} {numero_meio} {letra_meio}{numeros_fim}")
        
        # Remove espaços de todas as variações para comparação
        variacoes_limpas = set()
        for var in variacoes:
            variacoes_limpas.add(self.limpa_texto_placa(var))
        
        return list(variacoes_limpas)

    def is_placa_brasileira_alvo(self, texto_detectado: str, placa_alvo: str, threshold=1.0) -> tuple:
        """
        Verifica se texto detectado corresponde a uma placa brasileira AAA#A##
        Retorna (é_match, similaridade, melhor_variacao)
        """
        texto_limpo = self.limpa_texto_placa(texto_detectado)
        variacoes_alvo = self.gera_variacoes_placa(placa_alvo)
        
        melhor_similaridade = 0
        melhor_variacao = texto_limpo
        
        # Testa todas as variações
        for variacao in variacoes_alvo:
            # Match exato
            if texto_limpo == variacao:
                return True, 1.0, variacao
            
            # Similaridade
            similaridade = difflib.SequenceMatcher(None, texto_limpo, variacao).ratio()
            if similaridade > melhor_similaridade:
                melhor_similaridade = similaridade
                melhor_variacao = variacao
        
        # Verifica se atinge o threshold
        is_match = melhor_similaridade >= threshold
        
        return is_match, melhor_similaridade, melhor_variacao

    def image_to_base64(self, image_path):
        """Converte imagem para base64 para envio via API"""
        try:
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')
        except:
            return None

    def buscar_placa(self, placa_alvo: str, threshold=1.0):
        """
        Busca uma placa específica no vídeo
        Retorna dicionário com resultados encontrados
        """
        print(f"🇧🇷 BUSCA PLACA BRASILEIRA: {placa_alvo}")
        
        # Limpa pasta anterior
        for arquivo in os.listdir(self.save_dir):
            file_path = os.path.join(self.save_dir, arquivo)
            if os.path.isfile(file_path):
                os.remove(file_path)

        cap = cv2.VideoCapture(self.video_path)
        frame_num = 0
        deteccoes_encontradas = []

        # Simple centroid-based tracker for motos to count unique veículos
        tracks = []  # each track: {'id', 'last_pos':(x,y), 'first_pos':(x,y), 'last_frame', 'seen_count'}
        next_track_id = 1
        moto_events = []  # raw moto detections (frame, centroid, track_id)

        # Plate ranking: quando uma placa é confirmada, atribuímos uma ordem (1,2,3...) baseada
        # na ordem de confirmação de placas. Isso garante que a moto com placa confirmada
        # receba um número consistente mesmo que o track_id mude por fragilidade do tracker.
        plate_rank_counter = 0
        plate_to_rank = {}  # mapa placa_limpa -> rank (int)

        # Pass-order counting (linha virtual): conta motos quando o centro cruza uma linha
        pass_counter = 0
        # line position ratio (vertical position measured from top). 0.0 top, 1.0 bottom
        count_line_ratio = 0.6
        count_line_y = None  # será calculado ao ter frame

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_num += 1

            # Processa a cada 15 frames para melhor performance
            if frame_num % 15 != 0:
                continue

            results = self.model(frame)[0]
            
            if results.boxes is not None:
                for i, (box, cls, conf) in enumerate(zip(results.boxes.xyxy, results.boxes.cls, results.boxes.conf)):
                    if int(cls) == 3 and float(conf) > 0.5:  # Moto com boa confiança
                        x1, y1, x2, y2 = map(int, box)
                        moto_img = frame[y1:y2, x1:x2]

                        # Calcula centro da bounding box (posição da moto)
                        cx = int((x1 + x2) / 2)
                        cy = int((y1 + y2) / 2)

                        # Tenta associar a um track existente (distância euclidiana)
                        assigned_track_id = None
                        max_distance = 80  # pixels, heurística – ajustar conforme necessário
                        max_frame_gap = 60  # frames sem ver o objeto para considerar perdido

                        best_dist = None
                        assigned_track = None
                        for track in tracks:
                            # Ignora tracks muito antigos
                            if frame_num - track['last_frame'] > max_frame_gap:
                                continue
                            tx, ty = track['last_pos']
                            dist = ((cx - tx) ** 2 + (cy - ty) ** 2) ** 0.5
                            if dist <= max_distance and (best_dist is None or dist < best_dist):
                                assigned_track_id = track['id']
                                assigned_track = track
                                best_dist = dist

                        if assigned_track_id is None:
                            # Novo veículo
                            assigned_track_id = next_track_id
                            tracks.append({
                                'id': assigned_track_id,
                                'first_pos': (cx, cy),
                                'last_pos': (cx, cy),
                                'first_frame': frame_num,
                                'last_frame': frame_num,
                                'seen_count': 1
                            })
                            next_track_id += 1
                            # novo track reference
                            assigned_track = tracks[-1]
                        else:
                            # Atualiza track existente
                            # guarda posição anterior para detectar crossing
                            prev_y = assigned_track['last_pos'][1]
                            assigned_track['last_pos'] = (cx, cy)
                            assigned_track['last_frame'] = frame_num
                            assigned_track['seen_count'] += 1

                            # calcula linha de contagem na primeira vez que tivermos frame
                            if count_line_y is None:
                                count_line_y = int(frame.shape[0] * count_line_ratio)

                            # Verifica cruzamento da linha (qualquer direção)
                            try:
                                if (not assigned_track.get('counted', False)) and prev_y is not None and count_line_y is not None:
                                    # cruzou de cima para baixo
                                    if prev_y < count_line_y <= cy:
                                        pass_counter += 1
                                        assigned_track['pass_order'] = pass_counter
                                        assigned_track['counted'] = True
                                    # cruzou de baixo para cima
                                    elif prev_y > count_line_y >= cy:
                                        pass_counter += 1
                                        assigned_track['pass_order'] = pass_counter
                                        assigned_track['counted'] = True
                            except Exception:
                                pass

                        # Guarda evento bruto de detecção de moto
                        moto_events.append({'frame': frame_num, 'centroid': (cx, cy), 'track_id': assigned_track_id})
                        
                        if moto_img.size == 0:
                            continue
                        
                        try:
                            resultados_ocr = self.reader.readtext(moto_img, detail=1)
                            
                            # Coleta todos os textos com boa confiança
                            textos_detectados = []
                            for bbox, texto, conf_ocr in resultados_ocr:
                                if conf_ocr > 0.3:
                                    texto_limpo = self.limpa_texto_placa(texto)
                                    if len(texto_limpo) >= 2:
                                        textos_detectados.append((texto_limpo, conf_ocr, texto))
                            
                            # Testa textos individuais e combinados
                            textos_para_testar = [(t[0], t[2], t[1]) for t in textos_detectados]
                            
                            # Adiciona combinações de textos
                            if len(textos_detectados) >= 2:
                                for j in range(len(textos_detectados)):
                                    for k in range(j+1, len(textos_detectados)):
                                        t1, c1, orig1 = textos_detectados[j]
                                        t2, c2, orig2 = textos_detectados[k]
                                        
                                        combinacoes = [
                                            (f"{t1}{t2}", f"{orig1}+{orig2}", min(c1, c2)),
                                            (f"{t2}{t1}", f"{orig2}+{orig1}", min(c1, c2))
                                        ]
                                        textos_para_testar.extend(combinacoes)
                            
                            # Testa todos os textos
                            for texto_limpo, texto_original, conf_ocr in textos_para_testar:
                                is_match, similaridade, variacao = self.is_placa_brasileira_alvo(texto_limpo, placa_alvo, threshold)
                                
                                if is_match:
                                    print(f"✅ MATCH encontrado! Frame {frame_num}")
                                    print(f"   Texto: '{texto_original}' -> '{texto_limpo}'")
                                    print(f"   Similaridade: {similaridade:.3f}")
                                    
                                    # Salva detecção
                                    frame_marcado = frame.copy()
                                    cv2.rectangle(frame_marcado, (x1, y1), (x2, y2), (0, 255, 0), 5)
                                    cv2.putText(frame_marcado, f"MATCH: {texto_limpo}", (x1, y1 - 60),
                                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                                    cv2.putText(frame_marcado, f"ALVO: {placa_alvo}", (x1, y1 - 35),
                                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                                    cv2.putText(frame_marcado, f"SIM: {similaridade:.0%}", (x1, y1 - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                                    # Adiciona informação do track/posição (ex.: MOTO #10)
                                    try:
                                        # Preferir mostrar pass_order (ordem de passagem) quando disponível
                                        label_id = None
                                        if assigned_track is not None and assigned_track.get('pass_order') is not None:
                                            label_id = assigned_track.get('pass_order')
                                        elif assigned_track is not None and assigned_track.get('plate_rank') is not None:
                                            label_id = assigned_track.get('plate_rank')
                                        elif assigned_track_id is not None:
                                            label_id = assigned_track_id

                                        if label_id is not None:
                                            cv2.putText(frame_marcado, f"MOTO #{label_id}", (x1, y2 + 30),
                                                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)
                                        # Marca o centro da bounding box no frame completo
                                        cv2.circle(frame_marcado, (cx, cy), 6, (0, 0, 255), -1)
                                        cv2.putText(frame_marcado, f"({cx},{cy})", (cx + 8, cy + 8),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                                    except Exception:
                                        pass
                                    
                                    # Nomes dos arquivos
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    nome_base = f"match_{texto_limpo}_frame{frame_num}_{timestamp}"
                                    
                                    arquivo_frame = os.path.join(self.save_dir, f"{nome_base}_frame.jpg")
                                    arquivo_moto = os.path.join(self.save_dir, f"{nome_base}_moto.jpg")
                                    
                                    # Salva imagens
                                    cv2.imwrite(arquivo_frame, frame_marcado)
                                    # Adiciona marcação simples também na imagem recortada da moto
                                    try:
                                        moto_marcada = moto_img.copy()
                                        # Centro relativo na imagem recortada
                                        rel_cx = cx - x1
                                        rel_cy = cy - y1
                                        if 0 <= rel_cx < moto_marcada.shape[1] and 0 <= rel_cy < moto_marcada.shape[0]:
                                            cv2.circle(moto_marcada, (rel_cx, rel_cy), 5, (0, 0, 255), -1)
                                            if assigned_track_id is not None:
                                                cv2.putText(moto_marcada, f"MOTO #{assigned_track_id}", (5, 20),
                                                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
                                        cv2.imwrite(arquivo_moto, moto_marcada)
                                    except Exception:
                                        # Fallback: salva sem marcação
                                        cv2.imwrite(arquivo_moto, moto_img)
                                    
                                    # Converte para base64
                                    frame_b64 = self.image_to_base64(arquivo_frame)
                                    moto_b64 = self.image_to_base64(arquivo_moto)
                                    
                                    deteccao = {
                                        'frame': frame_num,
                                        'texto_ocr': texto_original,
                                        'texto_limpo': texto_limpo,
                                        'variacao_alvo': variacao,
                                        'similaridade': similaridade,
                                        'confianca': conf_ocr,
                                        'arquivo_frame': arquivo_frame,
                                        'arquivo_moto': arquivo_moto,
                                        'frame_base64': frame_b64,
                                        'moto_base64': moto_b64,
                                        'timestamp': timestamp
                                    }
                                    # Atribui um 'rank' para a placa quando confirmada (ordem de confirmação)
                                    try:
                                        placa_key = texto_limpo
                                        if placa_key in plate_to_rank:
                                            plate_rank = plate_to_rank[placa_key]
                                        else:
                                            plate_rank_counter += 1
                                            plate_rank = plate_rank_counter
                                            plate_to_rank[placa_key] = plate_rank

                                        deteccao['plate_rank'] = plate_rank

                                        # Vincula rank ao track, se existir
                                        if assigned_track is not None:
                                            assigned_track['plate_rank'] = plate_rank
                                    except Exception:
                                        pass
                                    # Anexa informações do track/posição se disponível
                                    try:
                                        deteccao['track_id'] = assigned_track_id
                                        deteccao['centroid'] = (cx, cy)
                                        if assigned_track is not None and assigned_track.get('pass_order') is not None:
                                            deteccao['pass_order'] = assigned_track.get('pass_order')
                                    except:
                                        pass

                                    deteccoes_encontradas.append(deteccao)
                        
                        except Exception as e:
                            print(f"Erro no OCR: {e}")
                            continue

        cap.release()
        
        # Resultado final
        resultado = {
            'placa_pesquisada': placa_alvo,
            'total_deteccoes': len(deteccoes_encontradas),
            'deteccoes': deteccoes_encontradas,
            'variacoes_buscadas': self.gera_variacoes_placa(placa_alvo),
            'sucesso': len(deteccoes_encontradas) > 0,
            'moto_unicas': len(tracks),
            'motos_tracks': tracks,
            'moto_events': moto_events,
            'moto_passadas': pass_counter
        }
        
        return resultado

# Teste básico
if __name__ == "__main__":
    detector = PlacaDetector()
    resultado = detector.buscar_placa("TAT9G95", threshold=0.8)
    print(f"\nResultado: {resultado['total_deteccoes']} detecções encontradas")