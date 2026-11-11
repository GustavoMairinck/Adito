//! Casca desktop do Oráculo ESX.
//!
//! Ao abrir: escolhe uma porta livre em 127.0.0.1, gera um token aleatório e sobe o
//! backend Python (`desktop_server.py`) com esse token. O front pede `backend_info`,
//! que espera o `/health` responder e devolve a URL e o token. Ao fechar, encerra o backend.
//!
//! A chave da Mistral fica no cofre do SO e só chega ao backend por variável de ambiente
//! ao subir o processo; trocar a chave reinicia o backend na mesma porta e com o mesmo token.

use std::fs::{self, File};
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use serde::Serialize;
use tauri::{Manager, RunEvent, State};

const BACKEND_START_TIMEOUT: Duration = Duration::from_secs(90);
const KEYRING_SERVICE: &str = "br.edu.ifes.leds.oraculo-esx";
const KEYRING_USER: &str = "mistral-api-key";

struct Backend {
    port: u16,
    token: String,
    data_dir: PathBuf,
    log_path: PathBuf,
    child: Mutex<Option<Child>>,
}

#[derive(Serialize)]
struct BackendInfo {
    base_url: String,
    token: String,
}

#[derive(Serialize)]
struct KeyStatus {
    configured: bool,
    /// Falso quando o cofre do SO não está disponível (ex.: Linux sem Secret Service).
    store_available: bool,
    error: Option<String>,
}

fn free_port() -> std::io::Result<u16> {
    Ok(TcpListener::bind("127.0.0.1:0")?.local_addr()?.port())
}

