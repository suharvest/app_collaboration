// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::atomic::{AtomicBool, AtomicU16, AtomicU32, Ordering};
use std::sync::Mutex;
use std::time::Duration;
use tauri::{Manager, Emitter, WebviewUrl, WebviewWindowBuilder};
use tauri::webview::DownloadEvent;
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

/// Maximum file size accepted by save_file_dialog (50 MiB)
const MAX_SAVE_FILE_BYTES: usize = 50 * 1024 * 1024;
const MAX_SAVE_FILE_BASE64_LEN: usize = (MAX_SAVE_FILE_BYTES * 4 / 3) + 16;

/// Sanitize download filename to avoid path traversal and invalid characters.
fn sanitize_download_filename(raw: &str) -> String {
    let fallback = "download";
    let normalized = raw.replace('\\', "/");
    let base = normalized.rsplit('/').next().unwrap_or("").trim();

    if base.is_empty() || base == "." || base == ".." {
        return fallback.to_string();
    }

    let mut cleaned: String = base
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || matches!(c, '.' | '-' | '_' | '(' | ')' | ' ' | '%') {
                c
            } else {
                '_'
            }
        })
        .collect();

    cleaned = cleaned.trim_matches('.').trim().to_string();
    if cleaned.is_empty() || cleaned == "." || cleaned == ".." {
        return fallback.to_string();
    }

    if cleaned.len() > 120 {
        cleaned.truncate(120);
    }

    cleaned
}

/// Check whether a URL target should be considered internal to the app.
fn is_internal_navigation_target(scheme: &str, host: Option<&str>) -> bool {
    matches!(
        (scheme, host),
        ("tauri", Some("localhost"))
            | ("http" | "https", Some("tauri.localhost"))
            | ("http" | "https", Some("localhost" | "127.0.0.1"))
    )
}

/// Return true when a URL should be opened in the external browser.
fn should_open_external_browser(scheme: &str, host: Option<&str>) -> bool {
    matches!(scheme, "http" | "https") && !is_internal_navigation_target(scheme, host)
}

/// Windows: CREATE_NO_WINDOW flag to hide console windows
#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

/// Create a Command with hidden window on Windows
#[cfg(windows)]
fn hidden_command(program: &str) -> std::process::Command {
    use std::os::windows::process::CommandExt;
    let mut cmd = std::process::Command::new(program);
    cmd.creation_flags(CREATE_NO_WINDOW);
    cmd
}

/// Get an available port for the backend server
/// Uses TcpListener to verify the port is actually available
fn get_available_port() -> u16 {
    use std::net::TcpListener;

    // Try portpicker first, then verify with actual bind
    for attempt in 1..=10 {
        if let Some(port) = portpicker::pick_unused_port() {
            // Verify we can actually bind to this port
            match TcpListener::bind(format!("127.0.0.1:{}", port)) {
                Ok(listener) => {
                    // Port is available, drop the listener to release it
                    drop(listener);
                    log::info!("Found available port {} (attempt {})", port, attempt);
                    return port;
                }
                Err(e) => {
                    log::warn!(
                        "Port {} suggested by portpicker but bind failed: {} (attempt {})",
                        port, e, attempt
                    );
                    continue;
                }
            }
        }
    }

    // Fallback: let the OS assign a port
    log::warn!("portpicker failed, letting OS assign port");
    let listener = TcpListener::bind("127.0.0.1:0").expect("Failed to bind to any port");
    let port = listener.local_addr().unwrap().port();
    drop(listener);
    log::info!("OS assigned port {}", port);
    port
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
        // Use tasklist to check if process exists
        hidden_command("tasklist")
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
        // taskkill /T terminates child processes as well
        hidden_command("taskkill")
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
        // taskkill with /F /T forces termination including child processes
        hidden_command("taskkill")
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
        // On Windows, taskkill /T already handles child processes
        // This is a fallback using wmic
        let _ = hidden_command("wmic")
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
        let _ = hidden_command("taskkill")
            .args(["/F", "/IM", "provisioning-station.exe"])
            .output();
    }
}

