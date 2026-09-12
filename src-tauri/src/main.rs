#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    env,
    net::{TcpListener, TcpStream},
    path::{Path, PathBuf},
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    time::{Duration, Instant},
};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

const PORT_START: u16 = 18_766;
const PORT_END: u16 = 18_865;
const READY_TIMEOUT: Duration = Duration::from_secs(15);

#[derive(Debug, Clone)]
#[cfg(debug_assertions)]
struct PythonCommand {
    executable: String,
    prefix_args: Vec<String>,
}

#[cfg(debug_assertions)]
fn project_root() -> PathBuf {
    if let Some(value) = env::var_os("OSS_UPDATE_WATCH_ROOT") {
        return PathBuf::from(value);
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("src-tauri must have a parent")
        .to_path_buf()
}

fn user_data_dir() -> PathBuf {
    if let Some(value) = env::var_os("FOSSIGHT_DATA_DIR") {
        return PathBuf::from(value);
    }
    #[cfg(target_os = "windows")]
    if let Some(local_app_data) = env::var_os("LOCALAPPDATA") {
        return PathBuf::from(local_app_data).join("FossightData");
    }
    if let Some(xdg_data_home) = env::var_os("XDG_DATA_HOME") {
        return PathBuf::from(xdg_data_home).join("Fossight");
    }
    if let Some(home) = env::var_os("HOME") {
        return PathBuf::from(home)
            .join(".local")
            .join("share")
            .join("Fossight");
    }
    env::temp_dir().join("Fossight")
}

fn free_port() -> Result<u16, String> {
    if let Ok(value) = env::var("OSS_UPDATE_WATCH_DESKTOP_PORT") {
        let port = value
            .parse::<u16>()
            .map_err(|_| format!("Invalid OSS_UPDATE_WATCH_DESKTOP_PORT: {value}"))?;
        TcpListener::bind(("127.0.0.1", port))
            .map_err(|error| format!("Requested desktop port {port} is unavailable: {error}"))?;
        return Ok(port);
    }
    for port in PORT_START..=PORT_END {
        if TcpListener::bind(("127.0.0.1", port)).is_ok() {
            return Ok(port);
        }
    }
    Err(format!(
        "No free localhost port available in {PORT_START}-{PORT_END}"
    ))
}

#[cfg(debug_assertions)]
fn command_available(candidate: &PythonCommand) -> bool {
    let mut command = Command::new(&candidate.executable);
    command.args(&candidate.prefix_args).arg("--version");
    command.stdout(Stdio::null()).stderr(Stdio::null());
    #[cfg(target_os = "windows")]
    command.creation_flags(CREATE_NO_WINDOW);
    command
        .status()
        .map(|status| status.success())
        .unwrap_or(false)
}

#[cfg(debug_assertions)]
fn find_python() -> Result<PythonCommand, String> {
    #[cfg(target_os = "windows")]
    let candidates = [
        PythonCommand {
            executable: "python.exe".to_string(),
            prefix_args: Vec::new(),
        },
        PythonCommand {
            executable: "py.exe".to_string(),
            prefix_args: vec!["-3".to_string()],
        },
        PythonCommand {
            executable: "python".to_string(),
            prefix_args: Vec::new(),
        },
    ];
    #[cfg(not(target_os = "windows"))]
    let candidates = [
        PythonCommand {
            executable: "python3".to_string(),
            prefix_args: Vec::new(),
        },
        PythonCommand {
            executable: "python".to_string(),
            prefix_args: Vec::new(),
        },
        PythonCommand {
            executable: "py".to_string(),
            prefix_args: vec!["-3".to_string()],
        },
    ];

    candidates
        .into_iter()
        .find(command_available)
        .ok_or_else(|| "Python 3 was not found on PATH".to_string())
}

#[cfg(debug_assertions)]
fn python_path(root: &Path) -> String {
    let src = root.join("src").to_string_lossy().into_owned();
    match env::var_os("PYTHONPATH") {
        Some(existing) if !existing.is_empty() => {
            format!(
                "{src}{}{}",
                if cfg!(windows) { ";" } else { ":" },
                existing.to_string_lossy()
            )
        }
        _ => src,
    }
}

#[cfg(any(not(debug_assertions), test))]
fn packaged_backend_path() -> Result<PathBuf, String> {
    if let Some(value) = env::var_os("FOSSIGHT_BACKEND_EXE") {
        let path = PathBuf::from(value);
        if path.is_file() {
            return Ok(path);
        }
        return Err(format!(
            "FOSSIGHT_BACKEND_EXE does not point to a file: {}",
            path.display()
        ));
    }
    let current = env::current_exe()
        .map_err(|error| format!("Unable to locate Fossight executable: {error}"))?;
    let path = current
        .parent()
        .ok_or_else(|| "Fossight executable has no parent directory".to_string())?
        .join("fossight-backend.exe");
    if path.is_file() {
        Ok(path)
    } else {
        Err(format!(
            "Packaged Fossight backend not found at {}",
            path.display()
        ))
    }
}

fn start_backend(_root: &Path, data_dir: &Path, port: u16) -> Result<Child, String> {
    #[cfg(not(debug_assertions))]
    {
        let backend = packaged_backend_path()?;
        let mut command = Command::new(&backend);
        command
            .arg("--data-dir")
            .arg(data_dir)
            .arg("ui")
            .arg("--no-open")
            .arg("--port")
            .arg(port.to_string())
            .current_dir(data_dir)
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        #[cfg(target_os = "windows")]
        command.creation_flags(CREATE_NO_WINDOW);
        return command
            .spawn()
            .map_err(|error| format!("Unable to start packaged Fossight backend: {error}"));
    }

    #[cfg(debug_assertions)]
    {
        let python = find_python()?;
        let mut command = Command::new(&python.executable);
        command
            .args(&python.prefix_args)
            .arg("-m")
            .arg("oss_update_watch")
            .arg("--data-dir")
            .arg(data_dir)
            .arg("ui")
            .arg("--no-open")
            .arg("--port")
            .arg(port.to_string())
            .current_dir(_root)
            .env("PYTHONPATH", python_path(_root))
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        #[cfg(target_os = "windows")]
        command.creation_flags(CREATE_NO_WINDOW);
        command
            .spawn()
            .map_err(|error| format!("Unable to start developer Python backend: {error}"))
    }
}

fn wait_until_ready(child: &mut Child, port: u16) -> Result<(), String> {
    let deadline = Instant::now() + READY_TIMEOUT;
    loop {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return Ok(());
        }
        if let Some(status) = child
            .try_wait()
            .map_err(|error| format!("Unable to inspect Python backend: {error}"))?
        {
            return Err(format!("Python backend exited before ready: {status}"));
        }
        if Instant::now() >= deadline {
            return Err(format!(
                "Python backend did not become ready on port {port}"
            ));
        }
        thread::sleep(Duration::from_millis(80));
    }
}

