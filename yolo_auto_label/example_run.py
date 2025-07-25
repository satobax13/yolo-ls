from YoloClassAutolabel import YoloAutoLabel
from pathlib import Path
import os


API_KEY = os.getenv("API_KEY")
MODEL_NAME = os.getenv("YOLO_MODEL", "yolov8n.pt")
PROJECT_NAME = os.getenv("PROJECT_NAME")
UPLOAD_AS_ANNOTATIONS = os.getenv("UPLOAD_AS_ANNOTATIONS", 'false').lower() == "true"

LABEL_STUDIO_URL = "http://localhost:8080"


def main():
    # Инициализация
    auto_label = YoloAutoLabel(
        label_studio_url=LABEL_STUDIO_URL,
        ls_api_key=API_KEY,
        yolo_model_path= str(Path(__file__).parent.parent / "models" / MODEL_NAME)
    )
    # Запуск обработки
    auto_label.run(project_name=PROJECT_NAME, upload_as_annotations=UPLOAD_AS_ANNOTATIONS)


if __name__ == "__main__":
    main()
