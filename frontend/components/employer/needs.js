/* Потребности: список и создание с извлечением технологий из текста. */
import { ref, reactive, computed } from 'vue';
import { api } from '../../api.js';
import { store, toast, specName, gradeTitle, formatTitle, skillName, skillCode } from '../../store.js';
import { navigate } from '../../router.js';
import { useLoad, moneyRange, fmtDate } from '../../ui.js';

export const EmployerNeeds = {
  setup() {
    const { data, loading, error, reload } = useLoad(async () => {
      const [needs, selections] = await Promise.all([api.get('/needs'), api.get('/selections')]);
      return needs.map((n) => ({ ...n, selection: selections.find((s) => s.need_id === n.id) || (n.selection_id ? { id: n.selection_id, versions: [] } : null) })).reverse();
    });
    const busy = ref(null);
    async function build(n) {
      busy.value = n.id;
      try { const sel = await api.post(`/needs/${n.id}/selection`, {}); navigate(`/employer/selections/${sel.id}`); }
      catch (e) { toast(e.detail, 'err'); busy.value = null; }
    }
    return { data, loading, error, reload, build, busy, specName, gradeTitle, formatTitle, skillName, moneyRange, fmtDate };
  },
  template: `
    <PageHead title="Потребности и подборки" sub="Потребность — описание того, кто нужен. По ней собирается подборка кандидатов по категориям; уточнения сохраняются версиями.">
      <a href="#/employer/needs/new" class="btn btn-primary">Новая потребность</a>
    </PageHead>
    <Loader :loading="loading" :error="error" :empty="data && !data.length" empty-title="Потребностей пока нет" empty-hint="Опишите, кто нужен: свободным текстом и полями. Технологии извлекаются из текста автоматически, зарплата обязательна." @retry="reload">
      <template #empty><a href="#/employer/needs/new" class="btn btn-primary">Описать потребность</a></template>
      <div class="list">
        <div v-for="n in data" :key="n.id" class="item">
          <div class="row-between">
            <div>
              <div class="item-title">{{ n.title }}</div>
              <div class="item-meta"><span>{{ specName(n.specialization_code) }} · {{ gradeTitle(n.grade) }}</span><span>{{ formatTitle(n.work_format) }}<template v-if="n.city">, {{ n.city }}</template></span><span>{{ fmtDate(n.created_at) }}</span><span v-if="n.selection && n.selection.versions.length">версий подборки: {{ n.selection.versions.length }}</span></div>
            </div>
            <div class="row">
              <span class="price">{{ moneyRange(n.salary_min, n.salary_max) }}</span>
              <a v-if="n.selection" :href="'#/employer/selections/' + n.selection.id" class="btn btn-secondary btn-sm">Открыть подборку</a>
              <button v-else type="button" class="btn btn-primary btn-sm" :disabled="busy === n.id" @click="build(n)"><span v-if="busy === n.id" class="spinner"></span>Собрать подборку</button>
            </div>
          </div>
          <div class="chips" style="margin-top:8px"><span v-for="s in n.stack" :key="s" class="chip">{{ skillName(s) }}</span></div>
        </div>
      </div>
    </Loader>`,
};

