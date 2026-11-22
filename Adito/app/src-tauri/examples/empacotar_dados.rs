//! Tranca o `dados.db` para publicar no GitHub Releases (ADR-0007).
//!
//! Gerar a chave institucional (uma vez, ou a cada rotação):
//!     cargo run --example empacotar_dados -- gerar-chave
//!
//! Empacotar uma carga nova (a chave vem do ambiente, nunca da linha de comando):
//!     ADITO_DADOS_CHAVE=<64 hex> cargo run --example empacotar_dados -- empacotar <dados.db> <pasta-saida> [versao]
//!
//! Gera `<pasta-saida>/dados-<versao>-<sha>.db.enc` e `<pasta-saida>/manifest.json`. A versão padrão é a data de hoje (UTC).
//! Usa as mesmas funções que o app usa para abrir o pacote (`adito_lib::dados`).

use std::path::PathBuf;
use std::process::ExitCode;

use adito_lib::dados;

fn hoje_utc() -> String {
    // Dias desde 1970 → data civil (algoritmo de Howard Hinnant), sem depender de crate de datas.
    let segundos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let z = (segundos / 86_400) as i64 + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z - era * 146_097;
    let yoe = (doe - doe / 1_460 + doe / 36_524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = yoe + era * 400 + i64::from(m <= 2);
    format!("{y:04}-{m:02}-{d:02}")
}

fn empacotar(args: &[String]) -> Result<(), String> {
    let [entrada, saida, resto @ ..] = args else {
        return Err("uso: empacotar <dados.db> <pasta-saida> [versao]".into());
    };
    let versao = resto.first().cloned().unwrap_or_else(hoje_utc);
    let texto = std::env::var("ADITO_DADOS_CHAVE")
        .map_err(|_| "defina ADITO_DADOS_CHAVE com a chave institucional (64 hex)".to_string())?;
    let chave = dados::ler_chave(&texto)?;

    let banco = std::fs::read(entrada).map_err(|e| format!("{entrada}: {e}"))?;
    let (pacote, manifesto) = dados::empacotar(&chave, &banco, &versao)?;
    // Confere ida e volta antes de publicar.
    if dados::abrir_pacote(&chave, &pacote, &manifesto)? != banco {
        return Err("conferência falhou: o pacote não abre de volta no mesmo banco".into());
    }

    let saida = PathBuf::from(saida);
    std::fs::create_dir_all(&saida).map_err(|e| e.to_string())?;
    std::fs::write(saida.join(&manifesto.arquivo), &pacote).map_err(|e| e.to_string())?;
    let json = serde_json::to_string_pretty(&manifesto).map_err(|e| e.to_string())?;
    std::fs::write(saida.join(dados::MANIFESTO), json + "\n").map_err(|e| e.to_string())?;

    println!("versão:   {}", manifesto.versao);
    println!("tamanho:  {} bytes", manifesto.tamanho);
    println!("sha256:   {}", manifesto.sha256);
    println!("chave_id: {}", manifesto.chave_id);
    println!("gerados:  {}/{{{}, {}}}", saida.display(), manifesto.arquivo, dados::MANIFESTO);
    Ok(())
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let resultado = match args.first().map(String::as_str) {
        Some("gerar-chave") => {
            let texto = dados::gerar_chave();
            let chave = dados::ler_chave(&texto).expect("chave gerada é válida");
            println!("{texto}");
            eprintln!("chave_id: {} (guarde a chave num cofre; ela não é recuperável)", dados::chave_id(&chave));
            Ok(())
        }
        Some("empacotar") => empacotar(&args[1..]),
        _ => Err("uso: empacotar_dados gerar-chave | empacotar <dados.db> <pasta-saida> [versao]".into()),
    };
    match resultado {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("erro: {e}");
            ExitCode::FAILURE
        }
    }
}