fn health_ok(port: u16) -> bool {
    let Ok(mut stream) = TcpStream::connect_timeout(&([127, 0, 0, 1], port).into(), Duration::from_millis(500)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
    if stream
        .write_all(b"GET /health HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
        .is_err()
    {
        return false;
    }
    let mut head = [0u8; 16];
    let n = stream.read(&mut head).unwrap_or(0);
    String::from_utf8_lossy(&head[..n]).contains(" 200")
}

// ── Cofre do SO ──────────────────────────────────────────────────────────────

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

// ── Backend ──────────────────────────────────────────────────────────────────

/// Em desenvolvimento usa o Python do `.venv` do repositório; empacotado, o binário
/// `oraculo-backend` (sidecar) que fica ao lado do executável do app.
fn backend_command(port: u16) -> Command {
    let port_arg = port.to_string();
    if cfg!(debug_assertions) {
        let repo = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf();
        let python = std::env::var("ORACULO_PYTHON").map(PathBuf::from).unwrap_or_else(|_| {
            if cfg!(windows) {
                repo.join(".venv").join("Scripts").join("python.exe")
            } else {
                repo.join(".venv").join("bin").join("python")
            }
        });
        let api_dir = repo.join("backend").join("api");
        let mut cmd = Command::new(python);
        cmd.arg(api_dir.join("desktop_server.py"))
            .args(["--port", &port_arg])
            .current_dir(api_dir);
        cmd
    } else {
        let exe_dir = std::env::current_exe().unwrap().parent().unwrap().to_path_buf();
        let name = if cfg!(windows) { "oraculo-backend.exe" } else { "oraculo-backend" };
        let mut cmd = Command::new(exe_dir.join(name));
        cmd.args(["--port", &port_arg]);
        cmd
    }
}

fn spawn_backend(backend: &Backend) -> Result<Child, String> {
    let log = File::create(&backend.log_path).map_err(|e| e.to_string())?;
    let mut cmd = backend_command(backend.port);
    cmd.env("ORACULO_LOCAL_TOKEN", &backend.token)
        .env("ORACULO_DATA_DIR", &backend.data_dir)
        .env("DJANGO_DEBUG", "false")
        .env("PYTHONUNBUFFERED", "1")
        .stdin(Stdio::null())
        .stdout(Stdio::from(log.try_clone().map_err(|e| e.to_string())?))
        .stderr(Stdio::from(log));
    // Chave do cofre; sem ela o backend sobe e o chat avisa que falta configurar.
    // Em desenvolvimento, uma MISTRAL_API_KEY no ambiente vale se o cofre estiver vazio.
    match read_key() {
        Ok(Some(key)) => {
            cmd.env("MISTRAL_API_KEY", key);
        }
        _ if cfg!(debug_assertions) => {}
        _ => {
            cmd.env_remove("MISTRAL_API_KEY");
        }
    }
    cmd.spawn().map_err(|e| e.to_string())
}

fn stop_backend(backend: &Backend) {
    if let Some(mut child) = backend.child.lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

fn restart_backend(backend: &Backend) -> Result<(), String> {
    stop_backend(backend);
    let child = spawn_backend(backend)?;
    *backend.child.lock().unwrap() = Some(child);
    Ok(())
}

fn setup_backend(app: &tauri::App) -> Result<Backend, Box<dyn std::error::Error>> {
    let data_dir = app.path().app_local_data_dir()?;
    let log_dir = app.path().app_log_dir()?;
    fs::create_dir_all(&data_dir)?;
    fs::create_dir_all(&log_dir)?;

    let backend = Backend {
        port: free_port()?,
        token: uuid::Uuid::new_v4().simple().to_string(),
        data_dir,
        log_path: log_dir.join("backend.log"),
        child: Mutex::new(None),
    };
    restart_backend(&backend)?;
    Ok(backend)
}

// ── Comandos chamados pelo front ─────────────────────────────────────────────

#[tauri::command]
async fn backend_info(state: State<'_, Backend>) -> Result<BackendInfo, String> {
    let port = state.port;
    let started = Instant::now();
    loop {
        if health_ok(port) {
            return Ok(BackendInfo { base_url: format!("http://127.0.0.1:{port}"), token: state.token.clone() });
        }
        if let Some(child) = state.child.lock().unwrap().as_mut() {
            if let Ok(Some(status)) = child.try_wait() {
                return Err(format!("O backend encerrou ({status}). Veja {}", state.log_path.display()));
            }
        }
        if started.elapsed() > BACKEND_START_TIMEOUT {
            return Err(format!("O backend não respondeu em 90 s. Veja {}", state.log_path.display()));
        }
        tauri::async_runtime::spawn_blocking(|| std::thread::sleep(Duration::from_millis(300)))
            .await
            .map_err(|e| e.to_string())?;
    }
}

#[tauri::command]
fn llm_key_status() -> KeyStatus {
    match read_key() {
        Ok(found) => KeyStatus { configured: found.is_some(), store_available: true, error: None },
        Err(e) => KeyStatus { configured: false, store_available: false, error: Some(e) },
    }
}

/// Guarda a chave no cofre e reinicia o backend para ele passar a usá-la.
/// O front testa a chave antes (POST /api/config/test-llm-key) e depois chama backend_info de novo.
#[tauri::command]
fn set_llm_key(state: State<'_, Backend>, key: String) -> Result<(), String> {
    let key = key.trim();
    if key.is_empty() {
        return Err("Chave vazia.".into());
    }
    key_entry()?.set_password(key).map_err(|e| e.to_string())?;
    restart_backend(&state)
}

#[tauri::command]
fn clear_llm_key(state: State<'_, Backend>) -> Result<(), String> {
    match key_entry()?.delete_credential() {
        Ok(()) | Err(keyring::Error::NoEntry) => restart_backend(&state),
        Err(e) => Err(e.to_string()),
    }
}

pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let backend = setup_backend(app)?;
            app.manage(backend);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![backend_info, llm_key_status, set_llm_key, clear_llm_key])
        .build(tauri::generate_context!())
        .expect("erro ao iniciar o Oráculo ESX")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                stop_backend(&app.state::<Backend>());
            }
        });
}
