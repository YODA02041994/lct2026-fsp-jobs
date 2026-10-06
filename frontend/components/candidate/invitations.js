/* Приглашения кандидату: список и карточка, принять / отклонить. */
import { ref, computed, watch, onMounted } from 'vue';
import { api } from '../../api.js';
import { toast, confirmDialog } from '../../store.js';
import { route, navigate } from '../../router.js';
import { useLoad, moneyRange, fmtDateTime, fmtDate } from '../../ui.js';

export const CandidateInvitations = {
  setup() {
    const { data, loading, error, reload } = useLoad(() => api.get('/candidates/me/invitations'));
    const selected = ref(null); const busy = ref(false);
    const filter = ref('all');
    const list = computed(() => (data.value || []).filter((i) => filter.value === 'all' || (filter.value === 'open' ? ['sent', 'viewed'].includes(i.status) : i.status === filter.value)));
    async function open(inv) {
      selected.value = inv;
      if (inv.status === 'sent') {
        try { const upd = await api.post(`/invitations/${inv.id}/view`); Object.assign(inv, upd); window.dispatchEvent(new Event('fsp:invitations-changed')); }
        catch (_) { /* отметка просмотра не критична */ }
      }
      if (route.params.id !== String(inv.id)) navigate(`/candidate/invitations/${inv.id}`, { replace: true });
    }
    function close() { selected.value = null; navigate('/candidate/invitations', { replace: true }); }
    watch(data, (d) => { if (d && route.params.id) { const inv = d.find((x) => String(x.id) === route.params.id); if (inv) open(inv); } });
    async function respond(decision) {
      const inv = selected.value;
      const ok = await confirmDialog(decision === 'accept'
        ? { title: 'Принять приглашение?', text: `Компания «${inv.company_name}» получит ваши ФИО и контакты и свяжется с вами: ${inv.contact_method || 'способом, указанным в приглашении'}.`, ok: 'Принять' }
        : { title: 'Отклонить приглашение?', text: 'Работодатель увидит отказ. Контакты останутся скрытыми. Отменить решение будет нельзя.', ok: 'Отклонить', danger: true });
      if (!ok) return;
      busy.value = true;
      try {
        const upd = await api.post(`/invitations/${inv.id}/respond`, { decision });
        Object.assign(inv, upd);
        toast(decision === 'accept' ? 'Приглашение принято. Работодатель получил ваши контакты' : 'Приглашение отклонено', 'ok');
        window.dispatchEvent(new Event('fsp:invitations-changed'));
      } catch (e) { toast(e.detail, 'err'); } finally { busy.value = false; }
    }
    const counts = computed(() => ({ all: (data.value || []).length, open: (data.value || []).filter((i) => ['sent', 'viewed'].includes(i.status)).length, accepted: (data.value || []).filter((i) => i.status === 'accepted').length, declined: (data.value || []).filter((i) => i.status === 'declined').length }));
    return { data, list, loading, error, reload, selected, open, close, respond, busy, filter, counts, moneyRange, fmtDateTime, fmtDate };
  },
  template: `
    <PageHead title="Приглашения" sub="Работодатели нашли вас по категории и направили предложение. Зарплата и компания видны до начала общения; контакты откроются только после вашего согласия." />
    <Loader :loading="loading" :error="error" :empty="data && !data.length" empty-title="Приглашений пока нет" empty-hint="Работодатели увидят вас после прохождения теста и при включённом согласии на показ профиля. Чем больше подтверждённых технологий — тем выше вы в подборках." @retry="reload">
      <template #empty><a href="#/candidate/test" class="btn btn-primary">Пройти тест</a></template>
      <div class="tabs">
        <button type="button" :class="{ active: filter === 'all' }" @click="filter = 'all'">Все ({{ counts.all }})</button>
        <button type="button" :class="{ active: filter === 'open' }" @click="filter = 'open'">Ждут ответа ({{ counts.open }})</button>
        <button type="button" :class="{ active: filter === 'accepted' }" @click="filter = 'accepted'">Принятые ({{ counts.accepted }})</button>
        <button type="button" :class="{ active: filter === 'declined' }" @click="filter = 'declined'">Отклонённые ({{ counts.declined }})</button>
      </div>
      <div class="list">
        <div v-for="i in list" :key="i.id" class="item clickable" @click="open(i)">
          <div class="row-between">
            <div>
              <div class="item-title">{{ i.company_name }} <StatusBadge :status="i.status" style="margin-left:6px" /></div>
              <div class="item-meta"><span>{{ fmtDateTime(i.sent_at) }}</span><span v-if="i.vacancy">вакансия: {{ i.vacancy.title }}</span><span v-else>без привязки к вакансии</span><span>связь: {{ i.contact_method }}</span></div>
            </div>
            <div class="price big">{{ moneyRange(i.salary_min, i.salary_max) }}</div>
          </div>
          <p class="muted" style="margin:8px 0 0;font-size:14px">{{ i.message.length > 160 ? i.message.slice(0, 160) + '…' : i.message }}</p>
        </div>
        <div v-if="!list.length" class="empty"><div class="empty-title">В этой группе пусто</div></div>
      </div>
    </Loader>

    <Modal v-if="selected" :title="'Приглашение от «' + selected.company_name + '»'" @close="close">
      <div class="row-between" style="margin-bottom:10px"><StatusBadge :status="selected.status" /><span class="price big">{{ moneyRange(selected.salary_min, selected.salary_max) }}</span></div>
      <p class="pre-wrap" style="font-size:15px">{{ selected.message }}</p>
      <dl class="kv">
        <dt>Компания</dt><dd>{{ selected.company_name }}</dd>
        <dt>Зарплата в месяц</dt><dd>{{ moneyRange(selected.salary_min, selected.salary_max) }}</dd>
        <dt>Способ связи</dt><dd>{{ selected.contact_method }}</dd>
        <dt>Вакансия</dt><dd><a v-if="selected.vacancy" :href="'#/candidate/vacancies/' + selected.vacancy.id">{{ selected.vacancy.title }}</a><span v-else class="muted">без привязки к вакансии</span></dd>
      </dl>
      <hr class="sep">
      <div class="timeline">
        <span class="t done"><span class="dot"></span>отправлено {{ fmtDateTime(selected.sent_at) }}</span>
        <span class="t" :class="{ done: selected.viewed_at }"><span class="dot"></span>просмотрено {{ selected.viewed_at ? fmtDateTime(selected.viewed_at) : '' }}</span>
        <span class="t" :class="{ done: selected.responded_at }"><span class="dot"></span>{{ selected.status === 'declined' ? 'отклонено' : 'принято' }} {{ selected.responded_at ? fmtDateTime(selected.responded_at) : '' }}</span>
      </div>
      <div v-if="selected.status === 'accepted'" class="note note-ok" style="margin-top:12px">Вы приняли приглашение. Работодатель видит ваши ФИО и контакты и свяжется с вами: {{ selected.contact_method }}.</div>
      <div v-else-if="selected.status === 'declined'" class="note note-info" style="margin-top:12px">Приглашение отклонено. Контакты остались скрытыми.</div>
      <template #footer v-if="['sent', 'viewed'].includes(selected.status)">
        <button type="button" class="btn btn-danger" :disabled="busy" @click="respond('decline')">Отклонить</button>
        <button type="button" class="btn btn-primary" :disabled="busy" @click="respond('accept')"><span v-if="busy" class="spinner"></span>Принять и открыть контакты</button>
      </template>
    </Modal>`,
};
