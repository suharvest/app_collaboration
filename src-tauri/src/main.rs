// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;

/// Global flag to track sidecar state
static SIDECAR_STARTED: AtomicBool = AtomicBool::new(false);

/// Global backend port - set once at startup
static BACKEND_PORT: AtomicU16 = AtomicU16::new(0);

/// Get an available port for the backend server
fn get_available_port() -> u16 {
    portpicker::pick_unused_port().expect("No available ports")
}

/// Tauri command to get the backend port
#[tauri::command]
fn get_backend_port() -> u16 {
    BACKEND_PORT.load(Ordering::SeqCst)
}

/// Main entry point
fn main() {
    // Initialize logger for debug builds
    #[cfg(debug_assertions)]
    env_logger::init();

    let backend_port = get_available_port();
    BACKEND_PORT.store(backend_port, Ordering::SeqCst);
    log::info!("Selected backend port: {}", backend_port);

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .invoke_handler(tauri::generate_handler![get_backend_port])
        .setup(move |app| {
            let handle = app.handle().clone();
            let port = backend_port;

            // Spawn sidecar in async context
            tauri::async_runtime::spawn(async move {
                if let Err(e) = start_sidecar(&handle, port).await {
                    log::error!("Failed to start sidecar: {}", e);
                }
            });

            // Inject backend port into frontend
            // The frontend can also call get_backend_port command as a fallback
            let main_window = app.get_webview_window("main")
                .expect("Main window not found");

            let init_script = format!(
                "window.__BACKEND_PORT__ = {};",
                backend_port
            );

            // Inject immediately
            let _ = main_window.eval(&init_script);

            Ok(())
        })
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                log::info!("Window close requested, shutting down sidecar...");
            }
        })
        .run(tauri::generate_context!())
        .expect("Error while running Tauri application");
}

/// Start the Python backend sidecar
async fn start_sidecar(
    handle: &tauri::AppHandle,
    port: u16,
) -> Result<(), Box<dyn std::error::Error>> {
    if SIDECAR_STARTED.load(Ordering::SeqCst) {
        log::info!("Sidecar already started");
        return Ok(());
    }

    log::info!("Starting provisioning-station sidecar on port {}", port);

    // Get the resource directory where solutions are bundled
    let resource_path = handle.path().resource_dir()
        .expect("Failed to get resource directory");

    // Solutions are bundled via ../solutions/**/* which creates _up_/solutions
    let solutions_dir = resource_path.join("_up_").join("solutions");

    log::info!("Solutions directory: {:?}", solutions_dir);

    let mut args = vec![
        "--port".to_string(),
        port.to_string(),
        "--host".to_string(),
        "127.0.0.1".to_string(),
    ];

    // Only pass solutions-dir if it exists (bundled app)
    if solutions_dir.exists() {
        args.push("--solutions-dir".to_string());
        args.push(solutions_dir.to_string_lossy().to_string());
    }

    let sidecar = handle
        .shell()
        .sidecar("provisioning-station")
        .expect("Failed to create sidecar command")
        .args(&args);

    let (mut rx, _child) = sidecar.spawn()?;

    SIDECAR_STARTED.store(true, Ordering::SeqCst);
    log::info!("Sidecar spawned successfully");

    // Handle sidecar output in background
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    log::info!("[sidecar] {}", line_str);
                }
                CommandEvent::Stderr(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    log::warn!("[sidecar] {}", line_str);
                }
                CommandEvent::Terminated(status) => {
                    log::info!("Sidecar terminated with status: {:?}", status);
                    SIDECAR_STARTED.store(false, Ordering::SeqCst);
                    break;
                }
                CommandEvent::Error(err) => {
                    log::error!("Sidecar error: {}", err);
                }
                _ => {}
            }
        }
    });

    // Wait for backend to be ready
    let health_url = format!("http://127.0.0.1:{}/api/health", port);
    let client = reqwest::Client::new();

    for attempt in 1..=30 {
        match client.get(&health_url).send().await {
            Ok(response) if response.status().is_success() => {
                log::info!("Backend is ready (attempt {})", attempt);
                return Ok(());
            }
            _ => {
                if attempt % 5 == 0 {
                    log::info!("Waiting for backend to start... (attempt {})", attempt);
                }
                tokio::time::sleep(std::time::Duration::from_millis(200)).await;
            }
        }
    }

    Err("Backend failed to start within timeout".into())
}
