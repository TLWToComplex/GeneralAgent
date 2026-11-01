<!--
  统一登录页 —— 等价迁移自原型 index.html 第 19–162 行 + main.js 全文。

  行为逐条对齐 main.js：
     1. 输入框聚焦高亮、口令可见切换、输入即清错
     2. toast（3200ms 默认）
     3. 表单校验 → 提交 → 成功后 .done 900ms 再跳控制台；记住账号写 localStorage
     4. 指针镜面高光：把指针位置写成 --mx / --my 交给 CSS
     5. 页脚协议链接（演示态 toast）

  —— 本轮与原型不同之处（接真实后端登录，其余视觉零改动）：
     · 原型是"假登录"：校验通过后一个 1400ms 定时器直接进控制台。现在真的调后端：
       GET /captcha 取图形验证码 → POST /aiUser/login 换 JWT；
     · 因此模板新增验证码输入框（后端登录接口要求 captchaId + captchaCode）；
     · 去掉原型"账号≥3位 / 口令≥6位"的长度门槛：库里既有 a/b/c 这类测试账号，
       也可能有 6 位以下的历史口令（密码沿用老库 Werkzeug 哈希，后端本身不校验长度），
       长度校验只会把合法账号挡在门外 —— 只保留"非空"；
     · 失败文案直接取后端原文（`{"error": "..."}`），不再由前端臆造；
     · 后端验证码**一次性**（校验失败也作废），所以任何一次失败都重新获取，
       否则用户会一直卡在"验证码错误"。

  —— 按要求删掉的三块（对应原型 main.js 的标签页 / 二维码 / SSO 逻辑）：
     · 「口令登录 / 扫码登录」标签页与墨条 .tabs__ink；
     · 扫码面板 #qr（含 29×29 点阵 canvas 与「刷新二维码」按钮）；
     · 「其他登录方式」分隔线 + 统一身份认证 / 企业微信 / 飞书三个 SSO 入口。
     卡片里只剩口令登录一种方式，**没有假的登录入口**了。
     连带删掉的还有 login.css 里这批选择器（.tabs / .tab / .tabs__ink / .panel /
     .qr* / .divider / .sso*）—— 见该文件里的「已删除」说明段。
     要还原成原型的多方式登录，从原型 index.html 第 19–162 行 + main.js 抄回来即可。
