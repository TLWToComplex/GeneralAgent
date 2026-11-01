#Requires -Version 5.1
<#
.SYNOPSIS
  把 pip / npm / pnpm / uv / conda 的包源地址一次性替换为内网 mirror hub，并可一键回滚。

.DESCRIPTION
  改动的文件（全部为用户级，不改系统目录）：
    %APPDATA%\pip\pip.ini             pip（含 DSH 桌面版自带 Python 的 pip，两者读同一份用户配置）
    %USERPROFILE%\.npmrc              npm / pnpm / yarn(npm 协议)
    %USERPROFILE%\.condarc            仅当显式给了 -CondaChannel
    %USERPROFILE%\.dsh\.env           DSH 专属环境变量层（PIP_* / NPM_CONFIG_* / UV_* / NO_PROXY）
                                      改完需重启 DSH 桌面版；散装工具用 -PersistUserEnv 才生效

  设计要点：
    * 写入前先备份为 <文件>.bak-<时间戳>，-Revert 可回滚。
    * 默认先做连通性预检，两个源都不通就不动任何文件（除非 -Force）。
    * 幂等：重复执行不会产生重复行，已有其它键（超时、认证）原样保留。
    * 不会改 PATH / SSL_CERT_FILE / NODE_EXTRA_CA_CERTS 这类 DSH bootstrap 名
      （它们写进 .env 会让 DSH 启动直接报错，企业 CA 请用系统级环境变量）。

.EXAMPLE
  # 1) 先看计划，不写盘
  .\setup-internal-mirror.ps1 -HubBase http://172.16.234.96:8081 -DryRun

  # 1b) 只检查连通性与当前实际生效的源，不写盘
  .\setup-internal-mirror.ps1 -HubBase http://172.16.234.96:8081 -CheckOnly

  # 2) 正式执行（Nexus 形态）
  .\setup-internal-mirror.ps1 -HubBase http://172.16.234.96:8081 `
      -PipPath /repository/pypi-proxy/simple -NpmPath /repository/npm-proxy/

  # 3) https 自签证书
  .\setup-internal-mirror.ps1 -HubBase https://hub.corp.local -Insecure

  # 4) 让散装工具（终端里的 uv 等）也生效
  .\setup-internal-mirror.ps1 -HubBase http://172.16.234.96:8081 -PersistUserEnv

  # 5) 回滚
  .\setup-internal-mirror.ps1 -Revert
