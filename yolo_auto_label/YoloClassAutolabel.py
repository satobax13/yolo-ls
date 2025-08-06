from label_studio_sdk import LabelStudio
from ultralytics import YOLO
import cv2
from typing import List, Dict, Optional, Tuple
from ultralytics.engine.results import Results
import logging

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Вывод в консоль
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)

class Bbox:

    def __init__(self, x: float, y: float, width: float, height: float, class_name: str, score: float):

        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.class_name = class_name
        self.score = score

    @classmethod
    def from_yolo_results(cls, yolo_results: List[Results]) -> List["Bbox"]:
        """
        Создает список Bbox из результатов детекции YOLO

        :param yolo_results: Список объектов Results, содержащий результаты детекции YOLO
        :return: Список объектов Bbox с результатами детекции
        """

        bboxes = []

        for result in yolo_results:
            class_names = [result.names[int(class_id)] for class_id in result.boxes.cls.tolist()]
            boxes = result.boxes.xywhn.tolist()
            scores = result.boxes.conf.tolist()

            for class_n, box, score_box in zip(class_names, boxes, scores):
                bboxes.append(cls(
                    x=box[0],
                    y=box[1],
                    width=box[2],
                    height=box[3],
                    class_name=class_n,
                    score=score_box
                ))

        return bboxes

    def to_label_studio(self, image_size: Dict[str, int]) -> List:
        """
        Конвертирует Bbox в формат JSON Label Studio

        :param image_size: Словарь с размерами изображения
        :return: Список с JSON Label Studio
        """
        return [
            {
                "original_width": image_size["width"],
                "original_height": image_size["height"],
                "image_rotation": 0,
                "value": {
                    "x": self.x * 100 - self.width * 100 / 2,
                    "y": self.y * 100 - self.height * 100 / 2,
                    "width": self.width * 100,
                    "height": self.height * 100,
                    "rotation": 0,
                    "rectanglelabels": [self.class_name]
                },
                "from_name": "label",
                "to_name": "image",
                "type": "rectanglelabels",
                "origin": "manual"
            }
        ]



