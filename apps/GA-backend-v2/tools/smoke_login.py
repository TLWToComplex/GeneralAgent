"""真实 HTTP 冒烟：对着运行中的服务把登录链路跑一遍。

配合 ``tools/dev_sqlite_server.py --seed`` 使用（该脚本会预置固定答案的联调验证码，
否则随机验证码无法被外部脚本得知）：

    python tools/dev_sqlite_server.py --seed --port 8038
    python tools/smoke_login.py --base-url http://127.0.0.1:8038

覆盖 6 段：系统接口 → 验证码 → 登录分支 → 鉴权 → 改密 → 内部映射接口（供 proxy 调用）。
最后一段需要 ``--seed``（预置 ``demo → http://127.0.0.1:8083/`` 的映射）以及与
``tools/dev_sqlite_server.py`` 相同的内部接口密钥（默认 ``dev-internal-secret``，
可用 ``--internal-secret`` 覆盖）。

脚本可重复执行：改密环节会在演示账号上改成一个新的随机密码，并把该密码记到
``data/smoke_state.json``，下一次运行直接从这里读取，不需要还原密码
（「密码不能与近5次历史密码相同」这条规则本身也不允许把密码改回刚用过的值）。
想回到初始状态：停掉服务、删除 ``data/`` 目录，再重新 ``--seed`` 启动。

退出码 0 表示全部通过；任一断言失败即非 0 退出。
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]

#: 与 tools/dev_sqlite_server.py 保持一致
DEV_CAPTCHA_ID_PREFIX = "demo-captcha"
DEV_CAPTCHA_CODE = "ABCD"
DEV_CAPTCHA_COUNT = 50
DEV_USERNAME = "demo"
DEV_PASSWORD = "Kp!3RzT7Vm"
#: 默认管理员账号
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Aa123456"
#: 演示账号当前密码的落地文件（相对仓库根）
DEFAULT_STATE_FILE = "data/smoke_state.json"

# ---- 内部映射接口（供前置代理调用）与 tools/dev_sqlite_server.py 保持一致 ----
#: 携带共享密钥的请求头
INTERNAL_TOKEN_HEADER = "X-Internal-Token"
#: dev_sqlite_server 未配置 dsh.internal_secret 时使用的联调密钥
DEV_INTERNAL_SECRET = "dev-internal-secret"
#: --seed 预置的 dsh 实例
DEV_DSH_CONTAINER = "dsh-web-demo"
DEV_DSH_HOST = "127.0.0.1"
DEV_DSH_PORT = 8083


def fresh_password() -> str:
    """生成一个满足密码策略、且大概率没被用过的新密码。

    注意两个约束：连续数字/字母序列会被策略拒绝，因此只用两位随机数字；
    且两位数字天然不会与 ``DEV_PASSWORD``（Kp!3RzT7Vm）相同。
    """
    return f"Kp!{random.randint(10, 98)}RzT7Vm"


class Smoke:
    def __init__(
        self,
        base_url: str,
        captcha_prefix: str,
        captcha_code: str,
        count: int,
        state_file: Path,
        internal_secret: str,
    ) -> None:
        self.client = httpx.Client(base_url=base_url, timeout=15.0)
        self.captcha_prefix = captcha_prefix
        self.captcha_code = captcha_code
        self.captcha_cursor = 0
        self.captcha_count = count
        self.state_file = state_file
        self.internal_secret = internal_secret
        self.passed = 0
        self.failed: list[str] = []

    # ------------------------------------------------------------ 状态文件
    def load_state(self) -> dict:
        if self.state_file.is_file():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def save_state(self, **updates) -> None:
        state = self.load_state()
        state.update(updates)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def resolve_demo_password(self) -> str:
        """演示账号当前密码：优先取状态文件（上次冒烟改成的密码），其次取种子密码。"""
        return self.load_state().get("demo_password") or DEV_PASSWORD

    # ------------------------------------------------------------ 断言辅助
    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed.append(name)
            print(f"  [FAIL] {name} {detail}")

    def check_status(self, name: str, response, expected: int) -> None:
        self.check(
            f"{name} -> HTTP {expected}",
            response.status_code == expected,
            f"实际 {response.status_code} {response.text[:200]}",
        )

    def check_error(self, name: str, response, status: int, message: str) -> None:
        ok = response.status_code == status and response.json() == {"error": message}
        self.check(f"{name} -> {status} {message}", ok, f"实际 {response.status_code} {response.text[:200]}")

    def check_internal_error(self, name: str, response, status: int, message: str) -> None:
        """内部接口的错误体是 ``{code, message}``（与成功体同构），不是登录接口的 ``{error}``。"""
        ok = response.status_code == status and response.json() == {"code": status, "message": message}
        self.check(f"{name} -> {status} {message}", ok, f"实际 {response.status_code} {response.text[:200]}")

    # ------------------------------------------------------------ 业务辅助
    def next_captcha(self) -> str | None:
        while self.captcha_cursor < self.captcha_count:
            captcha_id = f"{self.captcha_prefix}-{self.captcha_cursor}"
            self.captcha_cursor += 1
            return captcha_id
        return None

    def login(
        self,
        username: str,
        password: str,
        *,
        code: str | None = None,
        captcha_id: str | None = None,
    ):
        """登录；验证码是一次性的，若取到已消费的 id 就自动换下一个。"""
        attempts = 1 if captcha_id else self.captcha_count
        response = None
        for _ in range(attempts):
            current_id = captcha_id or self.next_captcha()
            if current_id is None:
                raise RuntimeError(
                    "联调验证码已用尽，请重启 tools/dev_sqlite_server.py --seed"
                )
            response = self.client.post(
                "/aiUser/login",
                json={
                    "username": username,
                    "password": password,
                    "captchaId": current_id,
                    "captchaCode": code if code is not None else self.captcha_code,
                },
            )
            if captcha_id or response.json().get("error") != "验证码已过期，请重新获取":
                return response
        return response

    def login_ok(self, username: str, password: str) -> dict:
        response = self.login(username, password)
        if response.status_code != 200:
            raise RuntimeError(f"登录 {username} 失败: {response.status_code} {response.text}")
        return response.json()

    @staticmethod
    def headers(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------ 各阶段
    def run_system(self) -> None:
        print("\n[1] 系统接口")
        health = self.client.get("/health")
        self.check_status("GET /health", health, 200)
        self.check("health.status == ok", health.json().get("status") == "ok")

        root = self.client.get("/")
        self.check_status("GET /", root, 200)
        self.check("root.service", root.json().get("service") == "GA-backend-v2")

    def run_captcha(self) -> None:
        print("\n[2] 验证码接口")
        response = self.client.get("/captcha")
        self.check_status("GET /captcha", response, 200)
        body = response.json()
        self.check("captcha 响应结构", body.get("code") == 200 and body.get("message") == "success")
        data = body.get("data", {})
        self.check("captchaId 非空", bool(data.get("captchaId")))
        self.check(
            "captchaImage 为 PNG dataURL",
            str(data.get("captchaImage", "")).startswith("data:image/png;base64,"),
        )

    def run_login_branches(self) -> str:
        print("\n[3] 登录分支")
        wrong_captcha = self.login(ADMIN_USERNAME, ADMIN_PASSWORD, code="ZZZZ")
        self.check_error("验证码错误", wrong_captcha, 401, "验证码错误")

        wrong_body = self.client.post(
            "/aiUser/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
        )
        self.check_error("缺少 captchaId", wrong_body, 400, "captchaId为必填字段")

        non_json = self.client.post(
            "/aiUser/login", content="username=admin", headers={"Content-Type": "text/plain"}
        )
        self.check_error("非 JSON 请求体", non_json, 400, "请求体必须为JSON格式")

        unknown = self.login("nobody", ADMIN_PASSWORD)
        self.check_error("用户不存在", unknown, 401, "用户名或邮箱无效")

        wrong_password = self.login(ADMIN_USERNAME, "WrongPass!1")
        # 精确的「还剩 N 次」编号由单元测试保证；冒烟只校验文案形态，
        # 这样在非全新数据库上重复执行也不会误报。
        self.check(
            "密码错误提示（还剩 N 次机会）",
            wrong_password.status_code == 401
            and re.fullmatch(r"密码错误，还剩\d+次机会", wrong_password.json().get("error", "")) is not None,
            wrong_password.text,
        )

        success = self.login(ADMIN_USERNAME, ADMIN_PASSWORD)
        self.check_status("密码正确（并清零失败计数）", success, 200)
        body = success.json()
        self.check("登录响应结构", body.get("status") == "success" and body.get("message") == "登录成功")
        self.check("token 非空", bool(body.get("token")))
        self.check("passwordExpiredWarning 存在", "passwordExpiredWarning" in body)
        user = body.get("user", {})
        self.check("用户信息不含密码", "password" not in user)
        self.check("additional_info 已平铺", "additional_info" not in user and "last_login_time" in user)
        return body["token"]

    def run_auth_guard(self, admin_token: str, demo_uuid: str, demo_token: str) -> None:
        print("\n[4] 鉴权")
        guard_body = {"uuid": demo_uuid, "old_password": DEV_PASSWORD, "new_password": fresh_password()}
        no_token = self.client.post("/aiUser/changePassword", json=guard_body)
        self.check("无令牌 401 响应体", no_token.status_code == 401 and no_token.json() == {"message": "Bearer令牌缺失", "code": 401}, no_token.text)

        bad_token = self.client.post(
            "/aiUser/changePassword", json=guard_body, headers=self.headers("not-a-jwt")
        )
        self.check("非法令牌 401 响应体", bad_token.status_code == 401 and bad_token.json() == {"message": "Bearer令牌无效", "code": 401}, bad_token.text)

        non_admin = self.client.post(
            "/aiUser/unlockAccount", json={"uuid": demo_uuid}, headers=self.headers(demo_token)
        )
        self.check(
            "非管理员 403 响应体",
            non_admin.status_code == 403 and non_admin.json() == {"code": 403, "message": "权限不足，仅管理员可访问"},
            non_admin.text,
        )

        admin_self = self.client.post(
            "/aiUser/unlockAccount", json={"uuid": demo_uuid}, headers=self.headers(admin_token)
        )
        self.check_status("管理员解锁未锁定账号", admin_self, 200)
        self.check("解锁提示语", admin_self.json().get("message") == "该账号未被锁定，无需解锁")

        missing_uuid = self.client.post(
            "/aiUser/unlockAccount", json={}, headers=self.headers(admin_token)
        )
        self.check_error("缺少 uuid", missing_uuid, 400, "uuid为必填字段")

        unknown_uuid = self.client.post(
            "/aiUser/unlockAccount",
            json={"uuid": "00000000-0000-0000-0000-000000000000"},
            headers=self.headers(admin_token),
        )
        self.check_error("解锁不存在的用户", unknown_uuid, 404, "用户不存在")

    def run_change_password(
        self,
        demo_uuid: str,
        demo_token: str,
        demo_password: str,
        admin_uuid: str,
        admin_token: str,
    ) -> None:
        """在演示账号上验证改密：改成随机新密码并记入状态文件，不还原旧密码。"""
        print("\n[5] 修改密码")
        wrong_old = self.client.post(
            "/aiUser/changePassword",
            json={"uuid": demo_uuid, "old_password": "WrongPass!1", "new_password": fresh_password()},
            headers=self.headers(demo_token),
        )
        self.check_error("旧密码不正确", wrong_old, 401, "旧密码不正确")

        weak = self.client.post(
            "/aiUser/changePassword",
            json={"uuid": demo_uuid, "old_password": demo_password, "new_password": "short"},
            headers=self.headers(demo_token),
        )
        self.check_error("弱密码被拒", weak, 400, "密码长度不能少于10位")

        # 历史密码规则会让「改用过的密码」被拒；重复冒烟时换一个继续，
        # 因此这里循环尝试，命中的那次本身就证明规则生效。
        new_password = ""
        changed = None
        for _ in range(5):
            candidate = fresh_password()
            changed = self.client.post(
                "/aiUser/changePassword",
                json={"uuid": demo_uuid, "old_password": demo_password, "new_password": candidate},
                headers=self.headers(demo_token),
            )
            if changed.json().get("error") == "密码不能与近5次历史密码相同":
                continue
            new_password = candidate
            break

        self.check_status("改密成功", changed, 200)
        self.check("改密响应体", changed.json() == {"status": "success", "message": "密码更新成功"})

        # 先成功登录一次把失败计数清零，再验证旧密码失效
        relogin = self.login(DEV_USERNAME, new_password)
        self.check_status("新密码可登录", relogin, 200)
        stale = self.login(DEV_USERNAME, demo_password)
        self.check(
            "旧密码已失效（还剩 N 次机会）",
            stale.status_code == 401
            and re.fullmatch(r"密码错误，还剩\d+次机会", stale.json().get("error", "")) is not None,
            stale.text,
        )

        if changed.status_code == 200:
            # 不还原旧密码：一是会被「近5次历史密码」规则拒绝，
            # 二是重复执行时也无从得知上一次的密码，因此记到状态文件里
            self.save_state(demo_password=new_password)
            print(f"  [INFO] 演示账号新密码已记入 {self.state_file}")

        # 默认管理员初始密码 Aa123456 不满足密码策略（老项目同样如此），
        # 因此无法通过接口把密码改回该值——这里把这个既有约束固化下来。
        admin_restore = self.client.post(
            "/aiUser/changePassword",
            json={
                "uuid": admin_uuid,
                "old_password": ADMIN_PASSWORD,
                "new_password": ADMIN_PASSWORD,
            },
            headers=self.headers(admin_token),
        )
        self.check_error("默认管理员初始密码不满足策略（老项目同款约束）", admin_restore, 400, "密码长度不能少于10位")

    def run_internal_route(self, demo_uuid: str) -> None:
        """[6] 内部映射接口：前置代理按用户名/uuid 换取 dsh 实例的反代目标。

        这一段是「登录打通」与「新建会话进 dsh」之间的接缝：接口只负责把映射查出来，
        真正的反代由 proxy 完成。403（映射已停用）需要改库，只在单元测试里覆盖。
        """
        print("\n[6] 内部映射接口（供 proxy 调用）")
        url = "/internal/dsh/route"
        auth = {INTERNAL_TOKEN_HEADER: self.internal_secret}

        missing = self.client.get(url, params={"username": DEV_USERNAME})
        self.check_internal_error("缺密钥", missing, 401, "内部接口令牌缺失")

        wrong = self.client.get(
            url, params={"username": DEV_USERNAME}, headers={INTERNAL_TOKEN_HEADER: "not-the-secret"}
        )
        self.check_internal_error("密钥不对", wrong, 401, "内部接口令牌无效")

        neither = self.client.get(url, headers=auth)
        self.check_internal_error("username / uuid 都不给", neither, 400, "username与uuid必须且只能提供一个")

        both = self.client.get(url, params={"username": DEV_USERNAME, "uuid": demo_uuid}, headers=auth)
        self.check_internal_error("username 与 uuid 同时给", both, 400, "username与uuid必须且只能提供一个")

        by_name = self.client.get(url, params={"username": DEV_USERNAME}, headers=auth)
        self.check_status("按用户名查询", by_name, 200)
        if by_name.status_code != 200:
            self.check(
                "映射已预置",
                False,
                f"查询未命中：{by_name.text[:200]}；请确认服务是用 --seed 启动的，"
                f"且 --internal-secret 与 dsh.internal_secret 一致",
            )
            return

        data = by_name.json().get("data", {})
        self.check("username 以账号表为准回填", data.get("username") == DEV_USERNAME, str(data))
        self.check("containerName", data.get("containerName") == DEV_DSH_CONTAINER, str(data))
        self.check("proxyUser", data.get("proxyUser") == DEV_USERNAME, str(data))
        self.check(
            "host / port",
            data.get("host") == DEV_DSH_HOST and data.get("port") == DEV_DSH_PORT,
            str(data),
        )
        self.check(
            "target 可直接用于反代",
            data.get("target") == f"http://{DEV_DSH_HOST}:{DEV_DSH_PORT}/",
            str(data.get("target")),
        )
        self.check("status == 1（启用）", data.get("status") == 1, str(data.get("status")))
        self.check(
            "tokenFile 为 null（由代理自行推导）",
            data.get("tokenFile") is None,
            str(data.get("tokenFile")),
        )

        by_uuid = self.client.get(url, params={"uuid": demo_uuid}, headers=auth)
        self.check_status("按 uuid 查询", by_uuid, 200)
        self.check(
            "两种查法结果一致",
            by_uuid.json().get("data", {}).get("port") == data.get("port"),
            by_uuid.text[:200],
        )

        unknown = self.client.get(url, params={"username": "nobody"}, headers=auth)
        self.check_internal_error("用户不存在", unknown, 404, "用户不存在或已删除")

        unmapped = self.client.get(url, params={"username": ADMIN_USERNAME}, headers=auth)
        self.check_internal_error("用户存在但未登记实例", unmapped, 404, "该用户未登记 dsh 实例")

    def run(self) -> int:
        self.run_system()
        self.run_captcha()
        self.run_login_branches()

        print("\n[4'] 演示账号登录（用于非管理员分支）")
        demo_password = self.resolve_demo_password()
        demo = self.login(DEV_USERNAME, demo_password)
        if demo.status_code != 200:
            raise RuntimeError(
                f"登录 {DEV_USERNAME} 失败: {demo.status_code} {demo.text}\n"
                f"若演示账号密码已被改动，请删除 data/ 目录后重启 "
                f"tools/dev_sqlite_server.py --seed"
            )
        demo = demo.json()
        demo_uuid = demo["user"]["uuid"]
        self.check("演示账号登录成功", bool(demo_uuid))

        admin_user = self.login_ok(ADMIN_USERNAME, ADMIN_PASSWORD)
        self.run_auth_guard(admin_user["token"], demo_uuid, demo["token"])
        self.run_change_password(
            demo_uuid,
            demo["token"],
            demo_password,
            admin_user["user"]["uuid"],
            admin_user["token"],
        )
        self.run_internal_route(demo_uuid)

        print(f"\n===== 冒烟结果：通过 {self.passed} 项，失败 {len(self.failed)} 项 =====")
        for name in self.failed:
            print(f"  - {name}")
        return 1 if self.failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="登录链路真实 HTTP 冒烟")
    parser.add_argument("--base-url", default="http://127.0.0.1:8038")
    parser.add_argument("--captcha-id-prefix", default=DEV_CAPTCHA_ID_PREFIX)
    parser.add_argument("--captcha-code", default=DEV_CAPTCHA_CODE)
    parser.add_argument("--captcha-count", type=int, default=DEV_CAPTCHA_COUNT)
    parser.add_argument(
        "--state-file",
        default=DEFAULT_STATE_FILE,
        help="记录演示账号当前密码的本地文件（相对仓库根）",
    )
    parser.add_argument(
        "--internal-secret",
        default=DEV_INTERNAL_SECRET,
        help="内部映射接口的共享密钥（对应服务端 dsh.internal_secret）",
    )
    args = parser.parse_args()

    state_file = Path(args.state_file)
    if not state_file.is_absolute():
        state_file = REPO_ROOT / state_file

    smoke = Smoke(
        args.base_url,
        args.captcha_id_prefix,
        args.captcha_code,
        args.captcha_count,
        state_file,
        args.internal_secret,
    )
    try:
        return smoke.run()
    except Exception as exc:  # 连接失败、服务未启动等
        print(f"\n冒烟中断: {exc}")
        return 2
    finally:
        smoke.client.close()


if __name__ == "__main__":
    sys.exit(main())