#>
[CmdletBinding()]
param(
    # ======== 必改：内网 mirror hub 基地址 ========
    [string]$HubBase = 'http://172.16.234.96:8081',

    # ======== 各生态的路径（按 hub 实际形态改；Nexus3 默认如下）========
    [string]$PipPath = '/repository/pypi-proxy/simple',
    [string]$NpmPath = '/repository/npm-proxy/',

    # ======== 以下为可选覆盖：直接给完整 URL 时优先于 HubBase + Path ========
    [string]$PipIndexUrl = '',
    [string]$NpmRegistry = '',

    # ======== 可选：其它生态 ========
    # 内网 conda channel，例：http://172.16.234.96:8081/repository/anaconda-main/
    [string]$CondaChannel = '',
    # uv 安装 Python 本体的镜像（默认走 github.com/astral-sh，内网必改），例：http://hub/pbs/
    [string]$UvPythonMirror = '',

    # ======== 可选：认证与证书 ========
    # 写进 ~/.npmrc 的 //host/path/:_authToken=<值>（不要把 token 放环境变量：DSH 会把名字含 TOKEN/KEY/PASSWORD/SECRET 的环境变量从 agent 子进程里清掉）
    [string]$NpmAuthToken = '',
    # 额外 trusted-host，逗号分隔
    [string]$PipTrustedHostExtra = '',
    # 自签 https：关闭 pip/uv/npm/conda 的 TLS 校验
    [switch]$Insecure,

    # ======== 行为开关 ========
    # 同时写入用户级环境变量（对终端里所有工具生效；不写就只有 pip.ini/.npmrc/DSH 生效）
    [switch]$PersistUserEnv,
    # NO_PROXY 条目，留空 = 自动用 hub 主机名（避免内网地址被公司代理转发）
    [string[]]$NoProxy = @(),
    # 跳过连通性预检与执行后的自检
    [switch]$SkipVerify,
    # 真实下载一个小包/查一个包版本，端到端验证
    [switch]$SmokeTest,
    # 只打印计划，不写任何文件
    [switch]$DryRun,
    # 从最早一次备份回滚
    [switch]$Revert,
    # 预检不通也照写
    [switch]$Force,
    # 只检查连通性与当前生效值，不写盘
    [switch]$CheckOnly,
    # 批处理包装传入，本脚本忽略
    [switch]$NoPause,

    # ======== 测试 / 离线生成用：覆盖落点目录 ========
    [string]$AppDataDir = '',
    [string]$UserProfileDir = '',
    [string]$DshHome = '',
    # 指定 python 解释器用于自检，默认自动探测
    [string]$PythonExe = ''
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
if ($Insecure) {
    # 只影响本脚本进程的 HTTPS 校验
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
}

# ------------------------------------------------------------------ 输出
function Write-Step { param([string]$Text) Write-Host ''; Write-Host "-- $Text" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Text) Write-Host "   [ok]   $Text" -ForegroundColor Green }
function Write-Warn2{ param([string]$Text) Write-Host "   [warn] $Text" -ForegroundColor Yellow }
function Write-Err  { param([string]$Text) Write-Host "   [fail] $Text" -ForegroundColor Red }
function Write-Info { param([string]$Text) Write-Host "          $Text" }

