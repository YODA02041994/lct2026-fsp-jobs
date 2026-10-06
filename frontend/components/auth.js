/* Вход, регистрация, подтверждение почты. */
import { ref, reactive, computed, onMounted } from 'vue';
import { api } from '../api.js';
import { store, setSession, loadMe, homeFor, toast } from '../store.js';
import { navigate, route } from '../router.js';

const Side = {
  template: `
    <aside class="auth-side">
      <h1>Карьера ФСП</h1>
      <p>Платформа подбора ИТ-специалистов с обратной механикой: категорию кандидату присваивает тест, а работодатель сам находит подходящих людей и направляет приглашение с зарплатой.</p>
      <ol class="steps">
        <li><span class="n">1</span><span>Кандидат заполняет профиль, проходит опрос и тест — получает категорию «специализация × грейд».</span></li>
        <li><span class="n">2</span><span>Работодатель описывает потребность и получает подборку кандидатов с обоснованием.</span></li>
        <li><span class="n">3</span><span>Приглашение с зарплатой «от – до» — контакты открываются только после согласия кандидата.</span></li>
        <li><span class="n">4</span><span>Профиль связывается с ФСП ID: достижения в соревнованиях подтверждаются источником.</span></li>
      </ol>
    </aside>`,
};

export const LoginPage = {
  components: { Side },
  setup() {
    const form = reactive({ email: '', password: '' });
    const busy = ref(false);
    const error = ref('');
    const demo = computed(() => (store.catalog && store.catalog.demo_mode && store.catalog.demo_accounts) || []);
    async function submit() {
      busy.value = true; error.value = '';
      try {
        const r = await api.post('/auth/login', { email: form.email.trim(), password: form.password });
        setSession(r.access_token, r.role);
        await loadMe();
        navigate(homeFor(r.role));
      } catch (e) {
        error.value = e.detail;
      } finally { busy.value = false; }
    }
    function fill(acc) { form.email = acc.email; form.password = acc.password; }
    return { form, busy, error, submit, demo, fill };
  },
  template: `
    <div class="auth-wrap">
      <Side />
      <div class="auth-form"><div class="auth-card">
        <div class="tabs"><a class="active" href="#/login">Вход</a><a href="#/register">Регистрация</a></div>
        <h2>Вход в кабинет</h2>
        <form @submit.prevent="submit">
          <Field label="Электронная почта" required><input v-model="form.email" type="email" required autocomplete="username" placeholder="you@example.ru"></Field>
          <Field label="Пароль" required><input v-model="form.password" type="password" required autocomplete="current-password"></Field>
          <div v-if="error" class="note note-err">{{ error }}</div>
          <button class="btn btn-primary btn-block btn-lg" :disabled="busy"><span v-if="busy" class="spinner"></span>Войти</button>
        </form>
        <p class="muted" style="margin-top:12px;font-size:13px">Нет учётной записи? <a href="#/register">Зарегистрируйтесь</a> как кандидат или работодатель.</p>
        <div v-if="demo.length" class="demo-box">
          <strong>Демонстрационный режим.</strong> Учётные записи для проверки (пароль подставится сам):
          <ul style="margin:6px 0 0;padding-left:18px">
            <li v-for="a in demo" :key="a.email"><button type="button" @click="fill(a)">{{ a.email }}</button> — {{ a.title }}</li>
          </ul>
        </div>
      </div></div>
    </div>`,
};

