from YoloClassAutolabel import YoloAutoLabel
from pathlib import Path
from prefect import flow
import yaml

@flow
def yolo_autolabel_flow():
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    auto_label = YoloAutoLabel(
        label_studio_url="http://label-studio:8080",
        ls_api_key=config["api_key"],
        yolo_model_path=str(Path(__file__).parent.parent / "models" / config["model_name"]),
        host_local_storage_path=config["host_local_storage_path"]
    )
    auto_label.run(
        project_name=config["project_name"],
        upload_as_annotations=config["upload_as_annotations"]
    )


if __name__ == "__main__":
    yolo_autolabel_flow()