# ------------------------------------------------------------------ 文件工具
function Write-TextFile {
    param([string]$Path, [string]$Text)
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    $enc = New-Object System.Text.UTF8Encoding($false)   # 不要 BOM：.env / .npmrc 的首行键名不能被污染
    [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

# 把 "键=值" 文件（.env / .npmrc）合并成新内容；值为 $null 或空串表示删除该键
function Merge-KeyValues {
    param([string]$Text, [System.Collections.Specialized.OrderedDictionary]$Changes)
    $lines = @()
    if ($Text) { $lines = $Text -split "`r?`n" }
    $out = New-Object System.Collections.Generic.List[string]
    $applied = @{}
    foreach ($line in $lines) {
        $hit = $null
        foreach ($k in $Changes.Keys) {
            if ($line -match ('^\s*(?:export\s+)?' + [regex]::Escape([string]$k) + '\s*=')) { $hit = $k; break }
        }
        if ($null -ne $hit) {
            if (-not $applied.ContainsKey($hit)) {
                $v = $Changes[$hit]
                if ($null -ne $v -and "$v" -ne '') { $out.Add("$hit=$v") }
                $applied[$hit] = $true
            }
            continue
        }
        $out.Add($line)
    }
    foreach ($k in $Changes.Keys) {
        if ($applied.ContainsKey($k)) { continue }
        $v = $Changes[$k]
        if ($null -ne $v -and "$v" -ne '') { $out.Add("$k=$v") }
    }
    while ($out.Count -gt 0 -and $out[0].Trim() -eq '') { $out.RemoveAt(0) }
    while ($out.Count -gt 0 -and $out[$out.Count - 1].Trim() -eq '') { $out.RemoveAt($out.Count - 1) }
    return (($out -join "`r`n") + "`r`n")
}

# 把待新增的 INI 键插到 section 内容的末尾（即紧邻下一节之前的空行之上），而不是塞到空行之后
function Add-PendingIniKeys {
    param(
        [System.Collections.Generic.List[string]]$Out,
        [int]$HeaderEnd,
        [System.Collections.Specialized.OrderedDictionary]$Changes,
        [hashtable]$Applied
    )
    $ins = $Out.Count
    while ($ins -gt $HeaderEnd -and $Out[$ins - 1].Trim() -eq '') { $ins-- }
    foreach ($k in $Changes.Keys) {
        if ($Applied.ContainsKey($k)) { continue }
        $v = $Changes[$k]
        if ($null -ne $v -and "$v" -ne '') {
            $Out.Insert($ins, "$k = $v")
            $ins++
        }
        $Applied[$k] = $true
    }
}

# 把 INI 某个 section 内的键合并成新内容；值为 $null 或空串表示删除该键
function Merge-IniSection {
    param([string]$Text, [string]$Section, [System.Collections.Specialized.OrderedDictionary]$Changes)
    $lines = @()
    if ($Text) { $lines = $Text -split "`r?`n" }
    $out = New-Object System.Collections.Generic.List[string]
    $inSec = $false; $secSeen = $false; $applied = @{}; $secHeaderEnd = -1
    foreach ($line in $lines) {
        $t = $line.Trim()
        if ($t -match '^\[(.+?)\]\s*$') {
            if ($inSec) { Add-PendingIniKeys -Out $out -HeaderEnd $secHeaderEnd -Changes $Changes -Applied $applied }
            $name = ([string]$Matches[1]).Trim()
            $inSec = ($name -ieq $Section)
            if ($inSec) { $secSeen = $true }
            $out.Add($line)
            if ($inSec) { $secHeaderEnd = $out.Count }
            continue
        }
        if ($inSec) {
            $hit = $null
            foreach ($k in $Changes.Keys) {
                if ($t -match ('^' + [regex]::Escape([string]$k) + '\s*=')) { $hit = $k; break }
            }
            if ($null -ne $hit) {
                if (-not $applied.ContainsKey($hit)) {
                    $v = $Changes[$hit]
                    if ($null -ne $v -and "$v" -ne '') { $out.Add("$hit = $v") }
                    $applied[$hit] = $true
                }
                continue
            }
        }
        $out.Add($line)
    }
    if ($inSec) { Add-PendingIniKeys -Out $out -HeaderEnd $secHeaderEnd -Changes $Changes -Applied $applied }
    if (-not $secSeen) {
        while ($out.Count -gt 0 -and $out[$out.Count - 1].Trim() -eq '') { $out.RemoveAt($out.Count - 1) }
        if ($out.Count -gt 0) { $out.Add('') }
        $out.Add("[$Section]")
        foreach ($k in $Changes.Keys) {
            $v = $Changes[$k]
            if ($null -ne $v -and "$v" -ne '') { $out.Add("$k = $v") }
        }
    }
    while ($out.Count -gt 0 -and $out[$out.Count - 1].Trim() -eq '') { $out.RemoveAt($out.Count - 1) }
    return (($out -join "`r`n") + "`r`n")
}

function Get-ExistingValue {
    param([string]$Text, [string]$Key)
    if (-not $Text) { return '' }
    foreach ($line in ($Text -split "`r?`n")) {
        if ($line -match ('^\s*(?:export\s+)?' + [regex]::Escape([string]$Key) + '\s*=\s*(.*)$')) { return ([string]$Matches[1]).Trim() }
    }
    return ''
}

# 直连（不使用系统代理）探测一个 URL；401/403 也算可达
function Test-MirrorUrl {
    param([string]$Url, [int]$TimeoutMs = 8000)
    try {
        $req = [System.Net.HttpWebRequest]::Create($Url)
        $req.Method = 'GET'
        $req.Timeout = $TimeoutMs
        $req.ReadWriteTimeout = $TimeoutMs
        $req.Proxy = $null
        $req.UserAgent = 'dsh-mirror-setup/1.0'
        $resp = $req.GetResponse()
        $code = [int]$resp.StatusCode
        $resp.Close()
        return [pscustomobject]@{ Ok = $true; Detail = ('HTTP ' + $code) }
    } catch [System.Net.WebException] {
        $r = $_.Exception.Response
        if ($r) {
            $code = [int]$r.StatusCode
            $r.Close()
            return [pscustomobject]@{ Ok = $true; Detail = ('HTTP ' + $code + '（可达，可能需认证）') }
        }
        return [pscustomobject]@{ Ok = $false; Detail = $_.Exception.Message }
    } catch {
        return [pscustomobject]@{ Ok = $false; Detail = $_.Exception.Message }
    }
}

# 生效自检：打印 pip / npm 实际解析到的源
function Invoke-SelfCheck {
    param([string]$PythonExe, [switch]$RunSmoke, [string]$Stamp)
    Write-Step '生效自检'
    if (-not $PythonExe) {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($cmd) { $PythonExe = $cmd.Source }
    }
    if ($PythonExe) {
        $out = & $PythonExe -m pip config list 2>&1 | Out-String
        Write-Info 'python -m pip config list:'
        foreach ($l in ($out -split "`r?`n")) { if ($l.Trim()) { Write-Info ('  ' + $l.Trim()) } }
    } else {
        Write-Warn2 'PATH 上没有 python，跳过 pip 自检（pip.ini 已写好，任何 python 都会读它）'
    }
    $npmCmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmCmd) {
        $reg = & npm config get registry 2>&1 | Out-String
        Write-Ok ('npm config get registry -> ' + $reg.Trim())
    } else {
        Write-Warn2 'PATH 上没有 npm，跳过（.npmrc 已写好）'
    }
    if ($RunSmoke) {
        Write-Step '端到端冒烟测试'
        if ($PythonExe) {
            $tmp = Join-Path $env:TEMP ('mirror-smoke-' + $Stamp)
            New-Item -ItemType Directory -Force -Path $tmp | Out-Null
            Write-Info ('python -m pip download --no-deps -d ' + $tmp + ' six')
            $dl = & $PythonExe -m pip download --no-deps -d $tmp six --disable-pip-version-check 2>&1 | Out-String
            foreach ($l in ($dl -split "`r?`n")) { if ($l.Trim()) { Write-Info ('  ' + $l.Trim()) } }
            if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue }
        }
        $npmCmd2 = Get-Command npm -ErrorAction SilentlyContinue
        if ($npmCmd2) {
            $v = & npm view react version --silent 2>&1 | Out-String
            Write-Info ('npm view react version -> ' + $v.Trim())
        }
    }
}