export const RegisterPage = {
  components: { Side },
  setup() {
    const form = reactive({ role: 'candidate', email: '', password: '', password2: '', agree: false });
    const busy = ref(false);
    const error = ref('');
    const done = ref(null);
    async function submit() {
      error.value = '';
      if (form.password !== form.password2) { error.value = 'Пароли не совпадают'; return; }
      if (!form.agree) { error.value = 'Нужно согласие на обработку персональных данных'; return; }
      busy.value = true;
      try {
        done.value = await api.post('/auth/register', { email: form.email.trim(), password: form.password, role: form.role });
      } catch (e) { error.value = e.detail; } finally { busy.value = false; }
    }
    function go() { if (done.value && done.value.demo_confirm_url) location.href = done.value.demo_confirm_url; }
    return { form, busy, error, done, submit, go };
  },
  template: `
    <div class="auth-wrap">
      <Side />
      <div class="auth-form"><div class="auth-card">
        <div class="tabs"><a href="#/login">Вход</a><a class="active" href="#/register">Регистрация</a></div>
        <template v-if="done">
          <h2>Подтвердите почту</h2>
          <p>Мы отправили письмо на <strong>{{ done.email }}</strong>. Перейдите по ссылке из письма, чтобы завершить регистрацию и войти в кабинет.</p>
          <div v-if="done.demo_confirm_url" class="note note-pink">
            <strong>Демонстрационный режим:</strong> почта не отправляется, ссылка из письма показана здесь.
            <div style="margin-top:10px"><button type="button" class="btn btn-primary" @click="go">Перейти по ссылке из письма</button></div>
          </div>
          <p v-else class="muted" style="font-size:13px">Письмо не пришло? Проверьте папку «Спам» или зарегистрируйтесь заново через несколько минут.</p>
          <a href="#/login" class="btn btn-ghost">К странице входа</a>
        </template>
        <template v-else>
          <h2>Регистрация</h2>
          <p class="muted" style="font-size:14px">Выберите роль — у кандидата и работодателя разные кабинеты.</p>
          <form @submit.prevent="submit">
            <div class="role-pick">
              <label class="choice-card" :class="{ selected: form.role === 'candidate' }"><input type="radio" v-model="form.role" value="candidate"><span><span class="title">Я кандидат</span><br><span class="desc">ищу работу в ИТ, пройду тест и получу категорию</span></span></label>
              <label class="choice-card" :class="{ selected: form.role === 'employer' }"><input type="radio" v-model="form.role" value="employer"><span><span class="title">Я работодатель</span><br><span class="desc">подбираю специалистов и направляю приглашения</span></span></label>
            </div>
            <Field label="Электронная почта" required hint="На неё придёт ссылка для подтверждения"><input v-model="form.email" type="email" required autocomplete="email"></Field>
            <Field label="Пароль" required hint="Не короче 6 символов"><input v-model="form.password" type="password" required minlength="6" autocomplete="new-password"></Field>
            <Field label="Повторите пароль" required><input v-model="form.password2" type="password" required autocomplete="new-password"></Field>
            <label class="check" :class="{ on: form.agree }"><input type="checkbox" v-model="form.agree"><span><span class="check-title">Согласие на обработку персональных данных</span><br><span class="check-text">Даю согласие на обработку адреса почты и данных профиля для работы платформы (152-ФЗ). Согласие на показ профиля работодателям даётся отдельно, в настройках кабинета.</span></span></label>
            <div v-if="error" class="note note-err" style="margin-top:12px">{{ error }}</div>
            <button class="btn btn-primary btn-block btn-lg" style="margin-top:12px" :disabled="busy"><span v-if="busy" class="spinner"></span>Зарегистрироваться</button>
          </form>
        </template>
      </div></div>
    </div>`,
};

export const ConfirmPage = {
  components: { Side },
  setup() {
    const state = ref('busy');
    const error = ref('');
    onMounted(async () => {
      const token = route.query.token;
      if (!token) { state.value = 'error'; error.value = 'В ссылке нет кода подтверждения'; return; }
      try {
        const r = await api.get('/auth/confirm', { token });
        setSession(r.access_token, r.role);
        await loadMe();
        state.value = 'ok';
        toast('Почта подтверждена. Добро пожаловать!', 'ok');
        setTimeout(() => navigate(homeFor(r.role), { replace: true }), 900);
      } catch (e) { state.value = 'error'; error.value = e.detail; }
    });
    return { state, error };
  },
  template: `
    <div class="auth-wrap">
      <Side />
      <div class="auth-form"><div class="auth-card">
        <h2>Подтверждение почты</h2>
        <div v-if="state === 'busy'" class="state"><span class="spinner"></span> Проверяем ссылку…</div>
        <div v-else-if="state === 'ok'" class="note note-ok">Почта подтверждена, входим в кабинет…</div>
        <template v-else>
          <div class="note note-err">{{ error }}</div>
          <a href="#/login" class="btn btn-outline">К странице входа</a>
        </template>
      </div></div>
    </div>`,
};