-->
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchCaptcha, login as loginApi } from '@/api/auth'
import { isApiError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { rememberKey } from '@/config/runtime'

const router = useRouter()
const auth = useAuthStore()

/* ---------------------------------------------------------------- 表单 */
const username = ref('')
const password = ref('')
const showPwd = ref(false)
const remember = ref(true)
const loading = ref(false)
const btnLabel = ref('安全登录')
/** 各字段自己的错误文案（对应原型的 .field.is-error + .field__err） */
const errUser = ref('')
const errPwd = ref('')
const errCaptcha = ref('')
/** 表单级错误：账号锁定 / 超30天未登录 / 后端不可达这类归不到某个输入框的失败 */
const formError = ref('')
const doneOn = ref(false)
const doneMsg = ref('正在进入控制台…')

const userEl = ref<HTMLInputElement | null>(null)

/* ---------------------------------------------------------------- 图形验证码 */
const captchaId = ref('')
const captchaImage = ref('')
const captchaCode = ref('')
const captchaLoading = ref(false)
/** 刷新序号：并发刷新时丢弃过期响应，避免旧图覆盖新图（图与 id 必须成对） */
let captchaSeq = 0

/**
 * 取一张新的验证码。
 *
 * 后端验证码写入进程内存缓存、默认 300 秒有效、**一次性使用**，
 * 因此每次调用都会换掉 captchaId，并把输入框清空。
 */
async function loadCaptcha(): Promise<void> {
  const seq = ++captchaSeq
  captchaLoading.value = true
  errCaptcha.value = ''
  try {
    const data = await fetchCaptcha()
    if (seq !== captchaSeq) return // 已有更新的请求在飞，本次结果作废
    captchaId.value = data.captchaId
    captchaImage.value = data.captchaImage
    captchaCode.value = ''
  } catch (err) {
    if (seq !== captchaSeq) return
    captchaId.value = ''
    captchaImage.value = ''
    formError.value = isApiError(err) ? err.message : '图形验证码获取失败，请点击图片重试'
  } finally {
    if (seq === captchaSeq) captchaLoading.value = false
  }
}

function onCaptchaInput(): void {
  errCaptcha.value = ''
}

function clearErrors(): void {
  errUser.value = ''
  errPwd.value = ''
  errCaptcha.value = ''
  formError.value = ''
}
function onUserInput(): void {
  errUser.value = ''
}
function onPwdInput(): void {
  errPwd.value = ''
}

/** 成功后延迟跳转的定时器 */
let redirectTimer: number | null = null

/** 登录成功后：落地登录态 → 播完成动画 → 900ms 后进控制台 */
function succeed(
  token: string,
  user: Parameters<typeof auth.setSession>[1],
  passwordExpired?: boolean,
): void {
  const u = username.value.trim()
  try {
    if (remember.value) window.localStorage.setItem(rememberKey(), u)
    else window.localStorage.removeItem(rememberKey())
  } catch {
    /* ignore */
  }

  auth.setSession(token, user)
  password.value = '' // 不把口令留在内存里
  loading.value = false
  btnLabel.value = '安全登录'
  doneMsg.value = '正在挂载权限策略并进入控制台…'
  doneOn.value = true

  /* 后端的两条"只提醒不阻断"提示（老项目口径） */
  const notes: string[] = []
  if (passwordExpired) notes.push('密码已超过有效期，建议尽快修改')
  if (user.needUpdateMsg) notes.push('请补充真实姓名')
  if (notes.length) toast(notes.join('<br>'), 4200)

  redirectTimer = window.setTimeout(() => {
    void router.replace('/console/workbench')
  }, 900)
}

async function onSubmit(): Promise<void> {
  if (loading.value) return
  clearErrors()

  const u = username.value.trim()
  if (!u) {
    errUser.value = '请输入组织账号'
    userEl.value?.focus()
    return
  }
  if (!password.value) {
    errPwd.value = '请输入访问口令'
    return
  }
  const code = captchaCode.value.trim()
  if (!code) {
    errCaptcha.value = '请输入图形验证码'
    return
  }
  if (!captchaId.value) {
    formError.value = '图形验证码尚未就绪，请点击验证码图片重试'
    return
  }

  loading.value = true
  btnLabel.value = '身份校验中'

  try {
    const result = await loginApi({
      username: u,
      password: password.value,
      captchaId: captchaId.value,
      captchaCode: code,
    })
    succeed(result.token, result.user, result.passwordExpiredWarning)
    return
  } catch (err) {
    loading.value = false
    btnLabel.value = '安全登录'

    const message = isApiError(err) ? err.message : '登录失败，请稍后重试'

    /* 后端验证码一次性：失败后必须换一张，否则下一次提交必然是"验证码错误" */
    void loadCaptcha()

    /* 能定位到输入框的错误就近展示，其余（锁定 / 后端不可达）落在表单级 */
    if (message.includes('验证码')) {
      errCaptcha.value = message
      return
    }
    if (message.includes('用户名') || message.includes('邮箱')) {
      errUser.value = message
      userEl.value?.focus()
      return
    }
    if (message.includes('密码')) {
      errPwd.value = message
      return
    }
    formError.value =
      isApiError(err) && err.isNetworkError ? `${message}（后端默认监听 8038 端口）` : message
  }
}

/* 进页面时：回填记住的账号 → 取验证码 → 画二维码 → 提示被踢出的原因 */
onMounted(() => {
  try {
    const saved = window.localStorage.getItem(rememberKey())
    if (saved) {
      username.value = saved
      password.value = ''
      requestAnimationFrame(() => userEl.value?.blur())
    }
  } catch {
    /* 隐私模式忽略 */
  }

  void loadCaptcha()

  /* 被 401 踢出（令牌过期 / 后端重启换了密钥 / 账号被删）时带一句提示回登录页 */
  const notice = auth.consumeExpiredNotice()
  if (notice) toast(notice)
})

onBeforeUnmount(() => {
  if (redirectTimer !== null) window.clearTimeout(redirectTimer)
  if (toastTimer !== null) window.clearTimeout(toastTimer)
})

/* ---------------------------------------------------------------- 轻提示 */
const toastHtml = ref('')
const toastOn = ref(false)
let toastTimer: number | null = null
function toast(html: string, ms = 3200): void {
  toastHtml.value = html
  toastOn.value = true
  if (toastTimer !== null) window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => {
    toastOn.value = false
  }, ms)
}

/* ---------------------------------------------------------------- 指针镜面高光 */
const cardEl = ref<HTMLElement | null>(null)
let queued = false