# ------------------------------------------------------------------ 落点
if (-not $AppDataDir) { $AppDataDir = $env:APPDATA }
if (-not $UserProfileDir) { $UserProfileDir = $env:USERPROFILE }
if (-not $DshHome) {
    if ($env:DSH_HOME) { $DshHome = $env:DSH_HOME } else { $DshHome = Join-Path $UserProfileDir '.dsh' }
}
$Overridden = ($AppDataDir -ne $env:APPDATA) -or ($UserProfileDir -ne $env:USERPROFILE) -or ([bool]$env:DSH_HOME -and ($DshHome -ne $env:DSH_HOME))

$PipIniPath = Join-Path $AppDataDir 'pip\pip.ini'
$NpmRcPath = Join-Path $UserProfileDir '.npmrc'
$DotEnvPath = Join-Path $DshHome '.env'
$CondaRcPath = Join-Path $UserProfileDir '.condarc'

# ------------------------------------------------------------------ 回滚
if ($Revert) {
    Write-Step '回滚到最早一次备份（= 第一次执行本脚本之前的状态）'
    $any = $false
    foreach ($p in @($PipIniPath, $NpmRcPath, $DotEnvPath, $CondaRcPath)) {
        $dir = Split-Path -Parent $p
        $leaf = Split-Path -Leaf $p
        if (-not (Test-Path -LiteralPath $dir)) { continue }
        $baks = @(Get-ChildItem -LiteralPath $dir -Filter ($leaf + '.bak-*') -File -ErrorAction SilentlyContinue |
                Sort-Object Name)
        if ($baks.Count -gt 0) {
            $first = $baks[0]
            Copy-Item -LiteralPath $first.FullName -Destination $p -Force
            Write-Ok ("已恢复 " + $p + "  <-  " + $first.Name)
            if ($baks.Count -gt 1) {
                Write-Info ("共 " + $baks.Count + " 个备份，若只想撤销上一次，请手工选：" + (($baks | ForEach-Object { $_.Name }) -join ', '))
            }
            $any = $true
        } elseif (Test-Path -LiteralPath $p) {
            Write-Warn2 ("没有备份可恢复：" + $p + "（本脚本未写过它？请手工确认）")
        }
    }
    if ($PersistUserEnv) {
        foreach ($name in @('PIP_INDEX_URL', 'PIP_TRUSTED_HOST', 'NPM_CONFIG_REGISTRY', 'UV_DEFAULT_INDEX', 'UV_INDEX_URL', 'UV_INSECURE_HOST', 'UV_PYTHON_INSTALL_MIRROR')) {
            $cur = [System.Environment]::GetEnvironmentVariable($name, 'User')
            if ($cur) {
                [System.Environment]::SetEnvironmentVariable($name, $null, 'User')
                Write-Ok ("已清除用户级环境变量 " + $name)
                $any = $true
            }
        }
    }
    if (-not $any) { Write-Warn2 '没有找到任何可回滚的内容。' }
    exit 0
}

