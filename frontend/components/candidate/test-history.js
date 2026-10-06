/* История тестов и просмотр отдельного сеанса. */
import { ref, onMounted } from 'vue';
import { api } from '../../api.js';
import { gradeTitle, specName } from '../../store.js';
import { route, navigate } from '../../router.js';
import { useLoad, fmtDateTime, DECISION } from '../../ui.js';
import { TestResult } from './test.js';

export const TestHistory = {
  setup() {
    const { data, loading, error, reload } = useLoad(() => api.get('/tests/sessions'));
    return { data, loading, error, reload, fmtDateTime, gradeTitle, specName, DECISION };
  },
  template: `
    <PageHead title="История тестов" sub="Все сеансы: заявленный и полученный грейд, решение по итогам, доля верных ответов.">
      <a href="#/candidate/test" class="btn btn-primary">Пройти тест</a>
    </PageHead>
    <Loader :loading="loading" :error="error" :empty="data && !data.length" empty-title="Тестов ещё не было" empty-hint="Пройдите опрос и тест — категория появится в профиле, а здесь сохранится история." @retry="reload">
      <template #empty><a href="#/candidate/test" class="btn btn-primary">Начать</a></template>
      <div class="table-wrap"><table class="tbl">
        <thead><tr><th>Дата</th><th>Специализация</th><th>Заявлен</th><th>Результат</th><th>Решение</th><th>Верно</th><th>Статус</th><th></th></tr></thead>
        <tbody>
          <tr v-for="s in data" :key="s.id">
            <td>{{ fmtDateTime(s.finished_at || s.started_at) }}</td>
            <td>{{ specName(s.specialization_code) }}</td>
            <td>{{ gradeTitle(s.claimed_grade) }}</td>
            <td><strong>{{ s.result_grade ? gradeTitle(s.result_grade) : '—' }}</strong></td>
            <td>{{ DECISION[s.decision] || '—' }}<span v-if="s.applied" class="muted"> · применён</span></td>
            <td>{{ s.correct_total !== null && s.correct_total !== undefined ? s.correct_total + ' из ' + s.items_total : '—' }}</td>
            <td><StatusBadge :status="s.status" /></td>
            <td><a :href="'#/candidate/test/sessions/' + s.id" class="btn btn-ghost btn-sm">{{ s.status === 'active' ? 'Продолжить' : 'Открыть' }}</a></td>
          </tr>
        </tbody>
      </table></div>
    </Loader>`,
};

export const TestSessionPage = {
  components: { TestResult },
  setup() {
    const { data, loading, error, reload } = useLoad(() => api.get(`/tests/sessions/${route.params.id}`));
    function retake(grade) { navigate(`/candidate/test?grade=${grade}`); }
    return { data, loading, error, reload, retake, id: route.params.id, fmtDateTime, gradeTitle, specName };
  },
  template: `
    <PageHead :title="'Сеанс теста № ' + id">
      <a href="#/candidate/test/history" class="btn btn-ghost">К истории</a>
    </PageHead>
    <Loader :loading="loading" :error="error" @retry="reload">
      <div v-if="data" class="card">
        <template v-if="data.status === 'finished'"><TestResult :session="data" @retake="retake" /></template>
        <template v-else>
          <p>Тест не завершён: пройдено блоков {{ data.current_block - 1 }} из {{ data.blocks_total }}.</p>
          <a href="#/candidate/test" class="btn btn-primary">Продолжить в разделе «Тестирование»</a>
        </template>
      </div>
    </Loader>`,
};
