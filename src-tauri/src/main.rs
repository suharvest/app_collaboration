// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::atomic::{AtomicBool, AtomicU16, AtomicU32, Ordering};
use std::sync::Mutex;
use std::time::Duration;
use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};

/// Global flag to track sidecar state
static SIDECAR_STARTED: AtomicBool = AtomicBool::new(false);

/// Global backend port - set once at startup
static BACKEND_PORT: AtomicU16 = AtomicU16::new(0);

/// Global sidecar process ID for cleanup on exit
static SIDECAR_PID: AtomicU32 = AtomicU32::new(0);

/// Global sidecar child handle for graceful shutdown
static SIDECAR_CHILD: Mutex<Option<CommandChild>> = Mutex::new(None);

/// Graceful shutdown timeout in seconds
const GRACEFUL_SHUTDOWN_TIMEOUT_SECS: u64 = 5;

/// Get an available port for the backend server
fn get_available_port() -> u16 {
    portpicker::pick_unused_port().expect("No available ports")
}

/// Check if a process is still running (cross-platform)
fn is_process_running(pid: u32) -> bool {
    #[cfg(unix)]
    {
        // On Unix, kill with signal 0 checks if process exists
        use std::process::Command;
        Command::new("kill")
            .args(["-0", &pid.to_string()])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
    #[cfg(windows)]
    {
        use std::process::Command;
        // Use tasklist to check if process exists
        Command::new("tasklist")
            .args(["/FI", &format!("PID eq {}", pid), "/NH"])
            .output()
            .map(|o| {
                let output = String::from_utf8_lossy(&o.stdout);
                output.contains(&pid.to_string())
            })
            .unwrap_or(false)
    }
}

/// Send graceful termination signal (cross-platform)
fn send_terminate_signal(pid: u32) -> bool {
    #[cfg(unix)]
    {
        use std::process::Command;
        // SIGTERM (15) for graceful shutdown
        Command::new("kill")
            .args(["-15", &pid.to_string()])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
    #[cfg(windows)]
    {
        use std::process::Command;
        // taskkill without /F sends WM_CLOSE for graceful shutdown
        Command::new("taskkill")
            .args(["/PID", &pid.to_string()])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
}

/// Force kill a process (cross-platform)
fn force_kill_process(pid: u32) -> bool {
    #[cfg(unix)]
    {
        use std::process::Command;
        // SIGKILL (9) for force kill
        Command::new("kill")
            .args(["-9", &pid.to_string()])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
    #[cfg(windows)]
    {
        use std::process::Command;
        // taskkill with /F forces termination
        Command::new("taskkill")
            .args(["/F", "/PID", &pid.to_string()])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
}

/// Force kill by process name as fallback (cross-platform)
fn force_kill_by_name() {
    #[cfg(unix)]
    {
        use std::process::Command;
        let _ = Command::new("pkill")
            .args(["-9", "-f", "provisioning-station"])
            .output();
    }
    #[cfg(windows)]
    {
        use std::process::Command;
        let _ = Command::new("taskkill")
            .args(["/F", "/IM", "provisioning-station.exe"])
            .output();
    }
}

/// Gracefully shutdown the sidecar with timeout
/// Returns true if process exited gracefully, false if force killed
fn shutdown_sidecar_graceful() -> bool {
    let pid = SIDECAR_PID.swap(0, Ordering::SeqCst);

    if pid == 0 {
        log::info!("No sidecar PID to kill");
        SIDECAR_STARTED.store(false, Ordering::SeqCst);
        return true;
    }

    // Check if process is still running
    if !is_process_running(pid) {
        log::info!("Sidecar process {} already exited", pid);
        SIDECAR_STARTED.store(false, Ordering::SeqCst);
        return true;
    }

    log::info!("Sending graceful termination signal to sidecar (PID: {})", pid);

    // First, try to use the Tauri child handle if available
    if let Ok(mut guard) = SIDECAR_CHILD.lock() {
        if let Some(child) = guard.take() {
            log::info!("Using Tauri child handle for graceful shutdown");
            let _ = child.kill();
        }
    }

    // Also send system-level termination signal
    send_terminate_signal(pid);

    // Wait for graceful shutdown with timeout
    let check_interval = Duration::from_millis(100);
    let max_checks = (GRACEFUL_SHUTDOWN_TIMEOUT_SECS * 1000 / 100) as u32;

    for i in 0..max_checks {
        std::thread::sleep(check_interval);

        if !is_process_running(pid) {
            log::info!("Sidecar exited gracefully after {}ms", (i + 1) * 100);
            SIDECAR_STARTED.store(false, Ordering::SeqCst);
            return true;
        }

        if i > 0 && i % 10 == 0 {
            log::info!("Waiting for sidecar to exit... ({}ms elapsed)", (i + 1) * 100);
        }
    }

    // Graceful shutdown timed out, force kill
    log::warn!(
        "Sidecar did not exit gracefully within {}s, force killing",
        GRACEFUL_SHUTDOWN_TIMEOUT_SECS
    );

    force_kill_process(pid);

    // Wait a bit more for force kill to take effect
    for _ in 0..10 {
        std::thread::sleep(Duration::from_millis(100));
        if !is_process_running(pid) {
            log::info!("Sidecar force killed successfully");
            SIDECAR_STARTED.store(false, Ordering::SeqCst);
            return false;
        }
    }

    // Last resort: kill by name
    log::warn!("Force kill by PID failed, trying by process name");
    force_kill_by_name();

    SIDECAR_STARTED.store(false, Ordering::SeqCst);
    false
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
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                // Prevent default close behavior to ensure cleanup completes
                api.prevent_close();

                let app_handle = window.app_handle().clone();

                // Perform graceful shutdown in a separate thread to avoid blocking
                std::thread::spawn(move || {
                    log::info!("Window close requested, initiating graceful shutdown...");

                    // Gracefully shutdown sidecar with timeout
                    let graceful = shutdown_sidecar_graceful();

                    if graceful {
                        log::info!("Graceful shutdown completed successfully");
                    } else {
                        log::warn!("Graceful shutdown failed, process was force killed");
                    }

                    // Now exit the app
                    app_handle.exit(0);
                });
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

    let (mut rx, child) = sidecar.spawn()?;

    // Store PID for cleanup on exit
    let pid = child.pid();
    SIDECAR_PID.store(pid, Ordering::SeqCst);
    log::info!("Sidecar spawned with PID: {}", pid);

    // Store child handle for graceful shutdown
    if let Ok(mut guard) = SIDECAR_CHILD.lock() {
        *guard = Some(child);
    }

    SIDECAR_STARTED.store(true, Ordering::SeqCst);

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
                    SIDECAR_PID.store(0, Ordering::SeqCst);
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