# ------------------------------------------------------------------ 解析地址
if (-not $PipIndexUrl) { $PipIndexUrl = ($HubBase.TrimEnd('/') + $PipPath) }
if (-not $NpmRegistry) { $NpmRegistry = ($HubBase.TrimEnd('/') + $NpmPath) }

$pipUri = $null; $npmUri = $null
try { $pipUri = [Uri]$PipIndexUrl } catch { Write-Err "-PipIndexUrl 不是合法 URL：$PipIndexUrl"; exit 3 }
try { $npmUri = [Uri]$NpmRegistry } catch { Write-Err "-NpmRegistry 不是合法 URL：$NpmRegistry"; exit 3 }

$trustedHosts = New-Object System.Collections.Generic.List[string]
if ($pipUri.Host -and ($pipUri.Scheme -eq 'http' -or $Insecure)) { $trustedHosts.Add($pipUri.Host) }
if ($PipTrustedHostExtra) {
    foreach ($h in ($PipTrustedHostExtra -split ',')) {
        $h = $h.Trim()
        if ($h -and -not $trustedHosts.Contains($h)) { $trustedHosts.Add($h) }
    }
}
$trustedHostLine = ($trustedHosts -join ' ')

if ($NoProxy.Count -eq 0) {
    $np = New-Object System.Collections.Generic.List[string]
    foreach ($h in @($pipUri.Host, $npmUri.Host)) { if ($h -and -not $np.Contains($h)) { $np.Add($h) } }
    $NoProxy = $np.ToArray()
}

# npm 认证键：//host[:port]/<path>/:_authToken
$npmAuthKey = ''
if ($NpmAuthToken) {
    $authPath = $npmUri.AbsolutePath
    if (-not $authPath.EndsWith('/')) { $authPath += '/' }
    $npmAuthKey = '//' + $npmUri.Authority + $authPath + ':_authToken'
}

# ------------------------------------------------------------------ 计划
Write-Step '将写入的镜像源'
Write-Info ("pip   index-url : " + $PipIndexUrl)
Write-Info ("npm   registry  : " + $NpmRegistry)
if ($trustedHostLine) { Write-Info ("信任主机(trusted-host / allow-insecure-host) : " + $trustedHostLine) }
if ($CondaChannel) { Write-Info ("conda channel : " + $CondaChannel) }
if ($UvPythonMirror) { Write-Info ("uv python mirror : " + $UvPythonMirror) }
if ($NoProxy.Count -gt 0) { Write-Info ("NO_PROXY : " + ($NoProxy -join ',')) }
if ($Insecure) { Write-Info 'TLS 校验：已关闭（-Insecure）' }

