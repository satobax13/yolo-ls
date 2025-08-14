from YoloClassAutolabel import YoloAutoLabel
from pathlib import Path
from prefect import flow
import yaml

@flow
def yolo_autolabel_flow():

    config_path = str(Path(__file__).parent / "config.yaml")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    path_to_storage = str(Path(__file__).parent.parent.parent.parent.parent.parent / "label_studio" / "files" /  "tasks" / config["host_local_storage_path"])
    auto_label = YoloAutoLabel(
        label_studio_url="http://label-studio:8080",
        ls_api_key=config["api_key"],
        yolo_model_path=str(Path(__file__).parent.parent.parent.parent.parent.parent / "label_studio" / "files" / "models" / config["model_name"]),
        host_local_storage_path=path_to_storage
    )
    auto_label.run(
        project_name=config["project_name"],
        upload_as_annotations=config["upload_as_annotations"]
    )



if __name__ == "__main__":
    yolo_autolabel_flow()