class YoloAutoLabel:

    def __init__(self, label_studio_url: str, ls_api_key: str, yolo_model_path: str, host_local_storage_path: str):
        """
        :param label_studio_url: URL сервера Label Studio
        :param yolo_model_path: Путь к модели YOLO
        :param ls_api_key: API ключ Label Studio
        """
        self.client = LabelStudio(api_key=ls_api_key, base_url=label_studio_url)
        self.host_local_storage_path = host_local_storage_path
        self.yolo_model_path = yolo_model_path
        self.model = YOLO(self.yolo_model_path)
        # Словарь для смены местами названия и ID классов YOLO
        self.name_to_id = {name: id for id, name in self.model.names.items()}


    def _get_project(self, name: str) -> Optional[int]:
        """
        Получаем id проекта по названию, так как далее взаимодействие с API происходит не по названию проекта, а по его ID
        :param name: Название проекта
        :return: ID проекта
        :raise: ValueError
        """
        projects = self.client.projects.list()
        for project in projects.items:
            if project.title == name:
                return project.id
        raise ValueError(f'Проект с именем {name} не найден')

    def _get_local_storage(self, project_id: int):
        """

        :param project_id:
        :return:
        """
        path = '/label-studio/files' + self.host_local_storage_path
        self.client.import_storage.local.create(project=project_id, path=path, use_blob_urls=True)

        storage_id = self.client.import_storage.local.list(project=project_id)[-1].id

        self.client.import_storage.local.sync(id=storage_id)

    def _labels_check(self, project_id: int) -> List[int]:
        """
        Проверяет, содержит ли проект классы, проверяет подходят ли они для заданной модели YOLO.
        Возвращает список идентификаторов классов для YOLO, которые есть и в проекте LS.

        :param project_id: ID проекта
        :return: Список идентификаторов классов, общих для проекта и модели
        :raises ValueError: Если в проекте нет классов или нет нужных для YOLO классов
        """
        # Получаем информацию по проекту
        project_info = self.client.projects.get(id=project_id, )
        # Получаем классы из конфига проекта
        projects_labels = project_info.parsed_label_config["label"]["labels"]

        if not projects_labels:
            raise ValueError(f'Классы в проекте отсутствуют')

        # Получаем все классы из YOLO
        model_label_values = set(self.model.names.values())
        labels_for_yolo = []

        # По названиям классов из LS получаем соответствующие id классов для YOLO
        for label in projects_labels:
            if label in model_label_values:
                labels_for_yolo.append(self.name_to_id[label])

        if not labels_for_yolo:
            raise ValueError('В проекте отсутствуют необходимые классы для YOLO')
            
        unmatched_values = set(projects_labels) - set(model_label_values)
        logger.info(f"Неподходящие классы для YOLO: {', '.join(unmatched_values)}")
        
        return labels_for_yolo
    
    

    def _get_tasks(self, project_id: int) -> List[Tuple[str, int]]:
        """
        Получаем пути к изображениям в задании и ID задания по ID проекта
        :param project_id: ID проекта
        :return: Возвращает список с кортежами (Путь к изображению в задании, ID задания)
        :raise ValueError: Если в проекте нет заданий
        """
        task_ls = self.client.tasks.list(
            project=project_id
        )
        
        if not task_ls.items:
            raise ValueError(f'Отсутствуют задания в проекте')
            
        return [(task.data['image'], task.id) for task in task_ls.items]

    @staticmethod
    def _change_path(path) -> str:
        """
        Изменения пути local storage внутри docker на local storage на хосте, который использует Label Studio

        :param path: Путь к local storage внутри docker
        :return: Путь к local storage на хосте
        """
        new_path = '/tasks/' + path[path.find('=') + 1:]
        return new_path

    def _yolo_predict(self, image: str, classes_to_predict: List):
        """
        Выполняет предсказание YOLO для изображения

        :param image: Путь к изображению
        :param classes_to_predict: Список классов, которые нужно определить
        :return: Результаты предсказания
        :raises: RuntimeError
        """
        try:
            return self.model.predict(image, classes=classes_to_predict)
        except Exception as e:
            raise RuntimeError(f"Ошибка предсказания YOLO: {str(e)}")


    @staticmethod
    def _get_image_size(image) -> Dict[str, int]:
        """
        Возвращает размеры изображения (ширину и высоту)
        :param image: Изображение
        :return:
        """
        height, width = image.shape[:2]

        return {"height": height, "width": width}


    def run(self, project_name: str, upload_as_annotations: bool = False):
        """
        Обработка задач в проекте

        :param project_name: Название проекта
        :param upload_as_annotations: Флаг загрузки как annotations, иначе predictions
        """        
        print("\n\n\n", flush=True)

        logger.info(f"Начало обработки проекта: {project_name}")
        logger.info(f"Режим загрузки: {'annotations' if upload_as_annotations else 'predictions'}")

        # Получение ID проекта
        project_id = self._get_project(project_name)
        logger.info(f"Получен ID проекта: {project_id}")

        # Создаем и синхронизируем локальное хранилище
        self._get_local_storage(project_id)

        # Получение задач
        tasks = self._get_tasks(project_id)
        logger.info(f"Найдено задач: {len(tasks)}")

        # Проверка классов
        classes_to_predict = self._labels_check(project_id)
        logger.info(f"Классы для предсказания: {', '.join([self.model.names[classes] for classes in classes_to_predict])}")

        for task_path, task_id in tasks:
            logger.info(f"Обработка задачи {task_id} (файл: {task_path})")
            
            # Подготовка изображения
            task_path = self._change_path(task_path)

            try:
                image = cv2.imread(task_path)
            except FileNotFoundError:
                raise FileNotFoundError(f"Изображение не найдено: {task_path}")

            image_sizes = self._get_image_size(image)

            # Получение предсказаний
            predictions = self._yolo_predict(image, classes_to_predict)
            
            # Обработка bbox
            bbox_classes_scores = Bbox.from_yolo_results(predictions)
            logger.info(f"Получено {len(bbox_classes_scores)} предсказаний для задачи {task_id}")
            
            # Конвертация в формат Label Studio
            ls_results = [bbox.to_label_studio(image_sizes) for bbox in bbox_classes_scores]
            logger.info(f"Сконвертировано в формат Label Studio")

            # Загрузка результатов
            if not upload_as_annotations:
                scores = [bbox.score for bbox in bbox_classes_scores]
                for annotation, score in zip(ls_results, scores):
                    self.client.predictions.create(task=task_id, result=annotation, score=score)
                logger.info(f"Загружено {len(ls_results)} предсказаний для задачи {task_id}")
            else:
                for annotation in ls_results:
                    self.client.annotations.create(id=task_id, result=annotation, was_cancelled=False)
                logger.info(f"Загружено {len(ls_results)} аннотаций для задачи {task_id}")










