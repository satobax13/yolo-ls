FROM heartexlabs/label-studio:latest

COPY yolo_auto_label/requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt
