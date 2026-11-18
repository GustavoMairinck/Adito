//! Casca desktop do Muninn.
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

use std::collections::HashMap;
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::{Arc, Condvar, Mutex};
use std::time::{Duration, Instant};

use serde::Serialize;
use serde_json::{json, Value};
use tauri::ipc::Channel;
use tauri::{AppHandle, Emitter, Manager, RunEvent, State};
use tokio::sync::oneshot;

const START_TIMEOUT: Duration = Duration::from_secs(90);
const STOP_GRACE: Duration = Duration::from_secs(3);
const KEYRING_SERVICE: &str = "br.edu.ifes.leds.muninn";
const KEYRING_USER: &str = "gemini-api-key";

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

// ── Cofre do SO ──────────────────────────────────────────────────────────────

#[derive(Serialize)]
struct KeyStatus {
    configured: bool,
    /// Falso quando o cofre do SO não está disponível (ex.: Linux sem Secret Service).
    store_available: bool,
    error: Option<String>,
}

fn key_entry() -> Result<keyring::Entry, String> {
    keyring::Entry::new(KEYRING_SERVICE, KEYRING_USER).map_err(|e| e.to_string())
}

fn read_key() -> Result<Option<String>, String> {
    match key_entry()?.get_password() {
        Ok(key) => Ok(Some(key)),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(e) => Err(e.to_string()),
    }
}

// ── Processo do núcleo ───────────────────────────────────────────────────────

/// Em desenvolvimento usa o Python do `.venv` do repositório; empacotado, o binário
/// `muninn-backend` (sidecar) que fica ao lado do executável do app.
fn core_command() -> Command {
    if cfg!(debug_assertions) {
        let repo = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf();
        let python = std::env::var("MUNINN_PYTHON").map(PathBuf::from).unwrap_or_else(|_| {
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
        let name = if cfg!(windows) { "muninn-backend.exe" } else { "muninn-backend" };
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
        cmd.env("MUNINN_DATA_DIR", &self.data_dir)
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
        // Chave do cofre; sem ela o núcleo sobe e o chat avisa que falta configurar.
        // Em desenvolvimento, uma GEMINI_API_KEY no ambiente vale se o cofre estiver vazio.
        match read_key() {
            Ok(Some(key)) => {
                cmd.env("GEMINI_API_KEY", key);
            }
            _ if cfg!(debug_assertions) => {}
            _ => {
                cmd.env_remove("GEMINI_API_KEY");
            }
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
            let text = format!("O núcleo do Muninn encerrou. Veja {}", self.log_path.display());
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
fn llm_key_status() -> KeyStatus {
    match read_key() {
        Ok(found) => KeyStatus { configured: found.is_some(), store_available: true, error: None },
        Err(e) => KeyStatus { configured: false, store_available: false, error: Some(e) },
    }
}

/// Guarda a chave no cofre e reinicia o núcleo para ele passar a usá-la.
/// O front testa a chave antes (`config.test_llm_key`) e depois espera `core_ready`.
/// Assíncronos para o reinício (até alguns segundos) não travar a janela.
#[tauri::command]
async fn set_llm_key(state: CoreState<'_>, key: String) -> Result<(), String> {
    let key = key.trim().to_string();
    if key.is_empty() {
        return Err("Chave vazia.".into());
    }
    let core = Arc::clone(&state);
    tauri::async_runtime::spawn_blocking(move || {
        key_entry()?.set_password(&key).map_err(|e| e.to_string())?;
        core.restart()
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
async fn clear_llm_key(state: CoreState<'_>) -> Result<(), String> {
    let core = Arc::clone(&state);
    tauri::async_runtime::spawn_blocking(move || match key_entry()?.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => core.restart(),
        Err(e) => Err(e.to_string()),
    })
    .await
    .map_err(|e| e.to_string())?
}

fn setup_core(app: &tauri::App) -> Result<Arc<Core>, Box<dyn std::error::Error>> {
    let data_dir = app.path().app_local_data_dir()?;
    let log_dir = app.path().app_log_dir()?;
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
    tauri::Builder::default()
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
            set_llm_key,
            clear_llm_key
        ])
        .build(tauri::generate_context!())
        .expect("erro ao iniciar o Muninn")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                app.state::<Arc<Core>>().stop();
            }
        });
}
