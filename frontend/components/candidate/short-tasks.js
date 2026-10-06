/* Короткие задания от работодателей: список и форма ответа. */
import { ref, reactive } from 'vue';
import { api } from '../../api.js';
import { toast, skillName } from '../../store.js';
import { useLoad, fmtDate } from '../../ui.js';

export const CandidateShortTasks = {
  setup() {
    const { data, loading, error, reload } = useLoad(() => api.get('/candidates/me/short-tasks'));
    const drafts = reactive({}); const busy = ref(null);
    async function send(t) {
      const text = (drafts[t.id] || '').trim();
      if (!text) { toast('Напишите ответ', 'warn'); return; }
      busy.value = t.id;
      try { const upd = await api.post(`/short-tasks/${t.id}/answer`, { answer: text }); Object.assign(t, upd); toast('Ответ отправлен работодателю', 'ok'); }
      catch (e) { toast(e.detail, 'err'); } finally { busy.value = null; }
    }
    return { data, loading, error, reload, drafts, busy, send, skillName, fmtDate };
  },
  template: `
    <PageHead title="Короткие задания" sub="Работодатели время от времени предлагают небольшие практические вопросы. Ответ оценивает работодатель по шкале от 1 до 5; на грейд это не влияет, но повышает актуальность профиля в подборках." />
    <Loader :loading="loading" :error="error" :empty="data && !data.length" empty-title="Заданий пока нет" empty-hint="Когда работодатель опубликует задание по вашей специализации, оно появится здесь." @retry="reload">
      <div class="list">
        <div v-for="t in data" :key="t.id" class="card">
          <div class="row-between">
            <div><h3 style="margin-bottom:2px">{{ t.title }}</h3><div class="item-meta"><span>{{ t.company_name }}</span><span v-if="t.created_at">{{ fmtDate(t.created_at) }}</span></div></div>
            <span v-if="t.answered" class="badge" :class="t.employer_score ? 'st-accepted' : 'st-viewed'">{{ t.employer_score ? 'оценка ' + t.employer_score + ' из 5' : 'ответ отправлен, ждёт оценки' }}</span>
            <span v-else class="badge st-sent">ждёт ответа</span>
          </div>
          <div class="chips" style="margin:8px 0"><span v-for="s in t.technologies" :key="s" class="chip chip-tech">{{ skillName(s) }}</span></div>
          <p class="pre-wrap">{{ t.text }}</p>
          <div v-if="t.answered" class="note note-info" style="margin-bottom:0"><strong>Ваш ответ:</strong> <span class="pre-wrap">{{ t.answer }}</span></div>
          <form v-else @submit.prevent="send(t)">
            <Field label="Ваш ответ" hint="Свободный текст: подход, шаги, что проверите"><textarea v-model="drafts[t.id]" rows="4"></textarea></Field>
            <button class="btn btn-primary" :disabled="busy === t.id"><span v-if="busy === t.id" class="spinner"></span>Отправить ответ</button>
          </form>
        </div>
      </div>
    </Loader>`,
};
