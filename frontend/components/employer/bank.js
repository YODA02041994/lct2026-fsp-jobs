/* Банк кандидатов: поиск с фильтрами. */
import { reactive, computed } from 'vue';
import { api } from '../../api.js';
import { store, skillCode } from '../../store.js';
import { useLoad } from '../../ui.js';
import { CandidateCard } from './candidate-card.js';

export const EmployerBank = {
  components: { CandidateCard },
  setup() {
    const f = reactive({ specialization_code: '', grade: '', skills: [], fsp_only: false, q: '' });
    const { data, loading, error, reload } = useLoad(() => api.get('/candidates/search', { specialization_code: f.specialization_code, grade: f.grade, skills: f.skills.map(skillCode), fsp_only: f.fsp_only, q: f.q }));
    let t = null;
    function changed() { clearTimeout(t); t = setTimeout(reload, 250); }
    function clear() { Object.assign(f, { specialization_code: '', grade: '', skills: [], fsp_only: false, q: '' }); reload(); }
    const skillNames = computed(() => store.catalog.skills.map((s) => s.name));
    return { f, data, loading, error, reload, changed, clear, skillNames, store };
  },
  template: `
    <PageHead title="Банк кандидатов" sub="Все кандидаты, давшие согласие на показ профиля. Без описанной потребности порядок задают сила подтверждённого профиля, достижения ФСП и актуальность." />
    <div class="card" style="margin-bottom:14px">
      <div class="form-grid filters-3">
        <Field label="Специализация"><select v-model="f.specialization_code" @change="reload"><option value="">любая</option><option v-for="s in store.catalog.specializations" :key="s.code" :value="s.code">{{ s.name }}</option></select></Field>
        <Field label="Грейд"><select v-model="f.grade" @change="reload"><option value="">любой</option><option v-for="g in store.catalog.grades" :key="g.code" :value="g.code">{{ g.title }}</option></select></Field>
        <Field label="Поиск по словам"><input v-model="f.q" type="search" placeholder="псевдоним, технология, обоснование" @input="changed"></Field>
        <div class="span-2"><Field label="Стек (все перечисленные)"><TagsInput v-model="f.skills" :suggestions="skillNames" placeholder="технология" @update:modelValue="changed" /></Field></div>
        <label class="check" :class="{ on: f.fsp_only }" style="align-self:end;margin-bottom:14px"><input type="checkbox" v-model="f.fsp_only" @change="reload"><span><span class="check-title">Только с подтверждёнными достижениями ФСП</span></span></label>
      </div>
      <button type="button" class="btn btn-ghost btn-sm" @click="clear">Сбросить фильтры</button>
    </div>
    <Loader :loading="loading" :error="error" :empty="data && !data.length" empty-title="Кандидатов по этим условиям нет" empty-hint="Снимите часть фильтров. В банке только кандидаты с пройденным тестом и согласием на показ." @retry="reload">
      <p class="muted" style="font-size:13px">Найдено: {{ data && data.length }}</p>
      <div class="list"><CandidateCard v-for="c in data" :key="c.candidate_id" :card="c" score-label="оценка профиля из 100" /></div>
    </Loader>`,
};
