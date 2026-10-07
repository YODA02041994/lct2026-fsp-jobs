"""Проверяет понимание сетевого слоя Android: корутины, Retrofit, повторные запросы, кэш и обработка ошибок."""
from __future__ import annotations
import random
from ..base import template, Instance, shuffle_options
from ..common import _run_python, _sql_eval, _sql_block, _choice, _multi


@template("gen_mobile_network_background", title="Сетевой слой Android: корутины и Retrofit",
          competency="Android: сеть и фоновая работа",
          specializations=["mobile"], technologies=["android", "rest"], fmt="multichoice",
          grade_level="middle", difficulty_shift=0.0)
def _mobile_network_background(rng: random.Random) -> Instance:
    api = rng.choice(["UserApi", "OrderApi", "ProfileApi", "FeedApi"])
    method = rng.choice(["getUser", "loadOrders", "fetchProfile", "getFeed"])
    repo = rng.choice(["UserRepository", "OrderRepository", "ProfileRepository", "FeedRepository"])

    true_pool = [
        f"Вызов `{api}.{method}()` из Retrofit объявляется как `suspend fun` и не блокирует поток, если запускать его из корутины.",
        f"`viewModelScope.launch {{ repo.{method}() }}` автоматически отменит запрос при очистке ViewModel: при отмене корутины Retrofit отменяет и начатый HTTP-вызов.",
        "`withContext(Dispatchers.IO)` переключает выполнение на пул потоков ввода-вывода и возвращает результат обратно в исходный диспетчер.",
        "При повороте экрана запущенная в `viewModelScope` корутина продолжает работу, потому что ViewModel переживает пересоздание Activity.",
        "`Response<List<String>>` даёт доступ к `isSuccessful`, `code()` и `errorBody()`, чтобы различать успех и ошибку HTTP без исключения.",
        "`IOException` при сетевом запросе в корутине приходит как исключение; его можно поймать `try/catch` или через `runCatching`.",
    ]
    false_pool = [
        "Запуск `suspend`-функции Retrofit напрямую в главном потоке без корутины безопасен: Retrofit сам переключит поток.",
        "`viewModelScope.launch` создаёт корутину, которая автоматически перезапускается после каждого поворота экрана.",
        "Блокирующий вызов `Call.execute()` можно сделать прямо в главном потоке — система сама вынесет его в фон.",
        "Отмена `Job` у корутины не прерывает уже начатый HTTP-запрос Retrofit, поэтому отмена бесполезна.",
        "`Response<T>` бросает исключение при HTTP 404, поэтому `code()` проверять не нужно.",
        "Повторный запрос при ошибке сети нужно делать синхронно в главном потоке, чтобы не потерять порядок вызовов.",
    ]
    k = rng.randint(2, 3)
    correct = rng.sample(true_pool, k)
    wrong = rng.sample(false_pool, 6 - k)

    code = (
        f"class {repo}(private val api: {api}) {{\n"
        f"    suspend fun {method}(): List<String> = withContext(Dispatchers.IO) {{\n"
        f"        val r = api.{method}()\n"
        f"        if (!r.isSuccessful) throw IOException(\"HTTP \" + r.code())\n"
        f"        r.body() ?: emptyList()\n"
        f"    }}\n"
        f"}}\n\n"
        f"class ScreenViewModel : ViewModel() {{\n"
        f"    private val repo = {repo}(...)\n"
        f"    val state = MutableStateFlow<List<String>>(emptyList())\n"
        f"    fun load() = viewModelScope.launch {{\n"
        f"        runCatching {{ repo.{method}() }}\n"
        f"            .onSuccess {{ state.value = it }}\n"
        f"            .onFailure {{ state.value = emptyList() }}\n"
        f"    }}\n"
        f"}}"
    )

    return _multi(
        rng,
        f"Ниже фрагмент сетевого слоя на Android ({api}, Retrofit, корутины). "
        f"Какие утверждения о поведении этого кода верны? Выберите все подходящие.",
        correct, wrong,
        "Корутины в `viewModelScope` живут дольше Activity и отменяются при очистке ViewModel; "
        "`withContext(Dispatchers.IO)` переключает поток, а `Response<T>`/исключения позволяют различать HTTP-ошибки и сбои сети.",
        code=code, language="text",
    )
