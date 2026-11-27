//! Casca desktop do Adito.
//!
//! Ao abrir, sobe o núcleo Python (`desktop_server.py`) como processo filho, sem porta de rede.
//! A conversa é por stdin/stdout, uma mensagem JSON por linha (formato em `backend/nucleo/rpc/server.py`):
//!
//! - o front chama `core_call` / `core_stream` com um id; o Rust escreve o pedido no stdin do núcleo;
//! - uma thread lê o stdout do núcleo e entrega cada resposta a quem espera aquele id
//!   (e cada evento de stream ao `Channel` daquele id);
//! - o stderr do núcleo vai para o `backend.log`.
//!
//! Quando o app fecha, ou morre, o stdin do núcleo fecha e ele encerra sozinho.
//! A chave do Gemini fica no cofre do SO e só chega ao núcleo por variável de ambiente;
//! trocar a chave reinicia o núcleo.
//!
//! Distribuição (ADR-0006/0007): o app se atualiza pelo `tauri-plugin-updater` e a base
//! `dados.db` chega cifrada pelo GitHub Releases (ver `dados.rs`); a chave dela também fica no cofre.

pub mod dados;

use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::{Arc, Condvar, Mutex};
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tauri::ipc::Channel;
use tauri::{AppHandle, Emitter, Manager, RunEvent, State};
use tokio::sync::oneshot;

const START_TIMEOUT: Duration = Duration::from_secs(90);
const STOP_GRACE: Duration = Duration::from_secs(3);
const KEYRING_SERVICE: &str = "br.edu.ifes.leds.adito";
/// Entrada legada da v0.1.0 para a chave do Gemini; mantida para retrocompatibilidade.
const KEYRING_USER: &str = "gemini-api-key";
const LLM_CONFIG_FILENAME: &str = "llm_config.json";
const KNOWN_PROVIDERS: &[&str] = &[
    "gemini",
    "openai",
    "openrouter",
    "mistral",
    "zai",
    "together",
    "fireworks",
    "ollama",
];
/// IDs altos (acima de 2^53 do JS) para chamadas internas Rust → núcleo, sem colidir com IDs do front.
static INTERNAL_RPC_ID: AtomicU64 = AtomicU64::new(1u64 << 62);
/// Chave institucional que abre o `dados.db.enc` (ADR-0007).
const KEYRING_DADOS: &str = "dados-chave";
/// Identifiers antigos (o mais recente primeiro): Muninn e, antes dele, Oraculo-ESX.
/// Só servem para migrar dados e chave para o Adito.
const LEGACY_IDENTIFIERS: &[&str] = &["br.edu.ifes.leds.muninn", "br.edu.ifes.leds.oraculo-esx"];

/// Erro devolvido ao front, no mesmo formato de antes: um status no estilo HTTP e o corpo.
#[derive(Debug, Clone, Serialize)]
struct CoreError {
    status: u16,
    data: Value,
}

impl CoreError {
    fn new(status: u16, detail: impl Into<String>) -> Self {
        CoreError { status, data: json!({ "detail": detail.into() }) }
    }
}

type Reply = Result<Value, CoreError>;

enum Pending {
    Call(oneshot::Sender<Reply>),
    Stream(Channel<Value>, oneshot::Sender<Reply>),
}

impl Pending {
    /// Entrega a resposta. No stream, o fim também vai pelo Channel (`$end`), depois dos
    /// eventos, para o front nunca receber um evento depois de a chamada terminar.
    fn finish(self, reply: Reply) {
        match self {
            Pending::Call(tx) => {
                let _ = tx.send(reply);
            }
            Pending::Stream(channel, tx) => {
                let end = match &reply {
                    Ok(result) => json!({ "event": "$end", "ok": true, "result": result }),
                    Err(e) => json!({ "event": "$end", "ok": false, "error": e }),
                };
                let _ = channel.send(end);
                let _ = tx.send(reply);
            }
        }
    }
}

#[derive(Clone, PartialEq)]
enum Status {
    Starting,
    Ready,
    Failed(String),
}

struct Running {
    child: Child,
    stdin: ChildStdin,
    generation: u64,
}

struct Core {
    app: AppHandle,
    data_dir: PathBuf,
    log_path: PathBuf,
    running: Mutex<Option<Running>>,
    pending: Mutex<HashMap<u64, Pending>>,
    status: Mutex<(Status, u64)>,
    status_changed: Condvar,
}

// ── Cofre do SO e configuração multi-provedor ────────────────────────────────

#[derive(Serialize)]
struct KeyStatus {
    configured: bool,
    /// Falso quando o cofre do SO não está disponível (ex.: Linux sem Secret Service).
    store_available: bool,
    error: Option<String>,
}

/// Metadados não-sensíveis salvos em `data_dir/llm_config.json`. Nunca armazena chave de API.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
struct LlmConfigFile {
    provider: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    model: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    base_url: Option<String>,
}

impl Default for LlmConfigFile {
    fn default() -> Self {
        Self {
            provider: "gemini".to_string(),
            model: None,
            base_url: None,
        }
    }
}

#[derive(Serialize)]
struct LlmConfigStatus {
    provider: String,
    model: Option<String>,
    base_url: Option<String>,
    configured: bool,
    store_available: bool,
    has_key_by_provider: HashMap<String, bool>,
    error: Option<String>,
}

trait SecretStore {
    fn get(&self, user: &str) -> Result<Option<String>, String>;
    fn set(&self, user: &str, value: &str) -> Result<(), String>;
    fn delete(&self, user: &str) -> Result<(), String>;
}

struct OsKeyringStore;

impl SecretStore for OsKeyringStore {
    fn get(&self, user: &str) -> Result<Option<String>, String> {
        let entry = keyring::Entry::new(KEYRING_SERVICE, user).map_err(|e| e.to_string())?;
        match entry.get_password() {
            Ok(key) => Ok(Some(key)),
            Err(keyring::Error::NoEntry) => Ok(None),
            Err(e) => Err(e.to_string()),
        }
    }

    fn set(&self, user: &str, value: &str) -> Result<(), String> {
        let entry = keyring::Entry::new(KEYRING_SERVICE, user).map_err(|e| e.to_string())?;
        entry.set_password(value).map_err(|e| e.to_string())
    }

    fn delete(&self, user: &str) -> Result<(), String> {
        let entry = keyring::Entry::new(KEYRING_SERVICE, user).map_err(|e| e.to_string())?;
        match entry.delete_credential() {
            Ok(()) | Err(keyring::Error::NoEntry) => Ok(()),
            Err(e) => Err(e.to_string()),
        }
    }
}

fn normalize_provider(raw: &str) -> Result<String, String> {
    let clean = raw.trim().to_ascii_lowercase();
    if KNOWN_PROVIDERS.contains(&clean.as_str()) {
        Ok(clean)
    } else {
        Err(format!("Provedor desconhecido: '{raw}'."))
    }
}

fn provider_key_user(provider: &str) -> String {
    format!("llm-key-{provider}")
}

fn default_base_url_for(provider: &str) -> &'static str {
    match provider {
        "gemini" => "https://generativelanguage.googleapis.com/v1beta",
        "openai" => "https://api.openai.com/v1",
        "openrouter" => "https://openrouter.ai/api/v1",
        "mistral" => "https://api.mistral.ai/v1",
        "zai" => "https://api.z.ai/api/paas/v4",
        "together" => "https://api.together.xyz/v1",
        "fireworks" => "https://api.fireworks.ai/inference/v1",
        "ollama" => "http://localhost:11434/v1",
        _ => "",
    }
}

fn allow_custom_base_url_for(provider: &str) -> bool {
    matches!(provider, "zai" | "ollama")
}

