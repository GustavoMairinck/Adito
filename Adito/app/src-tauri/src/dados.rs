//! Base de dados cifrada (ADR-0007).
//!
//! O `dados.db` (nomes reais de 4 bases institucionais) nunca vai dentro do instalador.
//! Ele é publicado à parte no GitHub Releases, numa release fixa de tag `dados`, como dois arquivos:
//!
//! - `dados-<versão>-<sha>.db.enc` (nome único por publicação): o banco cifrado com AES-256-GCM (chave institucional de 256 bits);
//! - `manifest.json`: aberto, diz a versão dos dados, o SHA-256 do `.enc` e qual chave abre o pacote.
//!
//! O app baixa o manifesto ao abrir, compara com a versão instalada e, se o usuário aceitar,
//! baixa o `.enc`, confere tamanho e SHA-256, decifra com a chave guardada no cofre do SO e troca
//! o `dados.db` local. O `app.db` (chat, RAG e widgets) não é tocado.
//!
//! Quem publica usa `cargo run --example empacotar_dados` (mesmas funções deste módulo).

use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::Duration;

use aes_gcm::aead::{Aead, AeadCore, KeyInit, OsRng, Payload};
use aes_gcm::{Aes256Gcm, Key, Nonce};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// Cabeçalho do `.enc`; também entra como dado autenticado no GCM.
pub const MAGIC: &[u8] = b"ADITO-DADOS-1\n";
const NONCE_LEN: usize = 12;
/// Versão do formato do pacote. Um app antigo recusa formato que não conhece.
pub const FORMATO: u32 = 1;
/// Teto do download, para um manifesto adulterado não encher o disco.
pub const TAMANHO_MAXIMO: u64 = 512 * 1024 * 1024;
const MANIFESTO_MAXIMO: u64 = 64 * 1024;
const SQLITE_HEADER: &[u8] = b"SQLite format 3\0";

/// Onde ficam `manifest.json` e `dados.db.enc`. `ADITO_DADOS_URL` troca (fork, teste local).
pub const URL_PADRAO: &str = "https://github.com/SmartIdea-ifes-serra/Adito/releases/download/dados/";
pub const MANIFESTO: &str = "manifest.json";

/// Arquivo, ao lado do `dados.db`, que guarda qual versão está instalada.
const INSTALADO: &str = "dados.json";
const BANCO: &str = "dados.db";
const BANCO_NOVO: &str = "dados.db.novo";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Manifesto {
    pub formato: u32,
    pub versao: String,
    pub arquivo: String,
    pub tamanho: u64,
    pub sha256: String,
    /// Impressão digital da chave (não a chave): diz se a chave guardada abre este pacote.
    pub chave_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Instalado {
    pub versao: String,
    pub chave_id: String,
}

// ── Chave ────────────────────────────────────────────────────────────────────

pub type Chave = [u8; 32];

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

pub fn sha256_hex(bytes: &[u8]) -> String {
    hex(&Sha256::digest(bytes))
}

/// Gera uma chave nova (64 caracteres hexadecimais).
pub fn gerar_chave() -> String {
    hex(&Aes256Gcm::generate_key(OsRng))
}

/// Texto da chave como é guardado no cofre e repassado pela instituição.
pub fn chave_texto(chave: &Chave) -> String {
    hex(chave)
}

/// Lê a chave digitada: 64 caracteres hexadecimais; ignora espaços e maiúsculas.
pub fn ler_chave(texto: &str) -> Result<Chave, String> {
    let limpo: String = texto.chars().filter(|c| !c.is_whitespace()).collect::<String>().to_ascii_lowercase();
    if limpo.len() != 64 || !limpo.chars().all(|c| c.is_ascii_hexdigit()) {
        return Err("A chave dos dados tem 64 caracteres (0-9 e a-f). Confira se foi copiada inteira.".into());
    }
    let mut chave = [0u8; 32];
    for (i, par) in limpo.as_bytes().chunks(2).enumerate() {
        let s = std::str::from_utf8(par).map_err(|e| e.to_string())?;
        chave[i] = u8::from_str_radix(s, 16).map_err(|e| e.to_string())?;
    }
    Ok(chave)
}

/// Impressão digital curta da chave. Não permite recuperar a chave.
pub fn chave_id(chave: &Chave) -> String {
    let mut h = Sha256::new();
    h.update(b"adito-dados-chave-id\0");
    h.update(chave);
    hex(&h.finalize())[..16].to_string()
}

// ── Cifrar e abrir ───────────────────────────────────────────────────────────

pub fn cifrar(chave: &Chave, dados: &[u8]) -> Result<Vec<u8>, String> {
    let cifra = Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(chave));
    let nonce = Aes256Gcm::generate_nonce(&mut OsRng);
    let cifrado = cifra
        .encrypt(&nonce, Payload { msg: dados, aad: MAGIC })
        .map_err(|_| "Falha ao cifrar os dados.".to_string())?;
    let mut pacote = Vec::with_capacity(MAGIC.len() + NONCE_LEN + cifrado.len());
    pacote.extend_from_slice(MAGIC);
    pacote.extend_from_slice(&nonce);
    pacote.extend_from_slice(&cifrado);
    Ok(pacote)
}

