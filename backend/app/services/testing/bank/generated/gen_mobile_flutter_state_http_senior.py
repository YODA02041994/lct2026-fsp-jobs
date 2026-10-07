"""Проверяет понимание перерисовок Flutter, производительности длинных списков и обработки сетевых ошибок."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_mobile_flutter_state_http_senior", title="Flutter: состояние, списки и сетевые ошибки",
          competency="Мобильная разработка: состояние, производительность и сетевые сбои",
          specializations=["mobile"], technologies=["flutter", "http"], fmt="choice",
          grade_level="senior", difficulty_shift=0.2)
def _mobile_flutter_state_http(rng: random.Random) -> Instance:
    widget = rng.choice(["UserList", "FeedPage", "CatalogView", "MessagesScreen", "OrderHistory"])
    item = rng.choice(["UserTile", "FeedCard", "ProductRow", "MessageBubble", "OrderItem"])
    n = rng.choice([500, 1000, 5000, 10000])
    timeout = rng.choice([3, 5, 8, 10])
    cases = [
        (
            f"В StatefulWidget {widget} каждое получение следующей страницы данных вызывает setState, "
            f"который перестраивает весь список из {n} элементов, включая уже отрисованные. "
            f"Как устранить лишние перерисовки и сохранить плавную прокрутку?",
            [
                f"Вынести список в отдельный StatefulWidget и обновлять только его через setState, а элементы списка сделать const и оборачивать в RepaintBoundary",
                f"Заменить setState на setState(() {{}}) — пустой вызов не вызывает перерисовку",
                f"Обернуть весь {widget} в Opacity с значением 0.99, чтобы Flutter кешировал кадры",
                f"Отключить перерисовку через WidgetsBinding.instance.deferFirstFrame()",
                f"Увеличить значение cacheExtent у ListView до бесконечности",
                f"Передавать ключи GlobalKey каждому {item}, чтобы Flutter переиспользовал элементы",
            ],
            f"Локальное состояние выносится в отдельный виджет, а неизменяемые элементы помечаются const и оборачиваются в RepaintBoundary — тогда перестраивается только изменённая часть.",
        ),
        (
            f"В {widget} используется ListView.builder с {n} элементами, но при быстрой прокрутке заметны подёргивания, "
            f"а в логах видно, что build у {item} вызывается слишком часто. Какая причина наиболее вероятна?",
            [
                f"В {item} создаются новые экземпляры тяжёлых объектов (например, TextStyle или ImageProvider) прямо в build, и отсутствуют const-конструкторы",
                f"ListView.builder всегда перерисовывает все элементы, это его штатное поведение",
                f"Не задан ключ Key для каждого элемента списка",
                f"Слишком маленькое значение cacheExtent, нужно поставить double.infinity",
                f"Используется StatelessWidget вместо StatefulWidget",
                f"Элементы списка не обёрнуты в Container с фиксированной высотой",
            ],
            f"Создание новых тяжёлых объектов в build и отсутствие const приводят к лишним перестройкам; вынос их наружу и const-конструкторы решают проблему.",
        ),
        (
            f"Сетевой запрос в {widget} выполняется через http.get с таймаутом {timeout} секунд. "
            f"При медленной сети Future иногда не завершается, а при обрыве соединения выбрасывается SocketException. "
            f"Как корректно обработать оба случая?",
            [
                f"Обернуть запрос в try/catch, ловить TimeoutException и SocketException, а сам вызов ограничить через .timeout(Duration(seconds: {timeout}))",
                f"Ловить только Exception — этого достаточно для всех сетевых ошибок",
                f"Использовать Future.delayed на {timeout} секунд перед запросом, чтобы сеть успела ответить",
                f"Игнорировать ошибки: http.get сам повторяет запрос при сбое",
                f"Обернуть вызов в setState, тогда ошибка не всплывёт наружу",
                f"Заменить http.get на http.post — он устойчивее к обрывам",
            ],
            f"http.get по умолчанию без таймаута, поэтому нужен .timeout; ошибки таймаута и сокета ловятся отдельно через try/catch.",
        ),
        (
            f"В {widget} после каждого успешного ответа вызывается setState, который пересоздаёт список из {n} элементов. "
            f"Какой подход уменьшит количество перерисовок без потери функциональности?",
            [
                f"Хранить данные в ValueNotifier и обновлять только подписанные части через ValueListenableBuilder",
                f"Вызывать setState внутри addPostFrameCallback",
                f"Обернуть setState в WidgetsBinding.instance.scheduleFrame()",
                f"Заменить setState на markNeedsBuild у всего дерева",
                f"Использовать StatefulWidget вместо StatelessWidget для каждого {item}",
                f"Отключить автоматическую перерисовку через TickerMode",
            ],
            f"ValueNotifier с ValueListenableBuilder точечно перестраивает только подписанные виджеты, а не всё дерево.",
        ),
        (
            f"В {widget} запрос к серверу возвращает 503 при перегрузке. Сейчас ошибка показывается пользователю один раз. "
            f"Как реализовать устойчивую повторную попытку с учётом таймаута {timeout} секунд?",
            [
                f"Повторять запрос с экспоненциальной задержкой и ограничением числа попыток, каждый раз применяя .timeout(Duration(seconds: {timeout}))",
                f"Повторять запрос в бесконечном цикле до успеха без задержки",
                f"Повторять запрос только при SocketException, а 503 игнорировать",
                f"Увеличить таймаут до 60 секунд и не делать повторных попыток",
                f"Показывать ошибку и просить пользователя перезапустить приложение",
                f"Использовать Future.delayed на {timeout} секунд перед каждым повтором без ограничения количества",
            ],
            f"Экспоненциальная задержка с ограничением попыток и таймаутом предотвращает перегрузку сервера и зависание приложения.",
        ),
        (
            f"В {widget} элементы {item} содержат изображения, загружаемые по сети. При прокрутке списка из {n} элементов "
            f"память быстро растёт. Какая причина и решение наиболее корректны?",
            [
                f"Картинки декодируются в полном разрешении и заполняют ImageCache; нужно задать cacheWidth/cacheHeight (или ResizeImage), чтобы декодировать их под размер {item}",
                f"Список хранит все элементы в памяти; нужно использовать ListView вместо ListView.builder",
                f"Flutter не умеет выгружать изображения; нужно вручную вызывать System.gc()",
                f"Проблема в отсутствии ключей Key у элементов списка",
                f"Нужно обернуть каждое изображение в Opacity 0.5",
                f"Следует отключить кеширование изображений через ImageCache.clear() при каждой прокрутке",
            ],
            f"Image.network декодирует картинку в исходном размере, и даже лимиты ImageCache по умолчанию (1000 картинок, 100 МБ) быстро выбираются; cacheWidth/cacheHeight уменьшают декодированное изображение и расход памяти.",
        ),
        (
            f"В {widget} асинхронный запрос запускается в initState. Если пользователь уходит с экрана до ответа, "
            f"возникает исключение «setState() called after dispose()». Как это исправить?",
            [
                f"Проверять mounted перед вызовом setState после await и при необходимости отменять запрос через отмену Future или флаг",
                f"Перенести вызов setState в dispose",
                f"Обернуть setState в try/catch и игнорировать ошибку",
                f"Вызывать setState только в build",
                f"Использовать StatelessWidget вместо StatefulWidget",
                f"Отключить проверку жизненного цикла через WidgetsBinding.instance.allowFirstFrame()",
            ],
            f"Проверка mounted и отмена запроса при dispose предотвращают вызов setState на уничтоженном виджете.",
        ),
    ]
    idx = rng.randrange(len(cases))
    question, options, expl = cases[idx]
    return _choice(rng, question, options, 0, expl, language=None)