fn stop_backend(backend: &Arc<Mutex<Option<Child>>>) {
    let Ok(mut guard) = backend.lock() else {
        return;
    };
    if let Some(mut child) = guard.take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

fn run() -> Result<(), String> {
    #[cfg(debug_assertions)]
    let root = project_root();
    #[cfg(debug_assertions)]
    if !root.join("src").is_dir() {
        return Err(format!("Invalid Fossight root: {}", root.display()));
    }
    #[cfg(not(debug_assertions))]
    let root = PathBuf::new();
    let data_dir = user_data_dir();

    let port = free_port()?;
    let mut child = start_backend(&root, &data_dir, port)?;
    if let Err(error) = wait_until_ready(&mut child, port) {
        let _ = child.kill();
        let _ = child.wait();
        return Err(error);
    }

    let backend = Arc::new(Mutex::new(Some(child)));
    let backend_for_setup = backend.clone();
    let url: tauri::Url = format!("http://127.0.0.1:{port}/")
        .parse()
        .map_err(|error| format!("Invalid desktop URL: {error}"))?;

    let app = tauri::Builder::default()
        .setup(move |app| {
            tauri::WebviewWindowBuilder::new(app, "main", tauri::WebviewUrl::External(url.clone()))
                .title("Fossight")
                .inner_size(1420.0, 860.0)
                .min_inner_size(1000.0, 640.0)
                .resizable(true)
                .center()
                .build()?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .map_err(|error| {
            stop_backend(&backend_for_setup);
            format!("Unable to build Tauri application: {error}")
        })?;

    let backend_for_events = backend.clone();
    app.run(move |app_handle, event| match event {
        tauri::RunEvent::WindowEvent { label, event, .. }
            if label == "main" && matches!(event, tauri::WindowEvent::CloseRequested { .. }) =>
        {
            app_handle.exit(0);
        }
        tauri::RunEvent::Exit => stop_backend(&backend_for_events),
        _ => {}
    });
    Ok(())
}

fn main() {
    if let Err(error) = run() {
        eprintln!("Fossight desktop error: {error}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn project_root_contains_source_tree_in_repository_build() {
        assert!(project_root().join("src").is_dir());
    }

    #[test]
    fn user_data_dir_prefers_explicit_override() {
        // The helper consults the environment on every call, so setting a
        // value must win over the platform default.
        let key = "FOSSIGHT_DATA_DIR";
        let previous = env::var_os(key);
        env::set_var(key, "Z:\\FossightTestData");
        assert_eq!(user_data_dir(), PathBuf::from("Z:\\FossightTestData"));
        match previous {
            Some(value) => env::set_var(key, value),
            None => env::remove_var(key),
        }
    }

    #[test]
    fn python_path_starts_with_project_src() {
        let root = project_root();
        assert!(python_path(&root).starts_with(&root.join("src").to_string_lossy().into_owned()));
    }

    #[test]
    fn packaged_backend_path_honors_explicit_override() {
        let key = "FOSSIGHT_BACKEND_EXE";
        let previous = env::var_os(key);
        let path = env::current_exe().expect("current test executable");
        env::set_var(key, &path);
        assert_eq!(packaged_backend_path().expect("explicit backend"), path);
        match previous {
            Some(value) => env::set_var(key, value),
            None => env::remove_var(key),
        }
    }

    #[test]
    fn selected_port_can_be_bound_during_probe() {
        let port = free_port().expect("find a free desktop port");
        let listener = TcpListener::bind(("127.0.0.1", port)).expect("port should still be free");
        drop(listener);
    }
}
