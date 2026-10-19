# 外部通信の棚卸しと遮断（task-verify ステップ10）

> **この文書は自動実行フェーズで、外部通信の棚卸し（既定モードの P13 / `--run-only` のフェーズ7）に着手する直前に読み込みます。**
> `--manual`（生成のみ）では読み込みません。生成フェーズ（P4〜P9）でも読み込む必要はありません。
>
> 本文中の節番号（§0〜§6）は SKILL.md 本体からの参照名です。変更しないでください。

## §0. 原則

開発環境は、起動した**瞬間**から外部へデータを送りえます（WP-Cron・キューワーカー・スケジューラ・DDEV のフック）。メール送信を止めたつもりでも、SMTP プラグインやメール配信 API（SendGrid 等）との連携が有効なら送られます。外部 API（決済・SNS・Slack・CRM・外部ストレージへのバックアップ・エラー監視など）は種類が多く、事前に列挙しきれません。したがって本スキルは次の順序を崩しません。

1. **棚卸し**（§1）: 開発環境を起動せず、ファイルを読むだけでプロジェクトの外部通信の経路を洗い出す
2. **遮断層の適用と起動前ゲート**（§2・§3）: 適用できる遮断層を**すべて重ね**（メールはアプリ層とネットワーク層の両方）、ファイルの設置だけで適用して確かめる。**確かめられた層で覆えない経路が残れば起動しない**
3. **起動と起動直後確認**（§4）: 起動したら、検証項目と DB のバックアップより先に、各層が実行時にも効いていることを**送信を伴わない方法で**確かめる。効いていなければ直ちに停止する
4. **撤去**（§5）: 本スキルが起動した開発環境は**停止してから**遮断層を外す。遮断層を外した状態で開発環境を起動することは、どの経路でも行わない

**層を数えるのは確かめられたものだけです。** 効くかどうかを確かめる手段の無い防御（プロキシの環境変数、送信設定の差し替え等）も重ねますが、§3 の層数には数えません。

**秘密の値を記録しない**: 棚卸しで `.env` / `wp-config.php` 等を読む場合、記録してよいのはキー名・定数名・ホスト名だけです。API キー・パスワード・トークンの値を成果物・`state.json`・画面へ書いてはいけません。

## §1. 棚卸し（読み取りのみ）

### 1-1. 走査対象

| 対象 | 読むもの |
|---|---|
| 依存の宣言 | `composer.json` / `composer.lock` / `package.json` / ロックファイル。下表の SDK・HTTP クライアントの有無 |
| WordPress | `wp-content/plugins/*/`（**有効・無効を問わず全件**。起動前は DB の `active_plugins` を読めないため、設置されているものはすべて有効になりうるとみなす）／ `wp-content/mu-plugins/`（`function wp_mail` を定義するものがあれば記録する。2-1 の層が負けるため）／ テーマの `functions.php` と、そこから読み込まれるファイル |
| 自前のコード | 下表の呼び出しと、`https?://` で始まる外部 URL のリテラル。`vendor/` / `node_modules/` / WordPress コアは走査せず、SDK の有無は依存の宣言で判断する |
| 設定 | `.env*`（キー名のみ）・`wp-config.php`（定数名とホスト名のみ）・`config/` 配下・Docker Compose のファイル（`compose*.yaml` / `docker-compose*.yml`。override を含む）・crontab の定義 |
| DDEV | `.ddev/config*.yaml` の **`hooks` の全種類**（`pre-start` / `post-start` に限らず、本スキル自身が引き起こす `pre-stop` / `post-stop` / `pre-snapshot` / `post-snapshot` / `pre-import-db` / `post-import-db` / `pre-restore-snapshot` / `post-restore-snapshot` 等を含む。**`exec-host` はホスト上で走る**）・`web_extra_daemons`・`.ddev/` 配下の add-on（cron 系を含む）・`.ddev/.env*` と `web_environment`（**Mailpit の中継設定 `MP_SMTP_RELAY_*` の有無**を含む） |
| 定期・常駐で走るもの | キューワーカー・スケジューラ・WP-Cron |
| ブラウザ側 | テンプレート・JS が外部オリジンへ送るもの（フォームの `action`・`fetch` / XHR / `sendBeacon` の宛先・`WebSocket`・解析タグ・埋め込みフォーム） |
| task-dev の記録 | `dev-result.md` の `## パフォーマンスとセキュリティ` に列挙された外部通信。**手掛かりであって網羅の保証ではない**（全件は本節の走査で洗い出す） |

