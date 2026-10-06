/* Тестирование: специализация → заявленный грейд → стек → тест по блокам → результат. */
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { api } from '../../api.js';
import { store, refreshMe, toast, confirmDialog, gradeTitle, specName, skillName } from '../../store.js';
import { route, navigate } from '../../router.js';
import { useCountdown, fmtDate, futureOrPast, DECISION, pct } from '../../ui.js';

const GRADE_ORDER = ['junior', 'middle', 'senior', 'lead'];
const THRESHOLDS = { junior: -2.0, middle: -1.0, senior: 0.0, lead: 1.0 };

/* Результат сеанса: грейд, уверенность, по технологиям, предложения. */
export const TestResult = {
  props: { session: Object, compact: Boolean },
  emits: ['applied', 'retake'],
  setup(props, { emit }) {
    const r = computed(() => props.session.result || {});
    const busy = ref(false);
    const neighbor = computed(() => {
      const i = GRADE_ORDER.indexOf(props.session.claimed_grade);
      if (r.value.decision === 'suggest_lower') return GRADE_ORDER[Math.max(i - 1, 0)];
      if (r.value.decision === 'suggest_higher') return GRADE_ORDER[Math.min(i + 1, 3)];
      return null;
    });
    const targetGrade = computed(() => (r.value.decision === 'suggest_lower' ? r.value.result_grade : neighbor.value));
    const scale = computed(() => {
      const t = Number(r.value.theta || 0); const sd = Number(r.value.theta_sd || 0);
      const pos = (x) => Math.min(100, Math.max(0, ((x + 3) / 6) * 100));
      return { marker: pos(t), left: pos(t - sd), right: pos(t + sd), zones: [
        { g: 'junior', from: pos(-3), to: pos(-1) }, { g: 'middle', from: pos(-1), to: pos(0) }, { g: 'senior', from: pos(0), to: pos(1) }, { g: 'lead', from: pos(1), to: pos(3) }] };
    });
    const confidence = computed(() => {
      const sd = Number(r.value.theta_sd || 0.6);
      return sd <= 0.35 ? 'высокая' : sd <= 0.55 ? 'средняя' : 'низкая';
    });
    async function apply() {
      const ok = await confirmDialog({ title: `Применить грейд ${gradeTitle(targetGrade.value)}?`, text: 'Категория изменится сразу. Следующая смена грейда будет доступна через 90 дней.', ok: 'Применить' });
      if (!ok) return;
      busy.value = true;
      try { store.me = await api.post(`/tests/sessions/${props.session.id}/apply`); toast(`Грейд ${gradeTitle(targetGrade.value)} применён`, 'ok'); emit('applied'); }
      catch (e) { toast(e.detail, 'err'); } finally { busy.value = false; }
    }
    const fmt = (x) => (x === null || x === undefined ? '—' : Number(x).toFixed(2).replace('.', ','));
    return { r, busy, neighbor, targetGrade, apply, scale, confidence, fmt, gradeTitle, specName, skillName, fmtDate, futureOrPast, DECISION, pct, GRADE_ORDER };
  },
  template: `
    <div>
      <div class="grid" style="grid-template-columns: 220px 1fr; align-items:center">
        <div style="text-align:center">
          <div class="muted" style="font-size:13px">Результат теста</div>
          <div class="result-grade">{{ gradeTitle(r.result_grade) }}</div>
          <div class="muted" style="font-size:13px">заявлен {{ gradeTitle(session.claimed_grade) }} · {{ specName(session.specialization_code) }}</div>
        </div>
        <div>
          <div class="note" :class="r.decision === 'confirmed' ? 'note-ok' : r.decision === 'suggest_higher' ? 'note-pink' : 'note-warn'" style="margin-bottom:10px">
            <strong>{{ DECISION[r.decision] || r.decision }}.</strong>
            <template v-if="r.decision === 'confirmed'"> Категория «{{ specName(session.specialization_code) }} · {{ gradeTitle(r.result_grade) }}» подтверждена.</template>
            <template v-else-if="r.decision === 'suggest_lower'"> Грейд не понижается принудительно: заявленный {{ gradeTitle(session.claimed_grade) }} сохранён, но подборкам виден результат теста. Пройдите тест на уровень {{ gradeTitle(targetGrade) }}, чтобы подтвердить его уверенно.</template>
            <template v-else> Оценка минус разброс выше порога следующего грейда — можно повысить категорию до {{ gradeTitle(targetGrade) }}.</template>
          </div>
          <dl class="kv">
            <dt>Верных ответов</dt><dd>{{ r.correct_total }} из {{ r.items_total }}</dd>
            <dt>Оценка умения θ</dt><dd>{{ fmt(r.theta) }} ± {{ fmt(r.theta_sd) }} <span class="muted">· уверенность {{ confidence }}</span></dd>
          </dl>
        </div>
      </div>
      <div style="margin:14px 0 4px">
        <div style="position:relative;height:34px">
          <div style="position:absolute;left:0;right:0;top:12px;height:10px;border-radius:999px;overflow:hidden;display:flex">
            <span v-for="z in scale.zones" :key="z.g" :style="{ width: (z.to - z.from) + '%', background: z.g === r.result_grade ? 'var(--accent)' : '#E6E1EE', borderRight: '2px solid #fff' }" :title="gradeTitle(z.g) + ' от θ ' + ({junior:-2,middle:-1,senior:0,lead:1}[z.g])"></span>
          </div>
          <div style="position:absolute;top:10px;height:14px;background:rgba(49,15,83,.25);border-radius:4px" :style="{ left: scale.left + '%', width: Math.max(1, scale.right - scale.left) + '%' }" title="разброс ± θ_sd"></div>
          <div style="position:absolute;top:6px;width:4px;height:22px;background:var(--violet);border-radius:2px;transform:translateX(-50%)" :style="{ left: scale.marker + '%' }"></div>
        </div>
        <div style="display:flex;font-size:12px;color:var(--muted)">
          <span v-for="z in scale.zones" :key="z.g" :style="{ width: (z.to - z.from) + '%' }" style="text-align:center">{{ gradeTitle(z.g) }}</span>
        </div>
        <p class="muted" style="font-size:12.5px;margin-top:4px">Шкала умения: пороги грейдов стоят посередине между сложностями заданий соседних уровней. Полоса — разброс оценки.</p>
      </div>
      <h3 style="margin-top:14px">По технологиям</h3>
      <div v-if="!r.by_technology || !r.by_technology.length" class="muted" style="font-size:14px">Задания не были привязаны к технологиям.</div>
      <div v-else class="tech-rows">
        <div v-for="t in r.by_technology" :key="t.skill" class="tech-row">
          <span>{{ t.name || skillName(t.skill) }} <span v-if="t.total && t.correct / t.total >= 0.5" class="tag-check" title="подтверждено тестом">✓</span></span>
          <span class="bar"><span class="bar-fill" :style="{ width: (t.total ? Math.round(100 * t.correct / t.total) : 0) + '%' }"></span></span>
          <span class="muted">{{ t.correct }} из {{ t.total }}</span>
        </div>
      </div>
      <hr class="sep">
      <div class="row">
        <template v-if="r.decision !== 'confirmed'">
          <button v-if="r.decision === 'suggest_higher' && r.can_apply" type="button" class="btn btn-primary" :disabled="busy" @click="apply">Повысить грейд до {{ gradeTitle(targetGrade) }}</button>
          <button type="button" class="btn" :class="r.decision === 'suggest_lower' ? 'btn-primary' : 'btn-outline'" @click="$emit('retake', neighbor)">Пройти тест на уровень {{ gradeTitle(neighbor) }}</button>
          <button v-if="r.decision === 'suggest_lower' && r.can_apply" type="button" class="btn btn-outline" :disabled="busy" @click="apply">Принять грейд {{ gradeTitle(targetGrade) }} без пересдачи</button>
          <span v-if="!r.can_apply && r.grade_change_available_at && futureOrPast(r.grade_change_available_at)" class="muted" style="font-size:13px">Смена грейда будет доступна с {{ fmtDate(r.grade_change_available_at) }}</span>
          <span v-else-if="!r.can_apply && session.applied" class="muted" style="font-size:13px">Грейд по этому тесту уже применён</span>
        </template>
        <a v-if="!compact" href="#/candidate" class="btn btn-ghost">В кабинет</a>
        <a v-if="!compact" href="#/candidate/test/history" class="btn btn-ghost">История тестов</a>
      </div>
    </div>`,
};

