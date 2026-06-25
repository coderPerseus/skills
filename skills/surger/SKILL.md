---
name: surger
description: Diagnose and operate Surge for Mac through terminal-first workflows. Use when the user asks about Surge, surge-cli, proxy/VPN/TUN/enhanced mode, system proxy, DNS timeout, "no internet", "network not working", proxy nodes, policy groups, profile validation, modifying Surge profiles, reloading Surge, or helping a non-technical Mac user fix Surge-related network problems safely.
---

# Surger

Operate Surge for Mac as a terminal-first network assistant. Prefer `surge-cli` and macOS network commands before GUI actions, explain findings in plain language, and avoid exposing proxy secrets.

This skill combines a user-safe workflow with Surge's bundled official CLI reference. For advanced command semantics, full `dump`/`test` command lists, `set` key-path behavior, streaming command behavior, platform limits, and environment field definitions, read [references/command-reference.md](references/command-reference.md). The bundled official skill is mirrored at [references/official-skill.md](references/official-skill.md).

Authoritative sources:

- Surge manual CLI page: `https://manual.nssurge.com/others/cli.html`
- Official app-bundled skill: `/Applications/Surge.app/Contents/Resources/Skills/surge/`
- Local mirrored reference: [references/command-reference.md](references/command-reference.md)

After a Surge app update, refresh the mirrored official reference:

```bash
bash scripts/sync_official_surge_skill.sh
```

## Safety Rules

- Start read-only unless the user explicitly asks to change something.
- Before any change that can affect networking, state the exact command or file edit and ask for confirmation unless the user already gave explicit permission for that exact action.
- Treat these as network-changing actions: `surge-cli reload`, `surge-cli stop`, `surge-cli set`, `surge-cli flush dns`, `surge-cli switch-profile`, editing profiles, enabling TUN/enhanced mode, changing system proxy/VPN settings, updating external resources.
- Before editing a profile, copy it to a timestamped `.bak` file in the same directory.
- After editing a profile, run `surge-cli --check <profile>` before reloading.
- Do not paste full profiles, full `dump profile`, subscription URLs, proxy passwords, tokens, usernames, or private endpoints into the final answer. Redact or summarize.

## Quick Discovery

First find Surge and its CLI:

```bash
command -v surge-cli || true
test -x /Applications/Surge.app/Contents/Applications/surge-cli && echo /Applications/Surge.app/Contents/Applications/surge-cli
mdfind 'kMDItemFSName == "Surge.app"' | head
ps aux | rg -i '[s]urge'
```

Common local paths:

- App: `/Applications/Surge.app`
- CLI: `/Applications/Surge.app/Contents/Applications/surge-cli`
- Profiles: `~/Library/Application Support/Surge/Profiles/`
- Logs: `~/Library/Logs/Surge/`
- App state: `~/Library/Application Support/com.nssurge.surge-mac/`

If `surge-cli` is not in `PATH`, use the app-bundled CLI path directly.

Prefer `--raw` for machine parsing when inspecting live state:

```bash
surge-cli --raw environment
surge-cli --raw dump policy
```

If operating on a remote Surge instance, append `--remote password@host:port`; treat that password as sensitive and never echo it back.

## First Read-Only Snapshot

Run the bundled helper for a stable baseline:

```bash
bash scripts/surge_snapshot.sh
```

For a network failure report, include diagnostics and recent errors:

```bash
bash scripts/surge_snapshot.sh --diagnostics --logs
```

Use this output to answer three questions:

1. Is the Mac itself online?
2. Is Surge running and listening?
3. Is the problem DNS, system proxy, routing/TUN, a bad node, a policy rule, or the target website?

## Diagnosis Workflow

Use the smallest set of checks that proves the state.

```bash
scutil --proxy
route -n get default
lsof -nP -iTCP:8888 -sTCP:LISTEN
surge-cli environment
surge-cli diagnostics
surge-cli test-network
```

Interpret common results:

- System proxy points to `127.0.0.1:<port>` and Surge listens on that port: system proxy mode is active.
- Default route is `utun*`: TUN/enhanced mode or another VPN-like interface is active.
- Router/DNS/direct tests pass but one proxy fails: the Mac has network; a node or policy is broken.
- DNS tests fail for all DNS servers: diagnose local Wi-Fi/router/DNS before proxy nodes.
- Proxy test reaches the server but returns `403`: network path works; the service is refusing the request.
- UDP proxy tests fail while HTTP tests pass: ordinary browsing may work, but games, calls, QUIC, or some realtime apps may fail.

When the user says "no internet", test both direct and Surge paths:

