# Application Icons

Place your application icons in this directory:

## Required Files

| File | Size | Platform |
|------|------|----------|
| `32x32.png` | 32x32 px | All |
| `128x128.png` | 128x128 px | All |
| `128x128@2x.png` | 256x256 px | macOS (Retina) |
| `icon.icns` | Various | macOS |
| `icon.ico` | Various | Windows |

## Generating Icons

You can use the Tauri icon generator:

```bash
# Install tauri-cli if not already installed
cargo install tauri-cli

# Generate all icon variants from a single 1024x1024 PNG
cargo tauri icon path/to/your/1024x1024.png
```

## Placeholder

For development, you can use the default Tauri icons by running:

```bash
cargo tauri icon
```

This will use the Tauri logo as a placeholder.