/// Aceita chave vazia apenas quando o endpoint aponta explicitamente para loopback (http/https).
fn is_loopback_url(url: &str) -> bool {
    let trimmed = url.trim();
    let rest = if let Some(r) = trimmed.strip_prefix("http://") {
        r
    } else if let Some(r) = trimmed.strip_prefix("https://") {
        r
    } else {
        return false;
    };
    let authority = rest.split(&['/', '?', '#'][..]).next().unwrap_or("");
    let host_port = authority.rsplit('@').next().unwrap_or(authority);
    let host = if let Some(bracketed) = host_port.strip_prefix('[') {
        bracketed.split(']').next().unwrap_or("")
    } else {
        host_port.split(':').next().unwrap_or("")
    };
    matches!(host.to_ascii_lowercase().as_str(), "localhost" | "127.0.0.1" | "::1")
}

fn validate_custom_base_url(provider: &str, raw: Option<String>) -> Result<Option<String>, String> {
    let cleaned = raw
        .map(|s| s.trim().trim_end_matches('/').to_string())
        .filter(|s| !s.is_empty());
    let Some(url) = cleaned else {
        return Ok(None);
    };
    let default_url = default_base_url_for(provider).trim_end_matches('/');
    if !allow_custom_base_url_for(provider) {
        if url == default_url {
            return Ok(None);
        }
        return Err(format!("O provedor '{provider}' não permite alterar a Base URL."));
    }
    if !(url.starts_with("https://") || url.starts_with("http://")) {
        return Err("Base URL inválida. Use https:// (ou http:// apenas para servidor local).".into());
    }
    if url.starts_with("http://") && !is_loopback_url(&url) {
        return Err("Use https:// para servidores que não sejam locais.".into());
    }
    Ok(Some(url))
}

fn effective_base_url<'a>(provider: &str, base_url: Option<&'a str>) -> &'a str {
    match base_url.map(str::trim).filter(|s| !s.is_empty()) {
        Some(url) => url,
        None => default_base_url_for(provider),
    }
}

fn llm_config_path(data_dir: &Path) -> PathBuf {
    data_dir.join(LLM_CONFIG_FILENAME)
}

fn load_llm_config(data_dir: &Path) -> (LlmConfigFile, bool) {
    let path = llm_config_path(data_dir);
    let Ok(raw) = fs::read_to_string(&path) else {
        return (LlmConfigFile::default(), false);
    };
    match serde_json::from_str::<LlmConfigFile>(&raw) {
        Ok(mut cfg) => {
            if let Ok(valid) = normalize_provider(&cfg.provider) {
                cfg.provider = valid;
            } else {
                cfg.provider = "gemini".to_string();
            }
            cfg.model = cfg.model.map(|s| s.trim().to_string()).filter(|s| !s.is_empty());
            cfg.base_url = cfg.base_url.map(|s| s.trim().trim_end_matches('/').to_string()).filter(|s| !s.is_empty());
            (cfg, true)
        }
        Err(_) => (LlmConfigFile::default(), false),
    }
}

fn save_llm_config(data_dir: &Path, cfg: &LlmConfigFile) -> Result<(), String> {
    fs::create_dir_all(data_dir).map_err(|e| e.to_string())?;
    let json = serde_json::to_string_pretty(cfg).map_err(|e| e.to_string())?;
    fs::write(llm_config_path(data_dir), json).map_err(|e| e.to_string())
}

