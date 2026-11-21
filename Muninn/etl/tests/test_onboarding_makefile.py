"""Testes offline de onboarding, setup e execução local (Issues #83, #84, #87 e #88).

Cobre sem scraping web real nem compilação Rust:
- Muninn/scripts/gerar_lista_lattes.py (#83)
- rodar_desktop.sh: guarda de cargo (#84), sanitização /snap/ e Wayland GDK_BACKEND=x11 (#87)
- Muninn/scripts/validar_etl_env.py e guardas do Makefile (#83, #84, #88)
"""
from __future__ import annotations

import csv
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = ROOT_DIR / "Muninn" / "scripts"
GERAR_LATTES = SCRIPTS_DIR / "gerar_lista_lattes.py"
VALIDAR_ENV = SCRIPTS_DIR / "validar_etl_env.py"
RODAR_DESKTOP = ROOT_DIR / "rodar_desktop.sh"
MAKEFILE = ROOT_DIR / "Makefile"
MAKE_BIN = shutil.which("make") or "/usr/bin/make"


def _make_executable(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


# ── Issue #83: gerar_lista_lattes.py ─────────────────────────────────────────


class TestGerarListaLattes:
    def test_gera_csv_de_annassign_e_deduplica(self, tmp_path: Path) -> None:
        fonte = tmp_path / "fonte.py"
        fonte.write_text(
            'ROSTER_IDS: dict[str, str] = {\n'
            '    "Docente Um": "1234567890123456",\n'
            '    "Docente Dois": "6543210987654321",\n'
            '    "Duplicado": "1234567890123456",\n'
            '    "Invalido": "123",\n'
            '}\n',
            encoding="utf-8",
        )
        saida = tmp_path / "entradas" / "lattes.csv"

        proc = subprocess.run(
            [sys.executable, str(GERAR_LATTES), "--fonte", str(fonte), "--saida", str(saida)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert saida.is_file()
        with saida.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert rows == [
            {"nome": "Docente Um", "lattes_id": "1234567890123456"},
            {"nome": "Docente Dois", "lattes_id": "6543210987654321"},
        ]

    def test_gera_csv_de_assign_simples(self, tmp_path: Path) -> None:
        fonte = tmp_path / "fonte.py"
        fonte.write_text('ROSTER_IDS = {"Docente Tres": "1111222233334444"}\n', encoding="utf-8")
        saida = tmp_path / "lattes.csv"

        proc = subprocess.run(
            [sys.executable, str(GERAR_LATTES), "--fonte", str(fonte), "--saida", str(saida)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert "Docente Tres,1111222233334444" in saida.read_text(encoding="utf-8")

    def test_preserva_csv_customizado_sem_force(self, tmp_path: Path) -> None:
        fonte = tmp_path / "fonte.py"
        fonte.write_text('ROSTER_IDS = {"Docente Novo": "9999888877776666"}\n', encoding="utf-8")
        saida = tmp_path / "lattes.csv"
        conteudo_custom = "nome,lattes_id\nMinha Lista,0000111122223333\n"
        saida.write_text(conteudo_custom, encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(GERAR_LATTES), "--fonte", str(fonte), "--saida", str(saida)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        assert saida.read_text(encoding="utf-8") == conteudo_custom

        proc_force = subprocess.run(
            [sys.executable, str(GERAR_LATTES), "--fonte", str(fonte), "--saida", str(saida), "--force"],
            capture_output=True,
            text=True,
        )
        assert proc_force.returncode == 0
        assert "Docente Novo,9999888877776666" in saida.read_text(encoding="utf-8")

    def test_falha_com_instrucao_clara_quando_fonte_ausente(self, tmp_path: Path) -> None:
        fonte_inexistente = tmp_path / "nao_existe.py"
        saida = tmp_path / "entradas" / "lattes.csv"

        proc = subprocess.run(
            [sys.executable, str(GERAR_LATTES), "--fonte", str(fonte_inexistente), "--saida", str(saida)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 1
        assert "nome,lattes_id" in proc.stderr
        assert str(saida) in proc.stderr
        assert not saida.exists()

    def test_gera_lista_real_do_repositorio_em_tmp(self, tmp_path: Path) -> None:
        fonte_real = ROOT_DIR / "Etls" / "Horizon" / "Etl" / "src" / "scripts" / "generate_docentes_executive.py"
        if not fonte_real.is_file():
            pytest.skip("Fonte legada ROSTER_IDS não presente no ambiente")
        saida = tmp_path / "lattes.csv"
        proc = subprocess.run(
            [sys.executable, str(GERAR_LATTES), "--saida", str(saida)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        with saida.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) >= 80
        assert all(len(r["lattes_id"]) == 16 and r["lattes_id"].isdigit() for r in rows)


# ── Issues #84 e #87: rodar_desktop.sh ───────────────────────────────────────


def _setup_fake_desktop_workspace(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Cria estrutura mínima de trabalho para testar rodar_desktop.sh sem subir Vite/Tauri reais."""
    repo = tmp_path / "repo"
    script = repo / "rodar_desktop.sh"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(RODAR_DESKTOP.read_text(encoding="utf-8"), encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)

    _make_executable(repo / "Muninn" / "app" / ".venv" / "bin" / "python", "#!/usr/bin/env bash\nexit 0\n")
    (repo / "Muninn" / "app" / "data").mkdir(parents=True, exist_ok=True)
    (repo / "Muninn" / "app" / "data" / "dados.db").write_bytes(b"")
    (repo / "Muninn" / "app" / "frontend-vue").mkdir(parents=True, exist_ok=True)
    (repo / "Muninn" / "app" / "src-tauri").mkdir(parents=True, exist_ok=True)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    env_dump = tmp_path / "cargo_env_dump.txt"

    # Stubs de comandos básicos para simular Vite já rodando na pasta certa (sem abrir rede)
    _make_executable(fake_bin / "curl", "#!/usr/bin/env bash\nexit 0\n")
    _make_executable(fake_bin / "lsof", "#!/usr/bin/env bash\necho 12345\n")
    front_dir = (repo / "Muninn" / "app" / "frontend-vue").resolve()
    _make_executable(fake_bin / "readlink", f"#!/usr/bin/env bash\necho '{front_dir}'\n")
    return script, fake_bin, env_dump


class TestRodarDesktopSh:
    def test_sintaxe_bash_valida(self) -> None:
        proc = subprocess.run(["bash", "-n", str(RODAR_DESKTOP)], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr

    def test_falha_amigavel_sem_cargo_e_sem_cargo_env(self, tmp_path: Path) -> None:
        script, fake_bin, _ = _setup_fake_desktop_workspace(tmp_path)
        fake_home = tmp_path / "home_sem_rust"
        fake_home.mkdir()

        # PATH mínimo sem cargo (mantém /usr/bin e /bin apenas se cargo não estiver lá;
        # cria wrappers só para bash/dirname/cd não precisam, mas garantimos ausência de cargo)
        safe_bin = tmp_path / "safe_bin"
        safe_bin.mkdir()
        for cmd in ("bash", "dirname", "pwd", "env"):
            for d in ("/usr/bin", "/bin"):
                cand = Path(d) / cmd
                if cand.is_file():
                    (safe_bin / cmd).symlink_to(cand)
                    break

        env = {"HOME": str(fake_home), "PATH": f"{fake_bin}:{safe_bin}"}
        proc = subprocess.run(["/usr/bin/env", "bash", str(script)], capture_output=True, text=True, env=env)
        assert proc.returncode == 1
        assert "rustup.rs" in proc.stderr
        assert ".cargo/env: Arquivo" not in proc.stderr
        assert "No such file or directory" not in proc.stderr

    def test_carrega_cargo_env_limpa_snap_e_aplica_wayland(self, tmp_path: Path) -> None:
        script, fake_bin, env_dump = _setup_fake_desktop_workspace(tmp_path)
        fake_home = tmp_path / "home_com_rust"
        cargo_bin = fake_home / ".cargo" / "bin"
        _make_executable(
            cargo_bin / "cargo",
            f"#!/usr/bin/env bash\nenv > '{env_dump}'\nexit 0\n",
        )
        _make_executable(
            fake_home / ".cargo" / "env",
            f'export PATH="{cargo_bin}:$PATH"\n',
        )

        safe_bin = tmp_path / "safe_bin"
        safe_bin.mkdir()
        for cmd in ("bash", "dirname", "pwd", "env", "head", "sed"):
            for d in ("/usr/bin", "/bin"):
                cand = Path(d) / cmd
                if cand.is_file():
                    (safe_bin / cmd).symlink_to(cand)
                    break

        env = {
            "HOME": str(fake_home),
            "PATH": f"{fake_bin}:{safe_bin}",
            "XDG_SESSION_TYPE": "wayland",
            "GTK_PATH": "/snap/code/current/usr/lib/x86_64-linux-gnu/gtk-3.0",
            "GIO_MODULE_DIR": "/snap/code/current/usr/lib/x86_64-linux-gnu/gio/modules",
            "GSETTINGS_SCHEMA_DIR": "/snap/code/current/usr/share/glib-2.0/schemas",
            "LD_LIBRARY_PATH": "/snap/core20/current/lib/x86_64-linux-gnu",
            "GTK_EXE_PREFIX": "/snap/code/current/usr",
            "GTK_IM_MODULE_FILE": "/snap/code/current/immodules.cache",
        }
        proc = subprocess.run(["/usr/bin/env", "bash", str(script)], capture_output=True, text=True, env=env)
        assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"

        dumped = dict(
            line.split("=", 1) for line in env_dump.read_text(encoding="utf-8").splitlines() if "=" in line
        )
        for snap_var in (
            "GTK_PATH",
            "GIO_MODULE_DIR",
            "GSETTINGS_SCHEMA_DIR",
            "LD_LIBRARY_PATH",
            "GTK_EXE_PREFIX",
            "GTK_IM_MODULE_FILE",
        ):
            assert snap_var not in dumped, f"{snap_var} deveria ter sido removida"
        assert dumped.get("GDK_BACKEND") == "x11"
        assert dumped.get("WEBKIT_DISABLE_DMABUF_RENDERER") == "1"

    def test_preserva_ld_library_path_nao_snap_e_filtra_valor_misto(self, tmp_path: Path) -> None:
        script, fake_bin, env_dump = _setup_fake_desktop_workspace(tmp_path)
        _make_executable(fake_bin / "cargo", f"#!/usr/bin/env bash\nenv > '{env_dump}'\nexit 0\n")

        env = {
            "HOME": str(tmp_path),
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "XDG_SESSION_TYPE": "wayland",
            "LD_LIBRARY_PATH": "/opt/custom/lib:/snap/core20/current/lib:/usr/local/lib",
            "GTK_PATH": "/snap/code/current/gtk:/usr/lib/gtk-3.0",
            "GDK_BACKEND": "wayland",
            "WEBKIT_DISABLE_DMABUF_RENDERER": "0",
        }
        proc = subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env)
        assert proc.returncode == 0, proc.stderr

        dumped = dict(
            line.split("=", 1) for line in env_dump.read_text(encoding="utf-8").splitlines() if "=" in line
        )
        assert dumped.get("LD_LIBRARY_PATH") == "/opt/custom/lib:/usr/local/lib"
        assert dumped.get("GTK_PATH") == "/usr/lib/gtk-3.0"
        assert dumped.get("GDK_BACKEND") == "wayland"
        assert dumped.get("WEBKIT_DISABLE_DMABUF_RENDERER") == "0"

    def test_wayland_nativo_nao_forca_x11_mas_flag_forca(self, tmp_path: Path) -> None:
        script, fake_bin, env_dump = _setup_fake_desktop_workspace(tmp_path)
        _make_executable(fake_bin / "cargo", f"#!/usr/bin/env bash\nenv > '{env_dump}'\nexit 0\n")

        # Wayland nativo (sem /snap/ e sem MUNINN_FORCE_X11): preserva Wayland nativo
        env_native = {
            "HOME": str(tmp_path),
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "XDG_SESSION_TYPE": "wayland",
        }
        proc = subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env_native)
        assert proc.returncode == 0, proc.stderr
        dumped = dict(
            line.split("=", 1) for line in env_dump.read_text(encoding="utf-8").splitlines() if "=" in line
        )
        assert "GDK_BACKEND" not in dumped
        assert dumped.get("WEBKIT_DISABLE_DMABUF_RENDERER") == "1"

        # Com MUNINN_FORCE_X11=1 sob Wayland: ativa GDK_BACKEND=x11
        env_forced = {**env_native, "MUNINN_FORCE_X11": "1"}
        proc2 = subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env_forced)
        assert proc2.returncode == 0, proc2.stderr
        dumped2 = dict(
            line.split("=", 1) for line in env_dump.read_text(encoding="utf-8").splitlines() if "=" in line
        )
        assert dumped2.get("GDK_BACKEND") == "x11"

    def test_nao_forca_gdk_backend_em_x11(self, tmp_path: Path) -> None:
        script, fake_bin, env_dump = _setup_fake_desktop_workspace(tmp_path)
        _make_executable(fake_bin / "cargo", f"#!/usr/bin/env bash\nenv > '{env_dump}'\nexit 0\n")

        env = {
            "HOME": str(tmp_path),
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "XDG_SESSION_TYPE": "x11",
        }
        proc = subprocess.run(["bash", str(script)], capture_output=True, text=True, env=env)
        assert proc.returncode == 0, proc.stderr

        dumped = dict(
            line.split("=", 1) for line in env_dump.read_text(encoding="utf-8").splitlines() if "=" in line
        )
        assert "GDK_BACKEND" not in dumped


# ── Issue #88: validar_etl_env.py ────────────────────────────────────────────


class TestValidarEtlEnv:
    @staticmethod
    def _clean_env(**extra: str) -> dict[str, str]:
        base = {k: v for k, v in os.environ.items() if not k.startswith(("MUNINN_CRED", "INFISICAL_", "SRC_", "SIGPESQ_"))}
        base.update(extra)
        return base

    def test_falha_quando_env_ausente_e_ambiente_vazio(self, tmp_path: Path) -> None:
        proc = subprocess.run(
            [sys.executable, str(VALIDAR_ENV), "--env-file", str(tmp_path / ".env")],
            capture_output=True,
            text=True,
            env=self._clean_env(),
        )
        assert proc.returncode == 1
        assert "make setup-etl" in proc.stderr

    def test_aceita_credenciais_via_os_environ_sem_arquivo_env_e_alias_sigpesq_username(self, tmp_path: Path) -> None:
        missing_env = tmp_path / "nao_existe.env"
        # Modo env via os.environ com alias SIGPESQ_USERNAME (CI / container)
        proc_env = subprocess.run(
            [sys.executable, str(VALIDAR_ENV), "--env-file", str(missing_env), "--escopo", "all"],
            capture_output=True,
            text=True,
            env=self._clean_env(
                MUNINN_CREDENCIAIS="env",
                SRC_USER="u_src",
                SRC_PASSWORD="p_src",
                SIGPESQ_USERNAME="u_sig_alias",
                SIGPESQ_PASSWORD="p_sig",
            ),
        )
        assert proc_env.returncode == 0, proc_env.stderr

        # Modo infisical via os.environ sem arquivo .env
        proc_inf = subprocess.run(
            [sys.executable, str(VALIDAR_ENV), "--env-file", str(missing_env)],
            capture_output=True,
            text=True,
            env=self._clean_env(
                MUNINN_CREDENCIAIS="infisical",
                INFISICAL_CLIENT_ID="cid",
                INFISICAL_CLIENT_SECRET="csec",
                INFISICAL_PROJECT_ID="pid",
            ),
        )
        assert proc_inf.returncode == 0, proc_inf.stderr

    def test_precedencia_arquivo_env_sobre_os_environ(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        # .env define infisical (sem credenciais infisical); os.environ define env completo.
        # Mesma precedência do ETL (comum.py::config): .env ganha -> deve cobrar vars Infisical.
        env_file.write_text("MUNINN_CREDENCIAIS=infisical\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(VALIDAR_ENV), "--env-file", str(env_file)],
            capture_output=True,
            text=True,
            env=self._clean_env(
                MUNINN_CREDENCIAIS="env",
                SRC_USER="u",
                SRC_PASSWORD="p",
                SIGPESQ_USER="u2",
                SIGPESQ_PASSWORD="p2",
            ),
        )
        assert proc.returncode == 1
        assert "INFISICAL_CLIENT_ID" in proc.stderr

        # Se chave no .env está vazia, faz fallback para os.environ (como comum.py::config)
        env_file.write_text("MUNINN_CREDENCIAIS=env\nSIGPESQ_USER=\n", encoding="utf-8")
        proc_fb = subprocess.run(
            [sys.executable, str(VALIDAR_ENV), "--env-file", str(env_file), "--escopo", "sigpesq"],
            capture_output=True,
            text=True,
            env=self._clean_env(SIGPESQ_USERNAME="u_env", SIGPESQ_PASSWORD="p_env"),
        )
        assert proc_fb.returncode == 0, proc_fb.stderr

    def test_falha_quando_modo_invalido_ou_vazio(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("MUNINN_CREDENCIAIS=outro\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(VALIDAR_ENV), "--env-file", str(env_file)],
            capture_output=True,
            text=True,
            env=self._clean_env(),
        )
        assert proc.returncode == 1
        assert "infisical" in proc.stderr and "env" in proc.stderr

    def test_infisical_incompleto_e_completo(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("MUNINN_CREDENCIAIS=infisical\nINFISICAL_CLIENT_ID=id1\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(VALIDAR_ENV), "--env-file", str(env_file)],
            capture_output=True,
            text=True,
            env=self._clean_env(),
        )
        assert proc.returncode == 1
        assert "INFISICAL_CLIENT_SECRET" in proc.stderr
        assert "INFISICAL_PROJECT_ID" in proc.stderr
        assert "id1" not in proc.stderr

        env_file.write_text(
            "MUNINN_CREDENCIAIS=infisical\n"
            "INFISICAL_CLIENT_ID=id1\n"
            "INFISICAL_CLIENT_SECRET=sec1\n"
            "INFISICAL_PROJECT_ID=proj1\n",
            encoding="utf-8",
        )
        proc_ok = subprocess.run(
            [sys.executable, str(VALIDAR_ENV), "--env-file", str(env_file)],
            capture_output=True,
            text=True,
            env=self._clean_env(),
        )
        assert proc_ok.returncode == 0

    def test_env_granular_e_crlf_sem_vazamento_de_segredos(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        # Só SRC preenchido, com CRLF, aspas e comentário; SigPesq ausente
        env_file.write_bytes(
            b"# comentario\r\n"
            b"MUNINN_CREDENCIAIS = 'env'\r\n"
            b'SRC_USER="usuario_src"\r\n'
            b'SRC_PASSWORD="SUPER_SECRET_PASSWORD_999"\r\n'
            b"SIGPESQ_USER=\r\n"
            b"SIGPESQ_PASSWORD=\r\n"
        )

        # Escopo src deve passar
        proc_src = subprocess.run(
            [sys.executable, str(VALIDAR_ENV), "--env-file", str(env_file), "--escopo", "src"],
            capture_output=True,
            text=True,
            env=self._clean_env(),
        )
        assert proc_src.returncode == 0, proc_src.stderr
        assert "SUPER_SECRET_PASSWORD_999" not in proc_src.stdout + proc_src.stderr

        # Escopo sigpesq e all devem falhar sem vazar senha do SRC
        for escopo in ("sigpesq", "all"):
            proc_fail = subprocess.run(
                [sys.executable, str(VALIDAR_ENV), "--env-file", str(env_file), "--escopo", escopo],
                capture_output=True,
                text=True,
                env=self._clean_env(),
            )
            assert proc_fail.returncode == 1
            assert "SIGPESQ_USER" in proc_fail.stderr
            assert "SIGPESQ_PASSWORD" in proc_fail.stderr
            assert "SUPER_SECRET_PASSWORD_999" not in proc_fail.stdout + proc_fail.stderr


# ── Guards do Makefile (#83, #84, #88) ───────────────────────────────────────


class TestMakefileGuards:
    def test_check_brutos_falha_quando_ausente_ou_vazio_e_passa_quando_populado(self, tmp_path: Path) -> None:
        etl_dir = tmp_path / "etl"
        etl_dir.mkdir()

        # Ausente
        p1 = subprocess.run(
            ["make", "-f", str(MAKEFILE), f"ETL_DIR={etl_dir}", "check-brutos"],
            capture_output=True,
            text=True,
        )
        assert p1.returncode != 0
        assert "make etl" in p1.stdout + p1.stderr

        # Pasta vazia e pasta contendo apenas .gitkeep não contam como populadas
        (etl_dir / "brutos").mkdir()
        (etl_dir / "brutos" / ".gitkeep").write_text("", encoding="utf-8")
        p2 = subprocess.run(
            [MAKE_BIN, "-f", str(MAKEFILE), f"ETL_DIR={etl_dir}", "check-brutos"],
            capture_output=True,
            text=True,
        )
        assert p2.returncode != 0

        # Populada com arquivo real
        (etl_dir / "brutos" / "src").mkdir(parents=True)
        (etl_dir / "brutos" / "src" / "acoes.json").write_text("[]", encoding="utf-8")
        p3 = subprocess.run(
            [MAKE_BIN, "-f", str(MAKEFILE), f"ETL_DIR={etl_dir}", "check-brutos"],
            capture_output=True,
            text=True,
        )
        assert p3.returncode == 0, p3.stderr

    def test_dev_tauri_e_test_tauri_carregam_cargo_env_quando_fora_do_path(self, tmp_path: Path) -> None:
        fake_home = tmp_path / "home"
        cargo_bin = fake_home / ".cargo" / "bin"
        cargo_log = tmp_path / "cargo.log"
        _make_executable(cargo_bin / "cargo", f"#!/usr/bin/env bash\necho \"$*\" >> '{cargo_log}'\n")
        _make_executable(fake_home / ".cargo" / "env", f'export PATH="{cargo_bin}:$PATH"\n')

        tauri_dir = tmp_path / "src-tauri"
        tauri_dir.mkdir()
        safe_bin = tmp_path / "safe_bin"
        safe_bin.mkdir()
        for cmd in ("bash", "sh"):
            for d in ("/usr/bin", "/bin"):
                cand = Path(d) / cmd
                if cand.is_file():
                    (safe_bin / cmd).symlink_to(cand)
                    break

        env = {"HOME": str(fake_home), "PATH": str(safe_bin)}
        p_dev = subprocess.run(
            [MAKE_BIN, "-f", str(MAKEFILE), f"TAURI_DIR={tauri_dir}", "dev-tauri"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert p_dev.returncode == 0, f"stdout={p_dev.stdout}\nstderr={p_dev.stderr}"

        p_test = subprocess.run(
            [MAKE_BIN, "-f", str(MAKEFILE), f"TAURI_DIR={tauri_dir}", "test-tauri"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert p_test.returncode == 0, f"stdout={p_test.stdout}\nstderr={p_test.stderr}"
        assert cargo_log.read_text(encoding="utf-8").splitlines() == ["run", "test"]

    def test_check_desktop_falha_sem_cargo_e_passa_com_cargo(self, tmp_path: Path) -> None:
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        safe_bin = tmp_path / "safe_bin"
        safe_bin.mkdir()
        for cmd in ("bash", "sh"):
            for d in ("/usr/bin", "/bin"):
                cand = Path(d) / cmd
                if cand.is_file():
                    (safe_bin / cmd).symlink_to(cand)
                    break

        p_fail = subprocess.run(
            [MAKE_BIN, "-f", str(MAKEFILE), "check-desktop"],
            capture_output=True,
            text=True,
            env={"HOME": str(fake_home), "PATH": str(safe_bin)},
        )
        assert p_fail.returncode != 0
        assert "rustup.rs" in p_fail.stdout + p_fail.stderr

        _make_executable(safe_bin / "cargo", "#!/usr/bin/env bash\nexit 0\n")
        p_ok = subprocess.run(
            [MAKE_BIN, "-f", str(MAKEFILE), "check-desktop"],
            capture_output=True,
            text=True,
            env={"HOME": str(fake_home), "PATH": str(safe_bin)},
        )
        assert p_ok.returncode == 0, p_ok.stderr

    def test_check_front_valida_node_npm_e_node_modules(self, tmp_path: Path) -> None:
        front_dir = tmp_path / "front"
        front_dir.mkdir()
        p_no_modules = subprocess.run(
            [MAKE_BIN, "-f", str(MAKEFILE), f"FRONT_DIR={front_dir}", "check-front"],
            capture_output=True,
            text=True,
        )
        assert p_no_modules.returncode != 0
        assert "node_modules" in p_no_modules.stdout + p_no_modules.stderr or "Node.js" in p_no_modules.stdout + p_no_modules.stderr

        # Sem node/npm no PATH mesmo com node_modules presente
        (front_dir / "node_modules").mkdir()
        safe_bin = tmp_path / "safe_bin"
        safe_bin.mkdir()
        for cmd in ("bash", "sh"):
            for d in ("/usr/bin", "/bin"):
                cand = Path(d) / cmd
                if cand.is_file():
                    (safe_bin / cmd).symlink_to(cand)
                    break
        p_no_node = subprocess.run(
            [MAKE_BIN, "-f", str(MAKEFILE), f"FRONT_DIR={front_dir}", "check-front"],
            capture_output=True,
            text=True,
            env={"HOME": str(tmp_path), "PATH": str(safe_bin)},
        )
        assert p_no_node.returncode != 0
        assert "Node.js" in p_no_node.stdout + p_no_node.stderr

    def test_make_all_condicional_conforme_brutos(self, tmp_path: Path) -> None:
        """Verifica que `make all` dispara `etl` sem brutos/ e pula para `db` com brutos/ populado."""
        etl_dir = tmp_path / "etl"
        app_dir = tmp_path / "app"
        front_dir = tmp_path / "front"
        (front_dir / "node_modules").mkdir(parents=True)
        _make_executable(app_dir / ".venv" / "bin" / "python", "#!/usr/bin/env bash\nexit 0\n")
        _make_executable(etl_dir / ".venv" / "bin" / "python", "#!/usr/bin/env bash\nexit 0\n")

        fake_bin = tmp_path / "bin"
        for cmd in ("node", "npm", "cargo"):
            _make_executable(fake_bin / cmd, "#!/usr/bin/env bash\nexit 0\n")
        calls_log = tmp_path / "make_calls.log"
        stub_make = _make_executable(fake_bin / "stub_make", f"#!/usr/bin/env bash\necho \"$*\" >> '{calls_log}'\n")

        env = {**os.environ, "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"}
        base_args = [
            MAKE_BIN,
            "-f",
            str(MAKEFILE),
            f"APP_DIR={app_dir}",
            f"ETL_DIR={etl_dir}",
            f"FRONT_DIR={front_dir}",
            f"MAKE={stub_make}",
            "all",
        ]

        # 1. Com brutos/ ausente ou contendo apenas .gitkeep -> deve chamar etl e depois desktop
        (etl_dir / "brutos").mkdir(parents=True)
        (etl_dir / "brutos" / ".gitkeep").write_text("", encoding="utf-8")
        p1 = subprocess.run(base_args, capture_output=True, text=True, env=env)
        assert p1.returncode == 0, f"stdout={p1.stdout}\nstderr={p1.stderr}"
        calls1 = calls_log.read_text(encoding="utf-8").splitlines()
        assert calls1 == ["etl", "desktop"]

        # 2. Com brutos/ populado -> deve pular etl e chamar db + desktop
        calls_log.unlink()
        (etl_dir / "brutos" / "src").mkdir(parents=True)
        (etl_dir / "brutos" / "src" / "acoes.json").write_text("[]", encoding="utf-8")
        p2 = subprocess.run(base_args, capture_output=True, text=True, env=env)
        assert p2.returncode == 0, f"stdout={p2.stdout}\nstderr={p2.stderr}"
        calls2 = calls_log.read_text(encoding="utf-8").splitlines()
        assert calls2 == ["db", "desktop"]

    def test_dependencias_alvos_publicos_vs_autenticados_no_makefile(self) -> None:
        text = MAKEFILE.read_text(encoding="utf-8")
        lines = {line.split(":", 1)[0].strip(): line for line in text.splitlines() if ":" in line and not line.startswith("\t")}

        # Alvos públicos não exigem check-etl-env
        for public_target in ("etl-src-acoes", "etl-cnpq", "etl-lattes"):
            assert "check-etl-env" not in lines[public_target]

        # Alvos autenticados exigem check-etl-env apropriado
        assert "check-etl-env" in lines["etl"]
        assert "check-etl-env" in lines["etl-extract"]
        assert "check-etl-env-src" in lines["etl-src-participacoes"]
        assert "check-etl-env-sigpesq" in lines["etl-sigpesq"]

        # Alvos Python-only não exigem check-desktop nem check-front
        for py_target in ("test-etl", "test-core", "test-mcp", "db"):
            assert "check-desktop" not in lines[py_target]
            assert "check-front" not in lines[py_target]

        # db exige check-brutos
        assert "check-brutos" in lines["db"]
