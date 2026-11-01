/* ============================================================================
   前置代理（proxy）的配置文件 —— 模板

   用法（本地）：
     cp config.example.js config.js      # 然后按环境改 config.js（它已 gitignore）

   用法（Docker）：把宿主机那份挂进来即可，不必打进镜像：
     docker run -d --name dsh-proxy --network host \
       -v /opt/dsh/proxy-config.js:/app/config.js \
       -v /opt/dsh/tokens.d:/app/tokens.d \
       dsh-proxy

   也可以用别的位置：node server.js --config /etc/dsh/proxy.js

   本文件是一个普通的 CommonJS 模块（module.exports 一个对象），所以能写注释、
   能算表达式；改完**重启进程**生效。每一项都可以省略，省略即用注释里写的默认值。
   服务器不读任何环境变量 —— 配置只有一个来源，就是这个文件。
   ========================================================================== */
module.exports = {
  /* 【必填】与后端 config/config.yaml 的 dsh.internal_secret（或后端的
     DSH_INTERNAL_SECRET）完全相同；留空代理会拒绝启动。
     它只在本机 ↔ 后端之间使用，浏览器看不到。 */
  internalSecret: '',

  /* 监听端口。默认 80。
     Linux 绑 80 需要 root 或 setcap；Windows 需要管理员权限。
     本地没有权限就改成 8080，同时把前端 .env.local 的
     VITE_DSH_PROXY_BASE 改成 http://<host>:8080。 */
  port: 80,

  /* 后端地址（默认 http://127.0.0.1:8038）。代理由此调用
     GET /internal/dsh/route 校验「用户 → dsh 实例」映射。 */
  backendBaseUrl: 'http://127.0.0.1:8038',

  /* 浏览器地址栏看到的源，默认 http://172.16.235.50。
     用途：转发时会把 Origin/Sec-Fetch-* 删掉（回环改写需要），所以必须在这里
     先把「哪些源算自己人」说清楚 —— 子资源/fetch 的 Origin 不匹配会被 403。 */
  entryOrigin: 'http://172.16.235.50',

  /* 出错页「回到登录页」的链接。留空 = 由 entryOrigin 推导成
     <entryOrigin>:5173/#/login */
  frontendLoginUrl: '',

  /* dsh 启动令牌目录（dsh-new.sh 写入；后端下发了 tokenFile 时以它为准）。
     相对路径以**本文件所在目录**为基准。 */
  tokensDir: './tokens.d',

  /* dsh 会话缓存文件。相对路径同上。 */
  sessionsFile: './sessions.json',

  /* 「用户 → dsh 实例」映射的缓存毫秒数，默认 30000。
     设 0 = 每次请求都查后端（改了映射表的端口能立即生效）。 */
  routeCacheTtlMs: 30000,

  /* 签发 dsh_user cookie 的密钥。留空 = 每次启动随机生成。
     随机的代价：代理重启后用户需要从控制台重新点一次「新建会话」；
     配固定值则重启后旧标签页仍然有效。 */
  cookieSecret: '',

  /* 入口在 HTTPS 后面时置 true，给 cookie 加 Secure。 */
  cookieSecure: false,
}