```bash
curl --noproxy '*' -sS -o /dev/null -w 'direct http=%{http_code} total=%{time_total}s remote=%{remote_ip}\n' --connect-timeout 5 --max-time 10 http://connectivitycheck.platform.hicloud.com/generate_204
curl -x http://127.0.0.1:8888 -sS -o /dev/null -w 'surge http=%{http_code} total=%{time_total}s remote=%{remote_ip}\n' --connect-timeout 8 --max-time 15 http://www.gstatic.com/generate_204
```

## Inspect Surge State

Useful read-only CLI commands:

```bash
surge-cli dump request
surge-cli dump dns
surge-cli dump policy
surge-cli dump rule
surge-cli dump event
surge-cli external-resource list
surge-cli --check "$HOME/Library/Application Support/Surge/Profiles/<profile>.conf"
```

Use `dump profile` only when necessary, and redact before showing anything to the user:

```bash
surge-cli dump profile effective
```

Prefer summaries such as "profile validates", "policy group X selects node Y", "recent requests to domain Z go DIRECT", not full raw config.

Read [references/command-reference.md](references/command-reference.md) before using less common commands such as `watch`, `show-policy`, `test-policy-udp`, `test-policy-bandwidth`, `add-temp-rule`, `update-profile`, `proxy-runtime-status`, or `retrieve-data`.

Before mutating runtime settings, collect a minimal baseline:

```bash
surge-cli --raw environment
surge-cli --raw dump policy
```

Use `surge-cli --raw dump profile` only if the task needs profile-level facts; redact secrets before showing output.

## Fix Workflow

Follow this order:

1. Prove the failing layer with command output.
2. Explain the likely cause in one plain sentence.
3. Propose the smallest change.
4. Ask for confirmation if it changes networking or config.
5. Apply the change.
6. Validate with `surge-cli --check`, `surge-cli diagnostics`, or a targeted `curl`.

Low-risk read-only checks do not need confirmation. These changes do:

```bash
surge-cli flush dns
surge-cli reload
surge-cli test-group <group-name>
surge-cli switch-profile <profile-name>
surge-cli set <key-path> <value>
surge-cli external-resource update all
```

Important runtime environment keys:

- `ProxyMode`: `0=Direct`, `1=Global Proxy`, `2=Rule`.
- `AllProxyModePolicyNameKey`: policy name used when `ProxyMode=1`.
- `ProxyGroupSelection.<group>`: selected policy for a select group.
- `AutoPolicyGroupOverride.<group>`: temporary override for an auto group; use `<nil>` to clear.

Use `surge-cli --raw set key=value` for environment mutations, then immediately verify with `surge-cli --raw environment`.

For `set`, prefer scalar deltas and batch related updates in one command. Use `<nil>` to clear supported override values:

```bash
surge-cli --raw set ProxyMode=1 AllProxyModePolicyNameKey=ProxyA
surge-cli --raw set AutoPolicyGroupOverride.Streaming=<nil>
```

Streaming commands such as `diagnostics` and `test-policy-bandwidth` may emit incremental JSON chunks. Keep reading until the command-specific completion marker or `hasMore=false`; do not assume one response frame.

## Profile Edits

Use profile edits when CLI environment settings are insufficient.

```bash
profile="$HOME/Library/Application Support/Surge/Profiles/<profile>.conf"
cp "$profile" "$profile.bak.$(date +%Y%m%d-%H%M%S)"
```

Edit only the relevant key or rule. Then validate:

```bash
surge-cli --check "$profile"
```

Only reload after validation succeeds and the user confirms:

```bash
surge-cli reload
```

## Enhanced Mode / TUN

Do not guess config keys. Surge versions and profiles differ, and unsupported keys may be silently ignored or reported as unknown.

To handle "enable enhanced mode":

1. Check current state with `surge-cli environment`, `route -n get default`, `ifconfig | rg '^utun|utun'`, and `surge-cli diagnostics`.
2. Inspect the current profile's `[General]` section without exposing secrets.
3. Check whether the profile already contains TUN/enhanced-mode related keys.
4. Prefer Surge-supported CLI/environment switches if present.
5. If a profile edit is required, back up the profile, change only verified supported keys, validate with `surge-cli --check`, then reload after confirmation.

If diagnostics reports unknown keys such as `bypass-tun`, `bypass-system`, or `enhanced-mode-by-rule`, tell the user those lines are not being recognized by the installed Surge version/profile parser.

## Final Response Style

For non-technical users:

- Start with a clear verdict: normal, partially broken, or broken.
- Say what works and what does not.
- Name the likely failing layer.
- Give the next action, not a command dump.
- Mention exactly whether you changed anything.

Example:

> Your Mac is online and Surge is running. Normal web traffic works through Surge, but one proxy node times out and UDP relay is failing, so calls/games may be unstable. I did not change settings.