$envChanges = [ordered]@{}
$envChanges['PIP_INDEX_URL'] = $PipIndexUrl
if ($trustedHostLine) { $envChanges['PIP_TRUSTED_HOST'] = $trustedHostLine }
$envChanges['NPM_CONFIG_REGISTRY'] = $NpmRegistry
$envChanges['UV_DEFAULT_INDEX'] = $PipIndexUrl
$envChanges['UV_INDEX_URL'] = $PipIndexUrl
if ($Insecure -and $trustedHostLine) { $envChanges['UV_INSECURE_HOST'] = ($trustedHosts -join ',') }
if ($UvPythonMirror) { $envChanges['UV_PYTHON_INSTALL_MIRROR'] = $UvPythonMirror }
if ($NoProxy.Count -gt 0) { $envChanges['NO_PROXY'] = ($NoProxy -join ',') }

$plans = New-Object System.Collections.Generic.List[object]
$plans.Add([pscustomobject]@{
        Path    = $PipIniPath
        Kind    = 'ini'
        Changes = ([ordered]@{ 'index-url' = $PipIndexUrl; 'trusted-host' = $(if ($trustedHostLine) { $trustedHostLine } else { $null }) })
    })
$npmChanges = [ordered]@{}
$npmChanges['registry'] = $NpmRegistry
$npmChanges['strict-ssl'] = $(if ($Insecure) { 'false' } else { $null })
if ($NpmAuthToken -and $npmAuthKey) { $npmChanges[$npmAuthKey] = $NpmAuthToken }
$plans.Add([pscustomobject]@{
        Path    = $NpmRcPath
        Kind    = 'kv'
        Changes = $npmChanges
    })
$plans.Add([pscustomobject]@{
        Path    = $DotEnvPath
        Kind    = 'kv'
        Changes = $envChanges
    })

foreach ($plan in $plans) {
    $old = ''
    if (Test-Path -LiteralPath $plan.Path) { $old = [System.IO.File]::ReadAllText($plan.Path) }
    if ($plan.Kind -eq 'ini') { $new = Merge-IniSection -Text $old -Section 'global' -Changes $plan.Changes }
    else { $new = Merge-KeyValues -Text $old -Changes $plan.Changes }
    Add-Member -InputObject $plan -NotePropertyName Old -NotePropertyValue $old -Force
    Add-Member -InputObject $plan -NotePropertyName New -NotePropertyValue $new -Force

    Write-Step ("文件： " + $plan.Path)
    if (-not $old) { Write-Info '(文件不存在，将新建)' }
    foreach ($k in $plan.Changes.Keys) {
        $v = $plan.Changes[$k]
        if ($null -eq $v -or "$v" -eq '') { continue }
        $before = Get-ExistingValue -Text $old -Key $k
        if ($before) { Write-Info ("  " + $k + " : " + $before + "  ->  " + $v) }
        else { Write-Info ("  " + $k + " : (新增) " + $v) }
    }
    foreach ($k in $plan.Changes.Keys) {
        $v = $plan.Changes[$k]
        if ($null -ne $v -and "$v" -ne '') { continue }
        $before = Get-ExistingValue -Text $old -Key $k
        if ($before) { Write-Info ("  " + $k + " : " + $before + "  ->  (删除)") }
    }
    if ($old -eq $new) { Write-Info '(内容无变化)' }
}

if ($DryRun) {
    Write-Step 'DRY-RUN 结束：没有写入任何文件'
    exit 0
}