検索する呼び出しの例（部分一致。言語に応じて読み替える）:

| 種別 | 例 |
|---|---|
| HTTP | `wp_remote_` / `wp_safe_remote_` / `WP_Http` / `curl_init` / `curl_multi_` / `file_get_contents(` ＋ URL / `GuzzleHttp` / `HttpClient` / `Http::` / `fetch(` / `axios` / `XMLHttpRequest` / `sendBeacon` / `WebSocket` |
| メール | `wp_mail` / `mail(` / `PHPMailer` / `Mail::` / `Mailer` / `Notification` / `nodemailer` / SMTP の設定キー（`SMTP_` / `MAIL_HOST` / `MAIL_MAILER` 等） |
| ソケット | `fsockopen` / `stream_socket_client` / `socket_connect` |
| SDK | 決済（Stripe / PayPal / Square / PAY.JP）・メール配信（SendGrid / Mailgun / Amazon SES / Postmark / SparkPost / Brevo）・チャット（Slack / LINE / Discord / Chatwork）・SNS・クラウド（AWS / Google / Azure）・エラー監視（Sentry / Bugsnag）・解析・CRM・検索（Algolia）・プッシュ通知 |
| WordPress プラグイン | SMTP・メール配信・ニュースレター・決済ゲートウェイ・外部ストレージへのバックアップ・外部サービスへの接続（Jetpack 等）・フォームの外部連携・通知 |

**判別できないものは除外せず、通信先「不明」の経路として加えます**（取りこぼしを安全側へ倒すため）。除外してよいのは、読んで外部通信を伴わないと**確かめられた**ものだけです。

### 1-2. 経路の記録

経路は **（区分, 通信先）** の組を1件とします。同じ組の呼び出し箇所は1件にまとめ、検出箇所を併記します。

| 区分（この5値のみ） | 意味 |
|---|---|
| `mail` | メールの送信（`wp_mail` / PHP の `mail()` / SMTP / メール配信 API / Mailpit の中継） |
| `http` | アプリから外部への HTTP(S) 送信（API・Webhook・SDK・解析・バックアップ連携など） |
| `socket` | HTTP・SMTP 以外のソケット通信 |
| `host_hook` | **ホスト上で**走る処理（DDEV の `exec-host` フック、ホストで動かすワーカー・cron） |
| `browser` | ブラウザから外部オリジンへの送信 |

| 記録する項目 | 内容 |
|---|---|
| 通信先 | ホスト名（例: `api.stripe.com`）／ `不明`（URL が DB や管理画面の設定に保存されている等） |
| 区分 | 上表の5値 |
| 送信経路 | `WordPress のメール` / `PHP の mail()` / `WP HTTP API` / `HTTP(S)`（ブラウザ）/ `WebSocket`（ブラウザ）/ `その他` / `不明`（§3 の数え方に使う） |
| 検出箇所 | `path:line`（先頭3件まで。超過分は件数） |
| 発火契機 | `起動時` / `停止時` / `定期` / `操作時` / `不明` |

WordPress を検出した場合は、検出箇所の有無にかかわらず `mail`（WordPress のメール・通信先 `不明`）と `http`（WP HTTP API・通信先 `不明`）の2経路を**必ず**加えます（コアと任意のプラグインが送りうるため）。Mailpit の中継（`MP_SMTP_RELAY_*`）が設定されていれば、中継先のホストを `mail` の経路として加えます。

棚卸しは読み取りのみのため、SKILL.md「調査のサブエージェント委譲」の契約で委譲してかまいません。**経路の採否・ゲートの判定・記録はメイン会話が行います。**

## §2. 遮断層

各層は SKILL.md 10-6 のライフサイクル（`planned` の先行記録 → 適用 → 確認 → `applied`）に従い、`state.json` の `protection.egress.layers[]` へ**本スキルが設置したファイルとディレクトリを1件ずつ**記録します（既存のものは記録しない＝撤去しない）。**どの層も、開発環境の稼働の有無にかかわらずファイルを置くだけで適用でき、起動を必要としません。**