/// Cleanup any leftover provisioning-station processes from previous runs (cross-platform)
/// Returns the number of processes killed
fn cleanup_leftover_processes() -> u32 {
    let mut killed_count = 0;

    #[cfg(unix)]
    {
        use std::process::Command;

        // Find all provisioning-station processes (exclude grep itself)
        let output = Command::new("pgrep")
            .args(["-f", "provisioning-station"])
            .output();

        if let Ok(output) = output {
            let pids_str = String::from_utf8_lossy(&output.stdout);
            for line in pids_str.lines() {
                if let Ok(pid) = line.trim().parse::<u32>() {
                    println!("Found leftover provisioning-station process: PID {}", pid);

                    // Try graceful termination first
                    let _ = Command::new("kill")
                        .args(["-15", &pid.to_string()])
                        .output();

                    // Wait briefly
                    std::thread::sleep(Duration::from_millis(500));

                    // Check if still running, force kill if needed
                    if is_process_running(pid) {
                        println!("  Force killing PID {}...", pid);
                        force_kill_process(pid);
                    } else {
                        println!("  Terminated gracefully");
                    }
                    killed_count += 1;
                }
            }
        }
    }

    #[cfg(windows)]
    {
        // Use wmic to find provisioning-station processes
        let output = hidden_command("wmic")
            .args([
                "process",
                "where",
                "name like '%provisioning-station%'",
                "get",
                "processid",
            ])
            .output();

        if let Ok(output) = output {
            let pids_str = String::from_utf8_lossy(&output.stdout);
            for line in pids_str.lines().skip(1) {
                // Skip header
                if let Ok(pid) = line.trim().parse::<u32>() {
                    println!("Found leftover provisioning-station process: PID {}", pid);

                    // On Windows, just force terminate
                    let _ = hidden_command("taskkill")
                        .args(["/F", "/PID", &pid.to_string(), "/T"])
                        .output();

                    killed_count += 1;
                    println!("  Terminated");
                }
            }
        }
    }

    if killed_count > 0 {
        println!(
            "Cleaned up {} leftover provisioning-station process(es)",
            killed_count
        );
        // Give the system time to release resources
        std::thread::sleep(Duration::from_millis(500));
    }

    killed_count
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

/// Tauri command: show native save dialog and write file data
#[tauri::command]
async fn save_file_dialog(filename: String, data: String) -> Result<String, String> {
    if data.len() > MAX_SAVE_FILE_BASE64_LEN {
        return Err(format!(
            "file too large: max {} MB",
            MAX_SAVE_FILE_BYTES / 1024 / 1024
        ));
    }

    use base64::Engine;
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(&data)
        .map_err(|e| format!("base64 decode error: {}", e))?;

    if bytes.len() > MAX_SAVE_FILE_BYTES {
        return Err(format!(
            "file too large: max {} MB",
            MAX_SAVE_FILE_BYTES / 1024 / 1024
        ));
    }

    let mut dialog = rfd::AsyncFileDialog::new().set_file_name(&filename);
    if let Some(dl) = dirs::download_dir() {
        dialog = dialog.set_directory(dl);
    }

    if let Some(handle) = dialog.save_file().await {
        let path = handle.path().to_path_buf();
        std::fs::write(&path, &bytes).map_err(|e| format!("write error: {}", e))?;
        Ok(path.to_string_lossy().to_string())
    } else {
        Err("cancelled".to_string())
    }
}

/// Main entry point
fn main() {
    // Initialize logger (for both debug and release builds)
    // In release: RUST_LOG=info ./app to see logs
    let _ = env_logger::try_init();

    // IMPORTANT: Clean up any leftover processes BEFORE selecting port
    // This ensures residual sidecar processes don't hold ports
    let cleaned = cleanup_leftover_processes();
    if cleaned > 0 {
        println!("Pre-startup cleanup: removed {} leftover process(es)", cleaned);
    }

    let backend_port = get_available_port();
    BACKEND_PORT.store(backend_port, Ordering::SeqCst);
    println!("Selected backend port: {}", backend_port);
    log::info!("Selected backend port: {}", backend_port);

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .invoke_handler(tauri::generate_handler![get_backend_port, save_file_dialog])
        .setup(move |app| {
            let handle = app.handle().clone();
            let port = backend_port;

            // Spawn sidecar in background, then navigate to backend-served frontend.
            // Window starts with bundled frontend (splash screen) via WebviewUrl::default().
            // Once backend is ready, we navigate to http://127.0.0.1:{port}/ which serves
            // the same frontend from the backend. This avoids:
            //   - White screen on macOS first launch (splash shows immediately)
            //   - Custom protocol issues on Windows (final page served via normal HTTP)
            tauri::async_runtime::spawn(async move {
                if let Err(e) = start_sidecar(&handle, port).await {
                    log::error!("Failed to start sidecar: {}", e);
                    if let Some(win) = handle.get_webview_window("main") {
                        let _ = win.eval("document.getElementById('splash-status').textContent='Failed to start backend. Please restart.'");
                    }
                    return;
                }
                log::info!("Sidecar ready on port {}", port);

                // Navigate to backend-served frontend
                if let Some(win) = handle.get_webview_window("main") {
                    let backend_url = format!("http://127.0.0.1:{}", port);
                    log::info!("Navigating to backend: {}", backend_url);
                    let _ = win.navigate(backend_url.parse().unwrap());
                }
            });

            // Create window with bundled frontend (splash screen while backend starts)
            let nav_handle = app.handle().clone();
            let download_handle = app.handle().clone();

            let _main_window = WebviewWindowBuilder::new(app, "main", WebviewUrl::default())
                .title("SenseCraft Solution")
                .inner_size(1280.0, 800.0)
                .min_inner_size(800.0, 600.0)
                .resizable(true)
                .center()
                // Handle file downloads (e.g., Excel files)
                .on_download(move |_webview, event| {
                    match event {
                        DownloadEvent::Requested { url, destination } => {
                            log::info!("Download requested: {}", url);
                            if let Some(downloads_dir) = dirs::download_dir() {
                                let url_str = url.as_str();
                                // For blob URLs, extract filename from fragment (#filename)
                                // For regular URLs, extract from path
                                let raw_filename = if url_str.starts_with("blob:") {
                                    url_str.split('#').nth(1)
                                        .map(|f| f.replace("%20", " ").replace("%28", "(").replace("%29", ")"))
                                        .unwrap_or_else(|| "download".to_string())
                                } else {
                                    url_str.split('/').last()
                                        .and_then(|s| s.split('?').next())
                                        .unwrap_or("download")
                                        .to_string()
                                };
                                let filename = sanitize_download_filename(&raw_filename);
                                let dest_path = downloads_dir.join(&filename);
                                *destination = dest_path.clone();
                                log::info!("Download destination: {:?}", dest_path);
                            }
                            true // Allow the download
                        }
                        DownloadEvent::Finished { url, path, success } => {
                            log::info!("Download finished: {} (success: {})", url, success);
                            if success {
                                if let Some(path) = path {
                                    // Notify frontend about successful download
                                    if let Some(win) = download_handle.get_webview_window("main") {
                                        let _ = win.emit("download-complete", path.to_string_lossy().to_string());
                                    }
                                }
                            }
                            true
                        }
                        _ => true
                    }
                })
                // Handle navigation - open external links in default browser
                .on_navigation(move |url| {
                    let url_str = url.as_str();
                    log::info!("Navigation: {}", url_str);

                    // Check if this is an external link
                    // Internal origins:
                    //   macOS/Linux: tauri://localhost/
                    //   Windows:     http://tauri.localhost/ (Tauri v2 default)
                    //   Backend:     http://127.0.0.1:{port}/
                    // Use parsed scheme/host matching to avoid prefix bypasses like
                    // http://localhost.evil.com.
                    let scheme = url.scheme();
                    let host = url.host_str();
                    let is_external = should_open_external_browser(scheme, host);

                    if is_external {
                        log::info!("Opening external URL in browser: {}", url_str);
                        // Open in default browser
                        let shell = nav_handle.shell();
                        let _ = shell.open(url_str, None);
                        false // Prevent navigation in webview
                    } else {
                        true // Allow internal navigation
                    }
                })
                .build()
                .expect("Failed to create main window");

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

/// Get the sidecar cache directory for PyInstaller onedir extraction
/// Returns a path outside the .app bundle to avoid PyInstaller's bundle detection
fn get_sidecar_cache_dir(handle: &tauri::AppHandle) -> std::path::PathBuf {
    // Use app data directory for consistent location
    let app_data = handle.path().app_data_dir()
        .expect("Failed to get app data directory");
    app_data.join("sidecar")
}

/// Setup sidecar bundle for PyInstaller onedir mode
/// Extracts the sidecar executable + _internal to a cache directory outside the .app bundle
/// This avoids PyInstaller's macOS .app bundle detection which causes path issues
/// Returns the path to the extracted sidecar executable
fn setup_sidecar_bundle(handle: &tauri::AppHandle) -> Result<std::path::PathBuf, Box<dyn std::error::Error>> {
    let resource_path = handle.path().resource_dir()
        .expect("Failed to get resource directory");

    // _internal is bundled via binaries/_internal/**/*
    let internal_src = resource_path.join("binaries").join("_internal");

    // Check if we're in bundled mode (have _internal in resources)
    if !internal_src.exists() {
        // Development mode - sidecar runs from src-tauri/binaries/ directly
        log::info!("_internal not found in resources (development mode)");
        // Return None to indicate we should use normal sidecar path
        return Err("Development mode - use normal sidecar".into());
    }

    // Get cache directory
    let cache_dir = get_sidecar_cache_dir(handle);
    let extracted_exe = cache_dir.join(get_sidecar_exe_name());
    let extracted_internal = cache_dir.join("_internal");

    // Find the source sidecar executable
    let app_exe = std::env::current_exe()?;
    let macos_dir = app_exe.parent().unwrap();
    #[cfg(windows)]
    let sidecar_name = "provisioning-station.exe";
    #[cfg(not(windows))]
    let sidecar_name = "provisioning-station";
    let sidecar_src = macos_dir.join(sidecar_name);

    // Check if already extracted and version matches
    // Compare file sizes to detect version mismatch (size change indicates new build)
    let needs_extraction = if extracted_exe.exists() && extracted_internal.exists() {
        // Check if source and extracted exe have same size (simple version check)
        let src_size = std::fs::metadata(&sidecar_src).map(|m| m.len()).unwrap_or(0);
        let dst_size = std::fs::metadata(&extracted_exe).map(|m| m.len()).unwrap_or(0);
        if src_size != dst_size {
            log::info!("Sidecar version mismatch detected (size: {} vs {}), re-extracting", src_size, dst_size);
            true
        } else {
            log::info!("Sidecar already extracted at {:?} (version matches)", cache_dir);
            false
        }
    } else {
        true
    };

    if !needs_extraction {
        return Ok(extracted_exe);
    }

    // Verify source sidecar exists
    if !sidecar_src.exists() {
        return Err(format!("Sidecar executable not found at {:?}", sidecar_src).into());
    }

    log::info!("Extracting sidecar bundle to {:?}", cache_dir);
    log::info!("Found sidecar at: {:?}", sidecar_src);

    // Create cache directory
    std::fs::create_dir_all(&cache_dir)?;

    // Copy sidecar executable
    log::info!("Copying sidecar executable to: {:?}", extracted_exe);
    std::fs::copy(&sidecar_src, &extracted_exe)?;

    // Set executable permission on Unix
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = std::fs::metadata(&extracted_exe)?.permissions();
        perms.set_mode(0o755);
        std::fs::set_permissions(&extracted_exe, perms)?;
    }

    // Copy _internal directory
    if extracted_internal.exists() {
        log::info!("Removing old _internal directory");
        std::fs::remove_dir_all(&extracted_internal)?;
    }
    log::info!("Copying _internal directory to: {:?}", extracted_internal);
    copy_dir_recursive(&internal_src, &extracted_internal)?;

    // Set executable permissions on dynamic libraries (Unix)
    #[cfg(unix)]
    {
        set_dylib_permissions(&extracted_internal)?;
    }

    log::info!("Sidecar bundle extracted successfully");
    Ok(extracted_exe)
}

/// Get the sidecar executable name (platform-specific)
fn get_sidecar_exe_name() -> &'static str {
    #[cfg(windows)]
    { "provisioning-station.exe" }
    #[cfg(not(windows))]
    { "provisioning-station" }
}

/// Set executable permissions on dynamic libraries recursively
#[cfg(unix)]
fn set_dylib_permissions(dir: &std::path::Path) -> std::io::Result<()> {
    use std::os::unix::fs::PermissionsExt;

    for entry in std::fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();

        if path.is_dir() {
            set_dylib_permissions(&path)?;
        } else {
            let name = path.file_name()
                .map(|n| n.to_string_lossy().to_string())
                .unwrap_or_default();

            // Set executable for .so, .dylib files
            if name.ends_with(".so") || name.contains(".so.") || name.ends_with(".dylib") {
                let mut perms = std::fs::metadata(&path)?.permissions();
                perms.set_mode(0o755);
                std::fs::set_permissions(&path, perms)?;
            }
        }
    }
    Ok(())
}

/// Recursively copy a directory
fn copy_dir_recursive(src: &std::path::Path, dst: &std::path::Path) -> std::io::Result<()> {
    std::fs::create_dir_all(dst)?;
    for entry in std::fs::read_dir(src)? {
        let entry = entry?;
        let ty = entry.file_type()?;
        let src_path = entry.path();
        let dst_path = dst.join(entry.file_name());

        if ty.is_dir() {
            copy_dir_recursive(&src_path, &dst_path)?;
        } else {
            std::fs::copy(&src_path, &dst_path)?;
        }
    }
    Ok(())
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

    // Secondary cleanup check (primary is in main() before port selection)
    // This catches any processes that may have started between port selection and here
    let cleaned = cleanup_leftover_processes();
    if cleaned > 0 {
        log::warn!("Late cleanup: removed {} process(es) spawned after initial cleanup", cleaned);
    }

    println!("Starting provisioning-station sidecar on port {}", port);
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

    // Pass frontend dist directory to backend for serving static files
    let frontend_dir = resource_path.join("_up_").join("frontend").join("dist");
    if frontend_dir.exists() {
        args.push("--frontend-dir".to_string());
        args.push(frontend_dir.to_string_lossy().to_string());
    }

    // Try to setup and use extracted sidecar (PyInstaller onedir mode)
    // This extracts sidecar + _internal to a cache directory outside the .app bundle
    // which avoids PyInstaller's macOS bundle detection issues
    match setup_sidecar_bundle(handle) {
        Ok(extracted_exe) => {
            // Use extracted sidecar directly via Command
            log::info!("Using extracted sidecar at: {:?}", extracted_exe);

            use std::process::Stdio;

            let mut cmd = std::process::Command::new(&extracted_exe);
            cmd.args(&args)
                .stdout(Stdio::piped())
                .stderr(Stdio::piped());

            // Hide console window on Windows
            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                cmd.creation_flags(CREATE_NO_WINDOW);
            }

            let mut process = cmd.spawn()?;
            let pid = process.id();

            // Store PID for cleanup on exit
            SIDECAR_PID.store(pid, Ordering::SeqCst);
            log::info!("Sidecar spawned with PID: {}", pid);
            SIDECAR_STARTED.store(true, Ordering::SeqCst);

            // Spawn threads to read stdout/stderr
            let stdout = process.stdout.take();
            let stderr = process.stderr.take();

            if let Some(stdout) = stdout {
                std::thread::spawn(move || {
                    use std::io::BufRead;
                    let reader = std::io::BufReader::new(stdout);
                    for line in reader.lines() {
                        if let Ok(line) = line {
                            log::info!("[sidecar] {}", line);
                        }
                    }
                });
            }

            if let Some(stderr) = stderr {
                std::thread::spawn(move || {
                    use std::io::BufRead;
                    let reader = std::io::BufReader::new(stderr);
                    for line in reader.lines() {
                        if let Ok(line) = line {
                            log::warn!("[sidecar] {}", line);
                        }
                    }
                });
            }

            // Wait for process to exit in background and update state
            std::thread::spawn(move || {
                let _ = process.wait();
                log::info!("Sidecar process exited");
                SIDECAR_STARTED.store(false, Ordering::SeqCst);
                SIDECAR_PID.store(0, Ordering::SeqCst);
            });
        }
        Err(_) => {
            // Development mode - use Tauri's sidecar mechanism
            log::info!("Using Tauri sidecar (development mode)");

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
        }
    }

    // Wait for backend to be ready
    let health_url = format!("http://127.0.0.1:{}/api/health", port);
    let client = reqwest::Client::new();

    // First cold start (fresh install) can be slow due to:
    //   - Sidecar extraction (~55MB _internal directory)
    //   - PyInstaller first-run module loading
    //   - macOS Gatekeeper scanning new binaries
    // Use generous timeout: 60 attempts × 500ms = 30 seconds
    for attempt in 1..=60 {
        match client.get(&health_url).send().await {
            Ok(response) if response.status().is_success() => {
                log::info!("Backend is ready (attempt {})", attempt);
                return Ok(());
            }
            _ => {
                if attempt % 10 == 0 {
                    log::info!("Waiting for backend to start... (attempt {}/60)", attempt);
                }
                tokio::time::sleep(std::time::Duration::from_millis(500)).await;
            }
        }
    }

    // Backend never became healthy: clean up the spawned sidecar to avoid
    // leaving an orphan process occupying the selected port.
    log::error!("Backend health check timed out, cleaning up sidecar");
    if SIDECAR_PID.load(Ordering::SeqCst) != 0 {
        shutdown_sidecar_graceful();
    }
    SIDECAR_STARTED.store(false, Ordering::SeqCst);
    if let Ok(mut guard) = SIDECAR_CHILD.lock() {
        *guard = None;
    }

    Err("Backend failed to start within timeout".into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sanitize_download_filename_keeps_safe_name() {
        assert_eq!(sanitize_download_filename("report-2026_02(1).csv"), "report-2026_02(1).csv");
    }

    #[test]
    fn sanitize_download_filename_strips_path_segments() {
        assert_eq!(sanitize_download_filename("../../etc/passwd"), "passwd");
        assert_eq!(sanitize_download_filename(r"..\..\evil.txt"), "evil.txt");
    }

    #[test]
    fn sanitize_download_filename_rejects_empty_or_dot_names() {
        assert_eq!(sanitize_download_filename(""), "download");
        assert_eq!(sanitize_download_filename("."), "download");
        assert_eq!(sanitize_download_filename(".."), "download");
        assert_eq!(sanitize_download_filename("   "), "download");
    }

    #[test]
    fn sanitize_download_filename_replaces_unsafe_chars() {
        assert_eq!(sanitize_download_filename("bad*name?.txt"), "bad_name_.txt");
    }

    #[test]
    fn sanitize_download_filename_truncates_long_names() {
        let long_name = format!("{}.txt", "a".repeat(200));
        assert_eq!(sanitize_download_filename(&long_name).len(), 120);
    }

    #[test]
    fn navigation_internal_targets_are_allowed_in_webview() {
        assert!(is_internal_navigation_target("tauri", Some("localhost")));
        assert!(is_internal_navigation_target("http", Some("localhost")));
        assert!(is_internal_navigation_target("https", Some("127.0.0.1")));
        assert!(is_internal_navigation_target("http", Some("tauri.localhost")));
    }

    #[test]
    fn navigation_external_targets_are_detected_correctly() {
        assert!(should_open_external_browser("https", Some("example.com")));
        assert!(should_open_external_browser("http", Some("localhost.evil.com")));
        assert!(should_open_external_browser("http", Some("127.0.0.1.evil.com")));
        assert!(!should_open_external_browser("tauri", Some("localhost")));
        assert!(!should_open_external_browser("file", None));
    }
}