fn remove_llm_config(data_dir: &Path) -> Result<(), String> {
    let path = llm_config_path(data_dir);
    if path.exists() {
        fs::remove_file(path).map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// Aplica `llm_config.json` antes de gravar no cofre e desfaz o JSON se a gravação no cofre falhar.
fn apply_llm_config(
    data_dir: &Path,
    store: &dyn SecretStore,
    provider: &str,
    model: Option<String>,
    base_url: Option<String>,
    key: Option<String>,
    use_saved_key: bool,
) -> Result<(), String> {
    let provider = normalize_provider(provider)?;
    let trimmed_key = key.unwrap_or_default().trim().to_string();
    let trimmed_model = model.map(|s| s.trim().to_string()).filter(|s| !s.is_empty());
    let trimmed_url = validate_custom_base_url(&provider, base_url)?;
    let is_local = provider != "gemini" && is_loopback_url(effective_base_url(&provider, trimmed_url.as_deref()));

    if trimmed_key.is_empty() {
        if use_saved_key {
            let saved = read_provider_key(store, &provider)?;
            if saved.is_none() && !is_local {
                return Err("Nenhuma chave salva para este provedor. Informe a chave de API.".into());
            }
        } else if !is_local {
            return Err("Informe a chave de API.".into());
        }
    }

    let path = llm_config_path(data_dir);
    let previous = fs::read(&path).ok();
    let cfg = LlmConfigFile {
        provider: provider.clone(),
        model: trimmed_model,
        base_url: trimmed_url,
    };
    save_llm_config(data_dir, &cfg)?;

    if !trimmed_key.is_empty() {
        if let Err(err) = save_provider_key(store, &provider, &trimmed_key) {
            // Reverte llm_config.json para manter cofre e arquivo sincronizados em caso de falha.
            match previous {
                Some(bytes) => {
                    let _ = fs::write(&path, bytes);
                }
                None => {
                    let _ = fs::remove_file(&path);
                }
            }
            return Err(err);
        }
    }
    Ok(())
}

/// Remove a chave do provedor e limpa `llm_config.json` se ele era o provedor ativo.
/// Retorna `true` quando o provedor removido era o ativo e o núcleo precisa reiniciar.
fn clear_provider_key_and_config(
    data_dir: &Path,
    store: &dyn SecretStore,
    provider: Option<String>,
) -> Result<bool, String> {
    let (active_cfg, _) = load_llm_config(data_dir);
    let target = match provider {
        Some(p) if !p.trim().is_empty() => normalize_provider(&p)?,
        _ => active_cfg.provider.clone(),
    };
    delete_provider_key(store, &target)?;
    if target == active_cfg.provider {
        remove_llm_config(data_dir)?;
        Ok(true)
    } else {
        Ok(false)
    }
}

fn read_provider_key(store: &dyn SecretStore, provider: &str) -> Result<Option<String>, String> {
    let primary = provider_key_user(provider);
    if let Some(key) = store.get(&primary)? {
        if !key.trim().is_empty() {
            return Ok(Some(key));
        }
    }
    // Retrocompatibilidade v0.1.0: instalações anteriores guardavam a chave Gemini em `gemini-api-key`.
    if provider == "gemini" {
        if let Some(legacy) = store.get(KEYRING_USER)? {
            if !legacy.trim().is_empty() {
                return Ok(Some(legacy));
            }
        }
    }
    Ok(None)
}

fn save_provider_key(store: &dyn SecretStore, provider: &str, key: &str) -> Result<(), String> {
    store.set(&provider_key_user(provider), key)
}

fn delete_provider_key(store: &dyn SecretStore, provider: &str) -> Result<(), String> {
    store.delete(&provider_key_user(provider))?;
    if provider == "gemini" {
        store.delete(KEYRING_USER)?;
    }
    Ok(())
}

#[derive(Debug, PartialEq)]
struct ResolvedLlmEnv {
    set: Vec<(String, String)>,
    remove: Vec<String>,
}

fn resolve_llm_env(data_dir: &Path, store: &dyn SecretStore, debug_mode: bool) -> ResolvedLlmEnv {
    let (cfg, has_config_file) = load_llm_config(data_dir);
    let key = read_provider_key(store, &cfg.provider).ok().flatten();

    // Em desenvolvimento sem llm_config.json nem chave no cofre, preserva variáveis de ambiente manuais.
    if debug_mode && !has_config_file && key.is_none() {
        return ResolvedLlmEnv { set: vec![], remove: vec![] };
    }

    let mut set = vec![("ADITO_LLM_PROVIDER".to_string(), cfg.provider.clone())];
    let mut remove = vec![];

    match cfg.model {
        Some(model) => set.push(("ADITO_LLM_MODEL".to_string(), model)),
        None => remove.push("ADITO_LLM_MODEL".to_string()),
    }
    match cfg.base_url {
        Some(url) => set.push(("ADITO_LLM_BASE_URL".to_string(), url)),
        None => remove.push("ADITO_LLM_BASE_URL".to_string()),
    }
    match key {
        Some(secret) => {
            set.push(("ADITO_LLM_API_KEY".to_string(), secret.clone()));
            if cfg.provider == "gemini" {
                set.push(("GEMINI_API_KEY".to_string(), secret));
            } else {
                remove.push("GEMINI_API_KEY".to_string());
                remove.push("GOOGLE_API_KEY".to_string());
            }
        }
        None => {
            remove.push("ADITO_LLM_API_KEY".to_string());
            if cfg.provider != "gemini" || !debug_mode {
                remove.push("GEMINI_API_KEY".to_string());
                remove.push("GOOGLE_API_KEY".to_string());
            }
        }
    }

    ResolvedLlmEnv { set, remove }
}

fn build_llm_config_status(data_dir: &Path, store: &dyn SecretStore) -> LlmConfigStatus {
    let (cfg, _) = load_llm_config(data_dir);
    let mut has_key_by_provider = HashMap::new();
    let mut store_available = true;
    let mut error = None;

    for &prov in KNOWN_PROVIDERS {
        match read_provider_key(store, prov) {
            Ok(found) => {
                has_key_by_provider.insert(prov.to_string(), found.is_some());
            }
            Err(err) => {
                store_available = false;
                if error.is_none() {
                    error = Some(err);
                }
                has_key_by_provider.insert(prov.to_string(), false);
            }
        }
    }

    let active_has_key = has_key_by_provider.get(&cfg.provider).copied().unwrap_or(false);
    let active_is_local = cfg.provider != "gemini"
        && is_loopback_url(effective_base_url(&cfg.provider, cfg.base_url.as_deref()));
    let configured = active_has_key || active_is_local;

    LlmConfigStatus {
        provider: cfg.provider,
        model: cfg.model,
        base_url: cfg.base_url,
        configured,
        store_available,
        has_key_by_provider,
        error,
    }
}

fn key_entry() -> Result<keyring::Entry, String> {
    keyring::Entry::new(KEYRING_SERVICE, KEYRING_USER).map_err(|e| e.to_string())
}

/// Copia a chave do cofre do SO do serviço antigo para o do Adito (uma vez) e remove a antiga.
fn migrate_legacy_key() {
    let Ok(new) = key_entry() else { return };
    if !matches!(new.get_password(), Err(keyring::Error::NoEntry)) {
        return;
    }
    for legacy in LEGACY_IDENTIFIERS {
        let Ok(old) = keyring::Entry::new(legacy, KEYRING_USER) else { continue };
        if let Ok(secret) = old.get_password() {
            if new.set_password(&secret).is_ok() {
                let _ = old.delete_credential();
            }
            return;
        }
    }
}

const APP_IDENTIFIER: &str = "br.edu.ifes.leds.adito";

/// Pasta-base dos dados locais do usuário (a mesma que o Tauri usa em `app_local_data_dir`).
fn local_data_base() -> Option<PathBuf> {
    if cfg!(windows) {
        std::env::var_os("LOCALAPPDATA").map(PathBuf::from)
    } else if cfg!(target_os = "macos") {
        std::env::var_os("HOME").map(|h| PathBuf::from(h).join("Library/Application Support"))
    } else {
        std::env::var_os("XDG_DATA_HOME")
            .map(PathBuf::from)
            .or_else(|| std::env::var_os("HOME").map(|h| PathBuf::from(h).join(".local/share")))
    }
}

/// Precisa rodar antes de a janela existir: o WebView cria a pasta nova assim que sobe, e a
/// migração só acontece quando a pasta nova ainda não existe.
fn migrate_legacy_data() {
    let Some(base) = local_data_base() else { return };
    if let Err(e) = migrate_legacy_dir(&base.join(APP_IDENTIFIER)) {
        eprintln!("[migração] não foi possível mover a pasta de dados antiga: {e}");
    }
}

/// Move a pasta de dados antiga mais recente (irmã da nova, mesmo pai) para o nome do Adito,
/// se a nova ainda não existe.
fn migrate_legacy_dir(data_dir: &Path) -> std::io::Result<bool> {
    let Some(parent) = data_dir.parent() else { return Ok(false) };
    if data_dir.exists() {
        return Ok(false);
    }
    let Some(legacy) = LEGACY_IDENTIFIERS.iter().map(|n| parent.join(n)).find(|p| p.is_dir()) else {
        return Ok(false);
    };
    fs::rename(&legacy, data_dir)?;
    Ok(true)
}

// ── Processo do núcleo ───────────────────────────────────────────────────────

/// Em desenvolvimento usa o Python do `.venv` do repositório; empacotado, o binário
/// `adito-backend` (sidecar) que fica ao lado do executável do app.
fn core_command() -> Command {
    if cfg!(debug_assertions) {
        let repo = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf();
        let python = std::env::var("ADITO_PYTHON").map(PathBuf::from).unwrap_or_else(|_| {
            if cfg!(windows) {
                repo.join(".venv").join("Scripts").join("python.exe")
            } else {
                repo.join(".venv").join("bin").join("python")
            }
        });
        let nucleo_dir = repo.join("backend").join("nucleo");
        let mut cmd = Command::new(python);
        cmd.arg(nucleo_dir.join("desktop_server.py")).current_dir(nucleo_dir);
        cmd
    } else {
        let exe_dir = std::env::current_exe().unwrap().parent().unwrap().to_path_buf();
        let name = if cfg!(windows) { "adito-backend.exe" } else { "adito-backend" };
        Command::new(exe_dir.join(name))
    }
}

impl Core {
    fn set_status(&self, status: Status, generation: u64) {
        let mut guard = self.status.lock().unwrap();
        // Ignora avisos de um processo antigo (já substituído por um reinício).
        if guard.1 == generation {
            guard.0 = status;
            self.status_changed.notify_all();
        }
    }

    fn fail_pending(&self, error: CoreError) {
        let drained: Vec<Pending> = self.pending.lock().unwrap().drain().map(|(_, p)| p).collect();
        for pending in drained {
            pending.finish(Err(error.clone()));
        }
    }

    fn spawn(self: &Arc<Self>) -> Result<(), String> {
        let generation = {
            let mut guard = self.status.lock().unwrap();
            guard.1 += 1;
            guard.0 = Status::Starting;
            guard.1
        };
        // Acrescenta ao log: um reinício (troca da chave) não apaga o que a sessão já registrou.
        let log = OpenOptions::new().create(true).append(true).open(&self.log_path).map_err(|e| e.to_string())?;
        let mut cmd = core_command();
        cmd.env("ADITO_DATA_DIR", &self.data_dir)
            .env("PYTHONUNBUFFERED", "1")
            .env("PYTHONIOENCODING", "utf-8")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::from(log));
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            cmd.creation_flags(CREATE_NO_WINDOW);
        }
        // Configuração e segredo do provedor ativo resolvidos de llm_config.json + cofre do SO.
        let resolved = resolve_llm_env(&self.data_dir, &OsKeyringStore, cfg!(debug_assertions));
        for key in resolved.remove {
            cmd.env_remove(key);
        }
        for (key, value) in resolved.set {
            cmd.env(key, value);
        }
        let mut child = cmd.spawn().map_err(|e| {
            let msg = format!("Não foi possível iniciar o núcleo: {e}");
            self.set_status(Status::Failed(msg.clone()), generation);
            msg
        })?;
        let stdin = child.stdin.take().ok_or("stdin do núcleo indisponível")?;
        let stdout = child.stdout.take().ok_or("stdout do núcleo indisponível")?;
        *self.running.lock().unwrap() = Some(Running { child, stdin, generation });

        let core = Arc::clone(self);
        std::thread::Builder::new()
            .name("nucleo-stdout".into())
            .spawn(move || core.read_loop(BufReader::new(stdout), generation))
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    /// Lê o stdout do núcleo até ele fechar, entregando cada mensagem a quem a espera.
    fn read_loop(&self, reader: impl BufRead, generation: u64) {
        for line in reader.lines() {
            let Ok(line) = line else { break };
            let Ok(msg) = serde_json::from_str::<Value>(&line) else {
                eprintln!("[núcleo] linha inválida no stdout: {line}");
                continue;
            };
            match (msg.get("id").and_then(Value::as_u64), msg.get("event").and_then(Value::as_str)) {
                (None, Some("ready")) => self.set_status(Status::Ready, generation),
                (None, Some("fatal")) => {
                    let detail = msg["data"]["message"].as_str().unwrap_or("erro desconhecido");
                    let text = format!("O núcleo não iniciou: {detail}. Veja {}", self.log_path.display());
                    self.set_status(Status::Failed(text), generation);
                }
                (Some(id), Some(_)) => {
                    // Evento de stream: vai para o Channel do pedido, se ainda existir.
                    if let Some(Pending::Stream(channel, _)) = self.pending.lock().unwrap().get(&id) {
                        let _ = channel.send(json!({ "event": msg["event"], "data": msg["data"] }));
                    }
                }
                (Some(id), None) => {
                    if let Some(pending) = self.pending.lock().unwrap().remove(&id) {
                        let reply = if msg["ok"].as_bool() == Some(true) {
                            Ok(msg.get("result").cloned().unwrap_or(Value::Null))
                        } else {
                            let err = &msg["error"];
                            Err(CoreError {
                                status: err["status"].as_u64().unwrap_or(500) as u16,
                                data: err.get("data").cloned().unwrap_or(Value::Null),
                            })
                        };
                        pending.finish(reply);
                    }
                }
                _ => {}
            }
        }

        // Fim do stdout: o processo terminou. Se não foi um reinício pedido, avisa o front.
        let current = self.status.lock().unwrap().1 == generation;
        if current {
            let text = format!("O núcleo do Adito encerrou. Veja {}", self.log_path.display());
            self.set_status(Status::Failed(text.clone()), generation);
            self.fail_pending(CoreError::new(503, text.clone()));
            let _ = self.app.emit("core://exited", text);
        }
    }

    /// Fecha o stdin (o núcleo encerra sozinho); se demorar, mata o processo.
    fn stop(&self) {
        let Some(Running { mut child, stdin, generation }) = self.running.lock().unwrap().take() else {
            return;
        };
        {
            let mut guard = self.status.lock().unwrap();
            if guard.1 == generation {
                guard.1 += 1; // o leitor deste processo não deve marcar falha
            }
        }
        drop(stdin);
        let deadline = Instant::now() + STOP_GRACE;
        while Instant::now() < deadline {
            if let Ok(Some(_)) = child.try_wait() {
                return;
            }
            std::thread::sleep(Duration::from_millis(50));
        }
        let _ = child.kill();
        let _ = child.wait();
    }

    fn restart(self: &Arc<Self>) -> Result<(), String> {
        self.stop();
        self.fail_pending(CoreError::new(503, "O núcleo está reiniciando."));
        self.spawn()
    }

    /// Espera o núcleo ficar pronto (bloqueante; chamar fora do loop assíncrono).
    fn wait_ready(&self) -> Result<(), String> {
        let started = Instant::now();
        let mut guard = self.status.lock().unwrap();
        loop {
            match &guard.0 {
                Status::Ready => return Ok(()),
                Status::Failed(msg) => return Err(msg.clone()),
                Status::Starting => {}
            }
            let elapsed = started.elapsed();
            if elapsed >= START_TIMEOUT {
                return Err(format!("O núcleo não respondeu em 90 s. Veja {}", self.log_path.display()));
            }
            guard = self.status_changed.wait_timeout(guard, START_TIMEOUT - elapsed).unwrap().0;
        }
    }

    fn write(&self, message: &Value) -> Result<(), CoreError> {
        let mut guard = self.running.lock().unwrap();
        let running = guard.as_mut().ok_or_else(|| CoreError::new(503, "O núcleo não está rodando."))?;
        let mut line = serde_json::to_string(message).map_err(|e| CoreError::new(500, e.to_string()))?;
        line.push('\n');
        running
            .stdin
            .write_all(line.as_bytes())
            .and_then(|_| running.stdin.flush())
            .map_err(|e| CoreError::new(503, format!("Falha ao falar com o núcleo: {e}")))
    }

    async fn request(self: Arc<Self>, id: u64, method: String, params: Value, pending: Pending, rx: oneshot::Receiver<Reply>) -> Reply {
        let ready = Arc::clone(&self);
        tauri::async_runtime::spawn_blocking(move || ready.wait_ready())
            .await
            .map_err(|e| CoreError::new(500, e.to_string()))?
            .map_err(|msg| CoreError::new(503, msg))?;
        {
            let mut map = self.pending.lock().unwrap();
            if map.contains_key(&id) {
                return Err(CoreError::new(400, format!("Pedido {id} já está em andamento.")));
            }
            map.insert(id, pending);
        }
        if let Err(e) = self.write(&json!({ "id": id, "method": method, "params": params })) {
            self.pending.lock().unwrap().remove(&id);
            return Err(e);
        }
        rx.await.unwrap_or_else(|_| Err(CoreError::new(503, "O núcleo encerrou antes de responder.")))
    }
}

type CoreState<'a> = State<'a, Arc<Core>>;

// ── Comandos chamados pelo front ─────────────────────────────────────────────

/// Espera o núcleo ficar pronto. O front chama ao abrir e depois de trocar a chave.
#[tauri::command]
async fn core_ready(state: CoreState<'_>) -> Result<(), String> {
    let core = Arc::clone(&state);
    tauri::async_runtime::spawn_blocking(move || core.wait_ready()).await.map_err(|e| e.to_string())?
}

#[tauri::command]
async fn core_call(state: CoreState<'_>, id: u64, method: String, params: Value) -> Result<Value, CoreError> {
    let (tx, rx) = oneshot::channel();
    Arc::clone(&state).request(id, method, params, Pending::Call(tx), rx).await
}

/// Como `core_call`, mas os eventos (token, status, result, error) chegam por `on_event` antes da resposta.
#[tauri::command]
async fn core_stream(
    state: CoreState<'_>,
    id: u64,
    method: String,
    params: Value,
    on_event: Channel<Value>,
) -> Result<Value, CoreError> {
    let (tx, rx) = oneshot::channel();
    Arc::clone(&state).request(id, method, params, Pending::Stream(on_event, tx), rx).await
}

#[tauri::command]
fn core_cancel(state: CoreState<'_>, id: u64) {
    if state.pending.lock().unwrap().contains_key(&id) {
        let _ = state.write(&json!({ "method": "$cancel", "params": { "id": id } }));
    }
}

#[tauri::command]
fn llm_key_status(state: CoreState<'_>) -> KeyStatus {
    let status = build_llm_config_status(&state.data_dir, &OsKeyringStore);
    KeyStatus {
        configured: status.configured,
        store_available: status.store_available,
        error: status.error,
    }
}

#[tauri::command]
fn llm_config_status(state: CoreState<'_>) -> LlmConfigStatus {
    build_llm_config_status(&state.data_dir, &OsKeyringStore)
}

/// Valida credencial/modelo/URL direto no núcleo Python; quando `use_saved_key=true`,
/// o Rust busca o segredo no cofre e o envia ao núcleo sem nunca expor a chave ao frontend (A03).
#[tauri::command]
async fn test_llm_config(
    state: CoreState<'_>,
    provider: String,
    model: Option<String>,
    base_url: Option<String>,
    key: Option<String>,
    use_saved_key: Option<bool>,
) -> Result<Value, CoreError> {
    let provider = normalize_provider(&provider).map_err(|e| CoreError::new(400, e))?;
    let trimmed_key = key.unwrap_or_default().trim().to_string();
    let trimmed_model = model.map(|s| s.trim().to_string()).filter(|s| !s.is_empty());
    let trimmed_url = match validate_custom_base_url(&provider, base_url) {
        Ok(url) => url,
        Err(reason) => return Ok(json!({ "ok": false, "reason": reason })),
    };
    let is_local = provider != "gemini" && is_loopback_url(effective_base_url(&provider, trimmed_url.as_deref()));

    let effective_key = if !trimmed_key.is_empty() {
        trimmed_key
    } else if use_saved_key.unwrap_or(false) {
        let prov = provider.clone();
        let saved = tauri::async_runtime::spawn_blocking(move || read_provider_key(&OsKeyringStore, &prov))
            .await
            .map_err(|e| CoreError::new(500, e.to_string()))?
            .map_err(|e| CoreError::new(500, e))?;
        match saved {
            Some(secret) => secret,
            None if is_local => String::new(),
            None => {
                return Ok(json!({
                    "ok": false,
                    "reason": "Nenhuma chave salva para este provedor. Informe a chave de API.",
                }));
            }
        }
    } else {
        String::new()
    };

    let mut params = json!({
        "provider": provider,
        "key": effective_key,
    });
    if let Some(m) = trimmed_model {
        params["model"] = json!(m);
    }
    if let Some(u) = trimmed_url {
        params["base_url"] = json!(u);
    }

    let id = INTERNAL_RPC_ID.fetch_add(1, Ordering::Relaxed);
    let (tx, rx) = oneshot::channel();
    Arc::clone(&state)
        .request(id, "config.test_llm_key".to_string(), params, Pending::Call(tx), rx)
        .await
}

/// Persiste o provedor/modelo/URL em `llm_config.json`, guarda a chave isolada no cofre (quando informada)
/// e reinicia o núcleo para aplicar a configuração.
#[tauri::command]
async fn set_llm_config(
    state: CoreState<'_>,
    provider: String,
    model: Option<String>,
    base_url: Option<String>,
    key: Option<String>,
    use_saved_key: Option<bool>,
) -> Result<(), String> {
    let core = Arc::clone(&state);
    tauri::async_runtime::spawn_blocking(move || {
        apply_llm_config(
            &core.data_dir,
            &OsKeyringStore,
            &provider,
            model,
            base_url,
            key,
            use_saved_key.unwrap_or(false),
        )?;
        core.restart()
    })
    .await
    .map_err(|e| e.to_string())?
}

/// Compatibilidade com chamadas legadas (`set_llm_key(key)` → salva chave do Gemini).
#[tauri::command]
async fn set_llm_key(state: CoreState<'_>, key: String) -> Result<(), String> {
    let key = key.trim().to_string();
    if key.is_empty() {
        return Err("Chave vazia.".into());
    }
    set_llm_config(state, "gemini".to_string(), None, None, Some(key), Some(false)).await
}

/// Remove apenas a chave do provedor selecionado (sem afetar chaves de outros provedores).
/// Quando o provedor removido era o ativo, limpa `llm_config.json` e reinicia o núcleo.
#[tauri::command]
async fn clear_llm_key(state: CoreState<'_>, provider: Option<String>) -> Result<(), String> {
    let core = Arc::clone(&state);
    tauri::async_runtime::spawn_blocking(move || {
        if clear_provider_key_and_config(&core.data_dir, &OsKeyringStore, provider)? {
            core.restart()
        } else {
            Ok(())
        }
    })
    .await
    .map_err(|e| e.to_string())?
}

// ── Base de dados cifrada (ADR-0007) ─────────────────────────────────────────

fn dados_key_entry() -> Result<keyring::Entry, String> {
    keyring::Entry::new(KEYRING_SERVICE, KEYRING_DADOS).map_err(|e| e.to_string())
}

fn read_dados_key() -> Result<Option<dados::Chave>, String> {
    match dados_key_entry()?.get_password() {
        Ok(texto) => dados::ler_chave(&texto).map(Some),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(e) => Err(e.to_string()),
    }
}

/// Em desenvolvimento o núcleo cai no `data/dados.db` do repositório quando a pasta do usuário
/// não tem um (ver `dados_db_path()` no núcleo); aí não há o que pedir na tela.
fn dados_do_repositorio() -> bool {
    cfg!(debug_assertions) && Path::new(env!("CARGO_MANIFEST_DIR")).join("../data/dados.db").is_file()
}

#[derive(Serialize)]
struct DadosStatus {
    /// Há um `dados.db` para o núcleo usar (baixado, ou o do repositório em desenvolvimento).
    instalado: bool,
    versao: Option<String>,
    desenvolvimento: bool,
    chave_configurada: bool,
}

#[tauri::command]
async fn dados_status(state: CoreState<'_>) -> Result<DadosStatus, String> {
    let data_dir = state.data_dir.clone();
    tauri::async_runtime::spawn_blocking(move || {
        let instalado = dados::ler_instalado(&data_dir);
        let desenvolvimento = instalado.is_none() && dados_do_repositorio();
        DadosStatus {
            instalado: instalado.is_some() || desenvolvimento,
            versao: instalado.map(|i| i.versao),
            desenvolvimento,
            chave_configurada: matches!(read_dados_key(), Ok(Some(_))),
        }
    })
    .await
    .map_err(|e| e.to_string())
}

#[derive(Serialize)]
struct DadosRemoto {
    versao: String,
    tamanho: u64,
    /// A versão publicada é outra que a instalada (ou não há nenhuma instalada).
    atualizacao: bool,
    /// A chave guardada não abre esta versão (falta, ou a instituição trocou a chave).
    precisa_chave: bool,
}

/// Lê o `manifest.json` publicado. Não precisa de chave nem de conta no GitHub.
#[tauri::command]
async fn dados_verificar(state: CoreState<'_>) -> Result<DadosRemoto, String> {
    let m = dados::baixar_manifesto().await?;
    let data_dir = state.data_dir.clone();
    let (local, chave) = tauri::async_runtime::spawn_blocking(move || {
        (dados::ler_instalado(&data_dir), read_dados_key().ok().flatten())
    })
    .await
    .map_err(|e| e.to_string())?;
    Ok(DadosRemoto {
        atualizacao: local.is_none_or(|l| l.versao != m.versao),
        precisa_chave: chave.is_none_or(|c| dados::chave_id(&c) != m.chave_id),
        versao: m.versao,
        tamanho: m.tamanho,
    })
}

static INSTALANDO_DADOS: AtomicBool = AtomicBool::new(false);

struct LiberaInstalacao;
impl Drop for LiberaInstalacao {
    fn drop(&mut self) {
        INSTALANDO_DADOS.store(false, Ordering::SeqCst);
    }
}

/// Baixa, confere e troca o `dados.db`. Com `chave`, usa a chave digitada e, se ela abrir o
/// pacote, guarda no cofre; sem, usa a do cofre. O `app.db` não é tocado.
/// Devolve a versão instalada; o front espera `core_ready` depois.
#[tauri::command]
async fn dados_instalar(state: CoreState<'_>, chave: Option<String>) -> Result<String, String> {
    if INSTALANDO_DADOS.swap(true, Ordering::SeqCst) {
        return Err("Os dados já estão sendo atualizados.".into());
    }
    let _libera = LiberaInstalacao;

    let digitada = match chave.as_deref().map(str::trim).filter(|t| !t.is_empty()) {
        Some(texto) => Some(dados::ler_chave(texto)?),
        None => None,
    };
    let m = dados::baixar_manifesto().await?;
    let chave = match digitada {
        Some(c) => c,
        None => tauri::async_runtime::spawn_blocking(read_dados_key)
            .await
            .map_err(|e| e.to_string())??
            .ok_or("Informe a chave dos dados.")?,
    };
    if dados::chave_id(&chave) != m.chave_id {
        return Err(if digitada.is_some() {
            "Essa chave não abre esta versão dos dados. Confira com quem te passou a chave.".into()
        } else {
            "A chave dos dados mudou. Informe a nova chave para atualizar.".into()
        });
    }
    let pacote = dados::baixar_pacote(&m).await?;

    let core = Arc::clone(&state);
    tauri::async_runtime::spawn_blocking(move || {
        let banco = dados::abrir_pacote(&chave, &pacote, &m)?;
        drop(pacote);
        let novo = dados::preparar(&core.data_dir, &banco)?;
        drop(banco);
        if digitada.is_some() {
            dados_key_entry()?.set_password(&dados::chave_texto(&chave)).map_err(|e| e.to_string())?;
        }
        // O núcleo segura o dados.db aberto (no Windows, a troca falharia): para, troca, sobe.
        core.stop();
        core.fail_pending(CoreError::new(503, "O núcleo está reiniciando para carregar os dados novos."));
        let instalado = dados::Instalado { versao: m.versao.clone(), chave_id: m.chave_id.clone() };
        let trocou = dados::trocar(&core.data_dir, &novo, &instalado);
        if trocou.is_err() {
            let _ = fs::remove_file(&novo);
        }
        core.spawn()?;
        trocou.map(|_| m.versao)
    })
    .await
    .map_err(|e| e.to_string())?
}

// ── Exportação de dados do Chat (CSV / Excel) ────────────────────────────────

const EXPORT_MAX_BYTES: usize = 20 * 1024 * 1024;
const WINDOWS_RESERVED_NAMES: &[&str] = &[
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8",
    "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
];
static EXPORT_TMP_SEQ: AtomicU64 = AtomicU64::new(1);

#[derive(Debug, Serialize, PartialEq, Eq)]
struct ExportResultado {
    nome: String,
    caminho: String,
    cancelado: bool,
}

fn validar_payload_exportacao(bytes: &[u8]) -> Result<(), String> {
    if bytes.is_empty() {
        return Err("Não há dados para exportar.".into());
    }
    if bytes.len() > EXPORT_MAX_BYTES {
        return Err("O arquivo excede o limite máximo de 20 MB para exportação.".into());
    }
    Ok(())
}

fn validar_nome_exportacao(nome: &str) -> Result<(String, String), String> {
    let limpo = nome.trim();
    if limpo.is_empty() || limpo.len() > 180 {
        return Err("Nome de arquivo inválido para exportação.".into());
    }
    if limpo.contains('/')
        || limpo.contains('\\')
        || limpo.contains("..")
        || limpo.starts_with('.')
        || limpo.ends_with('.')
        || limpo.chars().any(|c| {
            c.is_control() || matches!(c, ':' | '*' | '?' | '"' | '<' | '>' | '|')
        })
    {
        return Err("Nome de arquivo contém caracteres não permitidos.".into());
    }

    let Some((stem, ext_raw)) = limpo.rsplit_once('.') else {
        return Err("O arquivo exportado deve ter extensão .csv ou .xlsx.".into());
    };
    let ext = ext_raw.to_ascii_lowercase();
    if ext != "csv" && ext != "xlsx" {
        return Err("Extensão não suportada. Use .csv ou .xlsx.".into());
    }
    let stem_limpo = stem.trim();
    if stem_limpo.is_empty() || stem_limpo.ends_with('.') {
        return Err("Nome base do arquivo inválido.".into());
    }
    let upper = stem_limpo.to_ascii_uppercase();
    let base_reservada = upper.split('.').next().unwrap_or("");
    if WINDOWS_RESERVED_NAMES.contains(&base_reservada) {
        return Err("Nome de arquivo reservado pelo sistema operacional.".into());
    }

    Ok((stem_limpo.to_string(), ext))
}

fn garantir_extensao_exportacao(destino: PathBuf, ext: &str) -> PathBuf {
    let tem_ext = destino
        .extension()
        .and_then(|e| e.to_str())
        .is_some_and(|e| e.eq_ignore_ascii_case(ext));
    if tem_ext {
        return destino;
    }
    let mut os = destino.into_os_string();
    os.push(".");
    os.push(ext);
    PathBuf::from(os)
}

fn gravar_exportacao_destino(
    destino: PathBuf,
    ext: &str,
    bytes: &[u8],
) -> Result<ExportResultado, String> {
    validar_payload_exportacao(bytes)?;
    let destino_final = garantir_extensao_exportacao(destino.clone(), ext);
    let extensao_acrescentada = destino_final != destino;
    let parent = destino_final
        .parent()
        .ok_or_else(|| "Pasta de destino inválida para exportação.".to_string())?;
    fs::create_dir_all(parent)
        .map_err(|e| format!("Não foi possível acessar a pasta de destino: {e}"))?;

    let nome = destino_final
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or_default()
        .to_string();

    if extensao_acrescentada {
        // O diálogo nativo não confirmou sobrescrita quando o usuário omitiu a extensão:
        // usa `create_new(true)` para nunca sobrescrever silenciosamente um arquivo já existente.
        match fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&destino_final)
        {
            Ok(mut arquivo) => {
                if let Err(e) = arquivo.write_all(bytes).and_then(|_| arquivo.sync_all()) {
                    let _ = fs::remove_file(&destino_final);
                    return Err(format!("Falha ao gravar o arquivo exportado: {e}"));
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {
                return Err(format!(
                    "Já existe um arquivo \"{nome}\" nesta pasta. Escolha outro nome ou informe a extensão .{ext} no diálogo para confirmar a substituição."
                ));
            }
            Err(e) => return Err(format!("Falha ao gravar o arquivo exportado: {e}")),
        }
    } else {
        let seq = EXPORT_TMP_SEQ.fetch_add(1, Ordering::Relaxed);
        let tmp = parent.join(format!(".adito-export-{}-{seq}.tmp", std::process::id()));
        let gravacao = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&tmp)
            .and_then(|mut arquivo| arquivo.write_all(bytes).and_then(|_| arquivo.sync_all()))
            .and_then(|_| fs::rename(&tmp, &destino_final));
        if let Err(e) = gravacao {
            let _ = fs::remove_file(&tmp);
            return Err(format!("Falha ao gravar o arquivo exportado: {e}"));
        }
    }

    Ok(ExportResultado {
        nome,
        caminho: destino_final.to_string_lossy().into_owned(),
        cancelado: false,
    })
}

/// Abre o diálogo nativo "Salvar como..." do SO para o usuário escolher onde salvar o
/// arquivo `.csv` ou `.xlsx` gerado pelo frontend e grava atomicamente no destino escolhido.
#[tauri::command]
async fn exportar_arquivo(
    app: tauri::AppHandle,
    nome: String,
    bytes: Vec<u8>,
) -> Result<ExportResultado, String> {
    use tauri_plugin_dialog::DialogExt;

    validar_payload_exportacao(&bytes)?;
    let (stem, ext) = validar_nome_exportacao(&nome)?;
    let nome_sugerido = format!("{stem}.{ext}");
    let filtro_nome = if ext == "xlsx" {
        "Planilha Excel (*.xlsx)"
    } else {
        "CSV (*.csv)"
    };

    let mut dialog = app
        .dialog()
        .file()
        .set_title("Salvar dados exportados")
        .set_file_name(&nome_sugerido)
        .add_filter(filtro_nome, &[ext.as_str()]);
    if let Ok(downloads) = app.path().download_dir() {
        dialog = dialog.set_directory(downloads);
    }

    let (tx, rx) = oneshot::channel();
    dialog.save_file(move |picked| {
        let _ = tx.send(picked);
    });

    let escolhido = rx
        .await
        .map_err(|_| "Não foi possível abrir o seletor de arquivos do sistema.".to_string())?;
    let Some(file_path) = escolhido else {
        return Ok(ExportResultado {
            nome: String::new(),
            caminho: String::new(),
            cancelado: true,
        });
    };

    let destino = file_path
        .into_path()
        .map_err(|e| format!("Caminho de destino inválido: {e}"))?;

    tauri::async_runtime::spawn_blocking(move || gravar_exportacao_destino(destino, &ext, &bytes))
        .await
        .map_err(|e| e.to_string())?
}

fn setup_core(app: &tauri::App) -> Result<Arc<Core>, Box<dyn std::error::Error>> {
    let data_dir = app.path().app_local_data_dir()?;
    let log_dir = app.path().app_log_dir()?;
    migrate_legacy_key();
    fs::create_dir_all(&data_dir)?;
    fs::create_dir_all(&log_dir)?;

    let core = Arc::new(Core {
        app: app.handle().clone(),
        data_dir,
        log_path: log_dir.join("backend.log"),
        running: Mutex::new(None),
        pending: Mutex::new(HashMap::new()),
        status: Mutex::new((Status::Starting, 0)),
        status_changed: Condvar::new(),
    });
    // O log começa limpo a cada abertura do app; os reinícios só acrescentam.
    File::create(&core.log_path)?;
    // Falha ao iniciar não derruba a janela: o front mostra a mensagem que vem de core_ready.
    if let Err(e) = core.spawn() {
        eprintln!("[núcleo] {e}");
    }
    Ok(core)
}

pub fn run() {
    migrate_legacy_data();
    let mut builder = tauri::Builder::default();
    // Atualização do app (ADR-0006): lê o latest.json do GitHub Releases; o front pergunta antes.
    // Em desenvolvimento (`cargo tauri dev` / `debug_assertions`), o updater do executável fica
    // desligado para não baixar releases antigas do GitHub sobre o build local (`tauri.conf.json`
    // permanece em 0.1.0 e o CI injeta a versão da tag apenas no release).
    #[cfg(not(debug_assertions))]
    {
        builder = builder.plugin(tauri_plugin_updater::Builder::new().build());
    }
    builder
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let core = setup_core(app)?;
            app.manage(core);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            core_ready,
            core_call,
            core_stream,
            core_cancel,
            llm_key_status,
            llm_config_status,
            test_llm_config,
            set_llm_config,
            set_llm_key,
            clear_llm_key,
            dados_status,
            dados_verificar,
            dados_instalar,
            exportar_arquivo
        ])
        .build(tauri::generate_context!())
        .expect("erro ao iniciar o Adito")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                app.state::<Arc<Core>>().stop();
            }
        });
}