| 層 | 前提 | 適用（ファイルの設置） | 起動前確認 | 起動後確認（送信しない） | 撤去 |
|---|---|---|---|---|---|
| `disable-emails-mu` | WordPress を検出 | 2-1 | 本スキルが設置したファイルが存在し、mu-plugin の写しが配布物と sha256 一致 | 2-3 の確認ファイルの出力が `wp_mail_defined_by=disable-emails` | 本スキルが設置したファイル・ディレクトリのみ削除 |
| `wp-egress-guard-mu` | WordPress を検出 | 2-2 の逐語ファイルを `wp-content/mu-plugins/000-verify-run-egress-guard.php` へ書き出す | ファイルが存在し逐語と一致 | 2-3 の出力が `pre_http_request=blocked`（HTTP の層）。メールの層としては `wp_mail_defined_by=core` かつ `wp_version` が 5.7 以上かつ `pre_wp_mail=blocked` の場合**だけ**数える（コアの `wp_mail()` 以外は `pre_wp_mail` を呼ばないため） | 同上 |
| `ddev-compose-guard` | DDEV を検出（`.ddev/config.yaml` ＋ `command -v ddev`。稼働は問わない） | 2-4 の内容を `.ddev/docker-compose.zz-verify-run.yaml` へ書き出す | `ddev debug compose-config` の出力で、対象サービスの `extra_hosts` に上書きが現れる | `ddev exec getent hosts <各通信先>` がすべて `127.0.0.1` | 停止の後にファイルを削除 |
| `compose-guard` | DDEV ではない Docker Compose を検出 | 2-4 と同じ内容（サービス名を読み替える）を `.claude/tasks/<TASK>/.verify-run/compose.guard.yaml` へ書き出す。起動・停止は 2-5 のファイル列で行う | 2-5 のファイル列による `docker compose … config` に上書きが現れる | `docker compose … exec <サービス> getent hosts <通信先>` が `127.0.0.1` | 停止の後にファイルを削除 |
| `ddev-mailpit` | DDEV を検出し、かつ Mailpit の中継（`MP_SMTP_RELAY_*`）が**設定されていない** | なし（DDEV は PHP の `sendmail_path` を Mailpit へ向けている） | —（前提を満たせば数え、起動後確認で確定する） | `ddev exec 'php -i' \| grep -i sendmail_path` が `mailpit` / `mhsendmail` を含み、`ddev exec printenv` に `MP_SMTP_RELAY_HOST` が無い | 不要 |
| `browser-block` | 採用した自動化手段が外部オリジンへの要求の遮断（SKILL.md 付録A の OP-15）を持つ | **`about:blank` を開いた状態で** OP-15 を適用してから、最初の URL へ遷移する（先に遷移すると、最初のページの解析タグ・ビーコンが遮断前に送られる） | —（同上） | 最初のページで `fetch('https://example.com/', {mode: 'no-cors'})` を評価し、**失敗する**こと（`no-cors` の応答は CORS で拒否されないため、成功すれば要求が外へ出たことを意味する。遮断が効いていなくても届くのは IANA の予約ドメインで、データは送られない） | ブラウザを閉じる |

> **Mailpit は単独では足りません。** DDEV の公式ドキュメントも、アプリが SMTP や外部の配信サービス連携を使う場合は Mailpit が捕捉しないと明記しています。`ddev-mailpit` は PHP の `mail()` / sendmail 経由だけを覆う層として数えます（§3）。中継が設定されていると Mailpit 自身が外へ送るため、その場合は層として数えず、中継先を `ddev-compose-guard` でループバックへ向けます。

> **`browser-block` は HTTP(S) の要求だけを覆います。** WebSocket の送信は覆わないため、棚卸しで見つかったブラウザ側の WebSocket の経路は0層として扱います（§3）。

#### 2-1. `disable-emails-mu`（Disable Emails の mu-plugin）

Disable Emails（https://wordpress.org/plugins/disable-emails/）は `wp_mail()` を、送信しない自前の実装で先に定義します。同梱の `mu-plugin/disable-emails-mu.php` は、`wp-content/plugins/disable-emails/disable-emails.php` が**読めさえすれば**（有効化されていなくても）それを読み込むローダーです。mu-plugins は通常のプラグインより先に読み込まれるため、**SMTP プラグインやメール配信プラグインが `wp_mail()` を置き換えるより先に、送信しない実装が確定します。** プラグインの有効・無効（DB の状態）に依存しないことが、起動前に適用できる理由です。

