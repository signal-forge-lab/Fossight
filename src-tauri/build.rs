use image::{DynamicImage, ImageFormat, Rgba, RgbaImage};
use std::{fs, io::Cursor, path::PathBuf};

fn build_ico(png: &[u8]) -> Vec<u8> {
    let mut ico = Vec::with_capacity(22 + png.len());
    ico.extend_from_slice(&[0, 0, 1, 0, 1, 0]);
    ico.extend_from_slice(&[0, 0, 0, 0, 1, 0, 32, 0]);
    ico.extend_from_slice(&(png.len() as u32).to_le_bytes());
    ico.extend_from_slice(&22u32.to_le_bytes());
    ico.extend_from_slice(png);
    ico
}

fn ensure_icon() {
    let manifest = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").expect("manifest dir"));
    let icon_dir = manifest.join("icons");
    fs::create_dir_all(&icon_dir).expect("create icon directory");

    let mut image = RgbaImage::from_pixel(256, 256, Rgba([0, 0, 0, 0]));
    let cx = 128.0_f32;
    let cy = 128.0_f32;
    for y in 0..256 {
        for x in 0..256 {
            let dx = x as f32 - cx;
            let dy = y as f32 - cy;
            let r = (dx * dx + dy * dy).sqrt();
            let pixel = if r <= 102.0 {
                Some(Rgba([79, 99, 224, 255]))
            } else {
                None
            };
            if let Some(pixel) = pixel {
                image.put_pixel(x, y, pixel);
            }
            if (48.0..=66.0).contains(&r) {
                image.put_pixel(x, y, Rgba([237, 240, 246, 255]));
            }
            if r <= 30.0 {
                image.put_pixel(x, y, Rgba([35, 40, 57, 255]));
            }
        }
    }

    let mut cursor = Cursor::new(Vec::new());
    DynamicImage::ImageRgba8(image)
        .write_to(&mut cursor, ImageFormat::Png)
        .expect("encode icon PNG");
    let png = cursor.into_inner();
    fs::write(icon_dir.join("icon.png"), &png).expect("write PNG icon");
    fs::write(icon_dir.join("icon.ico"), build_ico(&png)).expect("write ICO icon");
}

fn main() {
    ensure_icon();
    tauri_build::build();
}
