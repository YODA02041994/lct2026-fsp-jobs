/* Подборка: версии, категории слева, карточки кандидатов справа, уточнение фильтров. */
import { ref, reactive, computed, watch } from 'vue';
import { api } from '../../api.js';
import { store, toast, specName, gradeTitle, skillName, skillCode, WEIGHT_TITLES } from '../../store.js';
import { route } from '../../router.js';
import { useLoad, fmtDateTime, moneyRange } from '../../ui.js';
import { CandidateCard } from './candidate-card.js';

export const EmployerSelection = {
  components: { CandidateCard },
  setup() {
    const need = ref(null);
    const { data, loading, error, reload } = useLoad(async () => {
      const sel = await api.get(`/selections/${route.params.id}`);
      try { const needs = await api.get('/needs'); need.value = needs.find((n) => n.id === sel.need_id) || null; } catch (_) { /* заголовок потребности необязателен */ }
      return sel;
    });
    const versionNo = ref(null);
    const category = ref(null);           // { specialization_code, grade } | null
    const refining = ref(false); const busy = ref(false);
    const filters = reactive({ specialization_code: '', grades: [], skills: [], fsp_only: false, city: '', salary_max: null });
    const weights = reactive({});
    const versions = computed(() => (data.value ? data.value.versions : []));
    const version = computed(() => versions.value.find((v) => v.version_no === versionNo.value) || versions.value[versions.value.length - 1] || null);
    watch(data, (d) => { if (d && d.versions.length) { versionNo.value = d.versions[d.versions.length - 1].version_no; } });
    watch(version, (v) => {
      if (!v) return;
      const f = v.filters || {};
      Object.assign(filters, { specialization_code: f.specialization_code || '', grades: [...(f.grades || [])], skills: (f.skills || []).map(skillName), fsp_only: !!f.fsp_only, city: f.city || '', salary_max: f.salary_max ?? null });
      Object.keys(WEIGHT_TITLES).forEach((k) => { weights[k] = (v.weights && v.weights[k]) ?? (store.catalog.weights[k]); });
      category.value = null;
    });
    const results = computed(() => {
      if (!version.value) return [];
      const r = version.value.results || [];
      if (!category.value) return r;
      return r.filter((c) => c.category && c.category.specialization_code === category.value.specialization_code && c.category.grade === category.value.grade);
    });
    function pickCategory(c) { category.value = category.value && category.value.specialization_code === c.specialization_code && category.value.grade === c.grade ? null : { specialization_code: c.specialization_code, grade: c.grade }; }
    function toggleGrade(g) { const i = filters.grades.indexOf(g); i >= 0 ? filters.grades.splice(i, 1) : filters.grades.push(g); }
    const skillNames = computed(() => store.catalog.skills.map((s) => s.name));
    const weightsSum = computed(() => Object.values(weights).reduce((a, b) => a + Number(b || 0), 0));
    async function refine() {
      busy.value = true;
      try {
        // полный набор фильтров новой версии (не разница с прежней)
        const body = { filters: {
          specialization_code: filters.specialization_code || null,
          grades: filters.grades.length ? [...filters.grades] : null,
          skills: filters.skills.length ? filters.skills.map(skillCode) : null,
          fsp_only: !!filters.fsp_only,
          city: filters.city.trim() || null,
          salary_max: filters.salary_max ? Number(filters.salary_max) : null,
        } };
        body.weights = Object.fromEntries(Object.entries(weights).map(([k, v]) => [k, Number(v)]));
        const sel = await api.post(`/selections/${route.params.id}/refine`, body);
        data.value = sel; versionNo.value = sel.versions[sel.versions.length - 1].version_no; refining.value = false;
        toast(`Создана версия ${versionNo.value}. Прежние версии сохранены`, 'ok');
      } catch (e) { toast(e.detail, 'err'); } finally { busy.value = false; }
    }
    function filterSummary(v) {
      const f = v.filters || {}; const parts = [];
      if (f.specialization_code) parts.push(specName(f.specialization_code));
      if (f.grades && f.grades.length) parts.push(f.grades.map(gradeTitle).join(', '));
      if (f.skills && f.skills.length) parts.push(f.skills.map(skillName).join(', '));
      if (f.fsp_only) parts.push('только с ФСП ID');
      if (f.city) parts.push(f.city);
      if (f.salary_max) parts.push(`ожидания до ${moneyRange(null, f.salary_max)}`);
      return parts.length ? parts.join(' · ') : 'без дополнительных фильтров';
    }
    return { need, data, loading, error, reload, versions, version, versionNo, category, pickCategory, results, refining, refine, busy, filters, weights, weightsSum, toggleGrade, skillNames, filterSummary, store, specName, gradeTitle, skillName, moneyRange, fmtDateTime, WEIGHT_TITLES };
  },
  template: `
    <Loader :loading="loading" :error="error" @retry="reload">
      <template v-if="data">
        <PageHead :title="'Подборка: ' + (need ? need.title : 'потребность № ' + data.need_id)" :sub="need ? specName(need.specialization_code) + ' · ' + gradeTitle(need.grade) + ' · ' + moneyRange(need.salary_min, need.salary_max) + (need.city ? ' · ' + need.city : '') : ''">
          <a href="#/employer/needs" class="btn btn-ghost">К потребностям</a>
          <button type="button" class="btn btn-outline" @click="refining = !refining">{{ refining ? 'Скрыть уточнение' : 'Уточнить фильтры' }}</button>
        </PageHead>

        <div class="card" style="margin-bottom:14px">
          <div class="row-between">
            <div class="version-tabs">
              <span class="muted" style="font-size:13px">Версии подборки:</span>
              <button v-for="v in versions" :key="v.version_no" type="button" :class="{ on: version && version.version_no === v.version_no }" @click="versionNo = v.version_no" :title="fmtDateTime(v.created_at)">Версия {{ v.version_no }}</button>
            </div>
            <span v-if="version" class="muted" style="font-size:13px">{{ filterSummary(version) }} · {{ fmtDateTime(version.created_at) }}</span>
          </div>
          <div v-if="refining" style="margin-top:14px;border-top:1px solid var(--line);padding-top:14px">
            <h3>Уточнить подборку — будет создана новая версия</h3>
            <div class="form-grid">
              <Field label="Специализация"><select v-model="filters.specialization_code"><option value="">любая</option><option v-for="s in store.catalog.specializations" :key="s.code" :value="s.code">{{ s.name }}</option></select></Field>
              <Field label="Грейды"><div class="chips" style="padding-top:6px"><button v-for="g in store.catalog.grades" :key="g.code" type="button" class="chip chip-toggle" :class="{ on: filters.grades.includes(g.code) }" @click="toggleGrade(g.code)">{{ g.title }}</button></div></Field>
              <div class="span-2"><Field label="Обязательные технологии" hint="Останутся только кандидаты, у которых есть все перечисленные"><TagsInput v-model="filters.skills" :suggestions="skillNames" placeholder="технология" /></Field></div>
              <Field label="Город"><input v-model="filters.city" type="text"></Field>
              <Field label="Зарплатные ожидания не выше, ₽"><input v-model="filters.salary_max" type="number" min="0" step="10000"></Field>
              <div class="span-2"><label class="check" :class="{ on: filters.fsp_only }"><input type="checkbox" v-model="filters.fsp_only"><span><span class="check-title">Только с подтверждёнными достижениями ФСП</span><br><span class="check-text">Кандидаты, связавшие профиль с ФСП ID</span></span></label></div>
            </div>
            <details style="margin-bottom:12px"><summary style="cursor:pointer;color:var(--violet);font-weight:600;font-size:14px">Веса слагаемых оценки (сумма {{ weightsSum.toFixed(2).replace('.', ',') }})</summary>
              <div class="weights-grid" style="margin-top:8px"><Field v-for="(t, k) in WEIGHT_TITLES" :key="k" :label="t"><input v-model="weights[k]" type="number" min="0" max="1" step="0.05"></Field></div>
              <p class="muted" style="font-size:12.5px">Например, усильте «Стек» для узкой вакансии. Веса по умолчанию: стек 0,35 · грейд 0,25 · сила профиля 0,20 · ФСП 0,10 · актуальность 0,05 · условия 0,05.</p>
            </details>
            <div class="form-actions"><button type="button" class="btn btn-primary" :disabled="busy" @click="refine"><span v-if="busy" class="spinner"></span>Собрать новую версию</button><button type="button" class="btn btn-ghost" @click="refining = false">Отмена</button></div>
          </div>
        </div>

        <div v-if="version" class="selection">
          <aside>
            <h3 style="font-size:14px">Категории</h3>
            <div class="cat-list">
              <button type="button" class="cat" :class="{ on: !category }" @click="category = null"><div class="cat-title">Все категории</div><div class="cat-meta"><span>{{ version.results.length }} канд.</span></div></button>
              <button v-for="c in version.categories" :key="c.specialization_code + c.grade" type="button" class="cat" :class="{ on: category && category.specialization_code === c.specialization_code && category.grade === c.grade }" @click="pickCategory(c)">
                <div class="cat-title">{{ c.title }}</div>
                <div class="cat-meta"><span>{{ c.count }} канд.</span><span>средняя оценка {{ Math.round(c.avg_score * 100) }}</span></div>
              </button>
            </div>
            <p class="muted" style="font-size:12.5px;margin-top:10px">Категория присвоена тестом. Основная категория потребности и соседние по грейду.</p>
          </aside>
          <div>
            <div v-if="!results.length" class="empty"><div class="empty-title">В этой версии кандидатов нет</div><div class="empty-hint">Снимите часть фильтров или расширьте грейды — создастся новая версия, прежние останутся.</div></div>
            <div v-else class="list">
              <CandidateCard v-for="c in results" :key="c.candidate_id" :card="c" :weights="version.weights" :version-id="version.id" />
            </div>
          </div>
        </div>
      </template>
    </Loader>`,
};