| 手順 | 内容 |
|---|---|
| 1 | `wp-content/plugins/disable-emails/disable-emails.php` が無ければ、公式配布物 `https://downloads.wordpress.org/plugin/disable-emails.latest-stable.zip` を `.claude/tasks/<TASK>/.verify-run/downloads/` へ取得し、`wp-content/plugins/disable-emails/` へ展開する（`unzip -q`。無ければ `python3 -m zipfile -e`）。取得できなければこの層は**未適用**（E-13） |
| 2 | `wp-content/mu-plugins/` が無ければ作成する（作成した事実を記録する） |
| 3 | `wp-content/mu-plugins/` 内に `DISABLE_EMAILS_MU_PLUGIN` を定義するファイルが既にあれば何もしない。無ければ `wp-content/plugins/disable-emails/mu-plugin/disable-emails-mu.php` を `wp-content/mu-plugins/000-verify-run-disable-emails-mu.php` へコピーする |

- ファイル名を `000-` で始めるのは、mu-plugins がファイル名順に読み込まれ、`wp_mail()` は**先に定義したものが勝つ**ためです。それでも先に `wp_mail()` を定義する mu-plugin があれば起動後確認が不成立になり、この層は数えません（その場合、`wp_mail()` は別の実装に握られており、2-2 のメールの遮断も数えられないため、WordPress のメールの経路は0層になります）。
- 検証中は WordPress のメールが **Mailpit にも届きません**。メールの到達を合否に使う検証項目は、軸2（「受信箱」「実際にメールが届く」）でスキップされます。
- 取得した配布物はプロジェクトのコードとして実行されます。取得元は wordpress.org の公式配布 URL に限ります。

#### 2-2. `wp-egress-guard-mu`（本スキルの遮断用 mu-plugin）【逐語】

WordPress の HTTP API を通る外部送信の遮断と、Disable Emails が効かなかった場合に備えるメールの遮断（コアの `wp_mail()` の短絡と、PHPMailer の Mailpit への付け替え）を1ファイルで行います。**内容を変更せず**そのまま書き出してください。

```php
<?php
/*
 * Plugin Name: verify-run egress guard
 * Description: task-verify が検証中だけ設置する外部通信の遮断。検証の終了時に task-verify が削除する。本番へ持ち込まないこと。
 */

if (!defined('ABSPATH')) {
	exit;
}

function verify_run_egress_allowed_host($host) {
	$host = strtolower(trim((string) $host, '[]'));
	if (strpos($host, '::ffff:') === 0) {
		$host = substr($host, 7);
	}
	if ($host === '' || strpos($host, '169.254.') === 0) {
		return false;
	}
	if ($host === 'localhost' || $host === 'host.docker.internal') {
		return true;
	}
	foreach (array('.localhost', '.ddev.site', '.test', '.local', '.internal') as $suffix) {
		if (substr($host, -strlen($suffix)) === $suffix) {
			return true;
		}
	}
	if (filter_var($host, FILTER_VALIDATE_IP)) {
		return !filter_var($host, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE);
	}
	return false;
}

function verify_run_egress_block_http($pre, $args, $url) {
	if (verify_run_egress_allowed_host(wp_parse_url($url, PHP_URL_HOST))) {
		return $pre;
	}
	return new WP_Error('verify_run_egress_blocked', 'task-verify: external request blocked');
}

// 先頭で塞ぎ（独自の送信を行うフィルタに false 以外を渡す）、末尾で塞ぎ直す（後のフィルタが戻り値を書き換えても遮断を保つ）
add_filter('pre_http_request', 'verify_run_egress_block_http', PHP_INT_MIN, 3);
add_filter('pre_http_request', 'verify_run_egress_block_http', PHP_INT_MAX, 3);

add_filter('pre_wp_mail', '__return_false', PHP_INT_MIN);
add_filter('pre_wp_mail', '__return_false', PHP_INT_MAX);

add_action('phpmailer_init', function ($phpmailer) {
	if (!is_object($phpmailer) || !method_exists($phpmailer, 'isSMTP')) {
		return;
	}
	$phpmailer->isSMTP();
	$phpmailer->Host = '127.0.0.1';
	$phpmailer->Port = 1025;
	$phpmailer->SMTPAuth = false;
	$phpmailer->SMTPSecure = '';
	$phpmailer->SMTPAutoTLS = false;
}, PHP_INT_MAX);
```

