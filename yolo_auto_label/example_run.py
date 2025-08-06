from YoloClassAutolabel import YoloAutoLabel
from pathlib import Path
import yaml

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

API_KEY = config["api_key"]
MODEL_NAME = config["model_name"]
PROJECT_NAME = config["project_name"]
UPLOAD_AS_ANNOTATIONS = config["upload_as_annotations"]
HOST_LOCAL_STORAGE = config["host_local_storage_path"]
LABEL_STUDIO_URL = "http://label-studio:8080"



def main():
    # Инициализация
    auto_label = YoloAutoLabel(
        label_studio_url=LABEL_STUDIO_URL,
        ls_api_key=API_KEY,
        yolo_model_path= str(Path(__file__).parent.parent / "models" / MODEL_NAME),
        host_local_storage_path=HOST_LOCAL_STORAGE
    )
    # Запуск обработки
    auto_label.run(project_name=PROJECT_NAME, upload_as_annotations=UPLOAD_AS_ANNOTATIONS)


if __name__ == "__main__":
    main()