export const CandidateTest = {
  components: { TestResult },
  setup() {
    const step = ref(1);
    const options = ref(null);
    const history = ref([]);
    const loading = ref(true); const error = ref('');
    const form = reactive({ specialization_code: '', claimed_grade: '', declared_skills: [] });
    const session = ref(null);
    const answer = ref(null);
    const busy = ref(false);
    const interlude = ref(null);      // текст между блоками
    const me = computed(() => store.me || {});

    const currentItems = computed(() => (session.value ? session.value.items.filter((i) => i.block_no === session.value.current_block) : []));
    const pending = computed(() => currentItems.value.filter((i) => !i.answered));
    const current = computed(() => pending.value[0] || null);
    const itemIndex = computed(() => (session.value ? session.value.block_size - pending.value.length + 1 : 0));
    const progress = computed(() => {
      if (!session.value) return 0;
      const total = session.value.block_size * session.value.blocks_total;
      const done = (session.value.current_block - 1) * session.value.block_size + (session.value.block_size - pending.value.length);
      return Math.round((done / total) * 100);
    });

    const timer = useCountdown(() => { if (current.value && !busy.value) { toast('Время на задание вышло — переходим дальше', 'warn'); submit(true); } });
    watch(current, (it) => { answer.value = null; if (it) timer.start(it.seconds_left ?? (store.catalog && store.catalog.test ? store.catalog.test.item_seconds : 90)); else timer.stop(); });

    const specOptions = computed(() => (options.value ? options.value.specializations : (store.catalog ? store.catalog.specializations : [])));
    const gradeOptions = computed(() => (options.value ? options.value.grades : (store.catalog ? store.catalog.grades : [])));
    const selectedSpec = computed(() => specOptions.value.find((s) => s.code === form.specialization_code));
    const skillGroups = computed(() => {
      const groups = {}; const titles = { lang: 'Языки', framework: 'Фреймворки', db: 'Базы данных', data: 'Данные', ml: 'Машинное обучение', infra: 'Инфраструктура', web: 'Веб и протоколы', tools: 'Инструменты', qa: 'Тестирование', analytics: 'Аналитика', cloud: 'Облака' };
      (store.catalog ? store.catalog.skills : []).forEach((s) => { (groups[s.group] = groups[s.group] || { title: titles[s.group] || s.group, items: [] }).items.push(s); });
      return Object.values(groups);
    });
    const activeSession = computed(() => history.value.find((s) => s.status === 'active'));
    const canChange = computed(() => !options.value || options.value.can_change_grade);

    async function load() {
      loading.value = true; error.value = '';
      try {
        const [o, h] = await Promise.all([api.get('/tests/options'), api.get('/tests/sessions'), refreshMe()]);
        options.value = o; history.value = h;
        form.specialization_code = me.value.specialization_code || '';
        form.claimed_grade = route.query.grade || me.value.claimed_grade || me.value.grade || '';
        form.declared_skills = (me.value.skills || []).map((s) => s.skill).filter((c) => store.catalog.skills.some((k) => k.code === c));
        if (route.query.grade) step.value = 2;
      } catch (e) { error.value = e.detail; } finally { loading.value = false; }
    }
    onMounted(load);

    function toggleSkill(code) { const i = form.declared_skills.indexOf(code); i >= 0 ? form.declared_skills.splice(i, 1) : form.declared_skills.push(code); }
    async function start() {
      busy.value = true;
      try {
        session.value = await api.post('/tests/sessions', { specialization_code: form.specialization_code, claimed_grade: form.claimed_grade, declared_skills: form.declared_skills });
        step.value = session.value.status === 'finished' ? 5 : 4;
      } catch (e) { toast(e.detail, 'err'); } finally { busy.value = false; }
    }
    async function resume() {
      busy.value = true;
      try { session.value = await api.get(`/tests/sessions/${activeSession.value.id}`); step.value = session.value.status === 'finished' ? 5 : 4; }
      catch (e) { toast(e.detail, 'err'); } finally { busy.value = false; }
    }
    function answerReady() {
      const f = current.value && current.value.payload.format;
      if (f === 'exact') return typeof answer.value === 'string' && answer.value.trim() !== '';
      if (f === 'choice') return Number.isInteger(answer.value);
      if (f === 'multichoice') return Array.isArray(answer.value) && answer.value.length > 0;
      return false;
    }
    async function submit(timeout = false) {
      if (!current.value || busy.value) return;
      busy.value = true; timer.stop();
      const item = current.value;
      try {
        const r = await api.post(`/tests/sessions/${session.value.id}/answer`, { item_id: item.id, answer: answerReady() ? answer.value : null });
        item.answered = true;
        if (r.block_done) {
          const next = await api.post(`/tests/sessions/${session.value.id}/next`);
          if (next.status === 'finished') { session.value = next; step.value = 5; await refreshMe(); }
          else {
            interlude.value = `Блок ${session.value.current_block} из ${next.blocks_total} завершён. Следующий блок — задания уровня ${gradeTitle(next.current_level)}.`;
            session.value = next;
          }
        }
      } catch (e) {
        toast(e.detail, 'err');
        if (e.status === 409) { try { session.value = await api.get(`/tests/sessions/${session.value.id}`); if (session.value.status === 'finished') step.value = 5; } catch (_) { /* пусто */ } }
        else if (!timeout && current.value) timer.start(Math.max(5, timer.left.value));
      } finally { busy.value = false; }
    }
    function retake(grade) { session.value = null; interlude.value = null; form.claimed_grade = grade || form.claimed_grade; step.value = 2; navigate('/candidate/test'); }
    function reset() { session.value = null; interlude.value = null; step.value = 1; }

    return { step, options, loading, error, form, session, answer, busy, interlude, me, current, pending, itemIndex, progress, timer, specOptions, gradeOptions, selectedSpec, skillGroups, activeSession, canChange,
      toggleSkill, start, resume, submit, answerReady, retake, reset, load, gradeTitle, specName, skillName, fmtDate, futureOrPast, store };
  },
  template: `
    <PageHead title="Тестирование" sub="Категорию определяет тест: задания уникальны для каждого, но одинаковы по сложности. Два блока по несколько заданий, на задание — ограниченное время." >
      <a href="#/candidate/test/history" class="btn btn-ghost">История тестов</a>
    </PageHead>
    <Loader :loading="loading" :error="error" @retry="load">
      <!-- шаги -->
      <div class="steps-bar" v-if="step < 5">
        <span v-for="(t, i) in ['Специализация', 'Заявленный грейд', 'Стек', 'Тест']" :key="t" class="step" :class="{ done: step > i + 1, now: step === i + 1 }"><span class="n">{{ step > i + 1 ? '✓' : i + 1 }}</span>{{ t }}</span>
      </div>

      <div v-if="step === 1 && activeSession" class="note note-pink row-between">
        <span>У вас есть незавершённый тест ({{ specName(activeSession.specialization_code) }}, {{ gradeTitle(activeSession.claimed_grade) }}, начат {{ fmtDate(activeSession.started_at) }}).</span>
        <button type="button" class="btn btn-primary btn-sm" :disabled="busy" @click="resume">Продолжить тест</button>
      </div>

      <!-- 1. специализация -->
      <div v-if="step === 1" class="card">
        <h2>Шаг 1. Какая специализация вам ближе?</h2>
        <p class="muted">Это опрос: специализацию вы выбираете сами, тест затем подтверждает её набором заданий по компетенциям.</p>
        <div class="choice-cards">
          <label v-for="s in specOptions" :key="s.code" class="choice-card" :class="{ selected: form.specialization_code === s.code }">
            <input type="radio" v-model="form.specialization_code" :value="s.code">
            <span><span class="title">{{ s.name }}</span><br><span class="desc">{{ s.description }}</span><br>
              <span class="desc" :style="{ color: s.has_bank ? 'var(--ok)' : 'var(--warn)' }">{{ s.has_bank ? 'свои задания по специализации' : 'тест по общим компетенциям: SQL, алгоритмы, отладка, Git' }}</span></span>
          </label>
        </div>
        <div class="form-actions" style="margin-top:14px"><button type="button" class="btn btn-primary" :disabled="!form.specialization_code" @click="step = 2">Дальше</button></div>
      </div>

      <!-- 2. грейд -->
      <div v-else-if="step === 2" class="card">
        <h2>Шаг 2. На какой грейд претендуете?</h2>
        <p class="muted">Первый блок заданий будет уровня заявленного грейда, второй — выше или ниже в зависимости от ответов. Грейд по итогам не понижается принудительно.</p>
        <div v-if="me.grade && !canChange" class="note note-warn">Ваш грейд {{ gradeTitle(me.grade) }} изменён {{ fmtDate(me.grade_changed_at) }}; следующая смена — с {{ fmtDate(options.grade_change_available_at) }}. Тест можно пройти, результат сохранится в истории, но грейд пока не поменяется.</div>
        <div class="choice-cards">
          <label v-for="g in gradeOptions" :key="g.code" class="choice-card" :class="{ selected: form.claimed_grade === g.code }">
            <input type="radio" v-model="form.claimed_grade" :value="g.code"><span><span class="title">{{ g.title }}</span><br><span class="desc">{{ g.description }}</span></span>
          </label>
        </div>
        <div class="form-actions" style="margin-top:14px"><button type="button" class="btn btn-ghost" @click="step = 1">Назад</button><button type="button" class="btn btn-primary" :disabled="!form.claimed_grade" @click="step = 3">Дальше</button></div>
      </div>

      <!-- 3. стек -->
      <div v-else-if="step === 3" class="card">
        <h2>Шаг 3. Ваш стек</h2>
        <p class="muted">Из заявленного стека собираются блоки теста: каждый блок покрывает не меньше двух технологий. Технология считается подтверждённой, если по ней были задания и достаточно верных ответов. Выбрано: <strong>{{ form.declared_skills.length }}</strong>.</p>
        <div v-for="g in skillGroups" :key="g.title" style="margin-bottom:10px">
          <div class="muted" style="font-size:12.5px;margin-bottom:4px">{{ g.title }}</div>
          <div class="chips"><button v-for="s in g.items" :key="s.code" type="button" class="chip chip-toggle" :class="{ on: form.declared_skills.includes(s.code) }" @click="toggleSkill(s.code)">{{ s.name }}</button></div>
        </div>
        <div class="note note-info" style="margin-top:12px">Тест: {{ store.catalog.test.blocks }} блока по {{ store.catalog.test.block_size }} задания, до {{ store.catalog.test.item_seconds }} секунд на задание. Правильные ответы не показываются; вернуться к заданию нельзя. Когда начнёте — отвлекаться не стоит.</div>
        <div class="form-actions"><button type="button" class="btn btn-ghost" @click="step = 2">Назад</button><button type="button" class="btn btn-primary btn-lg" :disabled="busy" @click="start"><span v-if="busy" class="spinner"></span>Начать тест</button></div>
      </div>

      <!-- 4. тест -->
      <div v-else-if="step === 4 && session">
        <div v-if="interlude" class="card" style="text-align:center;padding:36px">
          <h2>{{ interlude }}</h2>
          <p class="muted">Переходите, когда будете готовы — таймер запустится с первым заданием блока.</p>
          <button type="button" class="btn btn-primary btn-lg" @click="interlude = null">Продолжить</button>
        </div>
        <template v-else-if="current">
          <div class="card">
            <div class="row-between" style="margin-bottom:10px">
              <div><strong>Задание {{ itemIndex }} из {{ session.block_size }}</strong> <span class="muted">· блок {{ session.current_block }} из {{ session.blocks_total }} · уровень {{ gradeTitle(current.level) }}</span></div>
              <div class="timer" :class="{ low: timer.left.value <= 15 }" title="Время на задание">⏱ {{ timer.text.value }}</div>
            </div>
            <div class="progress" style="margin-bottom:16px"><span :style="{ width: progress + '%' }"></span></div>
            <TestItemView :payload="current.payload" v-model="answer" :key="current.id" />
            <div class="form-actions" style="margin-top:14px">
              <button type="button" class="btn btn-primary" :disabled="busy || !answerReady()" @click="submit(false)"><span v-if="busy" class="spinner"></span>Ответить</button>
              <button type="button" class="btn btn-ghost" :disabled="busy" @click="submit(true)">Пропустить</button>
              <span class="muted" style="font-size:12.5px">Правильность ответа не показывается — это защита от утечки заданий.</span>
            </div>
          </div>
        </template>
        <div v-else class="state"><span class="spinner"></span> Готовим следующий блок…</div>
      </div>

      <!-- 5. результат -->
      <div v-else-if="step === 5 && session" class="card">
        <h2>Результат</h2>
        <TestResult :session="session" @retake="retake" @applied="session.result.can_apply = false" />
      </div>
    </Loader>`,
};
