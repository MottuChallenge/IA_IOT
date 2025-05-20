import cv2
from ultralytics import YOLO
import easyocr
import re
import os

def limpa_texto_placa(texto):
    texto = texto.upper()
    texto = re.sub(r'\s+', '', texto)          # remove espaços
    texto = re.sub(r'[^A-Z0-9]', '', texto)    # remove caracteres não alfanuméricos
    return texto

video_path = "reelsvideo.io_1747704391869.mp4"
placa_alvo = "GBW3B52"
start_time_sec = 36

model = YOLO("yolov8n.pt")
reader = easyocr.Reader(['en', 'pt'], gpu=False)

cap = cv2.VideoCapture(video_path)
cap.set(cv2.CAP_PROP_POS_MSEC, start_time_sec * 1000)

# Cria pasta para salvar prints, se não existir
save_dir = "prints_placa"
os.makedirs(save_dir, exist_ok=True)

frame_num = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_num += 1

    results = model(frame)[0]
    motos = [box for box, cls in zip(results.boxes.xyxy, results.boxes.cls) if int(cls) == 3]

    placa_encontrada = False

    for box in motos:
        x1, y1, x2, y2 = map(int, box)
        height = y2 - y1
        y_placa_start = y1 + int(height * 0.7)
        moto_placa_img = frame[y_placa_start:y2, x1:x2]

        gray = cv2.cvtColor(moto_placa_img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        resultado_ocr = reader.readtext(thresh)

        for (bbox, texto, conf) in resultado_ocr:
            texto = limpa_texto_placa(texto)

            if placa_alvo in texto or texto in placa_alvo:
                placa_encontrada = True
                cv2.rectangle(frame, (x1, y_placa_start), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"Placa: {texto}", (x1, y_placa_start - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                print(f"Placa {texto} encontrada no frame {frame_num}")

                # Salva print do frame com placa detectada
                filename = os.path.join(save_dir, f"placa_{texto}_frame_{frame_num}.jpg")
                cv2.imwrite(filename, frame)
                print(f"Print salvo em: {filename}")

    if placa_encontrada:
        cv2.imshow("Moto com placa alvo", frame)
        if cv2.waitKey(25) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