pub fn decifrar(chave: &Chave, pacote: &[u8]) -> Result<Vec<u8>, String> {
    let resto = pacote
        .strip_prefix(MAGIC)
        .ok_or("O arquivo baixado não é um pacote de dados do Adito.")?;
    if resto.len() < NONCE_LEN {
        return Err("Pacote de dados incompleto.".into());
    }
    let (nonce, cifrado) = resto.split_at(NONCE_LEN);
    Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(chave))
        .decrypt(Nonce::from_slice(nonce), Payload { msg: cifrado, aad: MAGIC })
        .map_err(|_| "Não foi possível abrir os dados: chave incorreta ou arquivo corrompido.".to_string())
}

/// Cifra um `dados.db` e monta o manifesto que vai junto no Release.
pub fn empacotar(chave: &Chave, banco: &[u8], versao: &str) -> Result<(Vec<u8>, Manifesto), String> {
    if !banco.starts_with(SQLITE_HEADER) {
        return Err("O arquivo de entrada não é um banco SQLite.".into());
    }
    let versao = versao.trim();
    if !nome_seguro(versao) {
        return Err("A versão dos dados só pode ter letras, números, '.', '_' e '-' (ex.: 2026-11-22).".into());
    }
    let pacote = cifrar(chave, banco)?;
    let sha256 = sha256_hex(&pacote);
    let manifesto = Manifesto {
        formato: FORMATO,
        versao: versao.to_string(),
        // Nome único por publicação (versão + início do SHA-256): o pacote novo nunca reaproveita
        // o nome de um antigo, então nem o cache do GitHub nem quem está baixando o anterior
        // veem um arquivo trocado por baixo do manifesto.
        arquivo: format!("dados-{versao}-{}.db.enc", &sha256[..12]),
        tamanho: pacote.len() as u64,
        sha256,
        chave_id: chave_id(chave),
    };
    Ok((pacote, manifesto))
}

/// Só letras, números, '.', '_' e '-', sem começar com '.': vale como nome de arquivo e trecho de URL.
fn nome_seguro(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 100
        && !s.starts_with('.')
        && s.chars().all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-'))
}

/// Confere o manifesto antes de qualquer download.
pub fn validar_manifesto(m: &Manifesto) -> Result<(), String> {
    if m.formato != FORMATO {
        return Err("Estes dados precisam de uma versão mais nova do Adito. Atualize o app primeiro.".into());
    }
    if !nome_seguro(&m.arquivo) {
        return Err("Manifesto dos dados inválido (nome de arquivo).".into());
    }
    if m.tamanho == 0 || m.tamanho > TAMANHO_MAXIMO {
        return Err("Manifesto dos dados inválido (tamanho).".into());
    }
    if m.sha256.len() != 64 || !m.sha256.chars().all(|c| c.is_ascii_hexdigit()) {
        return Err("Manifesto dos dados inválido (SHA-256).".into());
    }
    if !nome_seguro(&m.versao) {
        return Err("Manifesto dos dados inválido (versão).".into());
    }
    Ok(())
}

