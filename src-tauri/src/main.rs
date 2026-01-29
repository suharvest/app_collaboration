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

/// Global flag to track if shutdown is in progress (prevent re-entry)
static SHUTDOWN_IN_PROGRESS: AtomicBool = AtomicBool::new(false);

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
        // First kill child processes (PyInstaller spawns a child)
        let _ = Command::new("pkill")
            .args(["-15", "-P", &pid.to_string()])
            .output();

        // Then send SIGTERM to the main process
        Command::new("kill")
            .args(["-15", &pid.to_string()])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
    #[cfg(windows)]
    {
        use std::process::Command;
        // taskkill /T terminates child processes as well
        Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/T"])
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
        // First force kill child processes
        let _ = Command::new("pkill")
            .args(["-9", "-P", &pid.to_string()])
            .output();

        // Then force kill the main process
        Command::new("kill")
            .args(["-9", &pid.to_string()])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
    #[cfg(windows)]
    {
        use std::process::Command;
        // taskkill with /F /T forces termination including child processes
        Command::new("taskkill")
            .args(["/F", "/PID", &pid.to_string(), "/T"])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
}

/// Get child process PIDs (cross-platform)
#[allow(unused_variables)]
fn get_child_pids(parent_pid: u32) -> Vec<u32> {
    #[cfg(unix)]
    {
        use std::process::Command;
        // Use pgrep -P to get child PIDs
        if let Ok(output) = Command::new("pgrep")
            .args(["-P", &parent_pid.to_string()])
            .output()
        {
            let stdout = String::from_utf8_lossy(&output.stdout);
            return stdout
                .lines()
                .filter_map(|line| line.trim().parse::<u32>().ok())
                .collect();
        }
        vec![]
    }
    #[cfg(windows)]
    {
        // On Windows, we rely on taskkill /T to handle the tree
        vec![]
    }
}

/// Kill child processes of a given PID (cross-platform)
fn kill_child_processes(parent_pid: u32) {
    #[cfg(unix)]
    {
        use std::process::Command;
        // Use pkill -P to kill all children of the parent process
        let _ = Command::new("pkill")
            .args(["-9", "-P", &parent_pid.to_string()])
            .output();
    }
    #[cfg(windows)]
    {
        use std::process::Command;
        // On Windows, taskkill /T already handles child processes
        // This is a fallback using wmic
        let _ = Command::new("wmic")
            .args([
                "process",
                "where",
                &format!("ParentProcessId={}", parent_pid),
                "delete",
            ])
            .output();
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
        println!("No sidecar PID to kill");
        SIDECAR_STARTED.store(false, Ordering::SeqCst);
        // Fallback: kill by name in case PID wasn't recorded
        force_kill_by_name();
        return true;
    }

    // IMPORTANT: Get child PIDs BEFORE killing parent, as children become orphans after
    let child_pids = get_child_pids(pid);
    println!("Sidecar PID: {}, child PIDs: {:?}", pid, child_pids);

    // Check if process is still running
    if !is_process_running(pid) {
        println!("Sidecar process {} already exited", pid);
        // Kill any remaining children
        for child_pid in &child_pids {
            force_kill_process(*child_pid);
        }
        SIDECAR_STARTED.store(false, Ordering::SeqCst);
        return true;
    }

    println!("Sending graceful termination signal to sidecar (PID: {})", pid);

    // First, try to use the Tauri child handle if available
    if let Ok(mut guard) = SIDECAR_CHILD.lock() {
        if let Some(child) = guard.take() {
            println!("Using Tauri child handle for graceful shutdown");
            let _ = child.kill();
        }
    }

    // Also send system-level termination signal
    send_terminate_signal(pid);

    // Kill children explicitly (they might become orphans)
    for child_pid in &child_pids {
        send_terminate_signal(*child_pid);
    }

    // Wait for graceful shutdown with timeout
    let check_interval = Duration::from_millis(100);
    let max_checks = (GRACEFUL_SHUTDOWN_TIMEOUT_SECS * 1000 / 100) as u32;

    for i in 0..max_checks {
        std::thread::sleep(check_interval);

        // Check if both parent and all children have exited
        let parent_running = is_process_running(pid);
        let children_running: Vec<_> = child_pids.iter()
            .filter(|&&p| is_process_running(p))
            .collect();

        if !parent_running && children_running.is_empty() {
            println!("Sidecar and children exited gracefully after {}ms", (i + 1) * 100);
            SIDECAR_STARTED.store(false, Ordering::SeqCst);
            return true;
        }

        if i > 0 && i % 10 == 0 {
            println!("Waiting for sidecar to exit... ({}ms elapsed)", (i + 1) * 100);
        }
    }

    // Graceful shutdown timed out, force kill
    println!(
        "Sidecar did not exit gracefully within {}s, force killing",
        GRACEFUL_SHUTDOWN_TIMEOUT_SECS
    );

    // Force kill children first (using saved PIDs, not pkill -P which won't work for orphans)
    for child_pid in &child_pids {
        println!("Force killing child PID: {}", child_pid);
        force_kill_process(*child_pid);
    }
    // Then force kill the parent
    force_kill_process(pid);

    // Wait a bit more for force kill to take effect
    for _ in 0..10 {
        std::thread::sleep(Duration::from_millis(100));
        let any_running = is_process_running(pid) ||
            child_pids.iter().any(|&p| is_process_running(p));
        if !any_running {
            println!("Sidecar force killed successfully");
            SIDECAR_STARTED.store(false, Ordering::SeqCst);
            return false;
        }
    }

    // Last resort: kill by name
    println!("Force kill by PID failed, trying by process name");
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
        .build(tauri::generate_context!())
        .expect("Error while building Tauri application")
        .run(|app_handle, event| {
            match event {
                tauri::RunEvent::WindowEvent {
                    event: tauri::WindowEvent::CloseRequested { api, .. },
                    ..
                } => {
                    // Check if shutdown is already in progress
                    if SHUTDOWN_IN_PROGRESS.swap(true, Ordering::SeqCst) {
                        return; // Already shutting down
                    }

                    // Prevent default close to ensure cleanup completes
                    api.prevent_close();

                    // Synchronous cleanup - blocks UI but ensures completion
                    println!("Window close requested, initiating graceful shutdown...");
                    shutdown_sidecar_graceful();
                    println!("Shutdown complete, exiting...");
                    app_handle.exit(0);
                }
                tauri::RunEvent::ExitRequested { api, .. } => {
                    // If shutdown already in progress (from CloseRequested), let it exit
                    if SHUTDOWN_IN_PROGRESS.load(Ordering::SeqCst) {
                        // Don't prevent exit - cleanup already done
                        return;
                    }

                    // Cmd+Q or Dock quit - prevent immediate exit to allow cleanup
                    SHUTDOWN_IN_PROGRESS.store(true, Ordering::SeqCst);
                    api.prevent_exit();

                    // Synchronous cleanup
                    println!("Exit requested (Cmd+Q), initiating graceful shutdown...");
                    shutdown_sidecar_graceful();
                    println!("Shutdown complete, exiting...");
                    app_handle.exit(0);
                }
                tauri::RunEvent::Exit => {
                    // Final cleanup before exit (fallback)
                    println!("Application exiting, final cleanup...");
                    let pid = SIDECAR_PID.load(Ordering::SeqCst);
                    if pid != 0 {
                        println!("Sidecar still running at exit, force killing PID: {}", pid);
                        kill_child_processes(pid);
                        force_kill_process(pid);
                    }
                }
                _ => {}
            }
        });
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