# ------------------------------------------------------------------ 连通性预检
$preflightFailed = $false
if (-not $SkipVerify) {
    Write-Step '连通性预检'
    $targets = @($PipIndexUrl, $NpmRegistry)
    $up = 0
    foreach ($u in $targets) {
        $r = Test-MirrorUrl -Url $u
        if ($r.Ok) { Write-Ok ($u + '  ->  ' + $r.Detail); $up++ }
        else { Write-Warn2 ($u + '  ->  ' + $r.Detail) }
    }
    if ($up -eq 0 -and -not $Force) {
        Write-Err '两个源都不可达，未改动任何文件。请先接内网/VPN，核对 -HubBase 与路径；确实要强行写入就加 -Force。'
        if (-not $CheckOnly) { exit 2 }
        $preflightFailed = $true
        Write-Info '(-CheckOnly 模式：继续打印当前实际生效的源)'
    }
}

# ------------------------------------------------------------------ 只检查
if ($CheckOnly) {
    Write-Step 'CHECK-ONLY：不写盘'
    if (-not $SkipVerify -and -not $Overridden) {
        Invoke-SelfCheck -PythonExe $PythonExe -Stamp (Get-Date -Format 'yyyyMMdd-HHmmss')
    } else {
        Write-Info '未做工具自检（-SkipVerify 或覆盖了落点目录）。'
    }
    Write-Info '没有写入任何文件；去掉 -CheckOnly 才会真正替换地址。'
    if ($preflightFailed) { exit 2 }
    exit 0
}

# ------------------------------------------------------------------ 写入
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
Write-Step '写入'
foreach ($plan in $plans) {
    if (Test-Path -LiteralPath $plan.Path) {
        $bak = $plan.Path + '.bak-' + $stamp
        $n = 2
        while (Test-Path -LiteralPath $bak) { $bak = $plan.Path + '.bak-' + $stamp + '-' + $n; $n++ }
        Copy-Item -LiteralPath $plan.Path -Destination $bak -Force
        Write-Ok ('备份 ' + (Split-Path -Leaf $plan.Path) + ' -> ' + (Split-Path -Leaf $bak))
    }
    Write-TextFile -Path $plan.Path -Text $plan.New
    Write-Ok ('已写入 ' + $plan.Path)
}

# conda：走官方命令，避免手写 YAML
if ($CondaChannel) {
    Write-Step 'conda channel'
    $conda = Get-Command conda -ErrorAction SilentlyContinue
    if (-not $conda) {
        Write-Warn2 '未找到 conda，跳过（.condarc 保持原样）'
    } else {
        & conda config --remove-key channels 2>&1 | Out-Null
        & conda config --add channels $CondaChannel 2>&1 | Out-Null
        & conda config --set show_channel_urls true 2>&1 | Out-Null
        if ($Insecure) { & conda config --set ssl_verify false 2>&1 | Out-Null }
        Write-Ok ('conda channels 已指向 ' + $CondaChannel)
    }
}

# 用户级环境变量（散装工具才需要）
if ($PersistUserEnv) {
    Write-Step '用户级环境变量（setx 等价）'
    foreach ($k in $envChanges.Keys) {
        $v = $envChanges[$k]
        if ($null -eq $v -or "$v" -eq '') { continue }
        [System.Environment]::SetEnvironmentVariable($k, [string]$v, 'User')
        Write-Ok ($k + ' = ' + $v)
    }
    Write-Info '新开的终端/程序才会读到这些值。'
}

# ------------------------------------------------------------------ 自检
if (-not $SkipVerify -and -not $Overridden) {
    Invoke-SelfCheck -PythonExe $PythonExe -RunSmoke:$SmokeTest -Stamp $stamp
}

# ------------------------------------------------------------------ 收尾
Write-Step '完成'
Write-Info ('pip.ini  : ' + $PipIniPath)
Write-Info ('npmrc    : ' + $NpmRcPath)
Write-Info ('.dsh/.env: ' + $DotEnvPath)
Write-Info 'pip / npm / pnpm：立刻生效（每次执行都读配置文件）。'
Write-Info 'DSH 桌面版：重启一次，~/.dsh/.env 里的 PIP_* / NPM_CONFIG_* / UV_* / NO_PROXY 才会进 agent 子进程。'
Write-Info '回滚：setup-internal-mirror.cmd -Revert'
exit 0