//! Casca desktop do Oráculo ESX.
//!
//! Ao abrir: escolhe uma porta livre em 127.0.0.1, gera um token aleatório e sobe o
//! backend Python (`desktop_server.py`) com esse token. O front pede `backend_info`,
//! que espera o `/health` responder e devolve a URL e o token. Ao fechar, encerra o backend.

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

struct Backend {
    port: u16,
    token: String,
    log_path: PathBuf,
    child: Mutex<Option<Child>>,
}

#[derive(Serialize)]
struct BackendInfo {
    base_url: String,
    token: String,
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

fn start_backend(app: &tauri::App) -> Result<Backend, Box<dyn std::error::Error>> {
    let data_dir = app.path().app_local_data_dir()?;
    let log_dir = app.path().app_log_dir()?;
    fs::create_dir_all(&data_dir)?;
    fs::create_dir_all(&log_dir)?;

    let port = free_port()?;
    let token = uuid::Uuid::new_v4().simple().to_string();
    let log_path = log_dir.join("backend.log");
    let log = File::create(&log_path)?;

    let mut cmd = backend_command(port);
    cmd.env("ORACULO_LOCAL_TOKEN", &token)
        .env("ORACULO_DATA_DIR", &data_dir)
        .env("DJANGO_DEBUG", "false")
        .env("PYTHONUNBUFFERED", "1")
        .stdin(Stdio::null())
        .stdout(Stdio::from(log.try_clone()?))
        .stderr(Stdio::from(log));
    // A chave da Mistral virá do cofre do SO (próxima etapa); por ora, do ambiente se existir.
    let child = cmd.spawn()?;

    Ok(Backend { port, token, log_path, child: Mutex::new(Some(child)) })
}

fn stop_backend(backend: &Backend) {
    if let Some(mut child) = backend.child.lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

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

pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let backend = start_backend(app)?;
            app.manage(backend);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![backend_info])
        .build(tauri::generate_context!())
        .expect("erro ao iniciar o Oráculo ESX")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                stop_backend(&app.state::<Backend>());
            }
        });
}