- サイトの `home_url()` のホストは許可しません。本番の DB を取り込んだ環境では `home_url()` が本番のドメインを指していることがあり、許可するとループバックのつもりの要求が本番へ届くためです。
- `169.254.0.0/16`（クラウドのメタデータの範囲）と、IPv4 射影の IPv6 表記（`::ffff:` で始まるもの）の扱いを明示しているのは、`FILTER_FLAG_NO_RES_RANGE` がそれらを「予約済み」に含め、そのままでは許可へ倒れるためです。
- `phpmailer_init` の付け替え先（`127.0.0.1:1025`）は DDEV の Mailpit です。Mailpit の無い環境では接続が拒否されて送信が失敗するだけで、外部へは出ません（Mailpit の中継が設定されている場合は §2 の注のとおり中継先を塞ぎます）。この付け替えは、それを呼ぶ実装でしか効かないため、**層としては数えない追加の防御**です。
- 独自の送信を行うフィルタが `$pre` を無視して送る場合は、この mu-plugin では止められません。そのような送信は `ddev-compose-guard` の `extra_hosts` で通信先ごとに塞ぎます。

#### 2-3. 起動後確認ファイル【逐語】

`wp-cli` の `eval` に PHP を直接渡すと、`ddev exec` が引数を結合してコンテナ内のシェルへ渡すため、`$` や括弧のクォートが壊れます。確認は次のファイルを `.claude/tasks/<TASK>/.verify-run/egress-check.php` へ書き出し、`<wp_cli_prefix> eval-file .claude/tasks/<TASK>/.verify-run/egress-check.php` で実行してください（`<wp_cli_prefix>` は SKILL.md 10-4 で確定したもの。パスはプロジェクトルートからの相対で、空白も記号も含まないためクォートが要らない）。**内容を変更しないこと。送信は行いません。**

```php
<?php
// task-verify の起動直後確認。送信を伴わない。
$verify_run_file = function_exists('wp_mail') ? str_replace('\\', '/', (string) (new ReflectionFunction('wp_mail'))->getFileName()) : '';
if (substr($verify_run_file, -strlen('wp-includes/pluggable.php')) === 'wp-includes/pluggable.php') {
	$verify_run_owner = 'core';
} elseif (strpos($verify_run_file, '/disable-emails/') !== false) {
	$verify_run_owner = 'disable-emails';
} else {
	$verify_run_owner = 'other:' . $verify_run_file;
}
$verify_run_mail = apply_filters('pre_wp_mail', null, array('to' => '', 'subject' => '', 'message' => '', 'headers' => '', 'attachments' => array()));
$verify_run_http = apply_filters('pre_http_request', false, array(), 'https://api.example.com/');
echo 'wp_mail_defined_by=' . $verify_run_owner . "\n";
echo 'wp_version=' . get_bloginfo('version') . "\n";
echo 'pre_wp_mail=' . ($verify_run_mail === false ? 'blocked' : 'open') . "\n";
echo 'pre_http_request=' . (is_wp_error($verify_run_http) ? 'blocked' : 'open') . "\n";
```

確認ファイルは撤去（§5）の対象に含めます。

#### 2-4. `ddev-compose-guard`（DDEV の上書きファイル）

`.ddev/docker-compose.*.yaml` は `ddev start` のときに読み込まれます。ファイル名を `zz-` で始めるのは、既存の上書きファイルより後に読み込ませるためです。

```yaml
# task-verify が検証中だけ設置する外部通信の遮断。検証の終了時に task-verify が削除する。
services:
  web:
    extra_hosts:
      - "<通信先1>:127.0.0.1"
      - "<通信先2>:127.0.0.1"
    environment:
      HTTPS_PROXY: "http://127.0.0.1:9"
      https_proxy: "http://127.0.0.1:9"
      HTTP_PROXY: "http://127.0.0.1:9"
      http_proxy: "http://127.0.0.1:9"
      NO_PROXY: "<除外リスト>"
      no_proxy: "<除外リスト>"
```