/// Confere tamanho, SHA-256 e chave; devolve o `dados.db` decifrado.
pub fn abrir_pacote(chave: &Chave, pacote: &[u8], m: &Manifesto) -> Result<Vec<u8>, String> {
    if pacote.len() as u64 != m.tamanho || sha256_hex(pacote) != m.sha256.to_ascii_lowercase() {
        return Err("O download dos dados chegou diferente do publicado. Tente de novo.".into());
    }
    if chave_id(chave) != m.chave_id {
        return Err("Essa chave não abre esta versão dos dados.".into());
    }
    let banco = decifrar(chave, pacote)?;
    if !banco.starts_with(SQLITE_HEADER) {
        return Err("Os dados decifrados não são um banco SQLite.".into());
    }
    Ok(banco)
}

// ── Arquivos locais ──────────────────────────────────────────────────────────

/// Versão instalada, só se o `dados.db` também estiver lá.
pub fn ler_instalado(data_dir: &Path) -> Option<Instalado> {
    if !data_dir.join(BANCO).is_file() {
        return None;
    }
    let texto = fs::read_to_string(data_dir.join(INSTALADO)).ok()?;
    serde_json::from_str(&texto).ok()
}

/// Grava o banco novo ao lado do atual (o núcleo ainda pode estar usando o atual).
pub fn preparar(data_dir: &Path, banco: &[u8]) -> Result<PathBuf, String> {
    fs::create_dir_all(data_dir).map_err(|e| e.to_string())?;
    let novo = data_dir.join(BANCO_NOVO);
    let mut f = fs::File::create(&novo).map_err(|e| format!("Não foi possível gravar os dados: {e}"))?;
    f.write_all(banco).and_then(|_| f.sync_all()).map_err(|e| format!("Não foi possível gravar os dados: {e}"))?;
    Ok(novo)
}

/// Troca o `dados.db` pelo novo e registra a versão. Chamar com o núcleo parado.
pub fn trocar(data_dir: &Path, novo: &Path, instalado: &Instalado) -> Result<(), String> {
    for lateral in ["dados.db-wal", "dados.db-shm", "dados.db-journal"] {
        let _ = fs::remove_file(data_dir.join(lateral));
    }
    fs::rename(novo, data_dir.join(BANCO)).map_err(|e| format!("Não foi possível trocar os dados: {e}"))?;
    let texto = serde_json::to_string_pretty(instalado).map_err(|e| e.to_string())?;
    fs::write(data_dir.join(INSTALADO), texto).map_err(|e| e.to_string())
}

// ── Download ─────────────────────────────────────────────────────────────────

pub fn url_base() -> String {
    let mut base = std::env::var("ADITO_DADOS_URL").unwrap_or_else(|_| URL_PADRAO.to_string());
    if !base.ends_with('/') {
        base.push('/');
    }
    base
}

fn cliente() -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .user_agent(concat!("Adito/", env!("CARGO_PKG_VERSION")))
        .connect_timeout(Duration::from_secs(15))
        .timeout(Duration::from_secs(600))
        .build()
        .map_err(|e| e.to_string())
}

/// Baixa até `limite` bytes; acima disso, desiste.
pub async fn baixar(url: &str, limite: u64) -> Result<Vec<u8>, String> {
    let sem_rede = |e: reqwest::Error| format!("Sem conexão com o GitHub ({e}).");
    let mut resposta = cliente()?.get(url).send().await.map_err(sem_rede)?;
    if !resposta.status().is_success() {
        return Err(format!("O GitHub respondeu {} para {url}.", resposta.status()));
    }
    if resposta.content_length().is_some_and(|n| n > limite) {
        return Err("Arquivo maior que o esperado; download cancelado.".into());
    }
    let mut corpo = Vec::new();
    while let Some(parte) = resposta.chunk().await.map_err(sem_rede)? {
        if corpo.len() as u64 + parte.len() as u64 > limite {
            return Err("Arquivo maior que o esperado; download cancelado.".into());
        }
        corpo.extend_from_slice(&parte);
    }
    Ok(corpo)
}

pub async fn baixar_manifesto() -> Result<Manifesto, String> {
    let corpo = baixar(&format!("{}{MANIFESTO}", url_base()), MANIFESTO_MAXIMO).await?;
    let m: Manifesto = serde_json::from_slice(&corpo).map_err(|e| format!("Manifesto dos dados ilegível: {e}"))?;
    validar_manifesto(&m)?;
    Ok(m)
}

