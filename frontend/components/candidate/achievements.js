/* Достижения ФСП: связь с ФСП ID, записи с уровнем доверия, ручное добавление, скрытие. */
import { ref, reactive, computed, onMounted } from 'vue';
import { api } from '../../api.js';
import { store, refreshMe, toast, confirmDialog } from '../../store.js';
import { useLoad, fmtDate, TRUST } from '../../ui.js';

const KINDS = { rank: 'Спортивный разряд или звание', result: 'Результат соревнования', team: 'Участие в команде', rating: 'Рейтинг', other: 'Другое' };

export const CandidateAchievements = {
  setup() {
    const { data, loading, error, reload } = useLoad(() => api.get('/candidates/me/achievements'));
    const me = computed(() => store.me || {});
    const showHidden = ref(false);
    const adding = ref(false); const busy = ref(false);
    const form = reactive({ kind: 'result', title: '', discipline: '', date: '', place: '', document_name: '' });
    onMounted(refreshMe);
    const visible = computed(() => (data.value || []).filter((a) => showHidden.value || !a.hidden));
    const hiddenCount = computed(() => (data.value || []).filter((a) => a.hidden).length);
    const noHistory = computed(() => !me.value.fsp_id && data.value && !data.value.some((a) => a.trust_level === 'source'));
    async function link() {
      busy.value = true;
      try { const r = await api.get('/fsp/link/start'); location.href = r.redirect_url; }
      catch (e) { toast(e.detail, 'err'); busy.value = false; }
    }
    async function unlink() {
      const ok = await confirmDialog({ title: 'Отвязать ФСП ID?', text: 'Записи, подтверждённые источником, станут недействительными. Связать профиль снова можно в любой момент.', ok: 'Отвязать', danger: true });
      if (!ok) return;
      busy.value = true;
      try { store.me = await api.post('/fsp/unlink'); await reload(); toast('ФСП ID отвязан', 'ok'); } catch (e) { toast(e.detail, 'err'); } finally { busy.value = false; }
    }
    async function toggleHidden(a) {
      try { const upd = await api.patch(`/candidates/me/achievements/${a.id}`, { hidden: !a.hidden }); Object.assign(a, upd); toast(a.hidden ? 'Запись скрыта от работодателей' : 'Запись снова видна', 'ok'); }
      catch (e) { toast(e.detail, 'err'); }
    }
    async function add() {
      busy.value = true;
      try {
        const body = { kind: form.kind, title: form.title.trim(), discipline: form.discipline.trim(), date: form.date };
        if (form.place !== '') body.place = Number(form.place);
        if (form.document_name.trim()) body.document_name = form.document_name.trim();
        await api.post('/candidates/me/achievements', body);
        Object.assign(form, { kind: 'result', title: '', discipline: '', date: '', place: '', document_name: '' });
        adding.value = false; await reload(); toast('Запись добавлена со статусом «заявлено»', 'ok');
      } catch (e) { toast(e.detail, 'err'); } finally { busy.value = false; }
    }
    return { data, loading, error, reload, me, visible, hiddenCount, showHidden, noHistory, link, unlink, toggleHidden, adding, add, form, busy, KINDS, TRUST, fmtDate };
  },
  template: `
    <PageHead title="Достижения ФСП" sub="Профиль достижений виден работодателю и влияет на место в подборке с ограниченным весом. Уровень доверия у каждой записи свой: интерфейс их не смешивает.">
      <button type="button" class="btn btn-outline" @click="adding = true">Добавить запись вручную</button>
    </PageHead>
    <div class="grid" style="grid-template-columns: 1fr 320px; align-items:start">
      <div>
        <div class="legend" style="margin-bottom:10px">
          <span>Уровни доверия:</span>
          <TrustBadge v-for="(t, k) in TRUST" :key="k" :level="k" />
          <label class="check" style="padding:4px 8px;margin-left:auto;font-size:13px"><input type="checkbox" v-model="showHidden"> показывать скрытые ({{ hiddenCount }})</label>
        </div>
        <Loader :loading="loading" :error="error" :empty="data && !visible.length" :empty-title="noHistory ? 'История ФСП отсутствует' : 'Записей нет'"
          :empty-hint="noHistory ? 'Профиль не связан с ФСП ID, подтверждённых записей нет. Это не влияет на категорию — она определяется тестом. Вы можете связать ФСП ID или добавить достижение вручную: оно получит статус «заявлено».' : 'Все записи скрыты или удалены.'" @retry="reload">
          <template #empty><div class="row" style="justify-content:center"><button type="button" class="btn btn-primary" :disabled="busy" @click="link" v-if="!me.fsp_id">Связать с ФСП ID</button><button type="button" class="btn btn-outline" @click="adding = true">Добавить вручную</button></div></template>
          <div class="list">
            <div v-for="a in visible" :key="a.id" class="item ach-item" :class="{ 'hidden-rec': a.hidden }">
              <div>
                <div class="item-title">{{ a.title }}<span v-if="a.place" class="muted" style="font-weight:400"> · {{ a.place }} место</span></div>
                <div class="item-meta"><span>{{ KINDS[a.kind] || a.kind }}</span><span v-if="a.discipline">{{ a.discipline }}</span><span>{{ fmtDate(a.date) }}</span><span v-if="a.valid_until">действует до {{ fmtDate(a.valid_until) }}</span><span v-if="a.event">{{ a.event.name }}<template v-if="a.event.ekp_number"> · {{ a.event.ekp_number }}</template></span></div>
                <div class="row" style="margin-top:6px"><TrustBadge :level="a.trust_level" /><StatusBadge v-if="a.status !== 'active'" :status="a.status" /><span v-if="a.hidden" class="badge">скрыто от работодателей</span></div>
              </div>
              <div><button type="button" class="btn btn-ghost btn-sm" @click="toggleHidden(a)">{{ a.hidden ? 'Показать' : 'Скрыть' }}</button></div>
            </div>
          </div>
        </Loader>
      </div>
      <div class="card">
        <h3>ФСП ID</h3>
        <template v-if="me.fsp_id">
          <p style="margin:0 0 4px">Связан: <strong>{{ me.fsp_id }}</strong></p>
          <p class="muted" style="font-size:13px">с {{ fmtDate(me.fsp_linked_at) }}. Записи из реестра помечаются «подтверждено источником» и обновляются при входе.</p>
          <button type="button" class="btn btn-danger btn-sm" :disabled="busy" @click="unlink">Отвязать</button>
        </template>
        <template v-else>
          <p class="muted" style="font-size:13.5px">Связь с ФСП ID подтверждает достижения из реестра федерации: разряды, места на соревнованиях, участие в мероприятиях. Вы перейдёте на страницу входа ФСП ID и вернётесь обратно.</p>
          <button type="button" class="btn btn-primary btn-block" :disabled="busy" @click="link"><span v-if="busy" class="spinner"></span>Связать с ФСП ID</button>
        </template>
        <hr class="sep">
        <p class="muted" style="font-size:12.5px;margin:0">Видимость достижений работодателям настраивается в <a href="#/candidate/settings">настройках приватности</a>.</p>
      </div>
    </div>
    <Modal v-if="adding" title="Добавить достижение" @close="adding = false">
      <div class="note note-warn">Запись получит статус <strong>«заявлено»</strong>: она видна работодателю с этой пометкой и не учитывается в оценке как подтверждённая. Подтверждение документом или источником добавит оператор.</div>
      <form @submit.prevent="add" id="ach-form">
        <Field label="Тип" required><select v-model="form.kind" required><option v-for="(t, k) in KINDS" :key="k" :value="k">{{ t }}</option></select></Field>
        <Field label="Название" required><input v-model="form.title" type="text" required placeholder="например: 2 место, региональный этап чемпионата"></Field>
        <div class="form-grid">
          <Field label="Дисциплина" required><input v-model="form.discipline" type="text" required placeholder="продуктовое программирование"></Field>
          <Field label="Дата" required><input v-model="form.date" type="date" required></Field>
          <Field label="Место (если было)"><input v-model="form.place" type="number" min="1"></Field>
          <Field label="Название документа"><input v-model="form.document_name" type="text" placeholder="диплом, приказ…"></Field>
        </div>
      </form>
      <template #footer><button type="button" class="btn btn-ghost" @click="adding = false">Отмена</button><button form="ach-form" class="btn btn-primary" :disabled="busy">Добавить</button></template>
    </Modal>`,
};