| 項目 | 内容 |
|---|---|
| `extra_hosts` | 棚卸しで通信先が判明した `mail` / `http` / `socket` の全ホスト（Mailpit の中継先を含む）＋ 下記の既定のメール送信ホスト。`127.0.0.1` へ向けるため、要求はコンテナの外へ出ない。**§3 で数えるのはこの項目だけ** |
| 既定のメール送信ホスト | `smtp.gmail.com` / `smtp.office365.com` / `smtp.sendgrid.net` / `api.sendgrid.com` / `smtp.mailgun.org` / `api.mailgun.net` / `api.eu.mailgun.net` / `smtp.postmarkapp.com` / `api.postmarkapp.com` / `smtp.sparkpostmail.com` / `api.sparkpost.com` / `smtp-relay.brevo.com` / `api.brevo.com`。Amazon SES は棚卸しで判明したリージョンのホスト（`email-smtp.<region>.amazonaws.com` / `email.<region>.amazonaws.com`）を加える |
| プロキシ変数 | 応答しないローカルのポートを指し、環境変数のプロキシを尊重するクライアント（cURL・Guzzle 等）の外部送信を、通信先を問わず失敗させる。**効くかどうかはクライアントに依存し確かめられないため、§3 の層数には数えない**（追加の防御） |
| `NO_PROXY` | `localhost,127.0.0.1,::1,.ddev.site,.internal,host.docker.internal` ＋ `ddev debug compose-config` に現れる全サービス名（`db` 等） |
| 送信設定の差し替え | 環境変数から読まれるメール・外部連携の設定キー（例: Laravel の `MAIL_MAILER: "log"`）を無害な値へ差し替えてよい。ただし設定のキャッシュや `.env` の上書き読み込みで無視されうるため、**§3 の層数には数えない**（追加の防御）。**値を推測で作らない** |
| 対象サービス | `web` に加え、棚卸しで外部通信を持つと判定したサービス（キューワーカー等）。`db` には書かない |

#### 2-5. `compose-guard` の起動・停止に用いるファイル列

`docker compose` に `-f` を明示すると、`compose.override.yaml` / `docker-compose.override.yml` が**自動では読み込まれなくなります**。開発用の安全な設定（ローカルのメールキャッチャーやモックの送信先）は override に置かれていることが多く、読み落とすと本番相当の設定で起動しかねません。したがって次の順で**すべて**を `-f` で並べ、最後に遮断用のファイルを置きます（`up` / `stop` / `config` / `exec` のいずれも同じ列を使う）。

| 順 | ファイル |
|---|---|
| 1 | `COMPOSE_FILE` が設定されていればその列（区切りは `COMPOSE_PATH_SEPARATOR`、既定は `:`）。設定されていなければ、既定のファイル（`compose.yaml` / `compose.yml` / `docker-compose.yaml` / `docker-compose.yml` のうち Compose が採用するもの）と、存在する override ファイル |
| 2 | `.claude/tasks/<TASK>/.verify-run/compose.guard.yaml` |

## §3. 起動前ゲート（覆えない経路が残れば起動しない）

経路ごとに、**適用し起動前確認に合格した層**（起動前確認が「—」の層は前提を満たしたもの）のうち、その経路を覆うものを数えます。

| 経路（区分・送信経路） | 数える層 |
|---|---|
| `mail`・WordPress のメール | `disable-emails-mu` ／ `wp-egress-guard-mu`（起動後確認で `wp_mail_defined_by=core` の場合だけ）／ 通信先が判明していれば `ddev-compose-guard`・`compose-guard` |
| `mail`・PHP の `mail()` | `ddev-mailpit`（中継が設定されていない場合） |
| `mail`・その他（アプリ独自の SMTP・配信 API・Mailpit の中継） | `ddev-compose-guard`・`compose-guard`（通信先が `extra_hosts` に載っている場合） |
| `http`・WP HTTP API | `wp-egress-guard-mu`（通信先を問わない）／ 通信先が載っていれば `ddev-compose-guard`・`compose-guard` |
| `http` / `socket`・その他・不明 | `ddev-compose-guard`・`compose-guard`（通信先が載っている場合のみ。通信先 `不明` は覆えない） |
| `host_hook` | なし（ホスト上の処理はコンテナの層で覆えない） |
| `browser`・HTTP(S) | `browser-block` |
| `browser`・WebSocket | なし |