function applyPointer(): void {
  queued = false
  const card = cardEl.value
  if (!card) return
  card.style.setProperty('--mx', mx)
  card.style.setProperty('--my', my)
}
let mx = '12%'
let my = '-6%'

function onPointerMove(e: PointerEvent): void {
  const card = cardEl.value
  if (!card) return
  const r = card.getBoundingClientRect()
  if (!r.width || !r.height) return
  mx = `${(((e.clientX - r.left) / r.width) * 100).toFixed(2)}%`
  my = `${(((e.clientY - r.top) / r.height) * 100).toFixed(2)}%`
  if (!queued) {
    queued = true
    requestAnimationFrame(applyPointer)
  }
}

function onPointerLeave(): void {
  mx = '12%'
  my = '-6%'
  if (!queued) {
    queued = true
    requestAnimationFrame(applyPointer)
  }
}
</script>

<template>
  <div class="stage">
    <main class="cosmos">
      <div class="core" id="core">
        <span class="core__mark" role="img" aria-label="GeneralAgent">
          <svg viewBox="0 0 100 100" fill="none">
            <path d="M50 6 88 28.5v43L50 94 12 71.5v-43z" stroke="currentColor" stroke-opacity=".42" stroke-width="1.3" />
            <path d="M50 20 76 35v30L50 80 24 65V35z" stroke="currentColor" stroke-opacity=".9" stroke-width="1.7" />
            <path d="M50 20v-8M76 35l11-6M76 65l11 6M50 80v8M24 65l-11 6M24 35l-11-6"
                  stroke="currentColor" stroke-opacity=".5" stroke-width="1.1" stroke-linecap="round" />
            <circle cx="50" cy="50" r="5.1" fill="currentColor" />
            <circle cx="50" cy="20" r="2.5" fill="currentColor" />
            <circle cx="76" cy="65" r="2.5" fill="currentColor" />
            <circle cx="24" cy="65" r="2.5" fill="currentColor" />
          </svg>
        </span>
      </div>

      <div class="wordmark">
        <h1>GeneralAgent</h1>
      </div>

      <section class="auth">
        <div
          class="card"
          id="card"
          ref="cardEl"
          @pointermove="onPointerMove"
          @pointerleave="onPointerLeave"
        >
          <span class="card__lens" aria-hidden="true" />

          <!-- 口令登录。原型的「口令登录 / 扫码登录」标签页与「其他登录方式」已按要求删除，
               现在这张卡片只有一种登录方式，所以不再需要 tab 与面板切换机制。 -->
          <div class="panel" id="pwd">
            <form id="login-form" class="form" novalidate autocomplete="on" @submit.prevent="onSubmit">
              <label class="field" :class="{ 'is-error': !!errUser }">
                <span class="field__k">组织账号</span>
                <span class="field__box">
                  <svg class="field__ico" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <circle cx="12" cy="8" r="3.6" stroke="currentColor" stroke-width="1.5" />
                    <path d="M4.5 20c1.4-3.6 4.2-5.4 7.5-5.4S18.1 16.4 19.5 20" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                  </svg>
                  <input
                    id="username"
                    ref="userEl"
                    v-model="username"
                    name="username"
                    type="text"
                    placeholder="用户名 / 邮箱"
                    autocomplete="username"
                    spellcheck="false"
                    @input="onUserInput"
                  />
                  <span class="field__scan" aria-hidden="true" />
                </span>
                <span class="field__err" role="alert">{{ errUser }}</span>
              </label>

              <label class="field" :class="{ 'is-error': !!errPwd }">
                <span class="field__k">访问口令</span>
                <span class="field__box">
                  <svg class="field__ico" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <rect x="4.5" y="10" width="15" height="9.5" rx="2.4" stroke="currentColor" stroke-width="1.5" />
                    <path d="M8.2 10V7.6a3.8 3.8 0 0 1 7.6 0V10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                    <circle cx="12" cy="14.7" r="1.3" fill="currentColor" />
                  </svg>
                  <input
                    id="password"
                    v-model="password"
                    name="password"
                    :type="showPwd ? 'text' : 'password'"
                    placeholder="请输入访问口令"
                    autocomplete="current-password"
                    @input="onPwdInput"
                  />
                  <button
                    type="button"
                    class="field__eye"
                    id="eye"
                    :class="{ 'is-on': showPwd }"
                    aria-label="显示或隐藏口令"
                    @click="showPwd = !showPwd"
                  >
                    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M2.6 12S6.2 5.8 12 5.8 21.4 12 21.4 12 17.8 18.2 12 18.2 2.6 12 2.6 12Z" stroke="currentColor" stroke-width="1.5" />
                      <circle cx="12" cy="12" r="2.9" stroke="currentColor" stroke-width="1.5" />
                    </svg>
                  </button>
                  <span class="field__scan" aria-hidden="true" />
                </span>
                <span class="field__err" role="alert">{{ errPwd }}</span>
              </label>

              <!-- 图形验证码：输入框与图片并排，点图片换一张 -->
              <label class="field field--captcha" :class="{ 'is-error': !!errCaptcha }">
                <span class="field__k">图形验证码</span>
                <span class="field__row">
                  <span class="field__box">
                    <svg class="field__ico" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M12 3.2 19.2 6v6c0 4-3 7-7.2 9.3C7.8 19 4.8 16 4.8 12V6L12 3.2Z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round" />
                      <path d="M9.2 12.2 11.4 14.4 15.2 9.8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                    <input
                      id="captcha"
                      v-model="captchaCode"
                      name="captchaCode"
                      type="text"
                      inputmode="text"
                      maxlength="8"
                      placeholder="请输入图中字符"
                      autocomplete="off"
                      autocapitalize="off"
                      spellcheck="false"
                      @input="onCaptchaInput"
                    />
                    <span class="field__scan" aria-hidden="true" />
                  </span>

                  <img
                    v-if="captchaImage"
                    class="captcha"
                    :class="{ 'is-loading': captchaLoading }"
                    :src="captchaImage"
                    alt="图形验证码，点击刷新"
                    title="看不清？点击换一张"
                    role="button"
                    tabindex="0"
                    @click="loadCaptcha"
                    @keydown.enter.prevent="loadCaptcha"
                    @keydown.space.prevent="loadCaptcha"
                  />
                  <button
                    v-else
                    type="button"
                    class="captcha captcha--empty"
                    :disabled="captchaLoading"
                    title="点击重新获取验证码"
                    @click="loadCaptcha"
                  >
                    {{ captchaLoading ? '加载中…' : '点击加载' }}
                  </button>
                </span>
                <span class="field__err" role="alert">{{ errCaptcha }}</span>
              </label>

              <div class="row">
                <label class="check">
                  <input type="checkbox" id="remember" v-model="remember" />
                  <span class="check__box" aria-hidden="true">
                    <svg viewBox="0 0 16 16" fill="none"><path d="M3.4 8.4 6.6 11.6 12.7 4.8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></svg>
                  </span>
                  <span>记住此设备</span>
                </label>
                <a
                  class="link"
                  id="forgot"
                  href="#"
                  @click.prevent="toast('口令重置需通过<b>统一权限中心</b>发起，或联系组织管理员')"
                >
                  忘记口令
                </a>
              </div>

              <!-- 表单级错误：账号锁定 / 超过30天未登录 / 后端不可达 -->
              <p v-if="formError" class="formerr" role="alert" aria-live="polite">{{ formError }}</p>

              <button
                type="submit"
                class="btn"
                id="submit"
                :class="{ 'is-loading': loading }"
                :disabled="loading"
              >
                <span class="btn__label">{{ btnLabel }}</span>
                <span class="btn__arrow" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none"><path d="M5 12h13M12.5 6.2 18.4 12l-5.9 5.8" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" /></svg>
                </span>
                <span class="btn__load" aria-hidden="true" />
              </button>
            </form>
          </div>

          <div class="card__foot">
            <span>登录即表示同意</span>
            <a href="#" @click.prevent="toast('演示页面 · 目标内容尚未配置')">平台使用协议</a><span>·</span><a href="#" @click.prevent="toast('演示页面 · 目标内容尚未配置')">安全与隐私条款</a>
          </div>

          <div class="done" id="done" :class="{ 'is-on': doneOn }" :aria-hidden="!doneOn">
            <span class="done__ring" aria-hidden="true" />
            <svg class="done__ico" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M5.5 12.6 10 17.1 18.8 7.4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <p class="done__msg" id="done-msg">{{ doneMsg }}</p>
            <span class="done__bar" aria-hidden="true" />
          </div>
        </div>
      </section>
    </main>

    <div class="toast" id="toast" role="status" aria-live="polite" :class="{ 'is-on': toastOn }" v-html="toastHtml" />
  </div>
</template>
