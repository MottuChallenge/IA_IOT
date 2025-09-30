import cv2
from ultralytics import YOLO
import easyocr
import re
import os
import difflib

def limpa_texto_placa(texto: str) -> str:
    """Remove espaços e caracteres especiais"""
    texto = texto.upper().strip()
    texto = re.sub(r'[^A-Z0-9]', '', texto)
    return texto

def converte_numeros_para_letras(texto: str) -> str:
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

def gera_variacoes_placa(placa_base: str) -> list:
    """Gera todas as variações possíveis de uma placa considerando erros de OCR"""
    placa_limpa = limpa_texto_placa(placa_base)
    
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
    letra_convertida = converte_numeros_para_letras(letra_meio)
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
        variacoes_limpas.add(limpa_texto_placa(var))
    
    return list(variacoes_limpas)

def is_placa_brasileira_alvo(texto_detectado: str, placa_alvo: str, threshold=1.0) -> tuple:
    """
    Verifica se texto detectado corresponde a uma placa brasileira AAA#A##
    Retorna (é_match, similaridade, melhor_variacao)
    APENAS MATCHES 100% EXATOS!
    """
    texto_limpo = limpa_texto_placa(texto_detectado)
    variacoes_alvo = gera_variacoes_placa(placa_alvo)
    
    melhor_similaridade = 0
    melhor_variacao = texto_limpo
    match_exato = False
    
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

# Configurações
video_path = "teste.mp4"
placa_alvo = "TAT9G95"  # Padrão brasileiro: AAA#A##
save_dir = "prints_placa"

print(f"🇧🇷 BUSCA PLACA BRASILEIRA: {placa_alvo}")
print("🎯 APENAS MATCHES 100% EXATOS!")
print("=" * 50)

# Mostra as variações que serão buscadas
variacoes = gera_variacoes_placa(placa_alvo)
print(f"🔍 Variações que serão buscadas:")
for i, var in enumerate(variacoes, 1):
    print(f"   {i:2d}. {var}")
print("=" * 50)

# Limpa pasta anterior
os.makedirs(save_dir, exist_ok=True)
for arquivo in os.listdir(save_dir):
    os.remove(os.path.join(save_dir, arquivo))

# Modelos
model = YOLO("yolov8n.pt")
reader = easyocr.Reader(['en', 'pt'], gpu=False)

