/* Навыки: заявленные и подтверждённые тестом. */
import { computed, ref, onMounted } from 'vue';
import { api } from '../../api.js';
import { store, refreshMe, toast, skillName } from '../../store.js';
import { pct } from '../../ui.js';

export const CandidateSkills = {
  setup() {
    const me = computed(() => store.me || {});
    const skills = computed(() => me.value.skills || []);
    const confirmed = computed(() => skills.value.filter((s) => s.confirmed_by_test));
    const tested = computed(() => skills.value.filter((s) => !s.confirmed_by_test && s.test_score !== null && s.test_score !== undefined));
    const declared = computed(() => skills.value.filter((s) => !s.confirmed_by_test && (s.test_score === null || s.test_score === undefined)));
    const adding = ref(''); const busy = ref(false);
    const suggestions = computed(() => (store.catalog ? store.catalog.skills.map((s) => s.name) : []));
    onMounted(refreshMe);
    async function saveList(names) {
      busy.value = true;
      try { store.me = await api.put('/candidates/me', { skills: names }); } catch (e) { toast(e.detail, 'err'); } finally { busy.value = false; }
    }
    async function add() {
      const parts = adding.value.split(/[,;]+/).map((s) => s.trim()).filter(Boolean);
      if (!parts.length) return;
      const names = skills.value.map((s) => s.name || s.skill);
      parts.forEach((p) => { if (!names.some((n) => n.toLowerCase() === p.toLowerCase())) names.push(p); });
      await saveList(names); adding.value = ''; toast('Навыки добавлены', 'ok');
    }
    async function remove(s) {
      await saveList(skills.value.filter((x) => x.skill !== s.skill).map((x) => x.name || x.skill));
    }
    return { me, skills, confirmed, tested, declared, adding, add, remove, busy, suggestions, pct, skillName };
  },
  template: `
    <PageHead title="Навыки" sub="Подтверждённая тестом технология учитывается в подборе полностью, заявленная — частично. Подтвердить навык можно, пройдя тест с ним в заявленном стеке." />
    <div class="grid grid-2">
      <div class="card">
        <div class="card-head"><h2>Подтверждено тестом</h2><span class="badge st-accepted">{{ confirmed.length }}</span></div>
        <div v-if="!confirmed.length" class="muted" style="font-size:14px">Пока нет. <a href="#/candidate/test">Пройдите тест</a>, указав стек, — технологии с достаточной долей верных ответов станут подтверждёнными.</div>
        <div v-else class="tech-rows">
          <div v-for="s in confirmed" :key="s.skill" class="tech-row"><span><Tag confirmed>{{ s.name }}</Tag></span><span class="bar"><span class="bar-fill" :style="{ width: Math.round((s.test_score || 0) * 100) + '%' }"></span></span><span class="muted">{{ pct(s.test_score) }}</span></div>
        </div>
        <template v-if="tested.length">
          <hr class="sep">
          <h3 style="font-size:14px">Проверялось, но не подтверждено</h3>
          <div class="tech-rows">
            <div v-for="s in tested" :key="s.skill" class="tech-row"><span><Tag muted>{{ s.name }}</Tag></span><span class="bar"><span class="bar-fill" :style="{ width: Math.round((s.test_score || 0) * 100) + '%', opacity: .5 }"></span></span><span class="muted">{{ pct(s.test_score) }}</span></div>
          </div>
        </template>
      </div>
      <div class="card">
        <div class="card-head"><h2>Заявлено в профиле</h2><span class="badge">{{ declared.length }}</span></div>
        <div v-if="!declared.length && !skills.length" class="muted" style="font-size:14px">Стек не указан. Добавьте технологии — их увидит работодатель.</div>
        <div class="chips" style="margin-bottom:12px">
          <Tag v-for="s in declared" :key="s.skill" removable @remove="remove(s)">{{ s.name }}</Tag>
        </div>
        <form class="row" @submit.prevent="add">
          <input v-model="adding" type="text" list="skill-suggest" placeholder="технология, например PostgreSQL" style="flex:1;min-width:180px">
          <datalist id="skill-suggest"><option v-for="s in suggestions" :key="s" :value="s"></option></datalist>
          <button class="btn btn-outline" :disabled="busy || !adding.trim()">Добавить</button>
        </form>
        <p class="muted" style="font-size:12.5px;margin:10px 0 0">Название приводится к справочнику (например, «постгрес» → PostgreSQL); незнакомые сохраняются как есть.</p>
      </div>
    </div>`,
};