| 判定 | 帰結 |
|---|---|
| すべての経路が1層以上 | 起動してよい（§4）。経路ごとの層数（適用した層と、うち数えた層）を表示し、`verify-result.md` へ記録する |
| 0層の経路が1件以上 | **起動しない。** 0層の経路を一覧し、経路ごとに類型③で「この通信先は検証環境で外部へ影響しない（サンドボックス・テスト用の宛先等）と確認済みか」を尋ねる。承認された経路のみ通し、承認を `state.json`（保護ジャーナル領域）と `verify-result.md` の両方へ記録する。承認されない経路が残る、または対話できなければ **E-29**（開発環境を起動せず自動実行を中断） |

> **承認を経路単位にする理由**: 「起動してよいか」をまとめて尋ねると、何を通したのかが記録に残りません。通信先ごとの承認なら、後から「どの外部宛先へ何が送られえたか」を監査できます。

## §4. 起動と起動直後確認

| # | 手順 |
|---|---|
| 1 | 開発環境の稼働状態を `state.json` の `env.before`（`running` / `stopped`）へ記録する（**この時点では止めない**） |
| 2 | §2 の層を適用して起動前確認を行い、§3 のゲートを通す。**不成立なら E-29**（稼働中だった環境には触れずに、設置した層を撤去して終わる） |
| 3 | 稼働中だった場合は、ここで停止する（`ddev stop` / 2-5 のファイル列による `docker compose … stop` / 前提ブロックの `stop_command`）。上書きファイルは起動時にしか読まれず、稼働中の環境は遮断なしで起動されているため。**停止の手段が無ければ E-29**（遮断なしで起動された環境で検証しない）。停止したことは画面と `verify-result.md` の両方へ記録する（黙って止めない） |
| 4 | 起動する（DDEV は `ddev start`、`compose-guard` は 2-5 のファイル列による `docker compose … up -d`、それ以外は前提ブロックの `start_command`）。`env.started_by_skill = true` を記録する |
| 5 | **検証項目にも DB のバックアップにも先立って**、各層の起動後確認を行う（`browser-block` はブラウザを最初に開いた時点）。合格した層だけで数え直し、0層の経路（承認済みを除く）が1件でも生じたら **E-29**（直ちに停止し、原状復帰して中断） |
| 6 | 合格したら、SKILL.md 10-4 の検証前提の解決（`base_url` の到達確認など）へ進む |

**起動の手段は手順4 に定めたものに限ります。** 検証項目の実行中に開発環境を起動・再起動・作り直すこと（`ddev restart`、override や遮断用のファイルを欠いた `docker compose up`、ホスト上での開発サーバの起動など）は行いません（SKILL.md 11-6）。

## §5. 撤去（原状復帰）

撤去は SKILL.md ステップ12 の順序に従います: **DB の復元とカナリア照合 → 開発環境の停止 → 遮断層の撤去**。

| # | 規則 |
|---|---|
| 1 | **本スキルが起動した開発環境は、停止してから遮断層を外す**。稼働中に外すと、その瞬間から遮断のない環境が動き続ける。起動前ゲートで止まった（E-29。本スキルが何も起動していない）場合は、稼働状態に触れずに、設置した層だけを撤去する |
| 2 | 撤去するのは `protection.egress.layers[]` に記録した、**本スキルが設置したファイル・ディレクトリだけ**（既存の Disable Emails・既存の mu-plugins には触れない）。2-3 の確認ファイルも撤去する |
| 3 | 撤去後に各ファイルの不在を確かめ、`restored` を記録する。削除できないものが残れば **E-13**（残ったパスを逐語で表示し、手動での削除を求める） |
| 4 | **DB の復元に失敗した場合（E-14）は遮断層を外さない。** 検証中に作られたデータ（送信待ちのメール・通知・キュー）が残っており、遮断なしで起動するとそれらが送られるため。外さなかったことと、残したファイルの一覧を表示する |
| 5 | `env.before == running` でも、**遮断層を外した状態で再起動しない**。「検証前は起動していたが、遮断層を外した状態での再起動は行っていない（必要なら手動で起動する）」と表示する |

## §6. 記録

`verify-result.md` の `## 外部通信の棚卸し` へ、経路ごとに1行で記録します（列: 通信先 / 区分 / 送信経路 / 検出箇所 / 発火契機 / 数えた層 / 承認）。`## 保護措置` の表には、適用した層の一覧（数えた層と、数えない追加の防御の別）・開発環境の起動前の状態と最終状態を記録します。秘密の値は書きません（§0）。