export const EmployerNeedNew = {
  setup() {
    const form = reactive({ title: '', text: '', specialization_code: '', grade: '', stack: [], salary: { min: null, max: null }, work_format: '', city: '' });
    const busy = ref(false); const error = ref(''); const created = ref(null);
    const skillNames = computed(() => (store.catalog ? store.catalog.skills.map((s) => s.name) : []));
    async function submit() {
      error.value = '';
      if (form.salary.min === null || form.salary.max === null) { error.value = 'Зарплата «от» и «до» обязательна'; return; }
      if (form.salary.min > form.salary.max) { error.value = 'Зарплата «от» больше, чем «до»'; return; }
      busy.value = true;
      try {
        const body = { title: form.title.trim(), text: form.text.trim(), salary_min: form.salary.min, salary_max: form.salary.max };
        if (form.specialization_code) body.specialization_code = form.specialization_code;
        if (form.grade) body.grade = form.grade;
        if (form.stack.length) body.stack = form.stack.map(skillCode);
        if (form.work_format) body.work_format = form.work_format;
        if (form.city.trim()) body.city = form.city.trim();
        created.value = await api.post('/needs', body);
      } catch (e) { error.value = e.detail; } finally { busy.value = false; }
    }
    async function build() {
      busy.value = true;
      try { const sel = await api.post(`/needs/${created.value.need.id}/selection`, {}); toast('Подборка собрана', 'ok'); navigate(`/employer/selections/${sel.id}`); }
      catch (e) { toast(e.detail, 'err'); busy.value = false; }
    }
    return { form, busy, error, created, submit, build, skillNames, store, specName, gradeTitle, skillName, moneyRange };
  },
  template: `
    <PageHead title="Новая потребность" sub="Опишите, кто нужен и чем занимается команда. Технологии извлекутся из текста; явно заданные поля главнее." >
      <a href="#/employer/needs" class="btn btn-ghost">К списку</a>
    </PageHead>
    <div v-if="created" class="card" style="max-width:860px">
      <h2>Потребность сохранена: {{ created.need.title }}</h2>
      <p class="muted">Так система поняла описание. Если что-то не так — уточните фильтрами уже в подборке: прежние версии сохранятся.</p>
      <dl class="kv">
        <dt>Специализация</dt><dd>{{ specName(created.extracted.specialization_code || created.need.specialization_code) }}</dd>
        <dt>Грейд</dt><dd>{{ gradeTitle(created.extracted.grade || created.need.grade) }}</dd>
        <dt>Разбор текста</dt><dd>{{ created.extracted.source === 'rules+model' ? 'правила и языковая модель (текст обезличен)' : 'правила по словарю' }}</dd>
        <dt>Технологии из текста</dt><dd><span v-if="!created.extracted.stack || !created.extracted.stack.length" class="muted">не распознаны — используется заданный стек</span><span v-else class="chips"><span v-for="s in created.extracted.stack" :key="s" class="chip chip-tech">{{ skillName(s) }}</span></span></dd>
        <dt>Стек потребности</dt><dd><span class="chips"><span v-for="s in created.need.stack" :key="s" class="chip">{{ skillName(s) }}</span></span></dd>
        <dt>Зарплата</dt><dd>{{ moneyRange(created.need.salary_min, created.need.salary_max) }}</dd>
      </dl>
      <div class="form-actions" style="margin-top:14px"><button type="button" class="btn btn-primary btn-lg" :disabled="busy" @click="build"><span v-if="busy" class="spinner"></span>Собрать подборку</button><a href="#/employer/needs/new" class="btn btn-ghost" @click.prevent="created = null">Описать другую</a></div>
    </div>
    <form v-else class="card" style="max-width:860px" @submit.prevent="submit">
      <Field label="Заголовок" required><input v-model="form.title" type="text" required placeholder="например: Бэкенд-разработчик в команду витрин данных"></Field>
      <Field label="Описание свободным текстом" required hint="Кто нужен, чем занимается команда, какие задачи, какой стек. Технологии будут извлечены автоматически."><textarea v-model="form.text" rows="6" required></textarea></Field>
      <div class="form-grid">
        <Field label="Специализация" hint="Если не указать — определится по тексту"><select v-model="form.specialization_code"><option value="">по тексту</option><option v-for="s in store.catalog.specializations" :key="s.code" :value="s.code">{{ s.name }}</option></select></Field>
        <Field label="Грейд" hint="Соседние грейды тоже попадут в подборку"><select v-model="form.grade"><option value="">по тексту</option><option v-for="g in store.catalog.grades" :key="g.code" :value="g.code">{{ g.title }}</option></select></Field>
        <div class="span-2"><Field label="Стек (уточнение)" hint="Добавьте технологии, если в тексте их нет или хотите задать явно"><TagsInput v-model="form.stack" :suggestions="skillNames" placeholder="технология" /></Field></div>
        <div class="span-2"><MoneyRange v-model="form.salary" required label="Зарплата в месяц, ₽ (обязательно)" /></div>
        <Field label="Формат работы"><select v-model="form.work_format"><option value="">любой</option><option v-for="f in store.catalog.work_formats" :key="f.code" :value="f.code">{{ f.title }}</option></select></Field>
        <Field label="Город"><input v-model="form.city" type="text"></Field>
      </div>
      <div v-if="error" class="note note-err">{{ error }}</div>
      <div class="form-actions"><button class="btn btn-primary btn-lg" :disabled="busy"><span v-if="busy" class="spinner"></span>Сохранить потребность</button></div>
    </form>`,
};
