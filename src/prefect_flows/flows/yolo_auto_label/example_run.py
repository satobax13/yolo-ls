from yolo_class_auto_label import YoloAutoLabel
from prefect import flow
import yaml
import os


@flow
def yolo_autolabel_flow():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    auto_label = YoloAutoLabel(
        label_studio_url="http://label-studio:8080",
        ls_api_key=config["API_KEY"],
        yolo_model_path=os.getenv("MODEL_NAME"),
        host_local_storage_path=os.getenv("HOST_LOCAL_STORAGE_PATH")
    )
    auto_label.run(
        project_name=os.getenv("PROJECT_NAME"),
        upload_as_annotations=os.getenv("UPLOAD_AS_ANNOTATIONS").lower() == 'true'
    )



if __name__ == "__main__":
    yolo_autolabel_flow()
