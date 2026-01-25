// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;

/// Global flag to track sidecar state
static SIDECAR_STARTED: AtomicBool = AtomicBool::new(false);

/// Get an available port for the backend server
fn get_available_port() -> u16 {
    portpicker::pick_unused_port().expect("No available ports")
}

/// Main entry point
fn main() {
    // Initialize logger for debug builds
    #[cfg(debug_assertions)]
    env_logger::init();

    let backend_port = get_available_port();
    log::info!("Selected backend port: {}", backend_port);

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
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
            let main_window = app.get_webview_window("main")
                .expect("Main window not found");

            let script = format!(
                "window.__TAURI__ = window.__TAURI__ || {{}}; window.__BACKEND_PORT__ = {};",
                backend_port
            );

            // Execute after DOM ready
            let window_clone = main_window.clone();
            tauri::async_runtime::spawn(async move {
                // Give the frontend time to load
                tokio::time::sleep(std::time::Duration::from_millis(500)).await;
                if let Err(e) = window_clone.eval(&script) {
                    log::error!("Failed to inject backend port: {}", e);
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                log::info!("Window close requested, shutting down sidecar...");
                // Sidecar will be killed automatically when the app exits
                // because we're using spawn() which is tied to the process lifecycle
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

    let sidecar = handle
        .shell()
        .sidecar("provisioning-station")
        .expect("Failed to create sidecar command")
        .args(["--port", &port.to_string(), "--host", "127.0.0.1"]);

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
