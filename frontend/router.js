/* Маршрутизация по hash: #/login, #/candidate/..., #/employer/... Без библиотек. */
import { reactive, shallowRef } from 'vue';

export const route = reactive({ path: '/', params: {}, query: {}, name: '' });
export const current = shallowRef(null);   // { component, meta }
let routes = [];

function compile(pattern) {
  const keys = [];
  const re = new RegExp('^' + pattern.replace(/\/:([a-zA-Z_]+)/g, (_, k) => { keys.push(k); return '/([^/]+)'; }) + '/?$');
  return { re, keys };
}

export function defineRoutes(list) {
  routes = list.map((r) => ({ ...r, ...compile(r.path) }));
}

function parseLocation() {
  const hash = location.hash.startsWith('#') ? location.hash.slice(1) : '';
  const [rawPath, rawQuery = ''] = (hash || '/').split('?');
  const query = {};
  // параметры могут прийти и до решётки (редирект бэкенда после связи с ФСП ID: /?fsp=linked#/candidate/profile)
  new URLSearchParams(location.search).forEach((v, k) => { query[k] = v; });
  new URLSearchParams(rawQuery).forEach((v, k) => { query[k] = v; });
  return { path: rawPath.startsWith('/') ? rawPath : '/' + rawPath, query };
}

export function resolve() {
  const { path, query } = parseLocation();
  for (const r of routes) {
    const m = r.re.exec(path);
    if (!m) continue;
    const params = {};
    r.keys.forEach((k, i) => { params[k] = decodeURIComponent(m[i + 1]); });
    return { r, path, query, params };
  }
  return { r: null, path, query, params: {} };
}

export function navigate(path, { replace = false } = {}) {
  const target = '#' + path;
  if (replace) {
    const url = location.pathname + location.search + target;
    history.replaceState(null, '', url);
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  } else if (location.hash === target) {
    window.dispatchEvent(new HashChangeEvent('hashchange'));
  } else {
    location.hash = target;
  }
}

export function startRouter(beforeEach) {
  const apply = () => {
    const resolved = resolve();
    const redirect = beforeEach ? beforeEach(resolved) : null;
    if (redirect) { navigate(redirect, { replace: true }); return; }
    route.path = resolved.path;
    route.params = resolved.params;
    route.query = resolved.query;
    route.name = resolved.r ? resolved.r.name || resolved.r.path : '';
    current.value = resolved.r ? { component: resolved.r.component, meta: resolved.r.meta || {} } : null;
    window.scrollTo(0, 0);
  };
  window.addEventListener('hashchange', apply);
  apply();
}

export function isActive(prefix) {
  return route.path === prefix || route.path.startsWith(prefix + '/');
}