pub async fn baixar_pacote(m: &Manifesto) -> Result<Vec<u8>, String> {
    baixar(&format!("{}{}", url_base(), m.arquivo), m.tamanho).await
}

#[cfg(test)]
mod testes {
    use super::*;

    fn banco_falso() -> Vec<u8> {
        let mut b = SQLITE_HEADER.to_vec();
        b.extend_from_slice(b"conteudo de teste sem dado pessoal");
        b
    }

    fn pasta(nome: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("adito-dados-{nome}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&d);
        fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn chave_gerada_e_lida_de_volta() {
        let texto = gerar_chave();
        assert_eq!(texto.len(), 64);
        let chave = ler_chave(&texto).unwrap();
        assert_eq!(chave_texto(&chave), texto);
        // Espaços e maiúsculas (cópia de e-mail/PDF) não atrapalham.
        let baguncada = format!("  {} \n{}", texto[..32].to_uppercase(), &texto[32..]);
        assert_eq!(ler_chave(&baguncada).unwrap(), chave);
    }

    #[test]
    fn recusa_chave_mal_formada() {
        assert!(ler_chave("").is_err());
        assert!(ler_chave(&"a".repeat(63)).is_err());
        assert!(ler_chave(&"g".repeat(64)).is_err());
    }

    #[test]
    fn empacota_e_abre() {
        let chave = ler_chave(&gerar_chave()).unwrap();
        let (pacote, m) = empacotar(&chave, &banco_falso(), "2026-11-22").unwrap();
        validar_manifesto(&m).unwrap();
        assert!(pacote.starts_with(MAGIC));
        assert_eq!(abrir_pacote(&chave, &pacote, &m).unwrap(), banco_falso());
    }

    #[test]
    fn chave_errada_nao_abre() {
        let chave = ler_chave(&gerar_chave()).unwrap();
        let outra = ler_chave(&gerar_chave()).unwrap();
        let (pacote, m) = empacotar(&chave, &banco_falso(), "v1").unwrap();
        assert!(abrir_pacote(&outra, &pacote, &m).is_err());
        // Mesmo ignorando o chave_id, o GCM recusa.
        assert!(decifrar(&outra, &pacote).is_err());
    }

    #[test]
    fn pacote_adulterado_e_recusado() {
        let chave = ler_chave(&gerar_chave()).unwrap();
        let (mut pacote, m) = empacotar(&chave, &banco_falso(), "v1").unwrap();
        let ultimo = pacote.len() - 1;
        pacote[ultimo] ^= 1;
        assert!(abrir_pacote(&chave, &pacote, &m).is_err());
        // Com o SHA "corrigido" pelo atacante, o GCM ainda recusa.
        let m2 = Manifesto { sha256: sha256_hex(&pacote), ..m };
        assert!(abrir_pacote(&chave, &pacote, &m2).is_err());
    }

    #[test]
    fn so_empacota_sqlite() {
        let chave = ler_chave(&gerar_chave()).unwrap();
        assert!(empacotar(&chave, b"nao sou sqlite", "v1").is_err());
        assert!(empacotar(&chave, &banco_falso(), "  ").is_err());
        assert!(empacotar(&chave, &banco_falso(), "../x").is_err());
        let (_, m) = empacotar(&chave, &banco_falso(), " 2026-11-22 ").unwrap();
        assert!(m.arquivo.starts_with("dados-2026-11-22-") && m.arquivo.ends_with(".db.enc"), "{}", m.arquivo);
        assert!(m.arquivo.contains(&m.sha256[..12]));
        // Duas publicações da mesma versão nunca reaproveitam o nome (o nonce muda o SHA).
        let (_, m2) = empacotar(&chave, &banco_falso(), "2026-11-22").unwrap();
        assert_ne!(m.arquivo, m2.arquivo);
        assert_eq!(m.versao, "2026-11-22");
    }

    #[test]
    fn manifesto_suspeito_e_recusado() {
        let chave = ler_chave(&gerar_chave()).unwrap();
        let (_, m) = empacotar(&chave, &banco_falso(), "v1").unwrap();
        for arquivo in ["../dados.db.enc", "a/b", "", ".oculto", "https://x"] {
            let ruim = Manifesto { arquivo: arquivo.into(), ..m.clone() };
            assert!(validar_manifesto(&ruim).is_err(), "{arquivo}");
        }
        assert!(validar_manifesto(&Manifesto { formato: 2, ..m.clone() }).is_err());
        assert!(validar_manifesto(&Manifesto { tamanho: TAMANHO_MAXIMO + 1, ..m.clone() }).is_err());
        assert!(validar_manifesto(&Manifesto { sha256: "x".into(), ..m }).is_err());
    }

    #[test]
    fn troca_o_banco_e_registra_a_versao() {
        let d = pasta("troca");
        fs::write(d.join("dados.db"), "antigo").unwrap();
        fs::write(d.join("dados.db-wal"), "wal").unwrap();
        fs::write(d.join("app.db"), "chat").unwrap();
        assert_eq!(ler_instalado(&d), None);

        let novo = preparar(&d, &banco_falso()).unwrap();
        let inst = Instalado { versao: "v2".into(), chave_id: "abc".into() };
        trocar(&d, &novo, &inst).unwrap();

        assert_eq!(fs::read(d.join("dados.db")).unwrap(), banco_falso());
        assert!(!d.join("dados.db-wal").exists());
        assert!(!novo.exists());
        assert_eq!(fs::read_to_string(d.join("app.db")).unwrap(), "chat");
        assert_eq!(ler_instalado(&d), Some(inst));
        let _ = fs::remove_dir_all(&d);
    }

    /// Servidor HTTP mínimo: responde cada caminho com o corpo dado (ou 404).
    fn servidor(arquivos: Vec<(String, Vec<u8>)>) -> String {
        use std::io::{BufRead, BufReader};
        use std::net::TcpListener;
        let escuta = TcpListener::bind("127.0.0.1:0").unwrap();
        let endereco = format!("http://{}/", escuta.local_addr().unwrap());
        std::thread::spawn(move || {
            for conexao in escuta.incoming().flatten() {
                let mut leitor = BufReader::new(conexao.try_clone().unwrap());
                let mut linha = String::new();
                leitor.read_line(&mut linha).unwrap();
                let caminho = linha.split_whitespace().nth(1).unwrap_or("/").trim_start_matches('/').to_string();
                loop {
                    let mut h = String::new();
                    if leitor.read_line(&mut h).unwrap() <= 2 { break; }
                }
                let mut saida = conexao;
                match arquivos.iter().find(|(nome, _)| *nome == caminho) {
                    Some((_, corpo)) => {
                        let _ = write!(saida, "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n", corpo.len());
                        let _ = saida.write_all(corpo);
                    }
                    None => {
                        let _ = write!(saida, "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n");
                    }
                }
            }
        });
        endereco
    }

    #[test]
    fn baixa_manifesto_e_pacote_por_http() {
        let chave = ler_chave(&gerar_chave()).unwrap();
        let (pacote, m) = empacotar(&chave, &banco_falso(), "2026-11-22").unwrap();
        let url = servidor(vec![
            (MANIFESTO.to_string(), serde_json::to_vec(&m).unwrap()),
            (m.arquivo.clone(), pacote),
        ]);
        // Único teste que mexe nesta variável.
        std::env::set_var("ADITO_DADOS_URL", &url);
        let (manifesto, baixado) = tauri::async_runtime::block_on(async {
            let manifesto = baixar_manifesto().await.unwrap();
            let baixado = baixar_pacote(&manifesto).await.unwrap();
            // Limite menor que o arquivo: desiste.
            let curto = baixar(&format!("{url}{}", manifesto.arquivo), 10).await;
            assert!(curto.is_err());
            let ausente = baixar(&format!("{url}nao-existe"), 10).await;
            assert!(ausente.unwrap_err().contains("404"));
            (manifesto, baixado)
        });
        std::env::remove_var("ADITO_DADOS_URL");
        assert_eq!(manifesto, m);
        assert_eq!(abrir_pacote(&chave, &baixado, &manifesto).unwrap(), banco_falso());
    }

    #[test]
    fn sem_banco_nao_conta_como_instalado() {
        let d = pasta("sem-banco");
        fs::write(d.join(INSTALADO), r#"{"versao":"v1","chave_id":"x"}"#).unwrap();
        assert_eq!(ler_instalado(&d), None);
        let _ = fs::remove_dir_all(&d);
    }
}