#[cfg(test)]
mod testes_migracao {
    use super::*;

    fn base(nome: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("adito-{nome}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&d);
        fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn identifier_igual_ao_do_tauri_conf() {
        let conf = include_str!("../tauri.conf.json");
        assert!(conf.contains(&format!("\"identifier\": \"{APP_IDENTIFIER}\"")));
    }

    #[test]
    fn move_cada_pasta_antiga_quando_a_nova_nao_existe() {
        for (i, legado) in LEGACY_IDENTIFIERS.iter().enumerate() {
            let b = base(&format!("move-{i}"));
            fs::create_dir_all(b.join(legado)).unwrap();
            fs::write(b.join(legado).join("app.db"), "x").unwrap();
            let novo = b.join("br.edu.ifes.leds.adito");
            assert!(migrate_legacy_dir(&novo).unwrap());
            assert!(novo.join("app.db").exists());
            assert!(!b.join(legado).exists());
            let _ = fs::remove_dir_all(&b);
        }
    }

    #[test]
    fn prefere_a_pasta_do_muninn_a_do_oraculo() {
        let b = base("prefere");
        fs::create_dir_all(b.join("br.edu.ifes.leds.muninn")).unwrap();
        fs::write(b.join("br.edu.ifes.leds.muninn").join("app.db"), "muninn").unwrap();
        fs::create_dir_all(b.join("br.edu.ifes.leds.oraculo-esx")).unwrap();
        let novo = b.join("br.edu.ifes.leds.adito");
        assert!(migrate_legacy_dir(&novo).unwrap());
        assert_eq!(fs::read_to_string(novo.join("app.db")).unwrap(), "muninn");
        assert!(b.join("br.edu.ifes.leds.oraculo-esx").exists());
        let _ = fs::remove_dir_all(&b);
    }

    #[test]
    fn nao_sobrescreve_pasta_nova_existente() {
        let b = base("nao-sobrescreve");
        fs::create_dir_all(b.join(LEGACY_IDENTIFIERS[0])).unwrap();
        let novo = b.join("br.edu.ifes.leds.adito");
        fs::create_dir_all(&novo).unwrap();
        assert!(!migrate_legacy_dir(&novo).unwrap());
        assert!(b.join(LEGACY_IDENTIFIERS[0]).exists());
        let _ = fs::remove_dir_all(&b);
    }

    struct MemStore(Mutex<HashMap<String, String>>);

    impl MemStore {
        fn new() -> Self {
            Self(Mutex::new(HashMap::new()))
        }
    }

    impl SecretStore for MemStore {
        fn get(&self, user: &str) -> Result<Option<String>, String> {
            Ok(self.0.lock().unwrap().get(user).cloned())
        }
        fn set(&self, user: &str, value: &str) -> Result<(), String> {
            self.0.lock().unwrap().insert(user.to_string(), value.to_string());
            Ok(())
        }
        fn delete(&self, user: &str) -> Result<(), String> {
            self.0.lock().unwrap().remove(user);
            Ok(())
        }
    }

    #[test]
    fn retrocompatibilidade_v010_ativa_gemini_a_partir_de_chave_legada() {
        let dir = base("llm-legacy");
        let store = MemStore::new();
        store.set(KEYRING_USER, "AIza-legada").unwrap();

        let status = build_llm_config_status(&dir, &store);
        assert_eq!(status.provider, "gemini");
        assert!(status.configured);
        assert_eq!(status.has_key_by_provider.get("gemini"), Some(&true));
        assert_eq!(status.has_key_by_provider.get("openai"), Some(&false));

        let env = resolve_llm_env(&dir, &store, false);
        assert!(env.set.contains(&("ADITO_LLM_PROVIDER".into(), "gemini".into())));
        assert!(env.set.contains(&("ADITO_LLM_API_KEY".into(), "AIza-legada".into())));
        assert!(env.set.contains(&("GEMINI_API_KEY".into(), "AIza-legada".into())));

        // Remover Gemini limpa tanto llm-key-gemini quanto gemini-api-key legado
        save_provider_key(&store, "gemini", "AIza-nova").unwrap();
        save_provider_key(&store, "openai", "sk-openai").unwrap();
        delete_provider_key(&store, "gemini").unwrap();
        assert_eq!(read_provider_key(&store, "gemini").unwrap(), None);
        assert_eq!(read_provider_key(&store, "openai").unwrap(), Some("sk-openai".into()));

        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn llm_config_json_nao_grava_segredo_e_limpa_gemini_env_ao_trocar_provedor() {
        let dir = base("llm-config-json");
        let store = MemStore::new();
        save_provider_key(&store, "gemini", "AIza-secret").unwrap();
        save_provider_key(&store, "openai", "sk-secret").unwrap();

        let cfg = LlmConfigFile {
            provider: "openai".into(),
            model: Some("gpt-4o-mini".into()),
            base_url: None,
        };
        save_llm_config(&dir, &cfg).unwrap();
        let raw = fs::read_to_string(llm_config_path(&dir)).unwrap();
        assert!(!raw.contains("sk-secret"));
        assert!(!raw.contains("AIza-secret"));

        let env = resolve_llm_env(&dir, &store, true);
        assert!(env.set.contains(&("ADITO_LLM_PROVIDER".into(), "openai".into())));
        assert!(env.set.contains(&("ADITO_LLM_MODEL".into(), "gpt-4o-mini".into())));
        assert!(env.set.contains(&("ADITO_LLM_API_KEY".into(), "sk-secret".into())));
        assert!(env.remove.contains(&"GEMINI_API_KEY".to_string()));
        assert!(env.remove.contains(&"GOOGLE_API_KEY".to_string()));

        // Chave Gemini continua preservada no cofre ao trocar para OpenAI
        assert_eq!(read_provider_key(&store, "gemini").unwrap(), Some("AIza-secret".into()));

        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn loopback_permite_ollama_sem_chave_e_rejeita_hosts_remotos() {
        assert!(is_loopback_url("http://localhost:11434/v1"));
        assert!(is_loopback_url("http://127.0.0.1:8080/v1"));
        assert!(is_loopback_url("http://[::1]:11434/v1"));
        assert!(!is_loopback_url("https://localhost.evil.com/v1"));
        assert!(!is_loopback_url("ftp://localhost:11434/v1"));
        assert!(!is_loopback_url("https://api.openai.com/v1"));

        let dir = base("llm-ollama");
        let store = MemStore::new();
        save_llm_config(&dir, &LlmConfigFile {
            provider: "ollama".into(),
            model: Some("qwen2.5:7b".into()),
            base_url: None,
        }).unwrap();

        let status = build_llm_config_status(&dir, &store);
        assert_eq!(status.provider, "ollama");
        assert!(status.configured);
        assert_eq!(status.has_key_by_provider.get("ollama"), Some(&false));

        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn base_url_exige_https_remoto_e_respeita_allow_custom_base_url() {
        assert!(validate_custom_base_url("openai", Some("https://evil.example/v1".into())).is_err());
        assert!(validate_custom_base_url("zai", Some("http://api.z.ai/api/paas/v4".into())).is_err());
        assert_eq!(
            validate_custom_base_url("zai", Some("https://open.bigmodel.cn/api/paas/v4/".into())).unwrap(),
            Some("https://open.bigmodel.cn/api/paas/v4".into())
        );
        assert_eq!(
            validate_custom_base_url("ollama", Some("http://localhost:11434/v1".into())).unwrap(),
            Some("http://localhost:11434/v1".into())
        );
    }

    #[test]
    fn clear_provedor_ativo_remove_llm_config_json_e_falha_no_cofre_reverte_json() {
        let dir = base("llm-clear-rollback");
        let store = MemStore::new();
        apply_llm_config(&dir, &store, "mistral", Some("ministral-8b-latest".into()), None, Some("mis-k".into()), false)
            .unwrap();
        assert!(llm_config_path(&dir).exists());

        // Remover provedor ativo limpa llm_config.json e sinaliza reinício.
        assert!(clear_provider_key_and_config(&dir, &store, Some("mistral".into())).unwrap());
        assert!(!llm_config_path(&dir).exists());
        assert_eq!(read_provider_key(&store, "mistral").unwrap(), None);

        // Falha ao gravar no cofre reverte llm_config.json para o estado anterior.
        struct FailingStore;
        impl SecretStore for FailingStore {
            fn get(&self, _user: &str) -> Result<Option<String>, String> { Ok(None) }
            fn set(&self, _user: &str, _value: &str) -> Result<(), String> { Err("cofre bloqueado".into()) }
            fn delete(&self, _user: &str) -> Result<(), String> { Ok(()) }
        }
        let err = apply_llm_config(&dir, &FailingStore, "openai", Some("gpt-4o-mini".into()), None, Some("sk-1".into()), false);
        assert!(err.is_err());
        assert!(!llm_config_path(&dir).exists());

        let _ = fs::remove_dir_all(&dir);
    }

    #[test]
    fn exportar_rejeita_path_traversal_extensao_e_nomes_reservados() {
        for invalido in [
            "",
            "../segredo.csv",
            "sub/arquivo.csv",
            "sub\\arquivo.xlsx",
            "arquivo.exe",
            "sem_extensao",
            ".oculto.csv",
            "CON.csv",
            "nul.xlsx",
            "com1.csv",
            "a:b.csv",
            "a*b.xlsx",
        ] {
            assert!(
                validar_nome_exportacao(invalido).is_err(),
                "deveria rejeitar '{invalido}'"
            );
        }
        assert_eq!(
            validar_nome_exportacao("adito-projetos.XLSX").unwrap(),
            ("adito-projetos".into(), "xlsx".into())
        );
        assert!(validar_payload_exportacao(b"").is_err());
        let grande = vec![b'x'; EXPORT_MAX_BYTES + 1];
        assert!(validar_payload_exportacao(&grande).is_err());
    }

    #[test]
    fn exportar_garante_extensao_e_grava_no_destino_escolhido() {
        let dir = base("export-destino");

        // Acrescenta extensão se o usuário omitiu no diálogo "Salvar como..."
        let r1 = gravar_exportacao_destino(dir.join("meus-projetos"), "xlsx", b"PK-1").unwrap();
        assert!(!r1.cancelado);
        assert_eq!(r1.nome, "meus-projetos.xlsx");
        assert_eq!(fs::read(dir.join("meus-projetos.xlsx")).unwrap(), b"PK-1");

        // Preserva ponto no nome base (ex.: relatorio.2026 -> relatorio.2026.csv)
        let r2 = gravar_exportacao_destino(dir.join("relatorio.2026"), "csv", b"a;b\n1;2").unwrap();
        assert_eq!(r2.nome, "relatorio.2026.csv");
        assert_eq!(fs::read(dir.join("relatorio.2026.csv")).unwrap(), b"a;b\n1;2");

        // Se o usuário omitiu a extensão e já existe um arquivo com essa extensão, NÃO sobrescreve
        let err_sobrescrita = gravar_exportacao_destino(dir.join("meus-projetos"), "xlsx", b"PK-NAO-SOBRESCREVER");
        assert!(err_sobrescrita.is_err());
        assert_eq!(fs::read(dir.join("meus-projetos.xlsx")).unwrap(), b"PK-1");

        // Quando o usuário confirma sobrescrita no diálogo (caminho já com extensão), substitui atomicamente
        let r3 = gravar_exportacao_destino(dir.join("meus-projetos.xlsx"), "xlsx", b"PK-2").unwrap();
        assert_eq!(r3.nome, "meus-projetos.xlsx");
        assert_eq!(fs::read(dir.join("meus-projetos.xlsx")).unwrap(), b"PK-2");

        // Mantém extensão existente independente de maiúsculas/minúsculas
        let r4 = gravar_exportacao_destino(dir.join("SAIDA.CSV"), "csv", b"x;y").unwrap();
        assert_eq!(r4.nome, "SAIDA.CSV");
        assert_eq!(fs::read(dir.join("SAIDA.CSV")).unwrap(), b"x;y");

        let _ = fs::remove_dir_all(&dir);
    }
}