cap = cv2.VideoCapture(video_path)
frame_num = 0
deteccoes_encontradas = []

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_num += 1

    # Processa a cada 15 frames
    if frame_num % 15 != 0:
        continue

    results = model(frame)[0]
    
    if results.boxes is not None:
        for i, (box, cls, conf) in enumerate(zip(results.boxes.xyxy, results.boxes.cls, results.boxes.conf)):
            if int(cls) == 3 and float(conf) > 0.5:  # Moto com boa confiança
                x1, y1, x2, y2 = map(int, box)
                moto_img = frame[y1:y2, x1:x2]
                
                if moto_img.size == 0:
                    continue
                
                try:
                    resultados_ocr = reader.readtext(moto_img, detail=1)
                    
                    # Coleta todos os textos com boa confiança
                    textos_detectados = []
                    for bbox, texto, conf_ocr in resultados_ocr:
                        if conf_ocr > 0.3:
                            texto_limpo = limpa_texto_placa(texto)
                            if len(texto_limpo) >= 2:  # Pelo menos 2 caracteres
                                textos_detectados.append((texto_limpo, conf_ocr, texto))
                    
                    # Testa textos individuais
                    for texto_limpo, conf_ocr, texto_original in textos_detectados:
                        is_match, similaridade, variacao = is_placa_brasileira_alvo(texto_limpo, placa_alvo)
                        
                        if is_match and similaridade == 1.0:  # APENAS 100% EXATOS
                            print(f"\n🎯 *** MATCH 100% EXATO! *** Frame {frame_num}")
                            print(f"   Texto OCR: '{texto_original}' -> '{texto_limpo}'")
                            print(f"   Variação alvo: '{variacao}'")
                            print(f"   ✅ CERTEZA: 100%")
                            print(f"   Confiança OCR: {conf_ocr:.3f}")
                            
                            deteccoes_encontradas.append({
                                'frame': frame_num,
                                'texto_ocr': texto_original,
                                'texto_limpo': texto_limpo,
                                'variacao_alvo': variacao,
                                'similaridade': similaridade,
                                'confianca': conf_ocr
                            })
                    
                    # Combina textos adjacentes (comum em placas)
                    if len(textos_detectados) >= 2:
                        for j in range(len(textos_detectados)):
                            for k in range(j+1, len(textos_detectados)):
                                t1, c1, orig1 = textos_detectados[j]
                                t2, c2, orig2 = textos_detectados[k]
                                
                                # Testa ambas as ordens
                                combinacoes = [
                                    (f"{t1}{t2}", f"{orig1}+{orig2}"),
                                    (f"{t2}{t1}", f"{orig2}+{orig1}")
                                ]
                                
                                for comb_texto, comb_original in combinacoes:
                                    is_match, similaridade, variacao = is_placa_brasileira_alvo(comb_texto, placa_alvo)
                                    
                                    if is_match and similaridade == 1.0:  # APENAS 100% EXATOS
                                        print(f"\n🎯 *** MATCH 100% EXATO COMBINADO! *** Frame {frame_num}")
                                        print(f"   Textos OCR: '{comb_original}' -> '{comb_texto}'")
                                        print(f"   Variação alvo: '{variacao}'")
                                        print(f"   ✅ CERTEZA: 100%")
                                        print(f"   Confiança mín: {min(c1, c2):.3f}")
                                        
                                        # Salva detecção
                                        frame_marcado = frame.copy()
                                        cv2.rectangle(frame_marcado, (x1, y1), (x2, y2), (0, 255, 0), 5)
                                        cv2.putText(frame_marcado, f"MATCH 100%: {comb_texto}", (x1, y1 - 60),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                                        cv2.putText(frame_marcado, f"ALVO: {placa_alvo}", (x1, y1 - 35),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                                        cv2.putText(frame_marcado, f"CERTEZA: 100%", (x1, y1 - 10),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                                        
                                        # Salva arquivos
                                        nome_arquivo = f"MATCH_100%_{comb_texto}_frame{frame_num}"
                                        
                                        arquivo_frame = os.path.join(save_dir, f"{nome_arquivo}.jpg")
                                        cv2.imwrite(arquivo_frame, frame_marcado)
                                        
                                        arquivo_moto = os.path.join(save_dir, f"MOTO_{nome_arquivo}.jpg")
                                        cv2.imwrite(arquivo_moto, moto_img)
                                        
                                        print(f"   ✅ Salvo: {arquivo_frame}")
                                        
                                        deteccoes_encontradas.append({
                                            'frame': frame_num,
                                            'texto_ocr': comb_original,
                                            'texto_limpo': comb_texto,
                                            'variacao_alvo': variacao,
                                            'similaridade': similaridade,
                                            'confianca': min(c1, c2)
                                        })
                
                except Exception as e:
                    continue

cap.release()

print(f"\n🏁 BUSCA FINALIZADA")
print("=" * 50)

if deteccoes_encontradas:
    # Filtra apenas matches 100%
    matches_100 = [det for det in deteccoes_encontradas if det['similaridade'] == 1.0]
    
    if matches_100:
        print(f"🎯 {len(matches_100)} MATCH(ES) 100% EXATO(S) ENCONTRADO(S):")
        
        for i, det in enumerate(matches_100, 1):
            print(f"\n✅ {i}. Frame {det['frame']}:")
            print(f"   OCR: '{det['texto_ocr']}' -> '{det['texto_limpo']}'")
            print(f"   Alvo: '{det['variacao_alvo']}'")
            print(f"   🎯 CERTEZA: 100%")
            print(f"   Confiança: {det['confianca']:.3f}")
        
        print(f"\n� PRIMEIRO MATCH 100%:")
        primeiro = matches_100[0]
        print(f"   Placa detectada: {primeiro['texto_limpo']}")
        print(f"   Placa alvo: {placa_alvo}")
        print(f"   🎯 CERTEZA: 100%")
        print(f"   Frame: {primeiro['frame']}")
    else:
        print(f"⚠️  {len(deteccoes_encontradas)} detecção(ões) encontrada(s), mas NENHUMA com 100% de certeza")
        print("💡 Matches encontrados foram apenas aproximados")
else:
    print("❌ Nenhuma placa correspondente encontrada com 100% de certeza")
    print("💡 Dicas:")
    print("   - O script agora busca apenas matches 100% exatos")
    print("   - Verifique se a placa está no padrão brasileiro AAA#A##")
    print("   - Tente uma placa diferente se esta não estiver no vídeo")

print("=" * 50)